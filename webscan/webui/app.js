"use strict";

// ------------------------------------------------------------------ helpers
const $ = (id) => document.getElementById(id);
const SEV_ORDER = { critical: 0, high: 1, medium: 2, low: 3, info: 4, none: 5 };

let currentController = null;   // AbortController for the in-flight scan
let allResults = [];           // every streamed "result" event
let lastSummary = null;

// ------------------------------------------------------------------ build request
function readConfig() {
  return {
    targets: $("targets").value,
    base_path: $("basePath").value || "/",
    wordlist: $("wordlist").value,
    custom_paths: $("customPaths").value,
    concurrency: parseInt($("concurrency").value, 10) || 20,
    timeout: parseFloat($("timeout").value) || 8,
    method: $("method").value,
    follow_redirects: $("followRedirects").checked,
    verify_tls: $("verifyTls").checked,
    spoof_ip: $("spoofIp").value.trim(),
    host_header: $("hostHeader").value.trim(),
    extra_headers: $("extraHeaders").value,
    user_agent: $("userAgent").value.trim() || undefined,
  };
}

// ------------------------------------------------------------------ scanning
async function runScan(evt) {
  evt.preventDefault();
  if (!$("targets").value.trim()) return;

  resetResults();
  setScanning(true);

  currentController = new AbortController();
  let resp;
  try {
    resp = await fetch("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(readConfig()),
      signal: currentController.signal,
    });
  } catch (e) {
    if (e.name !== "AbortError") setProgress(`Request failed: ${e.message}`);
    setScanning(false);
    return;
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let nl;
      while ((nl = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, nl).trim();
        buffer = buffer.slice(nl + 1);
        if (line) handleEvent(JSON.parse(line));
      }
    }
  } catch (e) {
    if (e.name !== "AbortError") setProgress(`Stream error: ${e.message}`);
  }
  setScanning(false);
}

function handleEvent(ev) {
  switch (ev.type) {
    case "start":
      $("progressText").dataset.total = ev.total;
      setProgress(`Scanning ${ev.total} checks across ${ev.targets.length} target(s)…`);
      break;
    case "baseline":
      break; // (baseline info is used server-side; no UI row needed)
    case "result":
      allResults.push(ev);
      renderRow(ev);
      break;
    case "progress":
      updateBar(ev.done, ev.total);
      break;
    case "done":
      lastSummary = ev.summary;
      renderStats(ev.summary);
      finishProgress();
      break;
    case "fatal":
      setProgress(`Error: ${ev.error}`);
      break;
  }
}

// ------------------------------------------------------------------ rendering
function renderRow(r) {
  $("resultsTable").hidden = false;
  $("empty").hidden = true;
  $("filters").hidden = false;

  const tr = document.createElement("tr");
  tr.dataset.severity = r.severity;
  tr.dataset.verdict = r.verdict;
  tr.dataset.search = (r.url + " " + r.description + " " + (r.notes || []).join(" ")).toLowerCase();

  const confirmed = r.confirmed ? '<span class="confirmed" title="Content confirmed">✓</span>' : "";
  const link = `<a href="${escapeAttr(r.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(r.url)}</a>`;

  tr.innerHTML = `
    <td><span class="sev-pill sev-${r.severity}">${r.severity}</span></td>
    <td class="status">${r.status || "—"}</td>
    <td class="url-cell">${link}${confirmed}<div class="notes-cell">${escapeHtml(r.description || "")}</div></td>
    <td><span class="verdict ${r.verdict}">${r.verdict}</span></td>
    <td class="notes-cell">${escapeHtml((r.notes || []).join(" · "))}</td>`;

  // Insert keeping severity order (most severe on top).
  const body = $("resultsBody");
  const rank = SEV_ORDER[r.severity] ?? 9;
  let inserted = false;
  for (const row of body.children) {
    if ((SEV_ORDER[row.dataset.severity] ?? 9) > rank) {
      body.insertBefore(tr, row);
      inserted = true;
      break;
    }
  }
  if (!inserted) body.appendChild(tr);
  applyFilters();
}

function renderStats(summary) {
  const el = $("stats");
  el.innerHTML = "";
  const sevs = summary.by_severity || {};
  const order = ["critical", "high", "medium", "low"];
  let any = false;
  for (const s of order) {
    if (sevs[s]) {
      any = true;
      el.insertAdjacentHTML("beforeend",
        `<span class="stat sev-${s}"><b>${sevs[s]}</b> ${s}</span>`);
    }
  }
  el.insertAdjacentHTML("beforeend",
    `<span class="stat"><b>${summary.exposed || 0}</b> exposed</span>`);
  if (summary.protected) {
    el.insertAdjacentHTML("beforeend",
      `<span class="stat"><b>${summary.protected}</b> protected</span>`);
  }
  if (!any && !summary.exposed) {
    el.insertAdjacentHTML("beforeend",
      `<span class="stat" style="color:var(--ok)">No exposures found ✓</span>`);
  }
}

function updateBar(done, total) {
  const pct = total ? Math.round((done / total) * 100) : 0;
  $("barFill").style.width = pct + "%";
  setProgress(`${done} / ${total} checked (${pct}%) — ${allResults.length} findings`);
}

function finishProgress() {
  $("barFill").style.width = "100%";
  const total = $("progressText").dataset.total || allResults.length;
  setProgress(`Done. ${total} checks complete — ${allResults.length} findings. ${
    allResults.length ? "Review below and lock down anything exposed." : "Nothing notable found."}`);
}

// ------------------------------------------------------------------ filters
function applyFilters() {
  const q = $("search").value.trim().toLowerCase();
  const onlyExposed = $("onlyExposed").checked;
  for (const row of $("resultsBody").children) {
    const matchQ = !q || row.dataset.search.includes(q);
    const matchV = !onlyExposed ||
      ["exposed", "exists"].includes(row.dataset.verdict);
    row.style.display = (matchQ && matchV) ? "" : "none";
  }
}

// ------------------------------------------------------------------ ui state
function setScanning(on) {
  $("scanBtn").disabled = on;
  $("scanBtn").textContent = on ? "Scanning…" : "Scan";
  $("stopBtn").disabled = !on;
  $("exportBtn").disabled = on || allResults.length === 0;
}

function resetResults() {
  allResults = [];
  lastSummary = null;
  $("resultsBody").innerHTML = "";
  $("stats").innerHTML = "";
  $("resultsTable").hidden = true;
  $("empty").hidden = false;
  $("barFill").style.width = "0";
}

function setProgress(text) { $("progressText").textContent = text; }

function stopScan() {
  if (currentController) currentController.abort();
  setProgress("Stopped.");
  setScanning(false);
}

function exportJson() {
  const data = JSON.stringify({ summary: lastSummary, findings: allResults }, null, 2);
  const blob = new Blob([data], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "webscan-results.json";
  a.click();
  URL.revokeObjectURL(a.href);
}

// ------------------------------------------------------------------ escaping
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function escapeAttr(s) { return escapeHtml(s); }

// ------------------------------------------------------------------ wire up
$("scanForm").addEventListener("submit", runScan);
$("stopBtn").addEventListener("click", stopScan);
$("exportBtn").addEventListener("click", exportJson);
$("search").addEventListener("input", applyFilters);
$("onlyExposed").addEventListener("change", applyFilters);
document.querySelectorAll(".chip[data-ip]").forEach((c) =>
  c.addEventListener("click", () => { $("spoofIp").value = c.dataset.ip; }));
