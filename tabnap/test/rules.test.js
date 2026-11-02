// Unit tests for the pure decision logic. Run: npm test  (node --test)
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  addToAllowlist,
  DEFAULTS,
  entriesCovering,
  heavyCandidates,
  hostOf,
  inactiveMs,
  isAllowlisted,
  isUnderPressure,
  matchingAllowEntry,
  memoryUsedPercent,
  normalizeSiteEntry,
  planSweep,
  PRESSURE_BATCH,
  protectionReason,
  removeFromAllowlist,
  sanitizeSettings,
  sleepCounts,
  wantsAutoDiscardable,
} from '../src/rules.js';

const NOW = 1_800_000_000_000;
const MIN = 60 * 1000;
const MB = 1024 * 1024;

let nextId = 1;
function tab(over = {}) {
  return {
    id: nextId++,
    windowId: 1,
    url: 'https://example.com/',
    active: false,
    audible: false,
    pinned: false,
    discarded: false,
    status: 'complete',
    ...over,
  };
}
/** Settings with automatic modes off unless asked for, so each test is focused. */
function settings(over = {}) {
  return sanitizeSettings({ ...DEFAULTS, pressureEnabled: false, heavyEnabled: false, ...over });
}
const idleFor = (ms) => ({ inactiveSince: NOW - ms, dirty: false, keepAwake: false });

// ------------------------------------------------------------- allowlist

describe('normalizeSiteEntry', () => {
  const ok = {
    'https://www.YouTube.com/watch?v=1': 'youtube.com',
    'www.youtube.com': 'youtube.com',
    '*.youtube.com': 'youtube.com',
    '*://*.youtube.com/*': 'youtube.com',
    '  YouTube.com  ': 'youtube.com',
    'youtube.com/': 'youtube.com',
    'mail.google.com': 'mail.google.com',
    'https://mail.google.com/mail/u/0/#inbox': 'mail.google.com',
    'localhost:3000': 'localhost:3000',
    'http://localhost:3000/app': 'localhost:3000',
    localhost: 'localhost',
    'https://example.com:443/': 'example.com',
    'http://example.com:80': 'example.com',
    'example.com:443': 'example.com',
    'example.com:8443': 'example.com:8443',
    'https://example.com:8443/x': 'example.com:8443',
    '192.168.1.10:8080': '192.168.1.10:8080',
    'http://[::1]:3000/': '[::1]:3000',
    'www.com': 'www.com',
    'docs.example.co.uk.': 'docs.example.co.uk',
    'münchen.de': 'xn--mnchen-3ya.de',
    'https://user:pw@example.com/': 'example.com',
  };
  for (const [input, value] of Object.entries(ok)) {
    test(`${JSON.stringify(input)} -> ${value}`, () => {
      assert.deepEqual(normalizeSiteEntry(input), { ok: true, value });
    });
  }

  const bad = [
    '',
    '   ',
    'hello world',
    '!!!',
    'a..b',
    '-bad-.com',
    '*',
    'http://',
    'chrome://settings',
    'edge://settings',
    'about:blank',
    'file:///C:/Users/me/page.html',
    'javascript:alert(1)',
    'mailto:a@b.com',
    'ftp://example.com',
    'chrome-extension://abcdef/popup.html',
    'foo.*.com',
    null,
    42,
  ];
  for (const input of bad) {
    test(`rejects ${JSON.stringify(input)} with a message`, () => {
      const res = normalizeSiteEntry(input);
      assert.equal(res.ok, false);
      assert.equal(typeof res.error, 'string');
      assert.ok(res.error.length > 10);
    });
  }
});

describe('hostOf', () => {
  test('web URLs', () => {
    assert.equal(hostOf('https://www.YouTube.com/watch?v=1'), 'www.youtube.com');
    assert.equal(hostOf('http://localhost:3000/'), 'localhost:3000');
    assert.equal(hostOf('https://example.com:443/'), 'example.com');
    assert.equal(hostOf('http://127.0.0.1:8080/x'), '127.0.0.1:8080');
  });
  test('non-web URLs and junk', () => {
    for (const u of ['chrome://newtab/', 'edge://settings', 'file:///x', 'about:blank', 'chrome-extension://id/x.html', '', 'nope', undefined]) {
      assert.equal(hostOf(u), null, String(u));
    }
  });
});

