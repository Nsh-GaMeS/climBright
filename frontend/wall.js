const API_BASE = ""; // same origin as the Express server

async function apiJson(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || `Request failed (${res.status})`);
  }
  return data;
}

async function getFastApiUrl() {
  const res = await fetch("/config.json", { credentials: "include" });
  const cfg = await res.json().catch(() => ({}));
  return cfg.fastapiUrl || "";
}

async function requireSessionOrRedirect() {
  try {
    const data = await apiJson("/api/auth/me", { method: "GET" });
    const authStatus = document.getElementById("authStatus");
    if (authStatus) authStatus.textContent = `Signed in as ${data.user.email}`;

    const logoutBtn = document.getElementById("logoutBtn");
    if (logoutBtn) {
      logoutBtn.hidden = false;
      logoutBtn.addEventListener("click", async () => {
        await apiJson("/api/auth/logout", { method: "POST" });
        window.location.href = "/login";
      });
    }

    return data.user;
  } catch {
    window.location.href = "/login";
    return null;
  }
}

const wallImage = document.getElementById("wallImage");
const wallWrapper = document.getElementById("wallImageWrapper");
const holdInfoText = document.getElementById("holdInfoText");

let currentHolds = [];
let currentCoach = null;

function setInfoHtml(html) {
  if (!holdInfoText) return;
  holdInfoText.classList.remove("placeholder");
  holdInfoText.innerHTML = html;
}

async function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Failed to read file"));
    reader.onload = () => {
      const dataUrl = String(reader.result || "");
      const commaIdx = dataUrl.indexOf(",");
      resolve(commaIdx >= 0 ? dataUrl.slice(commaIdx + 1) : dataUrl);
    };
    reader.readAsDataURL(file);
  });
}

function renderHolds(holds, imgW, imgH) {
  if (!wallWrapper) return;
  document.querySelectorAll(".hold-marker").forEach((m) => m.remove());

  holds.forEach((hold) => {
    const bbox = hold.bbox;
    if (!Array.isArray(bbox) || bbox.length !== 4) return;
    const [x1, y1, x2, y2] = bbox;
    const cx = (x1 + x2) / 2;
    const cy = (y1 + y2) / 2;

    const marker = document.createElement("div");
    marker.className = "hold-marker";
    marker.style.left = `${(cx / imgW) * 100}%`;
    marker.style.top = `${(cy / imgH) * 100}%`;

    marker.addEventListener("click", () => {
      selectHold(hold);
    });

    wallWrapper.appendChild(marker);
  });
}

function selectHold(hold) {
  const conf = typeof hold.confidence === "number" ? hold.confidence : Number(hold.confidence || 0);
  const pct = conf <= 1 ? conf * 100 : conf;
  const inRouteA = Array.isArray(currentCoach?.routeA)
    ? currentCoach.routeA.some((h) => h.id === hold.id)
    : false;
  const inRouteB = Array.isArray(currentCoach?.routeB)
    ? currentCoach.routeB.some((h) => h.id === hold.id)
    : false;

  setInfoHtml(
    `
    <strong>Type:</strong> ${hold.type || "Unknown"}<br/>
    <strong>Confidence:</strong> ${pct.toFixed(1)}%<br/>
    <strong>In Route A:</strong> ${inRouteA ? "Yes" : "No"}<br/>
    <strong>In Route B:</strong> ${inRouteB ? "Yes" : "No"}
    `
  );
}

function showCoachSummary(coach) {
  if (!coach) return;
  const difficulty = coach.difficulty || "Unknown";
  const notes = coach.notes || "";
  setInfoHtml(
    `
    <strong>Suggested Difficulty:</strong> ${difficulty}<br/>
    <strong>Notes:</strong> ${notes}
    `
  );
}

async function analyzeWall(file) {
  if (!file) return;

  if (holdInfoText) {
    holdInfoText.classList.add("placeholder");
    holdInfoText.textContent = "Analyzing wall…";
  }

  const imageBase64 = await fileToBase64(file);
  const base64Payload = String(imageBase64).includes(",")
    ? String(imageBase64).split(",")[1]
    : String(imageBase64);

  // 1) Frontend calls FastAPI directly to get holds
  const fastapiUrl = await getFastApiUrl();
  if (!fastapiUrl) {
    setInfoHtml('<span style="color:#ff7b72">FASTAPI_URL is not configured.</span>');
    return;
  }

  let aiJson;
  try {
    const res = await fetch(fastapiUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: file.name,
        content_type: file.type || "image/jpeg",
        data: base64Payload,
      }),
    });
    aiJson = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(aiJson?.detail || aiJson?.error || `FastAPI request failed (${res.status})`);
  } catch (err) {
    setInfoHtml(`<span style="color:#ff7b72">AI error: ${err.message}</span>`);
    return;
  }

  currentHolds = Array.isArray(aiJson?.holds) ? aiJson.holds : [];

  // 2) Backend only runs pathfinder.py using the image + holds
  const result = await apiJson("/api/wall/analyze", {
    method: "POST",
    body: JSON.stringify({
      imageBase64,
      filename: file.name,
      holds: currentHolds,
    }),
  });

  currentCoach = result.coach || null;

  // Wait for the image to load so we know dimensions
  wallImage.onload = () => {
    const w = wallImage.naturalWidth || wallImage.width;
    const h = wallImage.naturalHeight || wallImage.height;
    renderHolds(currentHolds, w, h);
    showCoachSummary(currentCoach);
  };
  wallImage.src = URL.createObjectURL(file);
}

function setupWallImageUpload() {
  const box = document.getElementById("wallUpload");
  if (!box || !wallImage) return;
  const input = box.querySelector("input");

  box.addEventListener("click", () => input.click());

  box.addEventListener("dragover", (e) => {
    e.preventDefault();
    box.style.borderColor = "#3ddc97";
  });

  box.addEventListener("dragleave", () => {
    box.style.borderColor = "#30363d";
  });

  box.addEventListener("drop", (e) => {
    e.preventDefault();
    input.files = e.dataTransfer.files;
    box.style.borderColor = "#30363d";

    const file = input.files?.[0];
    if (!file) return;
    analyzeWall(file).catch((err) => {
      setInfoHtml(`<span style="color:#ff7b72">${err.message}</span>`);
    });
  });

  input.addEventListener("change", () => {
    const file = input.files[0];
    if (!file) return;

    analyzeWall(file).catch((err) => {
      setInfoHtml(`<span style="color:#ff7b72">${err.message}</span>`);
    });
  });
}

(async function init() {
  await requireSessionOrRedirect();
  setupWallImageUpload();
})();
