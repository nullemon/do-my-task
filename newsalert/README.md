# newsalert

Detects breaking news about **celebrities, anime, manga and TV** within 1–2 minutes and
rings your laptop with a loud alert and a desktop notification.

**Alert only.** It never publishes, posts, comments or messages anyone. Its only outputs
are alerts to you and its own logs.

```
[ANIME] [OFFICIAL SOURCE] Studio X announces Season 2 of Y
Summary: Studio X confirmed a second season of Y, with the original cast returning.
Source: @StudioX_official (X) · 47s ago
Links: original post · Anime News Network · Crunchyroll News
```

## How it works

```
 watchers (no AI)          pipeline                  engine                    dispatch
 ───────────────     ─────────────────────     ─────────────────────     ──────────────────────
 RSS / YouTube  ─┐   exact dedupe (URL,        cluster into a story      urgent → ring now
 Bluesky stream ─┼─▶ text hash, feed id)  ──▶  (cheap match, Haiku   ──▶ normal → chime, ≤1/30s
 X API          ─┤   drop >30 min old          tie-break if unclear)     quiet hours → digest
 Wikipedia SSE  ─┘   first poll = seed         Haiku triage + summary    mute → silent
                                               confidence label          ntfy.sh → laptop / phone
                                               follow-ups / retractions
```

1. **Watchers** poll or stream every source on its own interval (default 60 s). They use
   conditional GET (ETag / If-Modified-Since), honour `Retry-After` and back off on errors.
   They use no AI and cost nothing to run.
2. **Pipeline** drops exact duplicates, ignores anything published more than 30 minutes
   before it was fetched, and marks everything already in a feed as *seen* on that feed's
   first poll. So startup, downtime and newly added sources never flood you.
3. **Engine** groups items about the same event (same subject + same event type within
   6 h) into one **story**:
   - Cheap name/entity matching runs first. Haiku is called only to break ties.
   - New stories go to **Haiku triage** for relevance, category, event type, importance
     1–5, rumor flag and a ≤25-word summary.
   - Watchlist subjects get +1 importance.
   - Stories below importance 3 are dropped.
   - If Anthropic fails or takes longer than 3 s, the alert **still fires** with the raw
     headline, marked "no summary".
4. **Dispatch** sends the alert as soon as triage passes. A later source never rings again
   (max one ring per story). It can only upgrade the label with a quiet follow-up.

### Urgency

| | When | What you get |
|---|---|---|
| **urgent** | death, or importance 5, or a watchlist subject with importance ≥ 4 | loud ring that repeats until you dismiss it (ntfy priority 5) |
| **normal** | everything else that passed triage | single chime (ntfy priority 4); at most one per 30 s, the rest queue |
| **quiet** | "now confirmed by…" follow-ups, muted alerts | notification without sound (ntfy priority 2) |

### Confidence labels (computed from sources, never by AI)

| Label | Rule |
|---|---|
| `OFFICIAL SOURCE` | at least one `official` source (studio, publisher, agency, family, verified rep) |
| `CONFIRMED` | two **independent** `major` outlets, or official + major |
| `SINGLE OUTLET` | `major` source(s) from one ownership group only |
| `UNCONFIRMED` | only `signal` sources (Wikipedia edits, fan/aggregator accounts) |

- Rumors still alert but carry `· RUMOR`.
- Deaths backed only by `UNCONFIRMED` sources add **"Not confirmed — check before acting."**
- Outlets with the same `group` in `sources.yaml` count as one. Variety, Deadline, THR,
  Billboard and Rolling Stone are all Penske Media.
- If a later source raises the label, you get a quiet follow-up ("Now confirmed by: …").
- If a source deletes its post, or a Wikipedia edit is reverted within 15 minutes, you get
  a **"POSSIBLY FALSE"** follow-up. It chimes if the story had rung urgently or has no
  other source left.

## Setup

### 1. Install on the VM

Requires Python 3.12+.

```bash
cd newsalert
python3.12 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env && chmod 600 .env
```

### 2. Alerts: ntfy.sh → your Windows laptop