describe('isAllowlisted', () => {
  test('entry covers its host and all subdomains', () => {
    const list = ['google.com'];
    assert.ok(isAllowlisted('https://google.com/', list));
    assert.ok(isAllowlisted('https://www.google.com/search?q=1', list));
    assert.ok(isAllowlisted('https://mail.google.com/mail', list));
    assert.ok(isAllowlisted('https://a.b.google.com/', list));
  });
  test('a subdomain entry does not cover its parent or siblings', () => {
    const list = ['mail.google.com'];
    assert.ok(isAllowlisted('https://mail.google.com/', list));
    assert.ok(!isAllowlisted('https://google.com/', list));
    assert.ok(!isAllowlisted('https://www.google.com/', list));
    assert.ok(!isAllowlisted('https://docs.google.com/', list));
  });
  test('matches on label boundaries only', () => {
    assert.ok(!isAllowlisted('https://notgoogle.com/', ['google.com']));
    assert.ok(!isAllowlisted('https://google.com.evil.net/', ['google.com']));
  });
  test('ports: an entry with a port matches only that port', () => {
    const list = ['localhost:3000'];
    assert.ok(isAllowlisted('http://localhost:3000/', list));
    assert.ok(isAllowlisted('http://app.localhost:3000/', list));
    assert.ok(!isAllowlisted('http://localhost:4000/', list));
    assert.ok(!isAllowlisted('http://localhost/', list));
  });
  test('ports: an entry without a port matches every port', () => {
    assert.ok(isAllowlisted('http://localhost:3000/', ['localhost']));
    assert.ok(isAllowlisted('http://localhost/', ['localhost']));
    assert.ok(isAllowlisted('https://example.com:8443/', ['example.com']));
  });
  test('IP addresses match exactly', () => {
    assert.ok(isAllowlisted('http://10.0.0.1/', ['10.0.0.1']));
    assert.ok(!isAllowlisted('http://110.0.0.1/', ['10.0.0.1']));
  });
  test('non-web pages and empty lists never match', () => {
    assert.ok(!isAllowlisted('chrome://settings', ['settings']));
    assert.ok(!isAllowlisted('https://example.com/', []));
    assert.ok(!isAllowlisted('https://example.com/', undefined));
  });
  test('accepts a bare host as well as a URL', () => {
    assert.equal(matchingAllowEntry('mail.google.com', ['google.com']), 'google.com');
    assert.equal(matchingAllowEntry('localhost:3000', ['localhost:3000']), 'localhost:3000');
  });
});

describe('allowlist editing', () => {
  test('add normalizes, sorts and refuses duplicates', () => {
    const a = addToAllowlist(['zoom.us'], 'https://www.YouTube.com/watch?v=1');
    assert.deepEqual(a, { ok: true, value: 'youtube.com', list: ['youtube.com', 'zoom.us'] });
    const dup = addToAllowlist(a.list, '*.youtube.com');
    assert.equal(dup.ok, false);
    assert.equal(dup.value, 'youtube.com');
    assert.equal(addToAllowlist([], 'not a site').ok, false);
  });
  test('remove and entriesCovering', () => {
    const list = ['google.com', 'mail.google.com', 'youtube.com'];
    assert.deepEqual(entriesCovering('mail.google.com', list), ['google.com', 'mail.google.com']);
    assert.deepEqual(removeFromAllowlist(list, entriesCovering('mail.google.com', list)), ['youtube.com']);
    assert.deepEqual(removeFromAllowlist(list, 'youtube.com'), ['google.com', 'mail.google.com']);
  });
  test('sanitizeSettings cleans a stored allowlist', () => {
    const s = sanitizeSettings({ allowlist: ['WWW.Example.com', 'example.com', 'chrome://x', 5, 'localhost:3000'] });
    assert.deepEqual(s.allowlist, ['example.com', 'localhost:3000']);
  });
});

// ----------------------------------------------------------- protections

