# True Dog Stories: Project Handoff

Everything a new Claude session needs to continue this project.
**Read this file first, then `PROMPT.md` (the original brief).**

- **Repo:** https://github.com/nullemon/do-my-task, branch `claude/ready-check-smc4ba` (all code, scripts, research, photos)
- **Not in git** (too big, re-creatable): `models/`, `cases/*/footage/` (videos re-download with `lib/media.py`), `cases/*/work/` (render scratch), and the final `.mp4` files (on Gofile, links below)

---

## 1. What this is

A Facebook page and YouTube channel of **true, fact-checked dog stories**. Each video is made by an automated Python pipeline:
research → script → AI narration → real footage and photos → captions, maps, cards and music → 9:16 and 16:9 renders → QC → thumbnails → upload text → Gofile.

## 2. Status (as of 20 Nov 2026)

11 videos are finished, each with both formats, both thumbnails and an upload text file.

| # | Case folder | Video | Gofile | Real moving footage |
|---|---|---|---|---|
| 1 | `hachiko` | Hachikō: He Waited 9 Years | https://gofile.io/d/ekdsecAI (older version; re-render recommended) | photos only (made before the video-throughout rule) |
| 2 | `rintintin` | Rin Tin Tin: From a Battlefield to Hollywood | https://gofile.io/d/ps9CEzTr | 93%, his own 1920s films |
| 3 | `chips` | Chips: The Family Dog Who Charged a Machine Gun | https://gofile.io/d/p6kWHkXV | 73%, 1942–43 Army/Navy film |
| 4 | `stubby` | Stubby: Smuggled to War | https://gofile.io/d/I2rTmpA6 | 71%, his own division's 1918 film |
| 5 | `owney` | Owney: Around the World by Mail | https://gofile.io/d/Lcrr0oxB | 56%, 1897–1903 postal films |
| 6 | `lucca` | Lucca: 400 Missions, Not One Marine Lost | https://gofile.io/d/J3pvPwWi | about 50%, real 2012 USMC video of her |
| 7 | `judy` | Judy: Prisoner of War 81A | https://gofile.io/d/rpKQuVNR | 82%, 1937–46 newsreels |
| 8 | `bretagne` | Bretagne: They Lined Up to Salute Her | https://gofile.io/d/wZVFSiqa | 81%, FEMA search dogs (labelled "not Bretagne") |
| 9 | `patron` | Patron: 4 Kilos of Courage | https://gofile.io/d/gFBkpQJa | 51%, real video of Patron and Ukrainian sappers |
| 10 | `bobby` | Greyfriars Bobby: 14 Years at a Grave… or Did He? | https://gofile.io/d/KHyI0c63 | 52%, Edinburgh film |
| 11 | `smoky` | Smoky: 4 Pounds, 70 Feet of Darkness | https://gofile.io/d/cjcTLJ0U | 80%, 1943–45 Pacific film (labelled Yorkie clips) |

Gofile deletes files nobody downloads for a while, so download them.

**Known weak spots:**
- Smoky, Judy and Chips fail the `qc_empty.py` target (more than 20% "empty"). Every frame has footage, but the 1940s film is hazy and grey.
- Bretagne, Smoky and Judy have no free photo or video of the real dog. They use labelled stand-in clips, and the thumbnails say "illustrative".

## 3. The user's rules (follow these)

1. **Video must play throughout the whole video**: unique clips with no repeats (`timeline.py` flags reuse). Photos are allowed in places, but **never a plain black background**.
2. **Pronunciation must be right**:
   - Years are spoken naturally ("nineteen twenty-three", "twenty fifteen"); `lib/tts.py: years()` handles this.
   - "9/11" is spoken "nine eleven".
   - Every name is checked with faster-whisper after generation.
3. **Facts:**
   - Every claim needs 2+ reputable sources (see `cases/*/research.md`).
   - Correct popular myths on screen; never invent quotes.
   - Label stand-in footage as "(NOT <dog>)".
4. **Delivery:**
   - Each video gets **its own new Gofile folder** (`python lib/gofile.py <case>`).
   - The user prefers to get **all links together** at the end of a batch.
   - Keep messages short.
5. **Footage the user supplies:** when we can't download YouTube (cloud session), give them ONE combined `.bat`: `deliver/fetcher/FETCH_ALL_REMAINING_STORIES.bat` with `fetch_dog_footage.py`. They upload the zips.
6. The videos are **not monetized**, so non-commercial-licence models and assets are acceptable now.
7. The user wants minimal effort on their side: just do the work and only ask when it really matters.

## 4. Next task: a cloned voice (the user's own)

The user thinks the AI narration is why views are low. They rejected Kokoro (current), Chatterbox, and the Qwen3-TTS designed voices (samples in `deliver/voice_test*/`).

**Agreed plan:**
1. The user records `deliver/voice_clone/READ_THIS_ALOUD.txt` (about 2 minutes, quiet room, phone 15 cm away) and uploads it.
2. Clone the voice with the strongest free models; non-commercial licences are now fine:
   - **Qwen3-TTS Base** (`pip install qwen-tts`, `Qwen/Qwen3-TTS-12Hz-1.7B-Base`, `generate_voice_clone`; pass the reference text, which is the reading script, for ICL mode)
   - **Fish Audio S2 Pro**
   - **Voxtral TTS** (Mistral)
   - **IndexTTS2**
   - also worth checking: Dots.TTS, VoxCPM2, ZONOS2
