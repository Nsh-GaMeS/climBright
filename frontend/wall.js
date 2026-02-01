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
const overlaySvg = document.getElementById("wallOverlay");

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

function svgEl(tag, attrs = {}) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, String(v)));
  return el;
}

function clearOverlay() {
  if (!overlaySvg) return;
  while (overlaySvg.firstChild) overlaySvg.removeChild(overlaySvg.firstChild);
}

function bboxToCenter(bbox) {
  const [x1, y1, x2, y2] = bbox;
  const cx = (x1 + x2) / 2;
  const cy = (y1 + y2) / 2;
  const width = Math.max(1, x2 - x1);
  const height = Math.max(1, y2 - y1);
  return { cx, cy, width, height };
}

function resolveRouteSteps(coach, holds) {
  if (!coach) return [];
  const candidates = ["routeA", "route", "routeB"];
  for (const name of candidates) {
    const route = coach[name];
    if (!route) continue;
    if (Array.isArray(route.steps)) return route.steps;
    if (Array.isArray(route)) {
      return route
        .map((step, idx) => {
          if (Array.isArray(step?.bbox)) return step;
          const id = step?.id ?? step?.hold_id ?? step?.holdId;
          if (id === undefined) return null;
          const hold = holds.find((h) => String(h.id) === String(id));
          if (!Array.isArray(hold?.bbox)) return null;
          return { ...step, bbox: hold.bbox, hold_id: hold.id, instruction: step?.instruction || `Step ${idx + 1}` };
        })
        .filter(Boolean);
    }
  }
  return [];
}

function findHoldStepIndex(hold, coach, holds) {
  const steps = resolveRouteSteps(coach, holds);
  for (let i = 0; i < steps.length; i += 1) {
    const step = steps[i];
    const stepId = step?.hold_id ?? step?.id ?? step?.holdId;
    if (stepId !== undefined && hold?.id !== undefined) {
      if (String(stepId) === String(hold.id)) return i;
    }

    if (Array.isArray(step?.bbox) && Array.isArray(hold?.bbox)) {
      const matchesBbox =
        step.bbox.length === hold.bbox.length &&
        step.bbox.every((val, idx) => Math.abs(Number(val) - Number(hold.bbox[idx])) < 1e-3);
      if (matchesBbox) return i;
    }
  }
  return -1;
}

function stepToPoint(step, holds) {
  if (Array.isArray(step.center_norm) && Array.isArray(step.bbox_wh_norm) && wallImage) {
    const W = wallImage.naturalWidth || wallImage.width;
    const H = wallImage.naturalHeight || wallImage.height;
    const cx = step.center_norm[0] * W;
    const cy = step.center_norm[1] * H;
    return { cx, cy };
  }

  if (Array.isArray(step.bbox)) {
    const { cx, cy } = bboxToCenter(step.bbox);
    return { cx, cy };
  }

  const id = step?.hold_id ?? step?.id ?? step?.holdId;
  if (id !== undefined) {
    const hold = holds.find((h) => String(h.id) === String(id));
    if (Array.isArray(hold?.bbox)) {
      const { cx, cy } = bboxToCenter(hold.bbox);
      return { cx, cy };
    }
  }

  return null;
}

function renderOverlay(holds, coach) {
  if (!overlaySvg || !wallImage) return;

  clearOverlay();

  const imgW = wallImage.naturalWidth || wallImage.width;
  const imgH = wallImage.naturalHeight || wallImage.height;
  if (!imgW || !imgH) return;

  overlaySvg.setAttribute("viewBox", `0 0 ${imgW} ${imgH}`);
  overlaySvg.setAttribute("preserveAspectRatio", "none");

  const steps = resolveRouteSteps(coach, holds);
  if (!steps.length) return;

  const points = [];
  const nodes = [];
  steps.forEach((step, idx) => {
    const pt = stepToPoint(step, holds);
    if (!pt) return;
    points.push(pt);
    nodes.push({ pt, idx });
  });

  for (let i = 0; i < points.length - 1; i += 1) {
    const a = points[i];
    const b = points[i + 1];
    const line = svgEl("line", {
      x1: a.cx,
      y1: a.cy,
      x2: b.cx,
      y2: b.cy,
      stroke: "rgba(61,220,151,0.85)",
      "stroke-width": 6,
      "stroke-linecap": "round",
    });
    overlaySvg.appendChild(line);
  }

  nodes.forEach(({ pt, idx }) => {
    const circle = svgEl("circle", {
      cx: pt.cx,
      cy: pt.cy,
      r: 16,
      fill: "rgba(14,17,23,0.8)",
      stroke: "rgba(61,220,151,0.95)",
      "stroke-width": 4,
    });
    overlaySvg.appendChild(circle);

    const text = svgEl("text", {
      x: pt.cx,
      y: pt.cy + 6,
      "text-anchor": "middle",
      "font-size": 16,
      "font-weight": 700,
      fill: "rgba(61,220,151,0.98)",
    });
    text.textContent = String(idx + 1);
    overlaySvg.appendChild(text);
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
  const stepIdx = findHoldStepIndex(hold, currentCoach, currentHolds);
  const overlayNumber = stepIdx >= 0 ? stepIdx + 1 : hold.id;

  setInfoHtml(
    `
    <strong>Hold ID:</strong> ${overlayNumber}${
      stepIdx >= 0 ? ` (detector ID ${hold.id})` : ""
    }<br/>
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

  clearOverlay();

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
    renderOverlay(currentHolds, currentCoach);
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