describe('protectionReason', () => {
  const s = settings({ allowlist: ['youtube.com'] });

  test('an ordinary background tab is not protected', () => {
    assert.equal(protectionReason(tab(), idleFor(MIN), s), null);
  });
  test('non-web pages', () => {
    for (const url of ['chrome://settings/', 'edge://newtab/', 'chrome-extension://x/p.html', 'file:///tmp/a.html', 'about:blank', '']) {
      assert.equal(protectionReason(tab({ url }), null, s), 'internal', url);
    }
  });
  test('uses pendingUrl when url is empty', () => {
    assert.equal(protectionReason(tab({ url: '', pendingUrl: 'https://x.com/', status: 'loading' }), null, s), 'loading');
  });
  test('already discarded', () => {
    assert.equal(protectionReason(tab({ discarded: true }), null, s), 'asleep');
  });
  test('active tab', () => {
    assert.equal(protectionReason(tab({ active: true }), null, s), 'active');
    assert.equal(protectionReason(tab({ active: true }), null, s, { ignoreActive: true }), null);
  });
  test('allowlisted site (incl. subdomain)', () => {
    assert.equal(protectionReason(tab({ url: 'https://m.youtube.com/watch' }), null, s), 'allowlisted');
  });
  test('keep awake', () => {
    assert.equal(protectionReason(tab(), { keepAwake: true }, s), 'keep-awake');
  });
  test('audio, honoring the setting', () => {
    assert.equal(protectionReason(tab({ audible: true }), null, s), 'audio');
    assert.equal(protectionReason(tab({ audible: true }), null, settings({ protectAudio: false })), null);
  });
  test('pinned, honoring the setting', () => {
    assert.equal(protectionReason(tab({ pinned: true }), null, s), 'pinned');
    assert.equal(protectionReason(tab({ pinned: true }), null, settings({ protectPinned: false })), null);
  });
  test('unsaved form text, honoring the setting', () => {
    assert.equal(protectionReason(tab(), { dirty: true }, s), 'form');
    assert.equal(protectionReason(tab(), { dirty: true }, settings({ protectForms: false })), null);
  });
  test('still loading', () => {
    assert.equal(protectionReason(tab({ status: 'loading' }), null, s), 'loading');
  });
});

describe('wantsAutoDiscardable', () => {
  const s = settings({ allowlist: ['youtube.com'] });
  test('false for allowlisted or keep-awake tabs, true otherwise, null for browser pages', () => {
    assert.equal(wantsAutoDiscardable(tab({ url: 'https://www.youtube.com/' }), null, s), false);
    assert.equal(wantsAutoDiscardable(tab(), { keepAwake: true }, s), false);
    assert.equal(wantsAutoDiscardable(tab(), null, s), true);
    assert.equal(wantsAutoDiscardable(tab({ url: 'chrome://newtab/' }), null, s), null);
  });
});

// ----------------------------------------------------------- idle timing

describe('inactiveMs', () => {
  test('active tab is never idle', () => {
    assert.equal(inactiveMs(tab({ active: true, lastAccessed: NOW - 99 * MIN }), idleFor(99 * MIN), NOW), 0);
  });
  test('uses the time the tab was left, not lastAccessed, when there is a record', () => {
    const t = tab({ lastAccessed: NOW - 60 * MIN });
    assert.equal(inactiveMs(t, idleFor(2 * MIN), NOW), 2 * MIN);
  });
  test('record without a leave time counts as 0 (never unload early)', () => {
    const t = tab({ lastAccessed: NOW - 60 * MIN });
    assert.equal(inactiveMs(t, { inactiveSince: null }, NOW), 0);
  });
  test('falls back to lastAccessed only when there is no record', () => {
    assert.equal(inactiveMs(tab({ lastAccessed: NOW - 7 * MIN }), undefined, NOW), 7 * MIN);
    assert.equal(inactiveMs(tab(), undefined, NOW), 0);
  });
  test('never negative', () => {
    assert.equal(inactiveMs(tab(), { inactiveSince: NOW + 5000 }, NOW), 0);
  });
});

// ----------------------------------------------------------------- sweep

