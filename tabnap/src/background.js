// TabNap service worker. All decisions come from rules.js; this file only
// tracks tab state, talks to Chrome and runs the periodic sweep.
import {
  heavyCandidates,
  isUnderPressure,
  matchingAllowEntry,
  memoryUsedPercent,
  planSweep,
  protectionReason,
  REASON_TEXT,
  sleepCounts,
  tabUrl,
  hostOf,
  wantsAutoDiscardable,
} from './rules.js';
import { loadSettings, loadStats, makeLock } from './storage.js';

const ALARM = 'tabnap-sweep';
const SESSION_KEY = 'tabnap-state';
const PROBE_TIMEOUT_MS = 1000;

// ------------------------------------------------------------ tab state
// Shape kept in chrome.storage.session (survives service-worker restarts,
// cleared when the browser closes):
//   { seeded: bool,
//     tabs:   { [tabId]: { inactiveSince: ms|null, dirty: bool, keepAwake: bool } },
//     active: { [windowId]: tabId } }

const stateLock = makeLock();
let cache = null;

function blankState() {
  return { seeded: false, tabs: {}, active: {} };
}

function newRec() {
  return { inactiveSince: null, dirty: false, keepAwake: false };
}

function ensureRec(st, tabId) {
  if (!st.tabs[tabId]) st.tabs[tabId] = newRec();
  return st.tabs[tabId];
}

/**
 * Bring the stored state in line with the real tab list. Tabs TabNap has
 * never seen (open before install / browser start) get tab.lastAccessed as
 * their "inactive since" estimate; tabs it has a record for keep theirs.
 */
function reconcile(st, tabs, now) {
  const live = new Set();
  for (const tab of tabs) {
    live.add(String(tab.id));
    let rec = st.tabs[tab.id];
    if (!rec) {
      rec = ensureRec(st, tab.id);
      rec.inactiveSince = tab.active
        ? null
        : typeof tab.lastAccessed === 'number'
          ? tab.lastAccessed
          : now;
    } else if (tab.active) {
      rec.inactiveSince = null;
    } else if (rec.inactiveSince == null) {
      rec.inactiveSince = now; // we missed the switch; start counting now
    }
    if (tab.active) st.active[tab.windowId] = tab.id;
  }
  for (const id of Object.keys(st.tabs)) if (!live.has(id)) delete st.tabs[id];
  for (const w of Object.keys(st.active)) if (!live.has(String(st.active[w]))) delete st.active[w];
}

async function readState() {
  if (cache) return cache;
  const got = await chrome.storage.session.get(SESSION_KEY);
  const raw = got[SESSION_KEY];
  cache = raw && typeof raw === 'object' ? { ...blankState(), ...raw } : blankState();
  if (!cache.seeded) {
    reconcile(cache, await chrome.tabs.query({}), Date.now());
    cache.seeded = true;
    await chrome.storage.session.set({ [SESSION_KEY]: cache });
  }
  return cache;
}

/** Run fn(state) under the lock and persist whatever it changed. */
function updateState(fn) {
  return stateLock(async () => {
    try {
      const st = await readState();
      const result = await fn(st);
      await chrome.storage.session.set({ [SESSION_KEY]: st });
      return result;
    } catch (err) {
      cache = null; // re-read from storage next time
      throw err;
    }
  });
}

function readTabs() {
  return stateLock(async () => structuredClone((await readState()).tabs));
}

// ----------------------------------------------------------- tab events

chrome.tabs.onActivated.addListener(({ tabId, windowId }) => {
  updateState((st) => {
    const now = Date.now();
    const prev = st.active[windowId];
    if (prev != null && prev !== tabId && st.tabs[prev]) {
      // A tab dragged to another window may already be active there.
      const activeElsewhere = Object.entries(st.active).some(
        ([w, t]) => t === prev && Number(w) !== windowId,
      );
      if (!activeElsewhere) st.tabs[prev].inactiveSince = now;
    }
    ensureRec(st, tabId).inactiveSince = null;
    st.active[windowId] = tabId;
  }).catch(() => {});
});

chrome.tabs.onCreated.addListener((tab) => {
  updateState((st) => {
    const rec = ensureRec(st, tab.id);
    rec.inactiveSince = tab.active ? null : Date.now();
    if (tab.active) st.active[tab.windowId] = tab.id;
  }).catch(() => {});
});

chrome.tabs.onRemoved.addListener((tabId, info) => {
  updateState((st) => {
    delete st.tabs[tabId];
    if (st.active[info.windowId] === tabId || info.isWindowClosing) delete st.active[info.windowId];
  }).catch(() => {});
});

chrome.tabs.onReplaced.addListener((addedTabId, removedTabId) => {
  updateState((st) => {
    if (st.tabs[removedTabId]) {
      st.tabs[addedTabId] = st.tabs[removedTabId];
      delete st.tabs[removedTabId];
    }
    for (const w of Object.keys(st.active)) {
      if (st.active[w] === removedTabId) st.active[w] = addedTabId;
    }
  })
    .then(() => chrome.tabs.get(addedTabId))
    .then((tab) => syncAutoDiscardable([tab]))
    .catch(() => {});
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if ('url' in changeInfo || changeInfo.status === 'complete') {
    syncAutoDiscardable([tab]).catch(() => {});
  }
});

