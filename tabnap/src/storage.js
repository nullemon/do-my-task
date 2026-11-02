// Small chrome.storage helpers shared by the service worker, popup and options page.
import { DEFAULTS, sanitizeSettings } from './rules.js';

/** Settings + allowlist live in storage.sync so they follow the user's profile. */
export async function loadSettings() {
  const raw = await chrome.storage.sync.get(Object.keys(DEFAULTS));
  return sanitizeSettings(raw);
}

export async function saveSettings(patch) {
  await chrome.storage.sync.set(patch);
}

export const EMPTY_STATS = Object.freeze({ total: 0, idle: 0, pressure: 0, heavy: 0, manual: 0 });

/** Counters live in storage.local (they are per device). */
export async function loadStats() {
  const { stats } = await chrome.storage.local.get('stats');
  return { ...EMPTY_STATS, ...(stats && typeof stats === 'object' ? stats : {}) };
}

/**
 * Serialize async read-modify-write sections: each call waits for the
 * previous one to finish (even if it failed) before running.
 */
export function makeLock() {
  let tail = Promise.resolve();
  return (fn) => {
    const run = tail.then(fn);
    tail = run.catch(() => {});
    return run;
  };
}

/** Send a message to the service worker; resolves to null instead of throwing. */
export async function ask(message) {
  try {
    return await chrome.runtime.sendMessage(message);
  } catch {
    return null;
  }
}
