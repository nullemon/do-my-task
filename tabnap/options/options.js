import {
  addToAllowlist,
  DEFAULTS,
  formatMinutes,
  HEAVY_CHOICES,
  IDLE_CHOICES,
  memoryUsedPercent,
  PRESSURE_CHOICES,
  removeFromAllowlist,
} from '../src/rules.js';
import { loadSettings, loadStats, saveSettings } from '../src/storage.js';

const $ = (id) => document.getElementById(id);
const CHECKBOXES = ['enabled', 'protectAudio', 'protectPinned', 'protectForms', 'pressureEnabled', 'heavyEnabled'];
const SELECTS = {
  idleMinutes: { choices: IDLE_CHOICES, label: (v) => formatMinutes(v) },
  pressurePercent: { choices: PRESSURE_CHOICES, label: (v) => `${v}% free` },
  heavyLimitMB: { choices: HEAVY_CHOICES, label: (v) => (v >= 1000 ? `${v / 1000} GB` : `${v} MB`) },
};

let savedTimer = 0;
function flashSaved(text = 'Saved') {
  const el = $('saved');
  el.textContent = text;
  el.classList.add('show');
  clearTimeout(savedTimer);
  savedTimer = setTimeout(() => el.classList.remove('show'), 1400);
}

async function save(patch) {
  try {
    await saveSettings(patch);
    flashSaved();
    return true;
  } catch {
    flashSaved('Couldn’t save');
    return false;
  }
}

function fillSelect(id, value) {
  const { choices, label } = SELECTS[id];
  const select = $(id);
  const values = choices.includes(value) ? choices : [...choices, value].sort((a, b) => a - b);
  select.replaceChildren(
    ...values.map((v) => {
      const opt = document.createElement('option');
      opt.value = String(v);
      opt.textContent = label(v);
      return opt;
    }),
  );
  select.value = String(value);
}

function renderAllowlist(list) {
  const ul = $('allowlist');
  ul.replaceChildren(
    ...list.map((host) => {
      const li = document.createElement('li');
      const name = document.createElement('span');
      name.textContent = host;
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'remove';
      btn.textContent = 'Remove';
      btn.setAttribute('aria-label', `Remove ${host}`);
      btn.addEventListener('click', async () => {
        const { allowlist } = await loadSettings();
        if (await save({ allowlist: removeFromAllowlist(allowlist, host) })) {
          setMsg(`Removed ${host}.`, 'ok');
        }
      });
      li.append(name, btn);
      return li;
    }),
  );
  $('allow-empty').hidden = list.length > 0;
}

function render(s) {
  for (const id of CHECKBOXES) $(id).checked = s[id];
  for (const id of Object.keys(SELECTS)) fillSelect(id, s[id]);
  $('pressurePercent').disabled = !s.pressureEnabled;
  $('heavyLimitMB').disabled = !s.heavyEnabled;
  $('idleMinutes').disabled = !s.enabled;
  renderAllowlist(s.allowlist);
}

function renderStats(stats) {
  $('total').textContent = stats.total.toLocaleString();
  $('total-label').textContent = `${stats.total === 1 ? 'tab' : 'tabs'} unloaded on this device`;
  $('breakdown').textContent =
    `After the idle time: ${stats.idle} · Low memory: ${stats.pressure} · ` +
    `Heavy tabs: ${stats.heavy} · By you: ${stats.manual}`;
}

async function renderMemory() {
  try {
    const used = memoryUsedPercent(await chrome.system.memory.getInfo());
    if (used === null) return;
    $('mem-now').textContent = `Right now ${Math.round(used)}% of this computer’s memory is in use (${Math.round(100 - used)}% free).`;
    $('mem-now').hidden = false;
  } catch {
    // system.memory unavailable
  }
}

async function renderShortcut() {
  try {
    const commands = await chrome.commands.getAll();
    const cmd = commands.find((c) => c.name === 'unload-others');
    $('shortcut').textContent = (cmd && cmd.shortcut) || 'not set';
  } catch {
    // ignore
  }
}

function setMsg(text, kind = '') {
  const msg = $('add-msg');
  msg.textContent = text;
  msg.className = `msg ${kind}`;
  $('add-input').classList.toggle('invalid', kind === 'error');
}

// ---------------------------------------------------------------- wiring

for (const id of CHECKBOXES) {
  $(id).addEventListener('change', (e) => save({ [id]: e.target.checked }));
}
for (const id of Object.keys(SELECTS)) {
  $(id).addEventListener('change', (e) => save({ [id]: Number(e.target.value) }));
}

$('add-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const input = $('add-input');
  const { allowlist } = await loadSettings();
  const res = addToAllowlist(allowlist, input.value);
  if (!res.ok) {
    setMsg(res.error, 'error');
    return;
  }
  if (await save({ allowlist: res.list })) {
    setMsg(`Added ${res.value}. Its tabs won’t be unloaded.`, 'ok');
    input.value = '';
  } else {
    setMsg('Couldn’t save: the list may be too long.', 'error');
  }
  input.focus();
});

$('add-input').addEventListener('input', () => {
  if ($('add-msg').classList.contains('error')) setMsg('');
});

$('change-shortcut').addEventListener('click', () => {
  const edge = navigator.userAgent.includes('Edg/');
  chrome.tabs.create({ url: edge ? 'edge://extensions/shortcuts' : 'chrome://extensions/shortcuts' });
});

let resetArmed = false;
let resetTimer = 0;
$('reset').addEventListener('click', async () => {
  const btn = $('reset');
  if (!resetArmed) {
    resetArmed = true;
    btn.textContent = 'Click again to reset';
    btn.classList.add('confirm');
    resetTimer = setTimeout(() => {
      resetArmed = false;
      btn.textContent = 'Reset settings to defaults';
      btn.classList.remove('confirm');
    }, 4000);
    return;
  }
  clearTimeout(resetTimer);
  resetArmed = false;
  btn.textContent = 'Reset settings to defaults';
  btn.classList.remove('confirm');
  const defaults = { ...DEFAULTS };
  delete defaults.allowlist; // the never-unload list is kept
  await save(defaults);
  flashSaved('Settings reset');
});

chrome.storage.onChanged.addListener(async (changes, area) => {
  if (area === 'sync') render(await loadSettings());
  if (area === 'local' && changes.stats) renderStats(await loadStats());
});

(async () => {
  const [settings, stats] = await Promise.all([loadSettings(), loadStats()]);
  render(settings);
  renderStats(stats);
  renderMemory();
  renderShortcut();
})();
