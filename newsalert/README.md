# newsalert

Detects breaking news about **celebrities, anime, manga and TV** within 1–2 minutes and
rings your laptop. **Alert only:** it never publishes, posts, comments or messages anyone.
Its only outputs are alerts to you and its own logs.

> **Build status: step 1 of 8.** Watchers poll the RSS feeds, dedupe exact repeats and
> print new items to the console. No AI calls and no alerts yet.

| Step | What | Status |
|---|---|---|
| 1 | Skeleton, config, SQLite, RSS watcher, dedupe → console | ✅ done |
| 2 | ntfy (ntfy.sh) + Windows laptop listener that rings, `test-alert` | next |
| 3 | Haiku triage + one-line summary, alerts on real RSS stories | |
| 4 | Story clustering, confidence labels, follow-up upgrades, tests | |
| 5 | Bluesky (Jetstream) + YouTube channel watchers | |
| 6 | X API watcher (disabled until you have paid API keys) | |
| 7 | Wikipedia EventStreams watcher + revert detection | |
| 8 | Quiet hours, mute, stats, health checks, systemd + docker-compose | |

## Quick start (on the VM)

Requires Python 3.12+.

```bash
cd newsalert
python3.12 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env        # nothing in it is needed for step 1
```

1. **Check the feeds.** The seed URLs in `config/sources.yaml` couldn't be fetched from
   the build sandbox, so test them from your VM first:

   ```bash
   newsalert check-sources
   ```

   Each source prints `OK` or `FAIL`. It also flags feeds whose newest item looks dated
   in the future or hours old, which usually means the feed has the wrong time zone and
   its items would be treated as stale. To fix a failing source, set `enabled: false` or
   put in the right URL.

2. **Run it.**

   ```bash
   newsalert run
   ```

   The first poll of each source marks everything already in the feed as **seen without
   printing it**. That way you don't get a flood of old news. After that, each genuinely
   new article prints like this:

   ```
   [ANIME] [major] Anime News Network · 47s ago
     Studio X Announces Season 2 of Y
     https://www.animenewsnetwork.com/news/2026-11-01/...
   ```

   JSON logs go to stderr and `data/newsalert.log`. To watch new items only:
   `newsalert run 2>/dev/null`.

3. **Inspect what was stored.**

   ```bash
   newsalert items --limit 30
   ```

   `seeded` means it was already there at first poll. `stale` means it was published
   more than 30 minutes before we fetched it, so it is ignored. `new` means it would
   alert (from step 3 on).

4. **Run the tests.**

   ```bash
   pytest
   ```

## How it works so far

- **One loop per source**, every `interval` seconds (default 60). The first polls are
  staggered so the sources aren't all hit at once.
- **Polite fetching.** It sends `If-None-Match` / `If-Modified-Since`, so an unchanged
  feed costs one tiny 304. It honours `Retry-After` on 429/503. On errors it backs off
  exponentially (60s → 120s → … capped at 15 min). It sends an honest `User-Agent`, with
  no stealth or proxy tricks.
- **Exact dedupe.** Repeats are dropped by feed id, by normalized URL (tracking params,
  `www.`, trailing `/` and `#fragments` are ignored, and twitter.com counts as x.com),
  and by a normalized text hash within 72 h. Exact copies of the same text, such as
  syndicated wire copy, therefore count once. Grouping different articles about the
  same event into one story comes in step 4.
- **No stale backlog.** Items published more than 30 minutes before they were fetched
  never alert. This covers startup, downtime and newly added sources.
- **Secrets** live only in `.env`. Any env value whose name ends in `KEY`, `TOKEN`,
  `SECRET` or `PASSWORD` is scrubbed from every log line.

## Configuration

- `config/settings.yaml`: intervals, timeouts, backoff and the stale window.
- `config/sources.yaml`: every feed. Each one has a `category` (celebrity / anime /
  manga / tv) and a `trust` tier:
  - `official` is the studio, publisher, agency or rep itself.
  - `major` is a professional newsroom.
  - `signal` is fast but unverified, such as a Wikipedia edit or a fan/aggregator site.

  `group` marks shared ownership. Variety, Deadline, THR, Billboard and Rolling Stone
  are all Penske Media, so two of them together won't count as independent
  confirmation (step 4).
- `config/watchlist.yaml`: priority people and series (top anime and TV shows with their
  creators, voice actors, actors and composers). It boosts importance from step 3 on and
  drives Wikipedia page watching in step 7.

### Adding a source

```yaml
- name: Some Outlet
  type: rss
  url: https://example.com/feed.xml
  category: celebrity      # celebrity | anime | manga | tv
  trust: major             # official | major | signal
  group: some-outlet       # owner, for independence checks
  interval: 60             # optional
```

Run `newsalert check-sources --name "Some Outlet"` to test it, then restart `newsalert run`.

## Not supported (no allowed real-time access)

| Platform | Why |
|---|---|
| **Instagram** | No public API for reading other accounts in real time. Scraping breaks Meta's terms. |
| **TikTok** | Same: the Research API is not for this use, and scraping breaks the terms. |
| **X / Twitter** | Reading timelines needs paid API access, and you don't have it. Scraping with a logged-in account breaks X's terms and risks a ban, so it won't be built. The step 6 watcher ships disabled and switches on when `X_BEARER_TOKEN` is set. Until then, the same news is covered through the outlets' RSS feeds, YouTube channels and Bluesky. |
| **Reuters** | No public RSS feed anymore. |
| **AP** | No feed of its own. It is followed through Google News's public RSS search (`sources.yaml`), which adds a few minutes of delay. |
