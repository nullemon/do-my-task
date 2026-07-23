# webscan — website security toolkit

Two tools in one **local web app in your browser** (no build step, no installs —
just Python 3), for hardening **your own** sites:

1. **Exposure scan** — find exposed URLs, directories, config files, backups and
   secrets (`.git/`, `.env`, `backup.sql`, admin panels, open directory
   listings, …) so you can lock them down. Streams results live, ranked by
   severity, with a command-line mode too.
2. **403 / Forbidden bypass test** — you locked a directory (e.g. with
   `.htaccess`) and it returns *Forbidden*, but people still reach it. Paste the
   locked URL and it tries every known way in (IP-header spoofing, path/encoding
   tricks, method changes, `X-Original-URL`, Referer rules…), tells you which
   works, and — optionally, using Claude — explains why and writes the exact fix.

> ⚠️ **Authorized use only.** Only scan sites and servers you own or have
> written permission to test. All requests are made from the machine running
> the tool; nothing is sent anywhere else.

---

## Quick start (web app)

```bash
python3 serve.py
```

This starts a local server on `http://127.0.0.1:8765` and opens it in your
browser. Then:

1. **Target site URL(s)** — e.g. `https://mysite.com` (one per line for a bulk
   scan of several sites).
2. **Base path** — scan under `/`, or narrow to `/app`, `/blog`, etc.
3. **Wordlist** — pick what to look for (sensitive files, directories, …).
4. **Specific URLs / paths** *(optional)* — type any path of your choice to
   check, on top of the wordlist.
5. Click **Scan**. Findings stream in, most-severe first. **Export JSON** saves
   a report.

Everything exposed is something to review and lock down (deny access, move it
out of the web root, add auth, or disable directory listing).

---

## Spoof your server & IP

The **Spoof server & IP** panel lets you test your **own** access controls:

