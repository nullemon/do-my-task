// TabNap decision logic. Pure functions only: no chrome.* calls, no clocks,
// no I/O. Everything here is unit-tested in Node (see test/rules.test.js).

export const IDLE_CHOICES = [1, 5, 10, 15, 30, 60, 120, 240];
export const PRESSURE_CHOICES = [10, 15, 20, 25, 30];
export const HEAVY_CHOICES = [200, 400, 800, 1500];

export const DEFAULTS = Object.freeze({
  enabled: true,
  idleMinutes: 15,
  allowlist: [],
  protectAudio: true,
  protectPinned: true,
  protectForms: true,
  pressureEnabled: true,
  pressurePercent: 15,
  heavyEnabled: true,
  heavyLimitMB: 400,
});

// Pressure and heavy-tab unloading only touch tabs left at least this long ago.
export const MIN_BACKGROUND_MS = 60 * 1000;
// Pressure mode unloads at most this many tabs per check.
export const PRESSURE_BATCH = 5;

const MB = 1024 * 1024;

// ---------------------------------------------------------------- settings

function num(v, fallback, ok) {
  const n = typeof v === 'string' && v.trim() !== '' ? Number(v) : v;
  return typeof n === 'number' && Number.isFinite(n) && ok(n) ? n : fallback;
}

function bool(v, fallback) {
  return typeof v === 'boolean' ? v : fallback;
}

/** Merge stored values over the defaults, repairing anything malformed. */
export function sanitizeSettings(raw) {
  const r = raw && typeof raw === 'object' ? raw : {};
  return {
    enabled: bool(r.enabled, DEFAULTS.enabled),
    // Any positive number is accepted so tests can use sub-minute timeouts;
    // the UI only offers IDLE_CHOICES.
    idleMinutes: num(r.idleMinutes, DEFAULTS.idleMinutes, (n) => n > 0),
    allowlist: sanitizeAllowlist(r.allowlist),
    protectAudio: bool(r.protectAudio, DEFAULTS.protectAudio),
    protectPinned: bool(r.protectPinned, DEFAULTS.protectPinned),
    protectForms: bool(r.protectForms, DEFAULTS.protectForms),
    pressureEnabled: bool(r.pressureEnabled, DEFAULTS.pressureEnabled),
    pressurePercent: num(r.pressurePercent, DEFAULTS.pressurePercent, (n) => n > 0 && n < 100),
    heavyEnabled: bool(r.heavyEnabled, DEFAULTS.heavyEnabled),
    heavyLimitMB: num(r.heavyLimitMB, DEFAULTS.heavyLimitMB, (n) => n > 0),
  };
}

export function sanitizeAllowlist(list) {
  if (!Array.isArray(list)) return [];
  const out = [];
  for (const item of list) {
    const res = normalizeSiteEntry(item);
    if (res.ok && !out.includes(res.value)) out.push(res.value);
  }
  return out;
}

// --------------------------------------------------------------- allowlist

const LABEL_RE = /^(?!-)[a-z0-9_-]{1,63}(?<!-)$/;
const IPV4_RE = /^\d{1,3}(\.\d{1,3}){3}$/;

function isIpHostname(hostname) {
  return IPV4_RE.test(hostname) || hostname.startsWith('[');
}

function validHostname(hostname) {
  if (!hostname || hostname.length > 253) return false;
  if (isIpHostname(hostname)) return true;
  return hostname.split('.').every((label) => LABEL_RE.test(label));
}

/**
 * Turn whatever the user typed (a URL, a host, "*.host", "www.host") into the
 * canonical allowlist entry: lowercase host without "www.", plus ":port" when
 * a non-default port was given.
 * Returns {ok: true, value} or {ok: false, error}.
 */
