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

// ---- fyrfärgslek: låt editorn följa samma toggle som panel/PDF ----
function applyFourColor() {
  document.body.classList.toggle("fourcolor", !!getPath(state, "display.four_color"));
}

// ---- färg-kortkommandon: /c /d /h /s -> symbol ----
const SUIT_MAP = { "/c": "♣", "/d": "♦", "/h": "♥", "/s": "♠" };
function expandSuits(v) {
  v = v.replace(/\/nt/gi, "NT");
  return v.replace(/\/[cdhs]/gi, (m) => SUIT_MAP[m.toLowerCase()]);
}

// ---- 278: normalisera emoji-varianter av färgsymboler (♥️ = U+2665 U+FE0F) ----
// till rena glyfer utan variation selector (text U+FE0E eller emoji U+FE0F).
function normalizeSuits(v) {
  return v.replace(/([♠♣♥♦])[︎️]/g, "$1");
}

// ---- bind formulär <-> state ----
const fields = [...document.querySelectorAll("[data-path]")];

// ---- 276: textareas ska växa/krympa efter innehåll ----
function autosize(el) {
  el.style.height = "auto";
  el.style.height = el.scrollHeight + "px";
}
function stateToForm() {
  for (const el of fields) {
    if (el.type === "checkbox") el.checked = !!getPath(state, el.dataset.path);
    else el.value = getPath(state, el.dataset.path) ?? "";
  }
  for (const el of fields) {
    if (el.tagName === "TEXTAREA") autosize(el);
  }
  applyFourColor();
}
function formToStateField(el) {
  if (el.type === "checkbox") {
    setPath(state, el.dataset.path, el.checked);
    return;
  }
  let v = el.value;
  const norm = normalizeSuits(v);
  if (norm !== v) v = norm;
  if (v.includes("/")) {
    const exp = expandSuits(v);
    if (exp !== v) v = exp;
  }
  if (v !== el.value) el.value = v;
  setPath(state, el.dataset.path, v);
}

// ---- senast fokuserade fält (för färgpaletten) ----
let lastField = null;
for (const el of fields) {
  if (el.type === "checkbox") continue;
  el.addEventListener("focus", () => { lastField = el; });
}

const schedulePreview = debounce(renderPreview, 350);
const scheduleAutosave = debounce(persistLocal, 500);
for (const el of fields) {
  // Select fyrar inte alltid "input" tillförlitligt över browsers - lyssna
  // på "change" för dem (liksom för checkboxar), "input" för textfält.
  const evt = el.type === "checkbox" || el.tagName === "SELECT" ? "change" : "input";
  el.addEventListener(evt, () => {
    formToStateField(el);
    if (el.tagName === "TEXTAREA") autosize(el);
    if (el.dataset.path === "display.four_color") applyFourColor();
    if (exactMode) setLiveMode();
    schedulePreview();
    scheduleAutosave();
  });
}

// ---- 273: logotyp på omslaget - egen uppladdad bild som data-URI ----
document.getElementById("logoFile").addEventListener("change", (e) => {
  const file = e.target.files && e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    setPath(state, "display.logo_data", reader.result);
    setPath(state, "display.logo", "custom");
    document.getElementById("logoMode").value = "custom";
    if (exactMode) setLiveMode();
    schedulePreview();
    scheduleAutosave();
  };
  reader.onerror = () => showToast("Kunde inte läsa bildfilen", "err");
  reader.readAsDataURL(file);
});

// Kör om autosize på alla textareas vid omstorlek (rotation / responsivt läge),
// annars blir höjder uträknade vid en bredd stale när bredden ändras.
const rerunAutosizeAll = debounce(() => {
  for (const el of fields) if (el.tagName === "TEXTAREA") autosize(el);
}, 150);
window.addEventListener("resize", rerunAutosizeAll);

