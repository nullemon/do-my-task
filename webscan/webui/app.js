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

// ================================================================== TABS
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    const mode = tab.dataset.mode;
    $("mode-scan").hidden = mode !== "scan";
    $("mode-bypass").hidden = mode !== "bypass";
  });
});

// ================================================================== BYPASS MODE
let bpController = null;
let bpBaseline = null;
let bpBypasses = [];
const V_RANK = { BYPASS: 0, ignored: 1, redirect: 2, other: 3, "not-found": 4, blocked: 5, error: 6 };

function bpReadConfig() {
  return {
    target_url: $("bpUrl").value.trim(),
    spoof_ip: $("bpSpoofIp").value.trim() || "127.0.0.1",
    host_header: $("bpHostHeader").value.trim(),
    concurrency: parseInt($("bpConcurrency").value, 10) || 20,
    timeout: parseFloat($("bpTimeout").value) || 8,
    verify_tls: $("bpVerifyTls").checked,
    extra_headers: $("bpExtraHeaders").value,
  };
}

async function runBypass(evt) {
  evt.preventDefault();
  if (!$("bpUrl").value.trim()) return;

  bpBaseline = null; bpBypasses = [];
  $("bpBody").innerHTML = "";
  $("bpTable").hidden = true;
  $("bpEmpty").hidden = false;
  $("bpBanner").hidden = true;
  $("aiBox").hidden = true;
  $("aiResult").hidden = true;
  $("bpBarFill").style.width = "0";
  bpSetRunning(true);

  bpController = new AbortController();
  let resp;
  try {
    resp = await fetch("/api/bypass", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(bpReadConfig()),
      signal: bpController.signal,
    });
  } catch (e) {
    if (e.name !== "AbortError") $("bpProgressText").textContent = `Request failed: ${e.message}`;
    bpSetRunning(false);
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
        if (line) bpHandle(JSON.parse(line));
      }
    }
  } catch (e) {
    if (e.name !== "AbortError") $("bpProgressText").textContent = `Stream error: ${e.message}`;
  }
  bpSetRunning(false);
}

function bpHandle(ev) {
  switch (ev.type) {
    case "baseline": {
      bpBaseline = { url: ev.url, status: ev.status, locked: ev.locked };
      const b = $("bpBanner");
      b.hidden = false;
      b.className = "baseline-banner " + (ev.status === 0 ? "err" : ev.locked ? "locked" : "open");
      b.innerHTML = `<b>Baseline:</b> HTTP ${ev.status || "—"} — ${escapeHtml(ev.note)}`;
      break;
    }
    case "start":
      $("bpProgressText").dataset.total = ev.total;
      $("bpProgressText").textContent = `Trying ${ev.total} bypass techniques…`;
      break;
    case "result":
      bpRenderRow(ev);
      if (ev.bypass) bpBypasses.push(ev);
      break;
    case "progress": {
      const pct = ev.total ? Math.round((ev.done / ev.total) * 100) : 0;
      $("bpBarFill").style.width = pct + "%";
      $("bpProgressText").textContent = `${ev.done} / ${ev.total} tried — ${ev.bypasses} bypass(es) found`;
      break;
    }
    case "done":
      $("bpBarFill").style.width = "100%";
      bpFinish(ev);
      break;
    case "fatal":
      $("bpProgressText").textContent = `Error: ${ev.error}`;
      break;
  }
}

function bpRenderRow(r) {
  $("bpTable").hidden = false;
  $("bpEmpty").hidden = true;
  const tr = document.createElement("tr");
  const hdrs = Object.keys(r.sent_headers || {}).length
    ? `<div class="notes-cell">headers: ${escapeHtml(Object.entries(r.sent_headers).map(([k, v]) => `${k}: ${v}`).join(", "))}</div>`
    : "";
  const note = r.note ? `<div class="notes-cell">${escapeHtml(r.note)}</div>` : "";
  tr.innerHTML = `
    <td><span class="verdict-pill v-${r.verdict}">${r.verdict}</span></td>
    <td class="status">${r.status || "—"}</td>
    <td><span class="url-cell">${escapeHtml(r.technique)}</span><span class="cat-tag">${escapeHtml(r.category)} · ${escapeHtml(r.method)}${r.directory_listing ? " · dir listing" : ""}</span></td>
    <td class="notes-cell">${escapeHtml(r.description)}${hdrs}${note}</td>`;
  const body = $("bpBody");
  const rank = V_RANK[r.verdict] ?? 9;
  let inserted = false;
  for (const row of body.children) {
    const rv = row.querySelector(".verdict-pill")?.textContent || "";
    if ((V_RANK[rv] ?? 9) > rank) { body.insertBefore(tr, row); inserted = true; break; }
  }
  if (!inserted) body.appendChild(tr);
}