export function normalizeSiteEntry(input) {
  if (typeof input !== 'string') return { ok: false, error: 'Enter a site, like youtube.com' };
  let s = input.trim().toLowerCase();
  if (!s) return { ok: false, error: 'Enter a site, like youtube.com' };
  if (/\s/.test(s)) return { ok: false, error: 'A site address can’t contain spaces.' };

  const notWeb = { ok: false, error: 'Only websites (http:// or https://) can be added.' };
  const garbage = { ok: false, error: 'That doesn’t look like a website address, try something like youtube.com' };

  // "https://", "http://" or the match-pattern style "*://".
  let hadScheme = false;
  const schemeMatch = s.match(/^([a-z][a-z0-9+.-]*|\*):\/\//);
  if (schemeMatch) {
    const scheme = schemeMatch[1];
    if (scheme !== 'http' && scheme !== 'https' && scheme !== '*') return notWeb;
    hadScheme = scheme !== '*';
    s = (hadScheme ? scheme : 'http') + '://' + s.slice(schemeMatch[0].length);
  } else if (/^[a-z][a-z0-9+.-]*:(?!\d)/.test(s)) {
    return notWeb; // "about:blank", "chrome:settings", "mailto:a@b" ...
  } else {
    s = 'http://' + s;
  }

  // A leading "*." is redundant: subdomains always match.
  s = s.replace(/^(https?:\/\/)\*\./, '$1');

  let url;
  try {
    url = new URL(s);
  } catch {
    return garbage;
  }

  let hostname = url.hostname.replace(/\.$/, '');
  if (hostname.includes('*')) {
    return { ok: false, error: 'Wildcards aren’t needed: youtube.com already covers all of its subdomains.' };
  }
  if (!validHostname(hostname)) return garbage;
  if (hostname.startsWith('www.') && hostname.slice(4).includes('.') && !isIpHostname(hostname)) {
    hostname = hostname.slice(4);
  }

  let port = url.port; // '' when it is the scheme's default
  // "example.com:443" typed without a scheme means "the default https port".
  if (!hadScheme && (port === '443' || port === '80')) port = '';
  return { ok: true, value: port ? `${hostname}:${port}` : hostname };
}

/** "host[:port]" of an http(s) URL, lowercase; null for anything else. */
export function hostOf(url) {
  if (typeof url !== 'string' || !url) return null;
  let u;
  try {
    u = new URL(url);
  } catch {
    return null;
  }
  if (u.protocol !== 'http:' && u.protocol !== 'https:') return null;
  const hostname = u.hostname.replace(/\.$/, '');
  if (!hostname) return null;
  return u.port ? `${hostname}:${u.port}` : hostname;
}

export function isWebUrl(url) {
  return hostOf(url) !== null;
}

function splitHost(host) {
  // Handles "[::1]:3000", "localhost:3000", "example.com".
  const m = host.match(/^(\[[^\]]+\]|[^:]+)(?::(\d+))?$/);
  return m ? { hostname: m[1], port: m[2] || '' } : { hostname: host, port: '' };
}

/**
 * Which allowlist entry covers this URL (or host)? An entry covers its own
 * host and every subdomain; an entry with a port only covers that port, an
 * entry without a port covers every port. Returns the entry or null.
 */
export function matchingAllowEntry(urlOrHost, allowlist) {
  if (!Array.isArray(allowlist) || allowlist.length === 0) return null;
  const host = urlOrHost && urlOrHost.includes('://') ? hostOf(urlOrHost) : urlOrHost;
  if (!host) return null;
  const page = splitHost(host.toLowerCase());
  for (const entry of allowlist) {
    if (typeof entry !== 'string' || !entry) continue;
    const e = splitHost(entry);
    if (e.port && e.port !== page.port) continue;
    if (page.hostname === e.hostname) return entry;
    if (!isIpHostname(e.hostname) && page.hostname.endsWith('.' + e.hostname)) return entry;
  }
  return null;
}

export function isAllowlisted(urlOrHost, allowlist) {
  return matchingAllowEntry(urlOrHost, allowlist) !== null;
}

