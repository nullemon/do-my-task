# Make your Windows laptop ring for breaking news

newsalert runs on your Linux VM. When it finds an important story, it sends a message to
your private **ntfy** topic. A small listener on your Windows laptop picks the message up
and rings.

```
 Linux VM (newsalert)  --HTTPS-->  ntfy.sh  <--HTTPS--  Windows laptop (newsalert_listener.py)
                                      ^
                                      +--------------- phone / web app (optional)
```

What you get on the laptop:

| Alert | ntfy priority | What happens |
|---|---|---|
| **Urgent** | 5 | `ring.wav` loops, and a red window stays on top of everything with **Open** and **Dismiss** buttons. It keeps ringing until you press one. You also get a Windows notification. If more urgent alerts arrive while it rings, they stack up in the same window. |
| **Normal** | 4 | One chime and a Windows notification. |
| **Quiet** | 1–3 | A Windows notification, no sound (follow-ups, muted alerts). |

The listener only listens. It never posts anything. Both the VM and the laptop only make
**outgoing** HTTPS connections to ntfy.sh, so you don't need to open any ports.

Plan on about 15 minutes.

---

## 1. Install Python on the laptop

1. Go to <https://www.python.org/downloads/> and download the latest Python 3 for
   Windows (3.10 or newer).
2. Run the installer. On the first screen, **tick "Add python.exe to PATH"**, then click
   **Install Now**. The default install includes everything the listener needs, including
   Tk for the ring window. Nothing else needs to be installed: the listener uses only
   Python's standard library.
3. Open **Command Prompt** (press Start, type `cmd`, press Enter) and check it works:

   ```
   python --version
   ```

   You should see something like `Python 3.12.x`.

## 2. Pick a secret topic name

An ntfy topic works like a password. **Anyone who knows the name can read your alerts**,
so use a long random one. Run this on the VM (or in Command Prompt on the laptop):

```
python3 -c "import secrets; print('na_' + secrets.token_urlsafe(24))"
```

On Windows, type `python` instead of `python3`. You'll get something like
`na_Q3v9xK2mT7pL0aZr8sYc4WnE1uHbJd6f`. Copy it. You'll paste it in two places next.

## 3. Tell the VM where to send alerts