describe('planSweep: idle rule', () => {
  test('unloads tabs at or past the idle time, keeps younger ones', () => {
    const s = settings({ idleMinutes: 15 });
    const old = tab();
    const exact = tab();
    const young = tab();
    const state = { [old.id]: idleFor(40 * MIN), [exact.id]: idleFor(15 * MIN), [young.id]: idleFor(15 * MIN - 1) };
    const plan = planSweep([old, exact, young], state, s, NOW);
    assert.deepEqual(plan, [
      { tabId: old.id, reason: 'idle' },
      { tabId: exact.id, reason: 'idle' },
    ]);
  });
  test('sub-minute idle times work (used by the end-to-end test)', () => {
    const t = tab();
    const plan = planSweep([t], { [t.id]: idleFor(4000) }, settings({ idleMinutes: 0.05 }), NOW);
    assert.deepEqual(plan, [{ tabId: t.id, reason: 'idle' }]);
  });
  test('every protection is respected', () => {
    const s = settings({ idleMinutes: 1, allowlist: ['youtube.com'] });
    const tabs = [
      tab({ active: true }),
      tab({ url: 'https://www.youtube.com/watch' }),
      tab({ audible: true }),
      tab({ pinned: true }),
      tab(), // dirty
      tab(), // keep awake
      tab({ status: 'loading' }),
      tab({ url: 'chrome://settings/' }),
      tab({ discarded: true }),
    ];
    const state = Object.fromEntries(tabs.map((t) => [t.id, idleFor(500 * MIN)]));
    state[tabs[4].id].dirty = true;
    state[tabs[5].id].keepAwake = true;
    assert.deepEqual(planSweep(tabs, state, s, NOW), []);
    assert.deepEqual(planSweep(tabs, state, s, NOW, { manual: true }), []);
  });
  test('nothing automatic while paused, but manual still works', () => {
    const s = settings({ enabled: false, idleMinutes: 1 });
    const t = tab();
    const state = { [t.id]: idleFor(60 * MIN) };
    assert.deepEqual(planSweep([t], state, s, NOW, { pressure: true }), []);
    assert.deepEqual(planSweep([t], state, s, NOW, { manual: true }), [{ tabId: t.id, reason: 'manual' }]);
  });
  test('manual unloads every eligible background tab regardless of idle time', () => {
    const s = settings({ idleMinutes: 240 });
    const a = tab();
    const b = tab();
    const active = tab({ active: true });
    const state = { [a.id]: idleFor(1000), [b.id]: idleFor(0), [active.id]: { inactiveSince: null } };
    assert.deepEqual(planSweep([a, b, active], state, s, NOW, { manual: true }), [
      { tabId: a.id, reason: 'manual' },
      { tabId: b.id, reason: 'manual' },
    ]);
  });
});

describe('planSweep: memory pressure', () => {
  const s = settings({ idleMinutes: 60, pressureEnabled: true });

  test('least recently viewed first, at most 5, only tabs left ≥ 1 minute ago', () => {
    const minutes = [3, 50, 2, 10, 0.5, 30, 1, 20, 59];
    const tabs = minutes.map(() => tab());
    const state = Object.fromEntries(tabs.map((t, i) => [t.id, idleFor(minutes[i] * MIN)]));
    const plan = planSweep(tabs, state, s, NOW, { pressure: true });
    assert.equal(plan.length, PRESSURE_BATCH);
    assert.ok(plan.every((p) => p.reason === 'pressure'));
    const order = plan.map((p) => minutes[tabs.findIndex((t) => t.id === p.tabId)]);
    assert.deepEqual(order, [59, 50, 30, 20, 10]);
  });
  test('tabs under a minute are left alone', () => {
    const t = tab();
    assert.deepEqual(planSweep([t], { [t.id]: idleFor(59 * 1000) }, s, NOW, { pressure: true }), []);
  });
  test('idle tabs are unloaded on top of the pressure batch, never twice', () => {
    const tabs = Array.from({ length: 8 }, () => tab());
    const state = Object.fromEntries(tabs.map((t, i) => [t.id, idleFor((i < 2 ? 90 : 5 + i) * MIN)]));
    const plan = planSweep(tabs, state, s, NOW, { pressure: true });
    assert.equal(plan.filter((p) => p.reason === 'idle').length, 2);
    assert.equal(plan.filter((p) => p.reason === 'pressure').length, 5);
    assert.equal(new Set(plan.map((p) => p.tabId)).size, plan.length);
  });
  test('no pressure, or pressure mode off: nothing extra', () => {
    const t = tab();
    const state = { [t.id]: idleFor(10 * MIN) };
    assert.deepEqual(planSweep([t], state, s, NOW, { pressure: false }), []);
    assert.deepEqual(planSweep([t], state, settings({ idleMinutes: 60 }), NOW, { pressure: true }), []);
  });
  test('protected tabs are never picked under pressure', () => {
    const a = tab({ audible: true });
    const b = tab({ pinned: true });
    const state = { [a.id]: idleFor(30 * MIN), [b.id]: idleFor(30 * MIN) };
    assert.deepEqual(planSweep([a, b], state, s, NOW, { pressure: true }), []);
  });
});

