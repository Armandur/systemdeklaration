import { apiFetch, showToast, debounce } from "/static/utils.js";

const EMPTY = JSON.parse(document.getElementById("emptyData").textContent);
let state = structuredClone(EMPTY);
let currentId = null;

// ---- path-hjälpare (t.ex. "oppningsbud.0.svar") ----
function getPath(obj, path) {
  return path.split(".").reduce((o, k) => (o == null ? o : o[k]), obj);
}
function setPath(obj, path, val) {
  const ks = path.split(".");
  const last = ks.pop();
  let o = obj;
  for (const k of ks) o = o[k];
  o[last] = val;
}

// ---- färg-kortkommandon: /c /d /h /s -> symbol ----
const SUIT_MAP = { "/c": "♣", "/d": "♦", "/h": "♥", "/s": "♠" };
function expandSuits(v) {
  return v.replace(/\/[cdhs]/gi, (m) => SUIT_MAP[m.toLowerCase()]);
}

// ---- bind formulär <-> state ----
const fields = [...document.querySelectorAll("[data-path]")];
function stateToForm() {
  for (const el of fields) el.value = getPath(state, el.dataset.path) ?? "";
}
function formToStateField(el) {
  let v = el.value;
  if (v.includes("/")) {
    const exp = expandSuits(v);
    if (exp !== v) { v = exp; el.value = v; }
  }
  setPath(state, el.dataset.path, v);
}

// ---- senast fokuserade fält (för färgpaletten) ----
let lastField = null;
for (const el of fields) {
  el.addEventListener("focus", () => { lastField = el; });
}

const schedulePreview = debounce(renderPreview, 350);
const scheduleAutosave = debounce(persistLocal, 500);
for (const el of fields) {
  el.addEventListener("input", () => {
    formToStateField(el);
    if (exactMode) setLiveMode();
    schedulePreview();
    scheduleAutosave();
  });
}

// ---- färgpalett: infoga symbol vid markören i senast fokuserade fält ----
function insertAtCursor(el, text) {
  const start = el.selectionStart ?? el.value.length;
  const end = el.selectionEnd ?? el.value.length;
  el.value = el.value.slice(0, start) + text + el.value.slice(end);
  const pos = start + text.length;
  el.setSelectionRange(pos, pos);
  formToStateField(el);
  schedulePreview();
  scheduleAutosave();
}
for (const btn of document.querySelectorAll(".suitbtn")) {
  btn.addEventListener("mousedown", (e) => e.preventDefault()); // behåll fokus/markör
  btn.addEventListener("click", () => {
    if (!lastField) { showToast("Klicka i ett fält först", "err"); return; }
    lastField.focus();
    insertAtCursor(lastField, btn.dataset.suit);
  });
}

// ---- imposition ----
function imposition() {
  return {
    back_swap: document.getElementById("impSwap").checked,
    back_rotate: document.getElementById("impRotate").checked,
    trim_first_mm: Number(document.getElementById("impTrim").value) || 0,
    cut_marks: document.getElementById("impCut").checked,
    center_lines: document.getElementById("impCenter").checked,
  };
}
for (const id of ["impSwap", "impRotate", "impTrim", "impCut", "impCenter"]) {
  document.getElementById(id).addEventListener("change", () => {
    if (exactMode) refreshExact();
  });
}

// ---- förhandsvisning ----
const prevSpin = document.getElementById("prevSpin");
const previewFrame = document.getElementById("previewFrame");
previewFrame.addEventListener("load", () => { if (!exactMode) checkOverflow(); });

async function renderPreview() {
  prevSpin.hidden = false;
  try {
    const res = await apiFetch("/api/preview", {
      method: "POST", body: JSON.stringify({ payload: state }),
    });
    previewFrame.srcdoc = await res.text();
  } catch (e) {
    showToast("Kunde inte rendera: " + e.message, "err");
  } finally {
    prevSpin.hidden = true;
  }
}

// ---- 261: varna för text som inte får plats i en A6-panel ----
function checkOverflow() {
  const warn = document.getElementById("overflowWarn");
  const doc = previewFrame.contentDocument;
  if (!doc) { warn.hidden = true; return; }
  const over = [];
  for (const fig of doc.querySelectorAll("figure")) {
    const panel = fig.querySelector(".panel");
    const cap = fig.querySelector(".pcap");
    if (!panel) continue;
    if (panel.scrollHeight > panel.clientHeight + 2) {
      over.push(cap ? cap.textContent.trim() : "en panel");
    }
  }
  if (over.length) {
    warn.innerHTML = "⚠ Texten får inte plats i: <strong>" +
      over.join(", ") + "</strong>. Korta ner innehållet innan utskrift.";
    warn.hidden = false;
  } else {
    warn.hidden = true;
  }
}