// ---- färgpalett: infoga symbol vid markören i senast fokuserade fält ----
function insertAtCursor(el, text) {
  const start = el.selectionStart ?? el.value.length;
  const end = el.selectionEnd ?? el.value.length;
  el.value = el.value.slice(0, start) + text + el.value.slice(end);
  const pos = start + text.length;
  el.setSelectionRange(pos, pos);
  formToStateField(el);
  if (el.tagName === "TEXTAREA") autosize(el);
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
  const pageMargin = Number(document.getElementById("impPageMargin").value);
  return {
    back_swap: document.getElementById("impSwap").checked,
    back_rotate: document.getElementById("impRotate").checked,
    trim_first_mm: Number(document.getElementById("impTrim").value) || 0,
    cut_marks: document.getElementById("impCut").checked,
    center_lines: document.getElementById("impCenter").checked,
    binding_margin_mm: Number(document.getElementById("impBinding").value) || 0,
    binding_edge: document.getElementById("impBindEdge").value,
    page_margin_mm: Number.isNaN(pageMargin) ? 5 : pageMargin,
  };
}
// ---- 304: signatur av state+imposition för att undvika onödig PDF-generering ----
const sig = () => JSON.stringify({ p: state, i: imposition() });

const scheduleExact = debounce(() => { if (exactMode) refreshExact(); }, 400);
for (const id of ["impSwap", "impRotate", "impTrim", "impCut", "impCenter", "impBinding", "impBindEdge", "impPageMargin"]) {
  const el = document.getElementById(id);
  el.addEventListener("input", scheduleExact);
  el.addEventListener("change", scheduleExact);
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
let exactCache = { sig: null, html: null };
function setLiveMode() {
  exactMode = false;
  document.getElementById("btnExact").firstChild.textContent = "Visa exakt PDF ";
}
function enterExactMode() {
  exactMode = true;
  document.getElementById("btnExact").firstChild.textContent = "Live-förhandsvisning ";
  document.getElementById("overflowWarn").hidden = true;
}
async function refreshExact() {
  const s = sig();
  if (s === exactCache.sig && exactCache.html != null) {
    previewFrame.srcdoc = exactCache.html;
    enterExactMode();
    return;
  }
  const spin = document.getElementById("exactSpin");
  spin.hidden = false;
  try {
    const res = await apiFetch("/api/pdf-preview", {
      method: "POST",
      body: JSON.stringify({ payload: state, imposition: imposition() }),
    });
    const html = await res.text();
    previewFrame.srcdoc = html;
    exactCache = { sig: s, html };
    enterExactMode();
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

// ---- slå ihop en laddad payload med EMPTY - täcker även äldre deklarationer
// som saknar nyare display-fält (t.ex. logo/logo_data tillagda i 273) ----
function mergeWithEmpty(payload) {
  const merged = Object.assign(structuredClone(EMPTY), payload);
  merged.display = Object.assign(structuredClone(EMPTY.display), payload.display || {});
  return merged;
}

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
    state = mergeWithEmpty(saved.payload);
    currentId = saved.currentId ?? null;
    document.getElementById("decName").value = saved.name || "";
    return true;
  } catch { return false; }
}

// ---- PDF ----
let pdfCache = { sig: null, blob: null };
document.getElementById("btnPdf").addEventListener("click", async () => {
  const s = sig();
  const downloadBlob = (blob) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = (document.getElementById("decName").value || "systemdeklaration") + ".pdf";
    a.click();
    URL.revokeObjectURL(url);
  };
  if (s === pdfCache.sig && pdfCache.blob) {
    downloadBlob(pdfCache.blob);
    showToast("PDF genererad");
    return;
  }
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
    pdfCache = { sig: s, blob };
    downloadBlob(blob);
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
  state = mergeWithEmpty(d.payload);
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

// (temaväxlaren hanteras av theme.js)

// ---- 293: håll --header-h i synk med topbarens verkliga höjd (den wrappar) ----
function trackTopbarHeight() {
  const topbar = document.querySelector(".topbar");
  if (!topbar) return;
  const update = () => {
    document.documentElement.style.setProperty("--header-h", topbar.offsetHeight + "px");
  };
  update();
  new ResizeObserver(update).observe(topbar);
}
trackTopbarHeight();

// ---- init ----
const restored = restoreLocal();
stateToForm();
renderPreview();
refreshList();
if (restored) showToast("Återställde osparat utkast");