describe('planSweep: heavy tabs', () => {
  const s = settings({ idleMinutes: 60, heavyEnabled: true, heavyLimitMB: 400 });

  test('unloads a background tab over the JavaScript memory limit early', () => {
    const heavy = tab();
    const light = tab();
    const unknown = tab();
    const state = { [heavy.id]: idleFor(2 * MIN), [light.id]: idleFor(2 * MIN), [unknown.id]: idleFor(2 * MIN) };
    const heapByTab = { [heavy.id]: 401 * MB, [light.id]: 399 * MB }; // unknown: no reading
    assert.deepEqual(planSweep([heavy, light, unknown], state, s, NOW, { heapByTab }), [
      { tabId: heavy.id, reason: 'heavy' },
    ]);
  });
  test('waits until the tab has been in the background for a minute', () => {
    const t = tab();
    assert.deepEqual(planSweep([t], { [t.id]: idleFor(30 * 1000) }, s, NOW, { heapByTab: { [t.id]: 2000 * MB } }), []);
  });
  test('ignores junk readings and respects the switch and protections', () => {
    const t = tab();
    const state = { [t.id]: idleFor(5 * MIN) };
    for (const heap of [undefined, null, NaN, '900000000']) {
      assert.deepEqual(planSweep([t], state, s, NOW, { heapByTab: { [t.id]: heap } }), []);
    }
    const big = { heapByTab: { [t.id]: 2000 * MB } };
    assert.deepEqual(planSweep([t], state, settings({ idleMinutes: 60 }), NOW, big), []);
    assert.deepEqual(planSweep([t], { [t.id]: { ...idleFor(5 * MIN), dirty: true } }, s, NOW, big), []);
  });
  test('heavyCandidates lists background tabs ≥ 1 minute old not yet due for the idle rule', () => {
    const fresh = tab();
    const middle = tab();
    const due = tab();
    const active = tab({ active: true });
    const state = { [fresh.id]: idleFor(10 * 1000), [middle.id]: idleFor(5 * MIN), [due.id]: idleFor(61 * MIN) };
    assert.deepEqual(heavyCandidates([fresh, middle, due, active], state, s, NOW), [middle.id]);
    assert.deepEqual(heavyCandidates([middle], state, settings({ idleMinutes: 60 }), NOW), []);
  });
});

// ---------------------------------------------------------------- misc

describe('memory and counts', () => {
  test('memoryUsedPercent / isUnderPressure', () => {
    assert.equal(memoryUsedPercent({ capacity: 1000, availableCapacity: 250 }), 75);
    assert.equal(memoryUsedPercent(null), null);
    assert.equal(memoryUsedPercent({ capacity: 0, availableCapacity: 0 }), null);
    const s = settings({ pressurePercent: 15 });
    assert.equal(isUnderPressure({ capacity: 1000, availableCapacity: 100 }, s), true);
    assert.equal(isUnderPressure({ capacity: 1000, availableCapacity: 200 }, s), false);
    assert.equal(isUnderPressure(null, s), false);
  });
  test('sleepCounts counts web tabs only', () => {
    const tabs = [
      tab({ discarded: true }),
      tab({ discarded: true }),
      tab(),
      tab({ url: 'chrome://newtab/' }),
    ];
    assert.deepEqual(sleepCounts(tabs), { asleep: 2, total: 3 });
  });
  test('sanitizeSettings repairs junk and keeps valid values', () => {
    const s = sanitizeSettings({ idleMinutes: -3, pressurePercent: 'x', heavyLimitMB: 0, enabled: 'yes', protectAudio: false });
    assert.equal(s.idleMinutes, DEFAULTS.idleMinutes);
    assert.equal(s.pressurePercent, DEFAULTS.pressurePercent);
    assert.equal(s.heavyLimitMB, DEFAULTS.heavyLimitMB);
    assert.equal(s.enabled, true);
    assert.equal(s.protectAudio, false);
    assert.equal(sanitizeSettings({ idleMinutes: '30' }).idleMinutes, 30);
    assert.deepEqual(sanitizeSettings(undefined), { ...DEFAULTS, allowlist: [] });
  });
});
