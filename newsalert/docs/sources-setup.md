# Setting up YouTube, Bluesky, X and Wikipedia sources

These watchers use only official APIs, public feeds and public endpoints. None of
them logs in, scrapes pages, hides who it is or rotates proxies. Each one sends
the User-Agent from `settings.yaml` (`polling.user_agent`).

| Watcher | Keys needed | Cost | How it gets news |
|---|---|---|---|
| YouTube | none | free | Each channel's public Atom feed, polled every 2 min (conditional GET) |
| Bluesky | none | free | One Jetstream websocket for all accounts (push, about 1 s delay) |
| X | `X_BEARER_TOKEN` | **paid API tier** | Official X API v2, polled on a schedule with a monthly budget |
| Wikipedia | none (contact info in the User-Agent) | free | Wikimedia EventStreams (push) plus the public API for diffs |

After you edit `config/sources.yaml` or `config/settings.yaml`, restart
`newsalert run`.

## Before you start: put your contact in the User-Agent

Wikimedia's [User-Agent policy](https://meta.wikimedia.org/wiki/User-Agent_policy)
requires a descriptive User-Agent with a way to reach you. Clients without one
can be blocked. Edit `config/settings.yaml`:

```yaml
polling:
  user_agent: "newsalert/0.1 (personal breaking-news alerts; you@example.com)"
```

An email address or a URL both work. The Wikipedia watcher logs
`wikipedia.user_agent_without_contact` at startup until you've done this. Every
other watcher sends the same header, which is polite everywhere else too.

## YouTube

YouTube's Atom feed needs the **channel id** (`UC` plus 22 characters). An
`@handle` won't work.

```yaml
- name: MAPPA (YouTube)
  type: youtube
  account: UCjfAEJZdfbIjVHdo5yODfyQ   # channel id
  category: anime
  trust: official
  group: mappa
  interval: 120                       # optional; default youtube.interval (120 s)
```

You can give a full feed URL in `url:` instead, for example a playlist feed:
`https://www.youtube.com/feeds/videos.xml?playlist_id=UULF...` (that one lists a
channel's uploads without Shorts).

**Finding a channel id:** open the channel in a browser, choose *View page
source* and search for `"channelId"`. You can also open one of its videos and
click the channel name; if the URL looks like `/channel/UC...`, that is the id.

**Seeded channels.** Their ids were checked against public channel-stats sites,
because YouTube itself couldn't be reached from the build sandbox:

- Anime: Crunchyroll, Crunchyroll Dubs, Netflix Anime, Aniplex USA, MAPPA,
  ufotable, Toei Animation, TMS Entertainment.
- Manga: Jump Channel (Shueisha).
- TV: Netflix, Netflix Japan, HBO, HBO Max, Prime Video, Disney+.

TOHO animation, KADOKAWA Anime and Aniplex (Japan) ship with `enabled: false`
and a `UC_TODO_...` placeholder, because their ids couldn't be verified. Put in
the real id and set `enabled: true`. A channel with a malformed id is skipped at
startup with a `watcher.bad_source` log line.

The first poll of each channel marks its current videos as seen without
alerting. After that, a new upload alerts if YouTube lists it within 30 minutes
of its publish time. Scheduled premieres often show an earlier date and may be
treated as stale.

## Bluesky (no keys)

Jetstream is Bluesky's free public event stream. newsalert opens **one**
websocket and subscribes only to posts from the accounts in `sources.yaml`.

```yaml
- name: Anime News Network (Bluesky)
  type: bluesky
  account: animenewsnetwork.com      # handle, or a DID like did:plc:abc...
  category: anime
  trust: major
  group: ann
```

- **Handles** are resolved to DIDs at startup through the public
  `com.atproto.identity.resolveHandle` endpoint. The result is cached for 24 h
  (`bluesky.handle_cache_hours`). If a handle doesn't resolve, that source is
  reported as failing (`last_error`), and after 10 minutes the health checker
  alerts you.
- **Replies** are skipped unless `bluesky.include_replies: true`. **Reposts**
  never arrive, because they're a different record type. Link cards (title,
  description, URL) are added to the item text.
- **Deleted posts.** If a post we stored is deleted, the alert engine sends a
  "possibly false" follow-up.
- **Reconnects** use exponential backoff (1 s, 2 s, 4 s … up to 5 min). Each
  one resumes from a cursor a few seconds before the disconnect, so a short drop
  loses nothing. After repeated failures the watcher moves to the next official
  instance in `bluesky.jetstream_fallback_urls`. The cursor is also kept across
  restarts if the restart takes less than 30 minutes.
- **Timestamps.** A post's `createdAt` is set by the poster's app and can be
  wrong. A skewed clock, or an importer that copies years-old tweets over, both
  produce bad values. newsalert uses Jetstream's server receive time
  (`time_us`), and uses `createdAt` only when it is up to 5 minutes earlier
  than that. A backdated `createdAt` therefore can't make a fresh post look
  stale. Posts dated more than a day before they reached the network are
  archive imports and are skipped.

**Seeded accounts:** `animenewsnetwork.com` and `apnews.com` are enabled. ANN
announced that handle on its own site, and AP's is listed in public handle
directories. Four accounts ship with `enabled: false` because their handles
couldn't be confirmed from the sandbox: `variety.com`, `deadline.com`,
`hollywoodreporter.com` and `crunchyroll.com`. Open
`https://bsky.app/profile/<handle>`. If it is the real official account, set
`enabled: true`.

