import {
  addToAllowlist,
  entriesCovering,
  formatMinutes,
  normalizeSiteEntry,
  REASON_TEXT,
  removeFromAllowlist,
} from '../src/rules.js';
import { ask, loadSettings, saveSettings } from '../src/storage.js';

const $ = (id) => document.getElementById(id);
let tabId = null;
let status = null;

/** The tab this popup describes: the active tab (or ?tab=ID, used by tests). */
async function targetTabId() {
  const param = new URLSearchParams(location.search).get('tab');
  if (param && /^\d+$/.test(param)) return Number(param);
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab ? tab.id : null;
}

function plural(n, word) {
  return `${word}${n === 1 ? '' : 's'}`;
}

function showError(text) {
  $('error').textContent = text || '';
  $('error').hidden = !text;
}

function render(st) {
  const s = st.settings;
  $('enabled').checked = s.enabled;
  $('mode').textContent = s.enabled
    ? `Unloads tabs after ${formatMinutes(s.idleMinutes)}`
    : 'Paused: nothing is unloaded automatically';

  const { asleep, total } = st.counts;
  $('asleep').textContent = String(asleep);
  $('count-text').textContent = `of ${total} ${plural(total, 'tab')} asleep`;

  const used = st.memoryUsedPercent;
  $('mem').hidden = used === null;
  if (used !== null) {
    const pct = Math.round(used);
    $('mem-pct').textContent = `${pct}%`;
    $('mem-bar').style.width = `${pct}%`;
    $('mem').classList.toggle('low', 100 - used < s.pressurePercent);
  }

  const tab = st.tab;
  const web = Boolean(tab && tab.host);
  const statusEl = $('tab-status');
  statusEl.className = 'pill';
  if (!web) {
    $('host').textContent = 'Browser page';
    statusEl.textContent = REASON_TEXT.internal;
    statusEl.classList.add('protected');
  } else {
    $('host').textContent = tab.host;
    if (tab.reason) {
      statusEl.textContent = `Protected: ${tab.reasonText.charAt(0).toLowerCase()}${tab.reasonText.slice(1)}`;
      statusEl.classList.add('protected');
    } else if (!s.enabled) {
      statusEl.textContent = 'TabNap is paused';
      statusEl.classList.add('paused');
    } else {
      statusEl.textContent = `Sleeps after ${formatMinutes(s.idleMinutes)} in the background`;
    }
  }

  const site = web ? normalizeSiteEntry(tab.host) : null;
  const siteName = site && site.ok ? site.value : 'this site';
  $('allow-label').textContent = `Never unload ${siteName}`;
  $('allow').checked = Boolean(web && tab.allowEntry);
  $('allow').disabled = !web;
  $('awake').checked = Boolean(web && tab.keepAwake);
  $('awake').disabled = !web;
  for (const id of ['allow', 'awake']) {
    $(id).closest('.row').classList.toggle('disabled', !web);
  }

  const hint = $('allow-hint');
  if (web && tab.allowEntry && tab.allowEntry !== siteName) {
    hint.textContent = `Covered by ${tab.allowEntry} on your list.`;
    hint.hidden = false;
  } else {
    hint.hidden = true;
  }
}

async function refresh() {
  const st = await ask({ type: 'get-status', tabId });
  if (!st || st.error) {
    showError('TabNap is starting up, try again in a moment.');
    return;
  }
  status = st;
  render(st);
}

$('enabled').addEventListener('change', async (e) => {
  try {
    await saveSettings({ enabled: e.target.checked });
  } catch {
    showError('Couldn’t save the setting.');
  }
  refresh();
});

$('allow').addEventListener('change', async (e) => {
  showError('');
  const host = status && status.tab && status.tab.host;
  if (!host) return;
  const { allowlist } = await loadSettings();
  let next;
  if (e.target.checked) {
    const res = addToAllowlist(allowlist, host);
    if (!res.ok && !res.value) {
      showError(res.error);
      e.target.checked = false;
      return;
    }
    next = res.ok ? res.list : allowlist;
  } else {
    next = removeFromAllowlist(allowlist, entriesCovering(host, allowlist));
  }
  try {
    await saveSettings({ allowlist: next });
  } catch {
    showError('Couldn’t save: the list may be too long.');
  }
  refresh();
});

$('awake').addEventListener('change', async (e) => {
  await ask({ type: 'set-keep-awake', tabId, value: e.target.checked });
  refresh();
});

$('unload').addEventListener('click', async () => {
  const btn = $('unload');
  btn.disabled = true;
  btn.textContent = 'Unloading…';
  const res = await ask({ type: 'unload-others' });
  btn.disabled = false;
  btn.textContent = 'Unload other tabs now';
  if (!res || res.error) $('result').textContent = 'Something went wrong. Please try again.';
  else if (res.unloaded === 0) $('result').textContent = 'No other tabs could be unloaded.';
  else $('result').textContent = `Put ${res.unloaded} ${plural(res.unloaded, 'tab')} to sleep.`;
  refresh();
});

$('settings').addEventListener('click', () => {
  chrome.runtime.openOptionsPage();
  window.close();
});

chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'sync' || area === 'local') refresh();
});

async function showShortcut() {
  try {
    const commands = await chrome.commands.getAll();
    const cmd = commands.find((c) => c.name === 'unload-others');
    if (cmd && cmd.shortcut) {
      $('shortcut').textContent = cmd.shortcut;
      $('shortcut-wrap').hidden = false;
    }
  } catch {
    // commands API unavailable: just hide the hint
  }
}

(async () => {
  tabId = await targetTabId();
  await Promise.all([refresh(), showShortcut()]);
})();
