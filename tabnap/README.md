# TabNap

TabNap puts the tabs you aren't looking at to sleep so Chrome and Edge use less memory. Sites you pick are never put to sleep. It also works in Brave, Opera and other Chromium browsers.

## What it really does

No extension can put a memory limit on a tab, because browsers don't allow it. TabNap does the next best thing: it **unloads** background tabs using the browser's own tab-discarding feature, the one behind Chrome's Memory Saver and Edge's sleeping tabs. An unloaded tab frees almost all of its memory. It stays in your tab bar with its title and icon, and it reloads when you click it.

TabNap shows how many tabs are asleep, for example "9 of 31 tabs asleep". It does not show "MB saved", because an extension can't measure how much memory a tab uses.

## Install (Chrome, Edge, Brave, Opera)

1. Put the `tabnap` folder somewhere it can stay, such as `Documents\tabnap`. The browser loads the extension from that folder every time it starts.
2. Open the extensions page: `chrome://extensions` in Chrome, `edge://extensions` in Edge, `brave://extensions` in Brave, or `opera://extensions` in Opera.
3. Turn on **Developer mode**. In Chrome the switch is at the top right; in Edge it's in the left sidebar.
4. Click **Load unpacked** and choose the `tabnap` folder (the one that contains `manifest.json`).
5. Optional: pin TabNap from the puzzle-piece menu so its moon button is always in your toolbar.

## Using it

Click the moon button to see:

- **On/off switch**: pauses automatic unloading. While it's paused the toolbar badge shows "off".
- **N of M tabs asleep**, and how much of the computer's memory is in use.
- **This tab**: whether the tab is protected and why (for example "on your never-unload list" or "playing audio").
- **Never unload *site***: adds the current site to the never-unload list, or removes it.
- **Keep this tab awake**: protects just this tab until you close it or restart the browser.
- **Unload other tabs now**: puts every background tab to sleep right away, still skipping protected tabs. This works even while TabNap is paused. The keyboard shortcut is **Alt+Shift+U**; you can change it at `chrome://extensions/shortcuts`.
- **Settings**: opens the options page.

## Sites that are never unloaded

You can add a site from the popup with the "Never unload" switch, or in **Settings → Never unload these sites**, where you type a site or paste any link from it. TabNap tidies what you enter:

| You enter | Saved as |
|---|---|
| `https://www.YouTube.com/watch?v=1` | `youtube.com` |
| `www.youtube.com` or `*.youtube.com` | `youtube.com` |
| `http://localhost:3000/app` | `localhost:3000` |

- A site also covers its subdomains: `google.com` covers `mail.google.com` and `docs.google.com`.
- A subdomain covers only itself: `mail.google.com` does not cover `google.com` or `docs.google.com`.
- With a port, only that port is covered (`localhost:3000`). Without a port, every port is covered (`localhost`).
- Input that isn't a website, such as `chrome://settings` or text with spaces, is rejected with a message.

Tabs on these sites are also marked "not auto-discardable", so Chrome's Memory Saver and Edge's sleeping tabs leave them alone too. When you remove a site, that mark is removed as well.

## Settings and defaults

| Setting | Default | Choices |
|---|---|---|
| Automatic unloading | On | On / Off |
| Unload tabs after | 15 min | 1, 5, 10, 15, 30, 60 min, 2 h, 4 h |
| Protect tabs playing audio | On | On / Off |
| Protect pinned tabs | On | On / Off |
| Protect tabs with text you've typed but not sent | On | On / Off |
| When memory runs low | On, below 15% free | 10, 15, 20, 25, 30% free |
| Heavy tabs (JavaScript memory over) | On, 400 MB | 200 MB, 400 MB, 800 MB, 1.5 GB |
| Never-unload list | empty | |