// ------------------------------------------- Chrome's own tab discarding

/**
 * Allowlisted and keep-awake tabs get autoDiscardable:false so Chrome's
 * Memory Saver / Edge's Sleeping Tabs leave them alone too; everything else
 * gets autoDiscardable:true back.
 */
async function syncAutoDiscardable(tabs, settings, recs) {
  const s = settings || (await loadSettings());
  const r = recs || (await readTabs());
  await Promise.all(
    tabs.map(async (tab) => {
      if (!tab || typeof tab.id !== 'number') return;
      const want = wantsAutoDiscardable(tab, r[tab.id], s);
      if (want === null || tab.autoDiscardable === want) return;
      try {
        await chrome.tabs.update(tab.id, { autoDiscardable: want });
      } catch {
        // Tab closed meanwhile, or a page Chrome won't let us touch.
      }
    }),
  );
}

async function syncAllAutoDiscardable() {
  await syncAutoDiscardable(await chrome.tabs.query({}));
}

// ------------------------------------------------- content-script probe

/**
 * Ask the tab's content script for {dirty, heap}. Resolves to
 *   {status: 'ok', dirty, heap}  answer received (heap may be null)
 *   {status: 'none'}             no content script there (tab opened before
 *                                install, or a page scripts can't run in)
 *   {status: 'timeout'}          no answer in time (busy or frozen tab)
 */
async function probe(tabId) {
  let timer;
  const timeout = new Promise((resolve) => {
    timer = setTimeout(() => resolve({ status: 'timeout' }), PROBE_TIMEOUT_MS);
  });
  const ask = chrome.tabs
    .sendMessage(tabId, { type: 'tabnap-probe' }, { frameId: 0 })
    .then((res) =>
      res && typeof res === 'object'
        ? {
            status: 'ok',
            dirty: res.dirty === true,
            heap: typeof res.heap === 'number' && Number.isFinite(res.heap) ? res.heap : null,
          }
        : { status: 'none' },
    )
    .catch(() => ({ status: 'none' }));
  try {
    return await Promise.race([ask, timeout]);
  } finally {
    clearTimeout(timer);
  }
}

async function probeMany(tabIds) {
  const results = await Promise.all(tabIds.map(async (id) => [id, await probe(id)]));
  return new Map(results);
}

/** Store fresh dirty flags learned from probes; returns the updated records. */
async function applyProbeResults(probes) {
  if (probes.size === 0) return readTabs();
  return updateState((st) => {
    for (const [id, p] of probes) {
      const rec = st.tabs[id];
      if (!rec) continue;
      if (p.status === 'ok') rec.dirty = p.dirty;
      else if (p.status === 'none') rec.dirty = false; // the page that had the form is gone
      // timeout: keep what we had
    }
    return structuredClone(st.tabs);
  });
}

// --------------------------------------------------------------- memory

