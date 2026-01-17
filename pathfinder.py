import json
import os
from google.genai import client
from google.genai import types
from google.genai.errors import ClientError
from PIL import Image


SYSTEM_PROMPT = """
You are an indoor rock climbing coach.

You are given:

1) A wall photo

2) A JSON list of holds with reliable bounding boxes and reliable hold types.

Rules:

- Treat the JSON as the only reliable source for what holds exist and what type each hold is.

- Do NOT invent holds, hold types, or exact measurements.

- You may use the photo only for high-level context (specific color of route, orientation of hold, size of hold).

- Provide suggestions, not guarantees. Add a short safety disclaimer.

Task:

- Propose the most logical sequence from bottom to top using these holds.

- Explain how to climb each sequence in clear, step-by-step coaching language.

- Give a rough difficulty estimate (Easy / Moderate / Hard) and explain why using only hold types + spacing + route flow.

Output in JSON with keys: routeA, routeB, difficulty, notes which includes each hold that is involved in the sequence followed by the coordinated of that hold normalized to a single point as well as the size of its bounding box to allow the web ui to properly outline the hold.
"""

def load_files(image_path: str, json_path: str):
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Missing image: {image_path}")
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Missing json: {json_path}")

    img = Image.open(image_path).convert("RGB")
    with open(json_path, "r", encoding="utf-8") as f:
        hold_data = json.load(f)
    return img, hold_data


def normalize_holds(hold_data: dict, img_w: int, img_h: int) -> dict:
    """
    Adds center_norm and bbox_wh_norm to each hold using bbox [x1,y1,x2,y2]
    Accepts top-level "holds" or "objects".
    """
    key = "holds" if "holds" in hold_data else ("objects" if "objects" in hold_data else None)
    if key is None:
        raise ValueError('JSON must have top-level key "holds" or "objects".')

    out = {"image_size": {"w": img_w, "h": img_h}, "holds": []}

    for i, h in enumerate(hold_data[key]):
        # Support both "bbox" and "box" field names
        bbox = h.get("bbox") or h.get("box")
        if not bbox or not isinstance(bbox, list) or len(bbox) != 4:
            raise ValueError(f"Hold index {i} missing bbox/box: expected 'bbox':[x1,y1,x2,y2] or 'box':[x1,y1,x2,y2]")

        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        bw = max(1.0, (x2 - x1))
        bh = max(1.0, (y2 - y1))

        hold_id = h.get("id", i)
        hold_type = h.get("type", h.get("class_name", h.get("label", "Unknown")))

        out["holds"].append({
            "id": hold_id,
            "type": hold_type,
            "bbox": [x1, y1, x2, y2],
            "center_norm": [cx / img_w, cy / img_h],
            "bbox_wh_norm": [bw / img_w, bh / img_h],
        })

    return out


def run():
    # Get API key from environment 
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing API key. Set it in PowerShell: $env:GOOGLE_API_KEY='YOUR_KEY' and re-run.")

    genai_client = client.Client(api_key=api_key)

    image_path = "altitude2_classified.jpg"
    json_path = "detections.json"

    img, hold_data = load_files(image_path, json_path)
    img_w, img_h = img.size

    # Normalize + simplify JSON sent to Gemini
    normalized = normalize_holds(hold_data, img_w, img_h)
    holds_json_str = json.dumps(normalized, indent=2)

    print("--- Coach is analyzing the wall... ---")

    try:
        response = genai_client.models.generate_content(
            model="models/gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json"
            ),
            contents=[
                img,
                "Here is the hold data JSON (this is the only reliable hold info):",
                holds_json_str
            ]
        )

        # Print raw response text first (useful if JSON parse fails)
        print("\n--- RAW RESPONSE ---\n")
        print(response.text)

        # Try parsing strict JSON
        print("\n--- PARSED RESPONSE ---\n")
        result = json.loads(response.text)
        print(json.dumps(result, indent=2))
    except ClientError as e:
        msg = str(e)
        if "NOT_FOUND" in msg:
            print("Model not found or unsupported. Listing available models:")
            try:
                models = genai_client.models.list()
                names = [m.name for m in models]
                print(names)
                print("Pick a supported model from the list and update the 'model' parameter.")
            except Exception:
                print("Unable to list models. Please check your API access and permissions.")
        elif "RESOURCE_EXHAUSTED" in msg:
            print("Quota exceeded or no free tier available for the selected model.")
            print("Generating a local fallback suggestion from the provided holds...")
            fallback = build_local_coach(normalized)
            print("\n--- LOCAL COACH (FALLBACK) ---\n")
            print(json.dumps(fallback, indent=2))
        else:
            raise


if __name__ == "__main__":
    run()

def build_local_coach(normalized: dict) -> dict:
    holds = normalized.get("holds", [])
    if not holds:
        return {
            "routeA": [],
            "routeB": [],
            "difficulty": "Easy",
            "notes": "No holds provided; unable to generate a route."
        }

    # Bottom-to-top: sort by vertical center (y), ascending
    seq = sorted(holds, key=lambda h: h["center_norm"][1])
    routeA = [
        {
            "id": h["id"],
            "type": h.get("type", "Unknown"),
            "center_norm": h["center_norm"],
            "bbox_wh_norm": h["bbox_wh_norm"],
        }
        for h in seq
    ]
    # Alternate sequence skipping every other hold as a variation
    routeB = [
        {
            "id": h["id"],
            "type": h.get("type", "Unknown"),
            "center_norm": h["center_norm"],
            "bbox_wh_norm": h["bbox_wh_norm"],
        }
        for h in seq[::2]
    ]

    # Simple difficulty heuristic: harder types and larger spacing increase difficulty
    hard_types = {"Crimp", "Pinch", "Sloper", "Pocket"}
    easy_types = {"Jug", "Volume"}
    type_score = 0
    for h in routeA:
        t = (h.get("type") or "").title()
        if t in hard_types:
            type_score += 1
        elif t in easy_types:
            type_score -= 1

    # Average vertical spacing between consecutive holds
    if len(seq) > 1:
        gaps = [abs(seq[i+1]["center_norm"][1] - seq[i]["center_norm"][1]) for i in range(len(seq)-1)]
        avg_gap = sum(gaps) / len(gaps)
    else:
        avg_gap = 0.0

    if type_score >= 3 or avg_gap >= 0.15:
        difficulty = "Hard"
    elif type_score >= 1 or avg_gap >= 0.08:
        difficulty = "Moderate"
    else:
        difficulty = "Easy"

    notes = (
        "Fallback coach: This route is generated locally from your hold JSON. "
        "It uses hold types and spacing heuristics; verify on the wall and climb safely."
    )

    return {
        "routeA": routeA,
        "routeB": routeB,
        "difficulty": difficulty,
        "notes": notes,
    }