- **Unload tabs after** counts from the moment you switched away from a tab, not from when you last opened it. Tabs that were already open when TabNap started use the browser's "last opened" time as an estimate.
- **When memory runs low**: when the computer's free memory drops below the limit, TabNap also unloads background tabs that you left at least a minute ago. It starts with the tab you looked at longest ago and unloads at most 5 per check.
- **Heavy tabs**: when a background tab has been left for at least a minute and its page's JavaScript memory is over the limit, TabNap unloads it without waiting for the timer. That figure covers only the page's scripts, not the tab's total memory.
- TabNap checks every 30 seconds, so a tab can stay awake for up to 30 seconds after its time is up.
- The options page also shows how many tabs TabNap has unloaded on this device. **Reset settings to defaults** restores the table above but keeps your never-unload list.

## What is never unloaded

- The tab you're looking at in each window
- Sites on your never-unload list
- Tabs you set to "Keep this tab awake"
- Tabs playing audio (setting)
- Pinned tabs (setting)
- Tabs with text you've typed but not sent yet, such as a half-written comment, email or form (setting)
- Tabs that are still loading
- Browser and extension pages (`chrome://`, `edge://`, `file://` and others), and tabs that are already asleep

## Permissions and why

| Permission | Used for |
|---|---|
| `tabs` | Reading tab addresses to match your never-unload list and skip browser pages, and unloading tabs |
| `storage` | Saving your settings, the per-tab timers and the counter |
| `alarms` | Running the check every 30 seconds |
| `system.memory` | Reading how much of the computer's memory is free, for "When memory runs low" |
| Content script on `http://` and `https://` pages | Two jobs only: (1) noticing that you've typed text that isn't sent yet, and (2) reading the page's JavaScript memory figure for "Heavy tabs" |

The content script is the reason the browser warns that TabNap can "read and change all your data on all websites". It does not read what you type. It reports a single yes/no ("this page has unsent text") and a single number (JavaScript memory). It never reads or changes anything else on the page.

## Privacy

TabNap makes no network requests and has no analytics, no remote code and no accounts. Nothing you browse or type ever leaves your browser. Your settings and never-unload list are stored in your browser profile. If you've turned on Chrome or Edge sync, your browser syncs them like other extension settings.

## Limitations

- **An unloaded tab reloads when you click it.** The browser usually restores the scroll position, but a video's playback position or anything a web app hadn't saved may be lost. Sites that need to stay running (chat, notifications, timers) won't run while asleep, so add them to the never-unload list.
- **Unsent-text protection and the JavaScript memory reading only work in tabs opened or reloaded after TabNap is installed** (or updated). Older tabs can still be unloaded; they just lack these two checks until they're reloaded.
- **The JavaScript memory figure is approximate.** The browser rounds it, it covers only the page's scripts, and some browsers don't provide it at all. In those browsers, "Heavy tabs" does nothing.
- **"Keep this tab awake" lasts until the tab closes or the browser restarts.**
- **The browser can decline to unload a tab**; TabNap then skips it and tries again on the next check.
- **The memory reading in the popup is for the whole computer**, not for the browser alone.

## For developers

```
manifest.json        MV3 manifest
src/rules.js         all decision logic (pure, unit-tested)
src/background.js    service worker: tab tracking, 30-second sweep, messages
src/content.js       unsent-text flag + JavaScript memory reading
src/storage.js       chrome.storage helpers
popup/, options/     UI (src/ui.css is shared)
icons/               generated by tools/make_icons.py (needs Pillow)
test/                unit tests (node --test) and a Playwright end-to-end test
```

- `npm test` runs the unit tests (Node 22 or newer, no dependencies).
- `npm run test:e2e` loads the extension into Playwright's Chromium and checks real unloading. It needs a Playwright install; if a global one isn't found, set `NODE_PATH` to the folder that contains `playwright`. Screenshots are saved to `$TABNAP_SHOTS`, and the temporary browser profile goes under `$TABNAP_TMP`.
- `python tools/make_icons.py` regenerates the icons.