// ---- 268: exakt PDF-förhandsvisning (rastrerad) ----
let exactMode = false;
function setLiveMode() {
  exactMode = false;
  document.getElementById("btnExact").firstChild.textContent = "Visa exakt PDF ";
}
async function refreshExact() {
  const spin = document.getElementById("exactSpin");
  spin.hidden = false;
  try {
    const res = await apiFetch("/api/pdf-preview", {
      method: "POST",
      body: JSON.stringify({ payload: state, imposition: imposition() }),
    });
    previewFrame.srcdoc = await res.text();
    exactMode = true;
    document.getElementById("btnExact").firstChild.textContent = "Live-förhandsvisning ";
    document.getElementById("overflowWarn").hidden = true;
  } catch (e) {
    showToast("Kunde inte rendera PDF: " + e.message, "err");
  } finally {
    spin.hidden = true;
  }
}
document.getElementById("btnExact").addEventListener("click", () => {
  if (exactMode) { setLiveMode(); renderPreview(); }
  else refreshExact();
});

// ---- 265: autospara utkast i localStorage ----
const LS_KEY = "sysdek:autosave";
function persistLocal() {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify({
      name: document.getElementById("decName").value, payload: state, currentId,
    }));
  } catch {}
}
function restoreLocal() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return false;
    const saved = JSON.parse(raw);
    if (!saved || !saved.payload) return false;
    if (JSON.stringify(saved.payload) === JSON.stringify(EMPTY)) return false;
    state = Object.assign(structuredClone(EMPTY), saved.payload);
    currentId = saved.currentId ?? null;
    document.getElementById("decName").value = saved.name || "";
    return true;
  } catch { return false; }
}

// ---- PDF ----
document.getElementById("btnPdf").addEventListener("click", async () => {
  const spin = document.getElementById("pdfSpin");
  spin.hidden = false;
  try {
    const res = await fetch("/api/pdf", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ payload: state, imposition: imposition(),
        name: document.getElementById("decName").value || "systemdeklaration" }),
    });
    if (!res.ok) throw new Error(await res.text());
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = (document.getElementById("decName").value || "systemdeklaration") + ".pdf";
    a.click();
    URL.revokeObjectURL(url);
    showToast("PDF genererad");
  } catch (e) {
    showToast("PDF misslyckades: " + e.message, "err");
  } finally {
    spin.hidden = true;
  }
});

// ---- spara / ladda / ta bort / ny ----
async function refreshList(selectId) {
  const list = await apiFetch("/api/declarations");
  const sel = document.getElementById("decLoad");
  sel.innerHTML = '<option value="">Sparade...</option>' +
    list.map((d) => `<option value="${d.id}">${d.name}</option>`).join("");
  if (selectId) sel.value = String(selectId);
}

document.getElementById("btnSave").addEventListener("click", async () => {
  const name = document.getElementById("decName").value.trim() || "Namnlös";
  const body = JSON.stringify({ name, payload: state });
  try {
    if (currentId) {
      await apiFetch(`/api/declarations/${currentId}`, { method: "PUT", body });
    } else {
      const r = await apiFetch("/api/declarations", { method: "POST", body });
      currentId = r.id;
    }
    await refreshList(currentId);
    persistLocal();
    showToast("Sparad");
  } catch (e) { showToast("Spara misslyckades: " + e.message, "err"); }
});

document.getElementById("decLoad").addEventListener("change", async (e) => {
  const id = e.target.value;
  if (!id) return;
  const d = await apiFetch(`/api/declarations/${id}`);
  currentId = d.id;
  state = Object.assign(structuredClone(EMPTY), d.payload);
  document.getElementById("decName").value = d.name;
  if (exactMode) setLiveMode();
  stateToForm();
  persistLocal();
  renderPreview();
});

document.getElementById("btnNew").addEventListener("click", () => {
  currentId = null;
  state = structuredClone(EMPTY);
  document.getElementById("decName").value = "";
  document.getElementById("decLoad").value = "";
  if (exactMode) setLiveMode();
  stateToForm();
  persistLocal();
  renderPreview();
});

document.getElementById("btnDelete").addEventListener("click", async () => {
  if (!currentId) { showToast("Ingen sparad deklaration vald", "err"); return; }
  if (!confirm("Ta bort denna deklaration?")) return;
  await apiFetch(`/api/declarations/${currentId}`, { method: "DELETE" });
  currentId = null;
  await refreshList();
  showToast("Borttagen");
});

// ---- tema ----
document.getElementById("btnTheme").addEventListener("click", () => {
  const html = document.documentElement;
  const next = html.getAttribute("data-theme") === "dark" ? "light" : "dark";
  html.setAttribute("data-theme", next);
});

// ---- init ----
const restored = restoreLocal();
stateToForm();
renderPreview();
refreshList();
if (restored) showToast("Återställde osparat utkast");
