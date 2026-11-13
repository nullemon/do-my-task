# Reference code from the first 6 dog videos

These scripts worked in a cloud workspace. Paths start with `/home/claude/...`; make them relative.

## pipeline/ (shared by all 6 videos)

| File | What it does |
|---|---|
| `tts.py` | Kokoro `af_heart` narration, one sentence per call. **Upgrade:** generate one paragraph per call and take timings from whisper. |
| `timeline.py` | Turns `script.py` into `timeline.json`: shot spans, narration placement, real-audio clips, word-timed caption chunks, overlays. Imports `cfg.py`. |
| `render.py V\|H [spans] [still_times]` | Renders one .mp4 per span (`s000.mp4`…) through a PIL frame compositor piped to ffmpeg. It handles footage windows with crops, Ken Burns photos, maps (`MAP_PIN` / `MAP_ROUTE` / `MAP_OUT` / `MAP_HOME`), stat cards with counters, chapter cards, CTA cards, the hook headline, the title overlay, the header and word-highlight captions. `ONLY` mode: `render.py V 11,12`. Preview frames: `render.py V all 3.0,22.0`. |
| `music.py <seconds>` | An original warm piano and pad track (F major, 68 bpm) with reverb. |
| `mix.py` | Places the narration and real-audio clips, ducks the music (to 0.24 under voice, 0.05 under real audio), and writes `mix_raw.wav`. Then: `loudnorm=I=-14:TP=-1.5`. |
| `storyboard.py` | Start, middle and end frames of every span, plus a check that **flags footage reuse**. |

**Assembly:**

    concat s*.mp4 -c copy
    ffmpeg -i video.mp4 -ss 0.5 -i mix.m4a -map 0:v -map 1:a -c:v copy

The `-ss 0.5` is there because the timeline starts at 0.5 s.

## cases/<dog>/

`script.py` (segments plus visuals) and `cfg.py` (sources, photos, hook text, header, map and still settings) for each video.

## downloader/

The footage fetcher: YouTube, Pexels, web images, Openverse, Commons, the Library of Congress, whisper transcripts and zips.

## maps/

- `proj.mjs`: the US Albers map.
- `aus.mjs`: Australia.
- `cmap.mjs`: any country or bbox, with points projected in Mercator.
- The `*.json` files are the projected maps each video used.

## tools/

| File | What it does |
|---|---|
| `qc_empty.py` | Empty-screen QC. |
| `thumb_dog.py` | The thumbnail recipe. |
| `vttwords.py` | Word timings from YouTube auto-subtitles. |
| `sheet.py`, `cuts.py`, `stt.py`, `runq.sh`, `mkedit.py` | Shared tools from the true-crime kit. |

## seo/

The title, description and tags file for each video, including sources, credits and the "moments to listen to" list.