On the VM, edit `newsalert/.env` (copy it from `.env.example` if you haven't yet):

```
NTFY_URL=https://ntfy.sh
NTFY_TOPIC=na_Q3v9xK2mT7pL0aZr8sYc4WnE1uHbJd6f
NTFY_TOKEN=
ALERT_MODE=ntfy
```

If `NTFY_TOPIC` is empty, newsalert logs an error and falls back to `local` alerts on the
VM itself, which you usually can't hear.

## 4. Copy the listener to the laptop

You need these files on the laptop, for example in `C:\newsalert`:

```
C:\newsalert\
    newsalert_listener.py      <- from the repo's laptop\ folder
    listener.ini.example       <- from laptop\
    run-listener.cmd           <- from laptop\
    install-startup.cmd        <- from laptop\
    uninstall-startup.cmd      <- from laptop\
    stop-listener.cmd          <- from laptop\
    sounds\
        ring.wav               <- from the repo's config\sounds\ folder
        chime.wav              <- from config\sounds\
```

Copy them however suits you: a shared folder, a USB stick, or `scp`. Windows 10 and 11
have `scp` built in. Run this in Command Prompt, replacing `you@VM-ADDRESS` and the path:

```
mkdir C:\newsalert\sounds
scp you@VM-ADDRESS:newsalert/laptop/* C:\newsalert\
scp you@VM-ADDRESS:newsalert/config/sounds/*.wav C:\newsalert\sounds\
```

If you copy the whole repository instead, that works too. The listener also looks for
the sounds in `..\config\sounds`.

## 5. Create `listener.ini`

In `C:\newsalert`, copy `listener.ini.example` to `listener.ini` and open it in Notepad:

```
cd C:\newsalert
copy listener.ini.example listener.ini
notepad listener.ini
```

Set `topic =` to the same topic you put in the VM's `.env`, then save:

```
topic = na_Q3v9xK2mT7pL0aZr8sYc4WnE1uHbJd6f
```

Leave everything else as it is for now.

## 6. Test the ring (no internet needed)

```
cd C:\newsalert
python newsalert_listener.py --test-ring
```

A red **URGENT NEWS ALERT** window should appear on top of everything and the laptop
should ring. Press **Dismiss** (or **Open**) to stop it. To try the normal-alert sound and
a notification, run:

```
python newsalert_listener.py --test-chime
```

If you hear nothing, see [Troubleshooting](#troubleshooting).

## 7. Run the listener and send yourself a test

Start it in the console first so you can watch what it does:

```
python newsalert_listener.py
```

It should log `connecting to https://ntfy.sh` and show a "listener connected"
notification. Now, **from the VM**:

```bash
newsalert test-alert --urgent     # rings, with the window
newsalert test-alert --normal     # one chime + notification
```

You can also send raw messages with curl, which is handy for checking the path end to end:

```bash
curl -d "hi" ntfy.sh/na_Q3v9xK2mT7pL0aZr8sYc4WnE1uHbJd6f                    # quiet notification
curl -H "Priority: 5" -H "Title: Ring test" -d "hello" ntfy.sh/na_Q3v9xK2mT7pL0aZr8sYc4WnE1uHbJd6f   # rings
```

When it works, press **Ctrl+C** to stop the console listener. Then double-click
**`run-listener.cmd`** to run it in the background, with no window until an alert comes
in. It writes a log to `C:\newsalert\newsalert_listener.log`.

## 8. Start it automatically at login

Double-click **`install-startup.cmd`**. It puts a "newsalert listener" shortcut in your
Startup folder, so the listener starts every time you log in.

- To undo it, double-click `uninstall-startup.cmd`.
- To stop the listener that's running now, double-click `stop-listener.cmd`.
- Only one listener per topic runs on the laptop at a time. If you start a second one, it
  exits straight away.

---

## Optional: also get alerts on your phone or in a browser

This uses the same topic and needs no changes on the VM:

- **Phone:** install the **ntfy** app (Google Play, F-Droid or the App Store). Tap **+**,
  enter your topic, and keep the server as `ntfy.sh`. Priority 5 alerts arrive as
  max-priority notifications. On Android you can let that notification category override
  Do Not Disturb in the system notification settings.
- **Browser:** open <https://ntfy.sh/app>, subscribe to your topic, and allow
  notifications.

The **Open** links and up to 3 extra source links appear as buttons on the notification.

## Optional: more privacy with an access token

A long random topic is usually enough. If you want only your own devices to be able to
read or write the topic:

1. Create an account on ntfy.sh, on a plan that includes **reserved topics**. Reserve your
   topic and set it to deny access to everyone else.
2. Under **Account → Access tokens**, create a token (it starts with `tk_`).
3. Put the token in the VM's `.env` as `NTFY_TOKEN=tk_...`, and in `listener.ini` as
   `token = tk_...`. In the phone app, add the same user under **Settings → Users**.

The token is sent as an `Authorization: Bearer` header. It never appears in a URL, and
newsalert removes it from its logs. Keep it in `listener.ini`, not on the command line,
where other programs could see it.

You can also run your own ntfy server. Set `NTFY_URL` on the VM and `url =` in
`listener.ini` to its address.

Good to know about ntfy.sh:

- It keeps messages for about 12 hours. If the laptop was off or asleep, the listener
  fetches the messages it missed when it reconnects. Alerts older than 15 minutes by then
  are shown **without ringing** (setting: `ring_max_age_minutes`).
- The free tier allows a few hundred messages a day. If the VM logs
  `alert.delivery_failed` with HTTP 429, you've hit that limit.

## VM networking notes

- The VM needs **outbound HTTPS (port 443) to ntfy.sh** and nothing else for alerts.
  NAT, a bridged adapter or a host-only adapter with internet access all work.
- **Nothing needs to connect to the VM or to the laptop.** Don't forward any ports.
- Check it from the VM with `curl -d "hi" ntfy.sh/<your topic>`. If curl hangs or fails,
  the VM has no route to the internet, or a proxy is required (set `HTTPS_PROXY` in the
  VM's environment).
- If delivery fails, newsalert retries twice within 5 seconds. Then it logs
  `alert.delivery_failed` at ERROR level in `data/newsalert.log`.

---

## Troubleshooting

**Check the log first:** `C:\newsalert\newsalert_listener.log`. It shows each connection
attempt and each alert received.

**The window and ring work, but no Windows notification appears.**
- Focus Assist / Do Not Disturb hides notifications. On Windows 11 it's under
  **Settings → System → Notifications → Do not disturb**, and on Windows 10 it's
  **Focus assist**. The urgent ring window **still appears and rings** even then. Only the
  notification is hidden.
- The notifications show up as coming from **Windows PowerShell**. Make sure that app is
  allowed under **Settings → System → Notifications**.
- If notifications can't be shown at all, the listener falls back to a small popup in the
  bottom-right corner.

**No sound.**
- Check the volume, the mute key and the output device (headphones unplugged?).
- Run `python newsalert_listener.py --test-ring`. If the log says `sound file missing`,
  put `ring.wav` and `chime.wav` in `C:\newsalert\sounds\`, or set `sounds_dir` in
  `listener.ini`.

**No ring window (just sound and a notification).**
- The log says `tkinter not available`. Re-run the Python installer, choose **Modify**,
  and make sure **"tcl/tk and IDLE"** is ticked.

**`python` is not recognized.**
- Python isn't on PATH. Re-run the installer and tick **"Add python.exe to PATH"**, or use
  `py` instead of `python` in the commands above.

**Nothing arrives.**
- The topic in `listener.ini` must match `NTFY_TOPIC` on the VM exactly. It is
  case-sensitive.
- Send `curl -d "hi" ntfy.sh/<topic>` from the VM. It also shows up at
  `https://ntfy.sh/<topic>` in a browser.
- A firewall or proxy on the laptop's network may block ntfy.sh. The listener uses the
  Windows proxy settings (or `HTTPS_PROXY`). Corporate or school networks sometimes block
  ntfy.sh entirely. Try another network, such as a phone hotspot, to confirm.
- `HTTP 401/403` in the log means the topic is reserved. Set `token =` in `listener.ini`.
- If ntfy.sh is unreachable for more than 5 minutes, the listener shows a
  "no connection" notification. It keeps retrying forever and catches up on missed
  messages when it reconnects.

**Every alert rings twice.**
- Two things are listening. The usual cause is that the VM's `.env` has
  `ALERT_MODE=both` or `local` while newsalert is also running on the laptop itself. On
  the VM, use `ALERT_MODE=ntfy`.

**It rang for something old after the laptop woke up.**
- It shouldn't: alerts older than `ring_max_age_minutes` (default 15) are shown quietly.
  Lower that number in `listener.ini` if 15 minutes is too long for you.