The VM can't play sound on your laptop. Instead it publishes to a private
[ntfy.sh](https://ntfy.sh) topic, and a small listener on the laptop subscribes and rings.
The same topic works with the ntfy phone app with no code changes.

1. Pick a long random topic name. Anyone who knows it can read your alerts, so treat it
   like a password:
   ```bash
   python3 -c "import secrets; print('newsalert-' + secrets.token_urlsafe(18))"
   ```
2. In `.env` on the VM, set `NTFY_URL=https://ntfy.sh`, `NTFY_TOPIC=<that name>` and
   `ALERT_MODE=ntfy`. `NTFY_TOKEN` is only needed for an ntfy.sh account or reserved topic.
3. On the laptop, follow **[docs/laptop-setup.md](docs/laptop-setup.md)**. In short: install
   Python, copy the `laptop/` folder and the two sounds, put the topic in `listener.ini`,
   run `--test-ring`, then `install-startup.cmd` so it starts at login.
4. Test from the VM:
   ```bash
   newsalert test-alert --urgent
   ```
   The laptop should ring until you press **Dismiss**. Then try `--normal`, which chimes once.

If you run newsalert **directly on the laptop**, set `ALERT_MODE=local` (or `both`). It
then plays the sound and shows a native notification itself.

**VM networking:** the VM only needs **outbound HTTPS** to the feeds, `api.anthropic.com`,
`ntfy.sh`, `jetstream2.us-east.bsky.network` (Bluesky), `stream.wikimedia.org` /
`en.wikipedia.org` and `api.x.com` (if used). No inbound ports, port forwarding or bridged
networking is needed. NAT is fine.

### 3. Anthropic (triage + summary)

Put `ANTHROPIC_API_KEY=...` in `.env`. The model is `claude-haiku-5-5` at low effort with
strict JSON output, one short call per *new story*. Items that join an existing story
cost nothing. At typical feed volume that is well under $1 a day. `newsalert stats` shows the real number.
Without a key, every new item alerts on its raw headline, unfiltered.

### 4. Other sources

See **[docs/sources-setup.md](docs/sources-setup.md)** for YouTube channels, Bluesky
accounts (free, no keys), the X API, and Wikipedia.

- **X / Twitter:** reading timelines requires **paid** X API access. Logged-in scraping
  breaks X's terms, so it is not built. The X watcher is in place but stays off until you
  set `X_BEARER_TOKEN`. Mark the accounts you care most about with `priority: true`; those
  are polled most often within your tier's budget (`x:` in `settings.yaml`).
- **Wikimedia** asks for a contact address in the User-Agent. Add yours to
  `polling.user_agent` in `settings.yaml`.

### 5. Check feeds, then run

```bash
newsalert check-sources      # OK/FAIL per feed; flags wrong time zones and stale feeds
```

```bash
newsalert run
```

The first poll of each source seeds silently. From then on, alerts print to the console
as they are sent, as well as going to ntfy.

## Commands

| Command | What it does |
|---|---|
| `newsalert run` | start everything |
| `newsalert test-alert --urgent` / `--normal` | test the ring / chime end to end |
| `newsalert check-sources [--name X]` | fetch every RSS/YouTube feed once and report |
| `newsalert items [--status new\|seeded\|stale]` | recently stored raw items |
| `newsalert replay FILE [--no-ai] [--send] [--realtime]` | push recorded items through the full pipeline (dry run by default, temp DB) |
| `newsalert mute 30m` / `2h` / `1d` · `newsalert unmute` | nothing rings until then; alerts still arrive silently |
| `newsalert stats [--hours 24]` | median/p95 latency per source, alerts sent, Anthropic tokens and cost, failing watchers |
| `newsalert healthcheck` | exit 0 if the running process wrote a heartbeat recently (used by Docker) |

Try replay with the bundled fixtures:

```bash
newsalert replay tests/fixtures/replay_death_story.json --no-ai
```

```bash
newsalert replay tests/fixtures/replay_revert.json --no-ai
```

The first shows a Wikipedia-only death (UNCONFIRMED + warning), then TMZ and BBC
confirming it (a quiet follow-up), plus an unrelated story. The second shows a reverted
edit triggering a "possibly false" follow-up.

## Quiet hours, mute, health

- **Quiet hours** (`quiet_hours:` in `settings.yaml`, set `timezone` to yours): urgent
  alerts still ring. Normal alerts are held and arrive as **one digest** when quiet hours
  end.
- **Mute** (`newsalert mute 30m`): nothing rings. Alerts are still delivered silently, so
  nothing is lost.
- **Health:** if a watcher has failed for 10+ minutes, you get one normal alert naming it.
  If it recovers and then fails again, you get another.
- **Latency:** every story records `published_at`, `fetched_at`, `triaged_at` and
  `alerted_at`, which `stats` uses.

## Running 24/7

**systemd:** see the header of [`deploy/newsalert.service`](deploy/newsalert.service) for
the install commands, then:

```bash
sudo systemctl enable --now newsalert
```

```bash
journalctl -u newsalert -f
```

**Docker:**

```bash
docker compose up -d --build
```

```bash
docker compose exec newsalert newsalert stats
```

`config/` is mounted read-only (edit on the host, then restart) and `data/` holds the
SQLite DB and logs.

## Configuration

| File | What |
|---|---|
| `config/sources.yaml` | every feed/account: `type`, `url`/`account`, `category`, `trust` (`official`/`major`/`signal`), `group` (owner, for independence), `interval`, `enabled`, `priority` |
| `config/watchlist.yaml` | priority people & series: top 30 anime and top 30 TV shows with creators, voice actors, actors, composers (425 entries); `aliases` include Japanese names; `wikipedia` titles are watched for edits; `match_risk: true` marks names that are common words |
| `config/settings.yaml` | intervals, thresholds, clustering, alert spacing, quiet hours, health, per-watcher settings |
| `.env` | secrets only: `NTFY_*`, `ANTHROPIC_API_KEY`, `X_BEARER_TOKEN`. Never logged: any env value whose name ends in KEY/TOKEN/SECRET/PASSWORD is scrubbed from every log line |

**Add a source:**

```yaml
- name: Some Outlet
  type: rss                # rss | youtube | bluesky | x | wikipedia
  url: https://example.com/feed.xml
  category: celebrity      # celebrity | anime | manga | tv  (a hint; triage decides per story)
  trust: major
  group: some-outlet
  interval: 60
```

**Add a watchlist entry:**

```yaml
- name: Chainsaw Man
  kind: series             # series | person | studio
  category: anime
  aliases: [チェンソーマン]
  wikipedia: Chainsaw Man
```

Restart `newsalert run` after editing config.

## Not supported (no allowed real-time access)

| Platform | Why |
|---|---|
| **Instagram** | No public API for reading other accounts in real time. Scraping breaks Meta's terms. |
| **TikTok** | Same: the Research API is not for this use, and scraping breaks the terms. |
| **X / Twitter without paid API** | Logged-in scraping breaks X's terms and risks a ban. Use the official API (paid) or rely on the outlets' RSS, YouTube and Bluesky. |
| **Reuters** | No public RSS feed. |
| **AP** | No feed of its own. Followed through Google News's public RSS search (`sources.yaml`), which adds a few minutes of delay. |

## Development

```bash
pytest
```

Logs are JSON lines (stderr + `data/newsalert.log`).