To add an account, copy an entry and change `name` and `account`. A
domain-style handle (`studio.com`) proves the account owns that domain, which is
a good sign it's official.

## X (needs a paid API tier)

Reading other accounts' posts requires a paid X API tier. Until you set a
token, the X watcher logs `watcher.disabled` once and does nothing: it makes no
requests and raises no health alerts.

1. Get API access at <https://developer.x.com>. Create a project and app, then
   copy the app's **Bearer Token**.
2. Put it in `.env` (never in a YAML file):

   ```
   X_BEARER_TOKEN=AAAA...
   ```

   The token goes only into the `Authorization` header of requests to
   `api.x.com`. Env values ending in `TOKEN` are also scrubbed from every log
   line.
3. Set `x.monthly_read_budget` in `settings.yaml` to the number of posts your
   tier lets you read per month.
4. In `sources.yaml`, set `enabled: true` on the X accounts you want. Use
   `priority: true` for the few that matter most.

```yaml
- name: MAPPA (X)
  type: x
  account: MAPPA_Info        # handle without @
  category: anime
  trust: official
  group: mappa
  priority: true             # every x.priority_interval (5 min); others every 30 min
```

How it behaves:

- Handles are mapped to user ids once (`GET /2/users/by`) and cached.
- Each account is polled with `GET /2/users/:id/tweets?since_id=…`, without
  replies or reposts. First polls are spread evenly across the interval.
- The first poll of an account records its newest post without alerting.
- **Budget.** Every post read is counted per calendar month (UTC). At 90 % of
  `monthly_read_budget` only `priority: true` accounts are polled
  (`x.budget_throttled` in the log). At 100 % polling stops until the 1st of
  next month (`x.budget_exhausted`).
- **Rate limits.** When `x-rate-limit-remaining` reaches 0, or on a 429, the
  watcher waits until `x-rate-limit-reset` or `Retry-After`. If a 429 still
  happens, that account is marked failing. Repeated health alerts mean your
  intervals are too short for your tier, so raise `x.priority_interval` or
  `x.default_interval`.

Rough cost: each poll that finds nothing reads 0 posts. A busy studio account
posting 10 times a day costs about 300 reads a month, and polling interval
doesn't change that, since only new posts are returned.

The seeded X accounts are examples and ship with `enabled: false`. Check each
handle on x.com before enabling.

## Wikipedia (no keys)

One source watches English Wikipedia through Wikimedia EventStreams
(`recentchange`):

```yaml
- name: Wikipedia
  type: wikipedia
  category: celebrity
  trust: signal        # always signal: an edit is a hint, never a confirmation
  group: wikipedia
```

It watches these pages:

- **"Deaths in <Month> <Year>"** for the current month, last month's page for
  the first 7 days of a month (late-announced deaths are filed under the month
  they happened; see `wikipedia.deaths_previous_month_days`), and **"Deaths in
  <Year>"**. The titles roll over automatically. For each edit, the watcher
  fetches the diff and emits **one item per newly added entry**, e.g.
  `Deaths in November 2026: added "John Doe, 78, American actor (Show X)."`.
  Fixes to existing entries, moved lines, reverts, and bulk edits adding more
  than 10 entries are ignored.
- **Every `wikipedia:` page in `watchlist.yaml`.** Redirects are followed, and
  the lookup is refreshed weekly. Only human edits whose added text looks
  newsworthy become an item. Signals include:
  - a `death_date` / `death_place` / `death_cause` infobox value,
    `[[Category:2026 deaths]]`, a death-date template, or "is" changed to "was"
    in a biography;
  - died / passed away / killed / hospitalized / diagnosed with / arrested /
    charged with / sentenced …
  - for series pages, or anything "major" (hiatus, cancelled, retired, final
    chapter, was announced …): only when the added text also mentions this year
    or last year.

  The item's category comes from the watchlist entry.

**Revert detection.** Each emitted edit is remembered for 15 minutes
(`wikipedia.revert_window_minutes`). The edit counts as reverted if a later edit
on that page undoes it, rolls it back or restores an earlier revision (judged
from the edit summary), or if MediaWiki tags it `mw-reverted` (checked every
`wikipedia.revert_check_seconds`, one small API request). The alert engine then
sends a "possibly false" follow-up. Reverts after the window are ignored.

The stream reconnects with `Last-Event-ID`, so a short disconnect or restart
under 30 minutes doesn't miss edits. Edits older than that would be stale anyway.

## What isn't supported, and why

| Platform | Why |
|---|---|
| Instagram | No public API for reading other accounts in real time, and scraping breaks Meta's terms. |
| TikTok | The Research API isn't for this use, and scraping breaks the terms. |
| X without a paid tier | The free tier can't read timelines. Scraping X with a logged-in account breaks its terms and risks a ban. Follow the same studios through their RSS feeds, YouTube channels and Bluesky until you have a token. |
| YouTube by @handle | The public feed only takes channel ids. Look up the id once as shown above. The YouTube Data API would need a key and quota and isn't needed for this. |
| Wikipedia in other languages | Possible (`wikipedia.wiki` / `api_url`), but the Deaths-page parsing and keyword lists are written for English Wikipedia. |

## Checking it works

- `newsalert items --limit 30` lists stored items with their source.
- The JSON log shows `bluesky.connected`, `wikipedia.connected`, `x.started` or
  `watcher.disabled`, and `watcher.stream_error` / `watcher.error` with a retry
  delay when something fails.
- Each source's health is in the `source_state` table: `last_success_at`,
  `failing_since`, `last_error`. The health checker alerts when a source has
  been failing for 10 minutes.
