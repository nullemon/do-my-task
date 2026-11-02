// TabNap content script (top frame only).
// It does two things and sends nothing else to the extension:
//  1. tells the service worker one boolean: "this page has text the user
//     typed that is not sent yet" (so the tab is not unloaded and lost);
//  2. answers "how much JavaScript memory does this page use?" when asked.
// No page content, field values or URLs ever leave this script.
(() => {
  if (window.top !== window || window.__tabnapContent) return;
  window.__tabnapContent = true;

  const TEXT_INPUT_TYPES = new Set([
    'text', 'email', 'url', 'tel', 'password', 'number',
    'date', 'datetime-local', 'month', 'week', 'time',
  ]);
  const edited = new Set(); // fields the user typed into
  let lastSent = false;
  let timer = 0;

  function editingHost(el) {
    let host = el;
    while (host.parentElement && host.parentElement.isContentEditable) host = host.parentElement;
    return host;
  }

  function userField(el) {
    if (!el || el.nodeType !== 1) return null;
    if (el.isContentEditable) return editingHost(el);
    if (el.disabled || el.readOnly) return null;
    if (el.tagName === 'TEXTAREA') return el;
    if (el.tagName === 'INPUT' && TEXT_INPUT_TYPES.has(el.type)) return el;
    return null;
  }

  function hasText(el) {
    if (!el.isConnected) return false;
    if (el.isContentEditable) return el.textContent.trim() !== '';
    return typeof el.value === 'string' && el.value !== '';
  }

  function isDirty() {
    for (const el of edited) {
      if (!el.isConnected) edited.delete(el);
      else if (hasText(el)) return true;
    }
    return false;
  }

  function report(force) {
    const dirty = isDirty();
    if (dirty === lastSent && !force) return dirty;
    lastSent = dirty;
    try {
      chrome.runtime.sendMessage({ type: 'form-state', dirty }).catch(() => {});
    } catch {
      // Extension was reloaded or removed; this old script is orphaned.
    }
    return dirty;
  }

  function reportSoon() {
    clearTimeout(timer);
    timer = setTimeout(() => report(false), 250);
  }

  document.addEventListener(
    'input',
    (event) => {
      if (!event.isTrusted) return;
      const target = event.composedPath ? event.composedPath()[0] : event.target;
      const field = userField(target);
      if (!field) return;
      edited.add(field);
      reportSoon();
    },
    true,
  );

  document.addEventListener(
    'submit',
    (event) => {
      const form = event.target;
      for (const el of edited) if (form.contains(el)) edited.delete(el);
      reportSoon();
    },
    true,
  );

  document.addEventListener('reset', reportSoon, true);

  // A good moment to re-check: the user is leaving this tab.
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') report(false);
  });

  // Leaving the page: its typed text goes with it (or into the back/forward
  // cache, in which case pageshow below reports it again on return).
  window.addEventListener('pagehide', () => {
    if (lastSent) {
      lastSent = false;
      try {
        chrome.runtime.sendMessage({ type: 'form-state', dirty: false }).catch(() => {});
      } catch {
        // orphaned
      }
    }
  });
  window.addEventListener('pageshow', (event) => {
    if (event.persisted) report(true);
  });

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (!msg || msg.type !== 'tabnap-probe') return;
    const dirty = report(false);
    // Chrome-only and approximate: the page's JavaScript heap, not the whole
    // tab's memory. Undefined in browsers without performance.memory.
    const mem = performance && performance.memory;
    const heap = mem && typeof mem.usedJSHeapSize === 'number' ? mem.usedJSHeapSize : null;
    sendResponse({ dirty, heap });
  });
})();