/** All entries that cover a host (used when the popup toggle is switched off). */
export function entriesCovering(host, allowlist) {
  return (allowlist || []).filter((entry) => matchingAllowEntry(host, [entry]) !== null);
}

/** Add an entry; returns {ok, list, value} or {ok: false, error}. */
export function addToAllowlist(list, input) {
  const res = normalizeSiteEntry(input);
  if (!res.ok) return res;
  const current = sanitizeAllowlist(list);
  if (current.includes(res.value)) {
    return { ok: false, error: `${res.value} is already on the list.`, value: res.value };
  }
  return { ok: true, value: res.value, list: [...current, res.value].sort() };
}

export function removeFromAllowlist(list, values) {
  const drop = new Set(Array.isArray(values) ? values : [values]);
  return sanitizeAllowlist(list).filter((v) => !drop.has(v));
}

// ------------------------------------------------------------- protections

export const REASON_TEXT = Object.freeze({
  internal: 'Browser and extension pages are never unloaded',
  asleep: 'Already asleep',
  allowlisted: 'On your never-unload list',
  'keep-awake': 'You asked to keep this tab awake',
  audio: 'Playing audio',
  pinned: 'Pinned tab',
  form: 'Has text you typed that isn’t sent yet',
  active: 'You’re looking at it',
  loading: 'Still loading',
});

export function tabUrl(tab) {
  return (tab && (tab.url || tab.pendingUrl)) || '';
}

/**
 * Why must this tab not be unloaded? Returns a key of REASON_TEXT or null if
 * it may be unloaded. `rec` is TabNap's per-tab record ({dirty, keepAwake}).
 * opts.ignoreActive skips the "active" check (the popup always describes the
 * active tab, so "you're looking at it" would be useless there).
 */
export function protectionReason(tab, rec, settings, opts = {}) {
  const s = settings || DEFAULTS;
  const r = rec || {};
  const url = tabUrl(tab);
  if (!isWebUrl(url)) return 'internal';
  if (tab.discarded) return 'asleep';
  if (isAllowlisted(url, s.allowlist)) return 'allowlisted';
  if (r.keepAwake) return 'keep-awake';
  if (s.protectAudio && tab.audible) return 'audio';
  if (s.protectPinned && tab.pinned) return 'pinned';
  if (s.protectForms && r.dirty) return 'form';
  if (!opts.ignoreActive && tab.active) return 'active';
  if (tab.status && tab.status !== 'complete') return 'loading';
  return null;
}

/**
 * What Chrome/Edge's own Memory Saver / Sleeping Tabs should be allowed to do
 * with this tab: false for allowlisted or keep-awake tabs, true otherwise,
 * null for non-web pages (left untouched).
 */
export function wantsAutoDiscardable(tab, rec, settings) {
  const url = tabUrl(tab);
  if (!isWebUrl(url)) return null;
  const s = settings || DEFAULTS;
  if (isAllowlisted(url, s.allowlist)) return false;
  if (rec && rec.keepAwake) return false;
  return true;
}

// ------------------------------------------------------------- idle timing

/**
 * How long has this tab been in the background (ms)?
 *  - active tab: 0
 *  - TabNap saw it being left: now - rec.inactiveSince
 *  - TabNap has a record but never saw it leave (shouldn't happen; the
 *    background script repairs it): 0, so nothing is unloaded early
 *  - no record at all (tab existed before TabNap started): fall back to
 *    tab.lastAccessed, the last time it became active
 */
export function inactiveMs(tab, rec, now) {
  if (!tab || tab.active) return 0;
  let since;
  if (rec) since = rec.inactiveSince;
  else since = typeof tab.lastAccessed === 'number' ? tab.lastAccessed : null;
  if (typeof since !== 'number' || !Number.isFinite(since)) return 0;
  return Math.max(0, now - since);
}

// ------------------------------------------------------------------ sweep

/**
 * Background tabs that could be unloaded right now (no protection applies),
 * with how long each has been in the background.
 */
