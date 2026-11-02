// End-to-end test: loads the unpacked extension into Chromium with Playwright
// and checks real tab unloading. Run: npm run test:e2e
//
// Needs Playwright + its Chromium. If `require('playwright')` can't find a
// global install, set NODE_PATH to the folder containing it.
// Screenshots go to $TABNAP_SHOTS (default: <tmp>/tabnap-e2e); the throwaway
// browser profile goes under $TABNAP_TMP (default: the OS temp folder).
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const EXT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SHOTS = process.env.TABNAP_SHOTS || path.join(os.tmpdir(), 'tabnap-e2e');
const TMP = process.env.TABNAP_TMP || os.tmpdir();

function loadPlaywright() {
  const require = createRequire(import.meta.url);
  const candidates = ['playwright'];
  try {
    candidates.push(path.join(execSync('npm root -g', { encoding: 'utf8' }).trim(), 'playwright'));
  } catch {
    // npm not on PATH
  }
  for (const id of candidates) {
    try {
      return require(id);
    } catch {
      // try the next one
    }
  }
  throw new Error('Playwright not found: install it globally or set NODE_PATH to the folder that contains it.');
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function waitFor(fn, what, timeout = 15000) {
  const end = Date.now() + timeout;
  let last;
  while (Date.now() < end) {
    last = await fn();
    if (last) return last;
    await sleep(100);
  }
  throw new Error(`Timed out waiting for ${what} (last value: ${JSON.stringify(last)})`);
}

// --------------------------------------------------------------- fixtures

let server;
let port;
let ctx;
let userDataDir;
let sw;
let extId;
let controller; // an extension page used to send messages like the popup does
const pageErrors = [];
const tabs = {};

function startServer() {
  server = http.createServer((req, res) => {
    res.setHeader('content-type', 'text/html; charset=utf-8');
    if (req.url.startsWith('/form')) {
      res.end('<!doctype html><title>Form</title><h1>Write something</h1><form><textarea id="msg"></textarea><button>Send</button></form>');
    } else {
      const name = decodeURIComponent(req.url.split('/').pop() || 'page');
      res.end(`<!doctype html><title>${name}</title><h1>${name}</h1><p>A test page.</p>`);
    }
  });
  return new Promise((resolve) => server.listen(0, '127.0.0.1', () => resolve(server.address().port)));
}

const swEval = (fn, arg) => sw.evaluate(fn, arg);
const getTab = (id) => swEval((id) => chrome.tabs.get(id), id);
const send = (msg) => controller.evaluate((m) => chrome.runtime.sendMessage(m), msg);
const sessionState = () => swEval(async () => (await chrome.storage.session.get('tabnap-state'))['tabnap-state']);
const setSettings = (patch) => swEval((p) => chrome.storage.sync.set(p), patch);

async function openTab(url) {
  const tab = await swEval((url) => chrome.tabs.create({ url, active: false }), url);
  await waitFor(async () => (await getTab(tab.id)).status === 'complete', `${url} to load`);
  return tab.id;
}

async function activate(tabId) {
  await swEval((id) => chrome.tabs.update(id, { active: true }), tabId);
  await waitFor(async () => (await getTab(tabId)).active, `tab ${tabId} to become active`);
}

function watchErrors(page, label) {
  page.on('console', (msg) => {
    if (msg.type() === 'error') pageErrors.push(`${label}: ${msg.text()}`);
  });
  page.on('pageerror', (err) => pageErrors.push(`${label}: ${err.message}`));
}

before(async () => {
  fs.mkdirSync(SHOTS, { recursive: true });
  port = await startServer();
  const { chromium } = loadPlaywright();
  fs.mkdirSync(TMP, { recursive: true });
  userDataDir = fs.mkdtempSync(path.join(TMP, 'tabnap-profile-'));
  ctx = await chromium.launchPersistentContext(userDataDir, {
    channel: 'chromium', // the full browser; the headless shell can't run extensions
    headless: !process.env.HEADED,
    // Playwright's default --disable-field-trial-config makes Chromium discard a
    // tab by swapping in a new one, which crashes the browser while Playwright
    // is attached. Without it Chromium discards in place, like regular Chrome.
    ignoreDefaultArgs: ['--disable-field-trial-config'],
    args: [`--disable-extensions-except=${EXT}`, `--load-extension=${EXT}`],
  });
  const isOurs = (w) => w.url().endsWith('/src/background.js');
  sw = ctx.serviceWorkers().find(isOurs) || (await ctx.waitForEvent('serviceworker', { predicate: isOurs }));
  extId = new URL(sw.url()).host;
  sw.on('console', (msg) => {
    if (msg.type() === 'error') pageErrors.push(`service worker: ${msg.text()}`);
  });

  // Controller: the options page in its own window, so the test window's
  // active tab stays a normal web page.
  const pagePromise = ctx.waitForEvent('page', { predicate: (p) => p.url().includes('/options/options.html') });
  await swEval((url) => chrome.windows.create({ url, focused: false }), `chrome-extension://${extId}/options/options.html`);
  controller = await pagePromise;
  watchErrors(controller, 'options(controller)');
  await controller.waitForLoadState('load');
});

after(async () => {
  if (ctx) await ctx.close();
  if (server) server.close();
  if (userDataDir) fs.rmSync(userDataDir, { recursive: true, force: true });
});

// ------------------------------------------------------------------ tests

test('unloads an idle background tab, protects active/allowlisted/typed-in tabs', async () => {
  await setSettings({
    idleMinutes: 0.05, // 3 seconds; the UI only offers 1 minute and up
    pressureEnabled: false,
    heavyEnabled: false,
    allowlist: [`localhost:${port}`],
  });

  tabs.idle = await openTab(`http://127.0.0.1:${port}/page/idle`);
  tabs.allow = await openTab(`http://localhost:${port}/page/allowlisted`);
  tabs.form = await openTab(`http://127.0.0.1:${port}/form`);
  tabs.main = await openTab(`http://127.0.0.1:${port}/page/main`);

  // Type into the form while looking at it, then switch to the main tab.
  await activate(tabs.form);
  const formPage = await waitFor(() => ctx.pages().find((p) => p.url().endsWith('/form')), 'form page');
  await formPage.click('#msg');
  await formPage.keyboard.type('half-written reply');
  await waitFor(async () => (await sessionState())?.tabs?.[tabs.form]?.dirty === true, 'form tab marked dirty');
  await activate(tabs.main);

  const st = await sessionState();
  assert.equal(st.tabs[tabs.main].inactiveSince, null, 'active tab has no inactiveSince');
  assert.equal(typeof st.tabs[tabs.form].inactiveSince, 'number', 'tab left behind gets inactiveSince');

  // Allowlisted tab is also shielded from Chrome's own Memory Saver.
  await waitFor(async () => (await getTab(tabs.allow)).autoDiscardable === false, 'allowlisted tab autoDiscardable=false');
  assert.equal((await getTab(tabs.idle)).autoDiscardable, true);

  await sleep(3500); // let every background tab pass the 3-second idle time
  const res = await send({ type: 'sweep-now' });
  console.log('sweep-now ->', JSON.stringify(res));

  assert.equal((await getTab(tabs.idle)).discarded, true, 'idle background tab is unloaded');
  assert.equal((await getTab(tabs.main)).discarded, false, 'active tab is kept');
  assert.equal((await getTab(tabs.allow)).discarded, false, 'allowlisted tab is kept');
  assert.equal((await getTab(tabs.form)).discarded, false, 'tab with typed text is kept');
  assert.ok(!res.planned.some((p) => [tabs.main, tabs.allow, tabs.form].includes(p.tabId)));
});

test('"Unload other tabs now" unloads every eligible tab and respects keep-awake', async () => {
  await setSettings({ idleMinutes: 240 }); // automatic rule can't be the reason now
  tabs.extra1 = await openTab(`http://127.0.0.1:${port}/page/extra-1`);
  tabs.extra2 = await openTab(`http://127.0.0.1:${port}/page/extra-2`);
  tabs.awake = await openTab(`http://127.0.0.1:${port}/page/keep-awake`);

  assert.deepEqual(await send({ type: 'set-keep-awake', tabId: tabs.awake, value: true }), { ok: true });
  await waitFor(async () => (await getTab(tabs.awake)).autoDiscardable === false, 'keep-awake tab autoDiscardable=false');

  const before = (await swEval(() => chrome.storage.local.get('stats'))).stats?.total || 0;
  const res = await send({ type: 'unload-others' });
  console.log('unload-others ->', JSON.stringify(res));

  assert.equal((await getTab(tabs.extra1)).discarded, true);
  assert.equal((await getTab(tabs.extra2)).discarded, true);
  assert.equal((await getTab(tabs.awake)).discarded, false, 'keep-awake tab is kept');
  assert.equal((await getTab(tabs.allow)).discarded, false, 'allowlisted tab is kept');
  assert.equal((await getTab(tabs.form)).discarded, false, 'tab with typed text is kept');
  assert.equal((await getTab(tabs.main)).discarded, false, 'active tab is kept');
  assert.equal(res.unloaded, 2);
  const after = (await swEval(() => chrome.storage.local.get('stats'))).stats.total;
  assert.equal(after - before, 2, 'counter goes up');
});

test('content script answers the probe; form text cleared -> tab can sleep again', async () => {
  const formPage = ctx.pages().find((p) => p.url().endsWith('/form'));
  const reply = await swEval((id) => chrome.tabs.sendMessage(id, { type: 'tabnap-probe' }, { frameId: 0 }), tabs.form);
  assert.equal(reply.dirty, true);
  assert.ok(reply.heap === null || typeof reply.heap === 'number');
  console.log('probe ->', JSON.stringify(reply));

  // The page clears the field itself (as chat apps do after sending).
  await formPage.evaluate(() => {
    document.getElementById('msg').value = '';
  });
  await send({ type: 'unload-others' });
  assert.equal((await getTab(tabs.form)).discarded, true, 'cleared form tab is unloaded');
});

test('removing a site restores autoDiscardable; a sleeping tab reloads when clicked', async () => {
  await setSettings({ allowlist: [] });
  await waitFor(async () => (await getTab(tabs.allow)).autoDiscardable === true, 'autoDiscardable restored');

  await activate(tabs.idle);
  await waitFor(async () => {
    const t = await getTab(tabs.idle);
    return !t.discarded && t.status === 'complete';
  }, 'discarded tab to reload');
});

test('popup and options pages render without errors (screenshots)', async () => {
  await setSettings({
    allowlist: [`localhost:${port}`, 'github.com', 'mail.google.com', 'youtube.com'],
    idleMinutes: 15,
    pressureEnabled: true,
    heavyEnabled: true,
  });

  for (const scheme of ['light', 'dark']) {
    const popup = await ctx.newPage();
    watchErrors(popup, `popup(${scheme})`);
    await popup.emulateMedia({ colorScheme: scheme });
    await popup.setViewportSize({ width: 330, height: 520 });
    await popup.goto(`chrome-extension://${extId}/popup/popup.html?tab=${tabs.allow}`);
    await popup.waitForFunction(() => /tabs? asleep/.test(document.getElementById('count-text').textContent));
    await popup.waitForFunction(() => document.getElementById('host').textContent.includes('localhost'));
    assert.equal(await popup.isChecked('#allow'), true, 'popup shows the site as never-unload');
    assert.match(await popup.textContent('#tab-status'), /never-unload list/);
    const file = path.join(SHOTS, `popup-${scheme}.png`);
    await popup.screenshot({ path: file, fullPage: true });
    console.log('screenshot', file);

    if (scheme === 'light') {
      await popup.click('#unload');
      await popup.waitForFunction(() => /Put \d+ tabs? to sleep|No other tabs/.test(document.getElementById('result').textContent));
      console.log('popup unload ->', await popup.textContent('#result'));
    }
    await popup.close();
  }

  for (const scheme of ['light', 'dark']) {
    const options = await ctx.newPage();
    watchErrors(options, `options(${scheme})`);
    await options.emulateMedia({ colorScheme: scheme });
    await options.setViewportSize({ width: 900, height: 900 });
    await options.goto(`chrome-extension://${extId}/options/options.html`);
    await options.waitForFunction(() => document.querySelectorAll('#allowlist li').length >= 4);
    assert.equal(await options.inputValue('#idleMinutes'), '15');

    if (scheme === 'light') {
      await options.fill('#add-input', 'not a site!');
      await options.click('#add-form button');
      await options.waitForFunction(() => document.getElementById('add-msg').classList.contains('error'));
      console.log('options rejects junk ->', await options.textContent('#add-msg'));
      await options.fill('#add-input', 'https://www.Example.com/some/page?x=1');
      await options.click('#add-form button');
      await options.waitForFunction(() =>
        [...document.querySelectorAll('#allowlist li span')].some((s) => s.textContent === 'example.com'),
      );
    }
    const file = path.join(SHOTS, `options-${scheme}.png`);
    await options.screenshot({ path: file, fullPage: true });
    console.log('screenshot', file);
    await options.close();
  }

  const { allowlist } = await swEval(() => chrome.storage.sync.get('allowlist'));
  assert.ok(allowlist.includes('example.com'), 'entry added through the options page was saved');
  assert.deepEqual(pageErrors, [], 'no console errors in the extension');
});

test(
  'low-memory and heavy-tab modes (slow: waits 65 s)',
  { skip: !process.env.TABNAP_SLOW && 'set TABNAP_SLOW=1 to run' },
  async () => {
    // Start from a clean slate: everything unprotected in the background is asleep.
    await send({ type: 'unload-others' });
    await setSettings({
      enabled: false, // keep the 30-second alarm out of the way while we wait
      idleMinutes: 240,
      pressureEnabled: true,
      pressurePercent: 99.9, // "free memory below 99.9%" is always true
      heavyEnabled: true,
      heavyLimitMB: 0.5, // even a tiny test page uses more JavaScript memory than this
    });
    const ids = [];
    for (let i = 1; i <= 7; i++) ids.push(await openTab(`http://127.0.0.1:${port}/page/old-${i}`));
    const before = (await swEval(() => chrome.storage.local.get('stats'))).stats;

    await sleep(65000);
    await setSettings({ enabled: true });
    const res = await send({ type: 'sweep-now' });
    console.log('pressure/heavy sweep ->', JSON.stringify(res));

    for (const id of ids) assert.equal((await getTab(id)).discarded, true, `tab ${id} unloaded`);
    const after = (await swEval(() => chrome.storage.local.get('stats'))).stats;
    assert.equal(after.pressure - before.pressure, 5, 'pressure unloads at most 5 per check');
    assert.equal(after.heavy - before.heavy, 2, 'the rest go because of their JavaScript memory');
    if (res.planned.length === 7) {
      assert.deepEqual(
        res.planned.filter((p) => p.reason === 'pressure').map((p) => p.tabId),
        ids.slice(0, 5),
        'oldest first',
      );
    }
  },
);