function bpFinish(ev) {
  const n = ev.bypass_count;
  const insideOnly = n > 0 && (ev.bypasses || []).every((b) => b.inside_file);
  const someInside = (ev.bypasses || []).some((b) => b.inside_file);
  if (!ev.locked && ev.baseline_status) {
    $("bpProgressText").textContent =
      `Done. That URL wasn't Forbidden (HTTP ${ev.baseline_status}) — it may not be locked.`;
  } else if (n > 0) {
    if (insideOnly) {
      $("bpProgressText").innerHTML =
        `<b>Found it.</b> The directory is 403, but ${n} file(s) <b>inside</b> it are served directly ` +
        `(see the red rows). Your lock only hides the listing — the files are still public. ` +
        `Hit “Explain &amp; fix” for the exact config.`;
    } else {
      $("bpProgressText").textContent =
        `Done. Found ${n} working bypass(es)${someInside ? " (including files served inside the directory)" : ""} — see the red rows. Lock these down.`;
    }
    $("aiBox").hidden = false;
  } else if (ev.locked) {
    $("bpProgressText").textContent =
      "Done. No request-based bypass got through — the lock is holding. If people still see it, the way in is likely a cached copy, a different URL/alias, or a search-engine snapshot.";
  } else {
    $("bpProgressText").textContent = "Done.";
  }
}

function bpSetRunning(on) {
  $("bpRunBtn").disabled = on;
  $("bpRunBtn").textContent = on ? "Testing…" : "Test bypasses";
  $("bpStopBtn").disabled = !on;
}

function bpStop() {
  if (bpController) bpController.abort();
  $("bpProgressText").textContent = "Stopped.";
  bpSetRunning(false);
}

// ---- AI analysis ----
async function runAnalyze() {
  const btn = $("aiRunBtn");
  btn.disabled = true;
  btn.textContent = "Analyzing…";
  const box = $("aiResult");
  box.hidden = false;
  box.innerHTML = `<p class="ai-help">Asking Claude to explain and write the fix… (this can take a moment)</p>`;
  try {
    const resp = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        baseline: bpBaseline,
        bypasses: bpBypasses,
        api_key: $("aiKey").value.trim() || undefined,
      }),
    });
    const data = await resp.json();
    if (data.ok) bpRenderAnalysis(data.analysis);
    else if (data.needs_setup)
      box.innerHTML = `<div class="ai-setup">${escapeHtml(data.error)}</div>`;
    else box.innerHTML = `<div class="ai-error">${escapeHtml(data.error)}</div>`;
  } catch (e) {
    box.innerHTML = `<div class="ai-error">Request failed: ${escapeHtml(e.message)}</div>`;
  }
  btn.disabled = false;
  btn.textContent = "Explain & fix";
}

function bpRenderAnalysis(a) {
  const box = $("aiResult");
  let html = `<h3>AI analysis <span class="sev-pill sev-${a.overall_severity}">${a.overall_severity}</span></h3>`;
  html += `<div class="ai-card"><span class="ai-label">Root cause</span><p>${escapeHtml(a.root_cause)}</p>`;
  if (a.summary) html += `<p>${escapeHtml(a.summary)}</p>`;
  html += `</div>`;
  for (const b of a.bypasses || []) {
    html += `<div class="ai-card"><h4>${escapeHtml(b.technique)}</h4>` +
      `<p>${escapeHtml(b.how_it_works)}</p>` +
      `<p class="ai-fix"><span class="ai-label">Fix</span><br>${escapeHtml(b.fix)}</p></div>`;
  }
  if (a.recommended_config) {
    html += `<div class="ai-card"><span class="ai-label">Apply this configuration</span>` +
      `<pre>${escapeHtml(a.recommended_config)}</pre></div>`;
  }
  box.innerHTML = html;
}

// ------------------------------------------------------------------ wire up
$("bypassForm").addEventListener("submit", runBypass);
$("bpStopBtn").addEventListener("click", bpStop);
$("aiRunBtn").addEventListener("click", runAnalyze);
$("scanForm").addEventListener("submit", runScan);
$("stopBtn").addEventListener("click", stopScan);
$("exportBtn").addEventListener("click", exportJson);
$("search").addEventListener("input", applyFilters);
$("onlyExposed").addEventListener("change", applyFilters);
document.querySelectorAll(".chip[data-ip]").forEach((c) =>
  c.addEventListener("click", () => { $("spoofIp").value = c.dataset.ip; }));