export function eligibleTabs(tabs, tabState, settings, now) {
  const state = tabState || {};
  const out = [];
  for (const tab of tabs || []) {
    if (!tab || typeof tab.id !== 'number') continue;
    const rec = state[tab.id];
    if (protectionReason(tab, rec, settings)) continue;
    out.push({ tab, idle: inactiveMs(tab, rec, now) });
  }
  return out;
}

/**
 * Tabs whose JavaScript memory is worth asking about: eligible, in the
 * background for at least MIN_BACKGROUND_MS, but not yet due for the idle rule.
 */
export function heavyCandidates(tabs, tabState, settings, now) {
  const s = sanitizeSettings(settings);
  if (!s.heavyEnabled) return [];
  const idleMs = s.idleMinutes * 60 * 1000;
  return eligibleTabs(tabs, tabState, s, now)
    .filter((e) => e.idle >= MIN_BACKGROUND_MS && e.idle < idleMs)
    .map((e) => e.tab.id);
}

/**
 * Decide which tabs to unload.
 *   ctx.manual    -> "Unload other tabs now": every eligible background tab
 *   ctx.pressure  -> system is low on memory
 *   ctx.heapByTab -> {tabId: usedJSHeapSize bytes} from the content script
 * Returns [{tabId, reason: 'manual'|'idle'|'pressure'|'heavy'}].
 * Automatic reasons only apply while settings.enabled is true.
 */
export function planSweep(tabs, tabState, settings, now, ctx = {}) {
  const s = sanitizeSettings(settings);
  const eligible = eligibleTabs(tabs, tabState, s, now);

  if (ctx.manual) return eligible.map((e) => ({ tabId: e.tab.id, reason: 'manual' }));
  if (!s.enabled) return [];

  const plan = [];
  const taken = new Set();
  const take = (tabId, reason) => {
    taken.add(tabId);
    plan.push({ tabId, reason });
  };

  const idleMs = s.idleMinutes * 60 * 1000;
  for (const e of eligible) if (e.idle >= idleMs) take(e.tab.id, 'idle');

  const older = eligible.filter((e) => !taken.has(e.tab.id) && e.idle >= MIN_BACKGROUND_MS);

  if (s.pressureEnabled && ctx.pressure) {
    older
      .slice()
      .sort((a, b) => b.idle - a.idle) // least recently viewed first
      .slice(0, PRESSURE_BATCH)
      .forEach((e) => take(e.tab.id, 'pressure'));
  }

  if (s.heavyEnabled && ctx.heapByTab) {
    const limit = s.heavyLimitMB * MB;
    for (const e of older) {
      if (taken.has(e.tab.id)) continue;
      const heap = ctx.heapByTab[e.tab.id];
      if (typeof heap === 'number' && Number.isFinite(heap) && heap > limit) take(e.tab.id, 'heavy');
    }
  }
  return plan;
}

/** Percentage of RAM in use, or null when unknown. */
export function memoryUsedPercent(info) {
  if (!info || !(info.capacity > 0) || typeof info.availableCapacity !== 'number') return null;
  const used = 1 - info.availableCapacity / info.capacity;
  return Math.min(100, Math.max(0, used * 100));
}

export function isUnderPressure(info, settings) {
  const s = sanitizeSettings(settings);
  const used = memoryUsedPercent(info);
  if (used === null) return false;
  return 100 - used < s.pressurePercent;
}

/** "9 of 31 tabs asleep" counts (only web pages count as tabs that can sleep). */
export function sleepCounts(tabs) {
  let asleep = 0;
  let total = 0;
  for (const tab of tabs || []) {
    if (!isWebUrl(tabUrl(tab))) continue;
    total++;
    if (tab.discarded) asleep++;
  }
  return { asleep, total };
}

export function formatMinutes(min) {
  if (min < 1) return `${Math.round(min * 60)} sec`;
  if (min < 60) return `${min} min`;
  const h = min / 60;
  return `${h} hour${h === 1 ? '' : 's'}`;
}
