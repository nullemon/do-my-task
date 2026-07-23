# webscan — website exposure scanner

Find exposed URLs, directories, config files, backups and secrets on **your
own** website — so you can lock them down. Point it at a site and a path, hit
**Scan**, and it bulk-checks a wordlist of commonly-leaked paths (`.git/`,
`.env`, `backup.sql`, admin panels, open directory listings, …), streaming
results live and ranking them by severity.

It runs as a **local web app in your browser** (no build step, no installs —
just Python 3) and also has a **command-line** mode for scripting.

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