async function getMemoryInfo() {
  try {
    return await chrome.system.memory.getInfo();
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------- sweep

const sweepLock = makeLock();

async function bumpStats(byReason) {
  const stats = await loadStats();
  for (const [reason, n] of Object.entries(byReason)) {
    stats[reason] = (stats[reason] || 0) + n;
    stats.total += n;
  }
  await chrome.storage.local.set({ stats });
}

/** Re-check a tab right before unloading it, then discard it. */
async function discardTab(tabId, settings) {
  let tab;
  try {
    tab = await chrome.tabs.get(tabId);
  } catch {
    return false;
  }
  const recs = await readTabs();
  if (protectionReason(tab, recs[tabId], settings)) return false;
  try {
    const result = await chrome.tabs.discard(tabId);
    return Boolean(result);
  } catch {
    return false;
  }
}

/**
 * One pass over all tabs.
 *   manual: true  -> "Unload other tabs now" (every eligible background tab,
 *                    works even while TabNap is paused)
 *   manual: false -> the automatic rules (idle, low memory, heavy tabs)
 */
function sweep({ manual = false } = {}) {
  return sweepLock(async () => {
    const settings = await loadSettings();
    if (!manual && !settings.enabled) return { unloaded: 0, planned: [] };

    const { tabs, recs, now } = await updateState(async (st) => {
      const now = Date.now();
      const tabs = await chrome.tabs.query({});
      reconcile(st, tabs, now);
      return { tabs, recs: structuredClone(st.tabs), now };
    });

    let pressure = false;
    if (!manual && settings.pressureEnabled) {
      pressure = isUnderPressure(await getMemoryInfo(), settings);
    }

    // Ask content scripts for JavaScript memory (heavy-tab mode) and refresh
    // "unsaved text" flags that may be stale (field cleared by the page, or
    // the page navigated away).
    const toProbe = new Set(manual ? [] : heavyCandidates(tabs, recs, settings, now));
    if (settings.protectForms) {
      for (const tab of tabs) {
        const rec = recs[tab.id];
        if (rec && rec.dirty && !protectionReason(tab, { ...rec, dirty: false }, settings)) {
          toProbe.add(tab.id);
        }
      }
    }
    const probes = await probeMany([...toProbe]);
    const fresh = await applyProbeResults(probes);

    const heapByTab = {};
    for (const [id, p] of probes) if (p.status === 'ok' && p.heap !== null) heapByTab[id] = p.heap;

    const plan = planSweep(tabs, fresh, settings, now, { manual, pressure, heapByTab });

    // Last check for typed text in tabs we haven't asked yet; discardTab()
    // re-reads the records, so a tab found dirty here is skipped.
    if (settings.protectForms) {
      const unasked = plan.map((p) => p.tabId).filter((id) => !probes.has(id));
      await applyProbeResults(await probeMany(unasked));
    }

    const byReason = {};
    let unloaded = 0;
    for (const item of plan) {
      if (await discardTab(item.tabId, settings)) {
        unloaded++;
        byReason[item.reason] = (byReason[item.reason] || 0) + 1;
      }
    }
    if (unloaded) await bumpStats(byReason);
    return { unloaded, planned: plan };
  });
}

// ------------------------------------------------------------- messages

function isExtensionPage(sender) {
  return (
    sender.id === chrome.runtime.id &&
    typeof sender.url === 'string' &&
    sender.url.startsWith(chrome.runtime.getURL(''))
  );
}

async function setKeepAwake(tabId, value) {
  await updateState((st) => {
    ensureRec(st, tabId).keepAwake = Boolean(value);
  });
  try {
    await syncAutoDiscardable([await chrome.tabs.get(tabId)]);
  } catch {
    // tab gone
  }
  return { ok: true };
}

async function getStatus(tabId) {
  const [settings, tabs, recs, memory, stats] = await Promise.all([
    loadSettings(),
    chrome.tabs.query({}),
    readTabs(),
    getMemoryInfo(),
    loadStats(),
  ]);
  const tab = tabs.find((t) => t.id === tabId) || null;
  let current = null;
  if (tab) {
    const rec = recs[tab.id] || {};
    const reason = protectionReason(tab, rec, settings, { ignoreActive: true });
    current = {
      id: tab.id,
      host: hostOf(tabUrl(tab)),
      allowEntry: matchingAllowEntry(tabUrl(tab), settings.allowlist),
      keepAwake: Boolean(rec.keepAwake),
      reason,
      reasonText: reason ? REASON_TEXT[reason] : null,
    };
  }
  return {
    settings,
    counts: sleepCounts(tabs),
    memoryUsedPercent: memoryUsedPercent(memory),
    stats,
    tab: current,
  };
}

async function handleMessage(msg, sender) {
  if (!msg || typeof msg !== 'object') return null;

  // The only thing a web page's content script may tell us: "has unsent text".
  if (msg.type === 'form-state') {
    if (!sender.tab || sender.frameId !== 0 || typeof msg.dirty !== 'boolean') return null;
    const tabId = sender.tab.id;
    if (typeof tabId !== 'number' || tabId < 0) return null;
    await updateState((st) => {
      ensureRec(st, tabId).dirty = msg.dirty;
    });
    return { ok: true };
  }

  if (!isExtensionPage(sender)) return null;
  switch (msg.type) {
    case 'get-status':
      return getStatus(Number(msg.tabId));
    case 'set-keep-awake':
      return setKeepAwake(Number(msg.tabId), msg.value);
    case 'unload-others':
      return sweep({ manual: true });
    case 'sweep-now':
      return sweep({ manual: false });
    default:
      return null;
  }
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  handleMessage(msg, sender).then(
    (res) => sendResponse(res),
    () => sendResponse({ error: 'failed' }),
  );
  return true; // async response
});

// ------------------------------------------------- shortcut, alarm, badge

chrome.commands.onCommand.addListener((command) => {
  if (command === 'unload-others') sweep({ manual: true }).catch(() => {});
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM) sweep().catch(() => {});
});

async function ensureAlarm() {
  const existing = await chrome.alarms.get(ALARM);
  if (!existing) await chrome.alarms.create(ALARM, { periodInMinutes: 0.5, delayInMinutes: 0.5 });
}

async function updateBadge() {
  const { enabled } = await loadSettings();
  await chrome.action.setBadgeBackgroundColor({ color: '#6b6880' });
  await chrome.action.setBadgeText({ text: enabled ? '' : 'off' });
}

chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== 'sync') return;
  if ('allowlist' in changes) syncAllAutoDiscardable().catch(() => {});
  if ('enabled' in changes) updateBadge().catch(() => {});
});

async function init() {
  await ensureAlarm();
  await updateBadge();
  await updateState((st) => {
    // On install/startup, pick up every tab that is already open.
    return chrome.tabs.query({}).then((tabs) => reconcile(st, tabs, Date.now()));
  });
  await syncAllAutoDiscardable();
}

chrome.runtime.onInstalled.addListener(() => {
  init().catch(() => {});
});
chrome.runtime.onStartup.addListener(() => {
  init().catch(() => {});
});

// The worker can also wake up for an event; make sure the alarm exists.
ensureAlarm().catch(() => {});