3. Score each clone against the user's recording with a speaker-verification embedding (e.g. `speechbrain/spkrec-ecapa-voxceleb` cosine similarity) **and** whisper WER. Send the top 2 samples, same Hachikō paragraph, to the user.
4. If the user records 20–30 minutes, fine-tune the best model for a closer match (best done on their RTX GPU).
5. Plug the chosen model into `lib/tts.py` as a new engine:
   - Copy the existing pattern: `VOICE=chatterbox` runs `lib/cbx_worker.py` in a separate venv via `chatterbox_batch()`.
   - Plain-text engines use `plain_text()` and the name respellings in `lib/respell.py`.
   - Then run `VOICE=<engine> FORCE=1 python lib/tts.py <case>` for every case.
   - Check names in `work/tts/tts.json` → `heard`, fix respellings, and re-run.
6. Re-render all 11 (see section 6), QC them, and upload new Gofile links.
   - The new voices are slower, so videos will run about 5–6 minutes, which is fine.
   - Hachikō also needs the video-throughout upgrade (footage from the fetcher).

## 5. Repo layout

```
PROMPT.md            original brief (hook rules, 4 reel formats, captions, QC, SEO format)
STORIES.md           story list and fact-check flags
HANDOFF.md           this file
setup.bat / setup.sh one-time install (Python packages, ffmpeg, Kokoro model, Chatterbox venv, map deps)
voice.bat preview.bat render.bat qc.bat thumbs.bat fetch.bat new_story.bat   Windows launchers (window stays open, logs/)
lib/
  common.py      paths, fonts, case loading (cfg.SRC from footage/manifest.csv, cfg.PH from photos/manifest.csv), encoder (nvenc/x264)
  shots.py       script building blocks: P() photo, F() footage, FULL/SPLIT/BOARD/FREEZE/MAP/STAT/CTA, pop-ups POL/STAMP/CIRCLE/CHIP/PIN
  tts.py         narration: Kokoro (IPA dictionary cfg.PRON) or Chatterbox (VOICE=chatterbox); whisper word timings → captions
  respell.py     spoken respellings for plain-text TTS engines
  cbx_worker.py  Chatterbox runner (separate venv)
  timeline.py    script → work/timeline.json; prints % video screen time and FOOTAGE REUSE warnings
  render.py      PIL compositor → one mp4 per span (RESUME, ONLY=, PREVIEW=, STILLS=, JOBS=)
  music.py mix.py  original music; mix with ducking, -14 LUFS two-pass loudnorm and a true-peak limiter
  build.py       concat spans + mux audio → cases/<c>/deliver/
  pipeline.py    voice | preview | render | qc | new
  media.py       downloads cases/<c>/media.json items (Commons via CDN thumbnails, archive.org, DVIDS via curl); NO_API=1, SKIP_COMMONS=1
  vidsearch.py   search archive.org / DVIDS for clips
  clipsheet.py cliprows.py windows.py photosheet.py montage.py sheets.py qc_empty.py   review tools (contact sheets)
  thumbs.py      YouTube and Shorts thumbnails from cfg.THUMB
  gofile.py      upload deliver/ to a new Gofile folder
  maps/cmap.mjs  map data (node; d3-geo, world-atlas); optional rotation for world maps
cases/<code>/
  research.md media.json cfg.py script.py (VIS dict = clip choices) photos/ footage/(not in git) deliver/(thumbs + SEO txt) map_*.json
reference/           the original kit's working code and downloader (fetch_dog_footage.py has stories 7–18)
deliver/fetcher/     FETCH_ALL_REMAINING_STORIES.bat + .py for the user
deliver/voice_test*, deliver/voice_clone/   voice samples and the recording script
```

## 6. How to (re)make a video

```bash
python lib/media.py <case>            # download photos/footage listed in media.json (NO_API=1 if Wikimedia rate-limits)
python lib/tts.py <case>              # narration + word timings (VOICE=..., FORCE=1 to regenerate)
python lib/timeline.py <case>         # check: duration 4–6 min, video %, no REUSE warnings
python lib/mix.py <case>
STILLS=1,30,60,... python lib/render.py <case> V   # spot-check frames before a full render
python lib/pipeline.py <case> render  # 9:16 then 16:9, resumable
python lib/pipeline.py <case> qc      # qc_empty + contact sheets + loudness; LOOK at deliver/qc/*_sheet.jpg
python lib/thumbs.py <case>
python lib/gofile.py <case>           # new folder per video → deliver/gofile_link.txt
```

**Gotchas:**
- Re-rendering a single scene: `ONLY=i,i+1`, then re-run `build.py` for V and H.
- Before a long render, check `df -h`. Delete old `cases/*/work/out_*` folders, which can be 0.5–1 GB each.
- Wikimedia API rate limits: `media.py` falls back to CDN thumbnails and to the credits in `media.json`.
- Old film often has burned-in timecode or a vignette: crop it with `F(..., crop=dict(x0,y0,x1,y1))`. `render.py` also auto-crops black bars.
- Never leave background shell loops that `pgrep` for their own pattern; they match themselves and wait forever.

## 7. Ideas to grow views (not done yet)

- **Real-audio moments:** 2–4 per video (owners, handlers, news) in the Freeze format with yellow subtitles. These need the fetcher zips.
- **Shorts cut-downs:** a 30–50 second hook version of each video as separate Shorts and Reels, linking to the full video.
- **A/B thumbnails:** try a second thumbnail per video. The YouTube "Test & Compare" feature handles this.