- **Spoofed client IP** — injects `X-Forwarded-For`, `X-Real-IP`,
  `X-Client-IP`, `True-Client-IP`, etc. with the value you enter. Use this to
  check whether an IP allow-list (e.g. an admin panel "only reachable from the
  office") can be bypassed by a forged header. The `127.0.0.1` chip fills in
  the classic localhost-bypass test.
- **Your server / origin (Host header override)** — sends a custom `Host`
  header so you can hit your **origin server's IP directly** while presenting
  your real domain. Handy for testing the box behind a CDN/WAF, e.g. target
  `http://203.0.113.10` with Host `mysite.com`.

> This is header-based testing, which is the meaningful (and browser-possible)
> form of "spoofing" for probing your own app. It does **not** forge network
> packets.

If a path returns **403 without** the spoof and **200 with** it, your IP
control is bypassable — the scanner flags the difference.

---

## 403 / Forbidden bypass test

Switch to the **403 / Forbidden bypass test** tab when a directory you locked
still leaks. Paste the exact locked URL (e.g. `https://mysite.com/private/`) and
hit **Test bypasses**. It:

1. **Confirms the lock** — makes a normal request and checks it really is
   Forbidden (if it isn't, it tells you the directory may not be locked at all).
2. **Tries ~40 bypass techniques**, each a single ordinary HTTP request:
   - **IP-header spoofing** — `X-Forwarded-For`, `X-Real-IP`, `X-Client-IP`,
     `True-Client-IP`, … to test IP allow-lists (`Require ip`, `Deny/Allow`).
   - **Path & encoding tricks** — case changes, trailing `/.`, `//`, `..;/`,
     `%2e`/`%20`/`%00`, suffixes like `.json`/`~`, slash toggling — anything that
     matches the rule literally but resolves to the file on disk.
   - **HTTP method changes** — `POST`/`HEAD`/`PUT`/`OPTIONS`/arbitrary verbs and
     `X-HTTP-Method-Override`, to slip past `<Limit GET POST>` style rules.
   - **Routing headers** — `X-Original-URL` / `X-Rewrite-URL` (request an allowed
     path, smuggle the locked one in a header) and `Referer`-based `.htaccess`.
3. **Reports which got through** as red **BYPASS** rows — with the exact request
   and headers. It uses control requests to avoid false positives (a path trick
   that just hits your catch-all page, or a routing header the server correctly
   ignored, are *not* reported as bypasses).

### Explain & fix with AI (optional)

If bypasses are found, click **Explain & fix**. This is the only feature that
uses an AI API: it sends the results to **Claude** (`claude-opus-4-8`), which
explains the root cause, rates severity, and writes a corrected `.htaccess` /
server config you can apply. To enable it:

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...   # or run `ant auth login`, or paste a key in the UI
```

Without it, the deterministic bypass results and a built-in fix hint for each
technique still work — the AI just adds a written explanation and ready-to-paste
config.

> **What "spoof" means here:** header-based testing of your own access controls,
> which is the meaningful (and browser-possible) form. It does **not** forge
> network packets, and every request is read-only.

If **no** bypass gets through but people still see the content, the way in is
probably *outside* these request tests — a cached copy (CDN/browser), a search-
engine snapshot from before you locked it, or the file reachable at a different
URL/alias. The tool says so instead of pretending it found nothing.

---

## Command line

Same engine, no browser — good for automation/CI.

```bash
# Scan one site with the default wordlist
python3 scan.py https://mysite.com

# Scan a sub-path, more workers, export a JSON report
python3 scan.py https://mysite.com --path /app --workers 40 --json report.json

# Only the high-value stuff (.git, .env, backups)
python3 scan.py https://mysite.com --wordlist sensitive

# Bulk scan many targets from a file (one URL per line)
python3 scan.py --targets-file sites.txt

# Test your origin server IP while presenting your domain, and spoof an IP
python3 scan.py http://203.0.113.10 --host-header mysite.com --spoof-ip 127.0.0.1
```

Exit code is `2` if anything **exposed** was found, else `0` — so you can fail
a CI job when a leak appears.

### Useful CLI flags

| Flag | Meaning |
|------|---------|
| `--path /app` | Base path to scan under |
| `--wordlist NAME` | `common`, `sensitive`, `config`, `directories`, `info` |
| `--paths-file f` | Extra custom paths, one per line |
| `--workers N` | Concurrency (default 20) |
| `--timeout S` | Per-request timeout |
| `--method HEAD` | Faster, no body (skips content confirmation) |
| `--host-header H` | Override the `Host` header |
| `--spoof-ip IP` | Inject IP-spoofing headers |
| `--header "K: V"` | Add an arbitrary header (repeatable) |
| `--insecure` | Skip TLS certificate verification |
| `--follow-redirects` | Follow 3xx instead of just recording them |
| `--json FILE` | Write a full JSON report |

---

## What it detects & how

Each checked path is classified with a verdict and severity:

- **exposed** — reachable and (where possible) **confirmed** by content
  signature. A `.env` that actually contains `KEY=value`, a `.git/config` with
  `[core]`, a SQL dump with `CREATE TABLE`, or a directory with listing
  enabled — these are marked ✓ confirmed and ranked `critical`/`high`.
- **exists** — present but forbidden (`403`) or erroring (`5xx`). Confirms the
  path is there (and may be bypassable via the spoof headers).
- **protected** — `401`, or a redirect to a login/SSO page. This is the good
  outcome.
- **redirect** — `3xx` to somewhere else (location recorded).

**Soft-404 handling:** many sites (especially SPAs) return `200 OK` for *every*
path. Before scanning, webscan measures a baseline by requesting paths that
can't exist, then compares each real response's **content** against it. A hit
that's just the site's catch-all page is suppressed, so the findings list isn't
drowned in false positives — while genuine files are still caught even when
they happen to be the same size as the catch-all (content signatures override
the soft-404 filter).

Severity scale: `critical` › `high` › `medium` › `low` › `info`.

---

## Wordlists

| Profile | Looks for |
|---------|-----------|
| `common` | Everything below (default) |
| `sensitive` | VCS dirs (`.git`, `.svn`), secrets (`.env`, keys), backups/dumps |
| `config` | Sensitive + app configs & deployment files |
| `directories` | Browsable/listable dirs and admin panels |
| `info` | Info-disclosure (`phpinfo`, `server-status`) and logs |

The built-in list lives in `webscan/wordlists.py` — add your own entries there,
or pass site-specific paths at scan time (the **Specific URLs / paths** box in
the UI, or `--paths-file` on the CLI).

---

## Project layout

```
serve.py                 # start the web app  -> python3 serve.py
scan.py                  # command-line entry -> python3 scan.py <url>
webscan/
  engine.py              # concurrent scan engine, detection & soft-404 logic
  wordlists.py           # built-in path list + content signatures (edit me)
  server.py              # local web server + streaming NDJSON scan API
  cli.py                 # argparse command-line interface
  webui/
    index.html           # the app
    styles.css
    app.js               # form + live streaming results
```

No third-party dependencies — standard library only. Requires Python 3.8+.

---

## Notes & limits

- Bind stays on `127.0.0.1` so the tool isn't exposed to your network. Change
  with `python3 serve.py --host 0.0.0.0 --port 9000` only if you understand the
  implication.
- It's **read-only**: every request is a `GET`/`HEAD`. It never modifies the
  target.
- Be considerate: use `--delay` (CLI) or lower concurrency against production,
  and don't scan infrastructure you don't control.
