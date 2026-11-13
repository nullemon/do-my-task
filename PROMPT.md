# True Dog Stories Video Pipeline: Claude Code Brief

**How to use:**
1. Unzip this kit into a new folder (for example `Documents\DogStories`).
2. Double-click `setup.bat` once.
3. Open the folder in Claude Code.
4. Say: *"Read PROMPT.md and set everything up, then make the video for <story>."*

`STORIES.md` lists the stories: what's done, what's next, and the verified facts and fact-check warnings for each one.

Working reference code from the first 6 videos is in `reference/`. Reuse it and improve it; don't start from zero:
- `reference/pipeline/`: the renderer, timeline, voice, music and mix code.
- `reference/cases/<dog>/`: `script.py` and `cfg.py` for every finished video.
- `reference/downloader/`: the footage fetcher (.bat and .py).
- `reference/maps/`: map data and the map generators.
- `reference/tools/`: contact sheets, cut detection, speech-to-text, the job queue, `qc_empty.py`, and the thumbnail recipe.
- `reference/seo/`: the title, description and tags file for each video.

**Look at `examples/` first. The pictures show the target:**
- `1_reel_formats/`: the 4 layouts to mix in every video (section 3b), mocked up with our real footage.
- `2_BASELINE_improve_on_this/`: how our first 6 videos look. The hook text is good, but **the footage sits in a small window on a blurred background**, and 33–49% of the screen is "empty" according to `qc_empty.py`. Every new video must fill the screen far more than this.
- `3_our_thumbnails/`: the thumbnails for the first 6 videos (the style works; keep it).
- `4_finished_video_frames/`: 8-frame strips from every finished video, in both formats.
- `voice/`: Kokoro voice samples. **#1 `af_heart` is the channel voice.** Use it for every video.

---

## 1. Who I am and what you're making

I run a **dog page on Facebook and a dog YouTube channel**. You are my editor and producer. For each story, you make a complete video from start to finish:

- researched, **true and verified** stories (no fakes)
- an AI narrator (Kokoro TTS)
- real footage of the actual dog, plus moments where real audio plays with yellow subtitles
- animated title cards, maps and stat cards
- burned-in captions, gentle music, a header, a thumbnail, and an upload package

**Story topics that go viral in the dog niche:**
- heroic rescues: fires, floods, earthquakes, drowning
- incredible loyalty: waiting for owners, walking home
- K9 and military dog heroes
- shelter transformations: "nobody wanted him… then"
- famous dogs in history
- survival stories
- reunions

**Tone:** warm, emotional and uplifting, never grim. A strong hook in the first seconds. Every video ends with a call to subscribe and a comment question.

**Every video ships in two formats**, 30 fps, H.264, AAC:
- **9:16**, 1080x1920, for Facebook Reels and Shorts. Name it `<Dog> - <Hook Title> (9x16).mp4`.
- **16:9**, 1920x1080, for YouTube. Name it `16x9 - <Dog> - <Hook Title>.mp4`.

**Length: 4–6 minutes**, both formats. The script runs about 150 words per minute.

Build this as a **reusable pipeline**: one folder per story under `cases/<code>/`, with shared code in `lib/`. I will make many of these.

---

## 2. THE HOOK: the most important rule

People decide in the first 1–3 seconds whether to stay.

### First 3 seconds
- **Frame 1 is real footage or a real photo of the dog: moving, sharp and full-bleed.** Pick the most emotional true moment, such as the reunion, the dog in the ruins, the rescue, or the dog's face. No fade from black, no title card, and no blurred background.
- The **hook text appears in frame 1 and is huge**: 2–6 words per line, each line at least 8% of screen height and about 85% of screen width. White, with one yellow (or red) highlighted word, a heavy black stroke and a pop-in animation.
  - Good hooks from our videos: "LOST 2,551 MILES FROM HOME… HE WALKED BACK", "HER DOG NEVER LEFT", "HIS TOWN BURNED… HE REFUSED TO LEAVE".
- **The narrator starts within 0.5 s.** The first sentence opens a loop, for example:
  - "When the deadliest wildfire in California's history burned his town to the ground, this dog refused to leave."
  - "A three-year-old girl walks away from her home, into the Australian bush."
- If there is real audio worth hearing (a reunion, a rescuer's voice), you may open on it, with yellow subtitles.

### First 30 seconds
- **Change the picture every 2–4 seconds:** a new shot, a zoom punch, a photo pop-in, a map pin or a circle.
- Structure:
  1. hook
  2. twist ("But…")
  3. stakes
  4. optionally, a promise you pay off later ("…and what he did next made him a police dog")
  5. title card, **by 20 s at the latest**
- No dates and no backstory before the hook has landed.

### Throughout
- Put a mini open loop every 60–90 s: "But that wasn't the most amazing part…", "What the rescuers found next…"
- Pay off every promise.
- The ending lands on an emotional line about the dog, then the subscribe card, then the comment question.

---

## 3. NO EMPTY SCREEN: fill the frame

Our first 6 videos put a small framed window on a blurred copy of the same footage (`examples/2_BASELINE…`). **Upgrade that.**

- **Never** show a blurred or darkened frame with only a little text on it. A blurred background is only allowed behind a sharp foreground that covers at least 50% of the frame.
- **The 9:16 layout uses three zones that are always filled:**
  - **Top, 0–16%:** a header bar with the hook title and a small "DOG · PLACE YEAR" line in yellow. It stays the whole video.
  - **Middle, 16–72%:** footage, photo or graphic, **sharp and filling the full width**. When the source is 16:9, scale it to fill the width with a slow Ken Burns zoom. Or stack two sources: footage on top, and a photo, map or stat below.
  - **Lower, 72–88%:** captions, big and bold, 2 lines max.
  - Keep the **bottom 12% and right 12%** clear of anything important, because the Reels/Shorts buttons cover them.
- **Text, stat and chapter cards:** put a real photo or footage behind them at 40% brightness or more, with grain or paper texture and a slow 3–6% zoom. The text fills the card.
- **Every still image moves:** Ken Burns of at least 4% zoom per 5 s, or a slow pan.
- **16:9:** footage fills the frame, or sits in a window at least 70% of the width with a photo, map or stat filling the side. No big flat or blurred areas.
- Plain black is allowed only as a deliberate 0.5 s beat.
- **Automated check (required):** run `reference/tools/qc_empty.py` on every render. Target: under 20% average empty, nothing flagged in the first 30 s. Look at the first-30 s contact sheet yourself before delivering.

## 3b. Reel formats: mix them in every video

See `examples/1_reel_formats/Dog Reel Formats.jpg`. Every format keeps the header bar and fills the screen.

1. **SPLIT STACK** (the main body of the story)
   - Top: footage.
   - Bottom: a second visual: a photo of the dog, the owner, a map, a newspaper or a stat.
   - Between them: a dark caption band with red rules and big captions.
   - Label chips sit on the panels ("ABC NEWS · 2018", "HONORARY POLICE DOG").
2. **FULL-SCREEN + POP-UPS** (the hook, big reveals and emotional peaks)
   - One sharp shot fills the frame with a slow zoom.
   - Every 2–3 s something pops in: a polaroid, a red date stamp, a circle on the dog, a map pin, an arrow.
   - Big captions sit low, over a dark gradient.
3. **JOURNEY BOARD** (the recap at about 80%: "the whole journey", "everything he did")
   - A warm corkboard or scrapbook texture with pinned polaroids (clips can play inside them), red string between them, and yellow sticky notes with numbers ("2,551 MILES", "6 MONTHS", "12 LIVES").
   - The camera pans and zooms from item to item.
4. **FREEZE & MARK UP** (every real-audio moment: reunion, rescuer, owner, news interview)
   - Real footage fills the top 55–60%, then freezes on the key moment with a red circle, an arrow and "THAT'S MADISON".
   - The speaker label and yellow real-audio subtitles sit beneath.
   - A timeline of the story runs along the bottom with a progress dot.

**Default mix:**

| Part of the video | Format |
|---|---|
| Hook | 2 |
| Story | 1 |
| Real-audio moments | 4 |
| Recap at about 80% | 3 |
| Reveals and the reunion | 2 |

Switch format at least every 20–30 s. On 16:9, adapt each one: the split becomes side by side, the board is wide, and the freeze shows footage on the left with subtitles and the timeline on the right.

Keep the good parts of our current style:
- the animated route maps with a mile counter (`reference/maps/`)
- the stat cards with counting numbers
- the Playfair chapter cards
- the credit line "Source: …" under every clip

---

## 4. Voice: Kokoro TTS

- Install with `pip install kokoro-onnx soundfile`. Model files: `kokoro-v1.0.onnx` and `voices-v1.0.bin` from the kokoro-onnx GitHub releases (model-files-v1.0). `setup.bat` downloads them.
- **Voice: `af_heart`, lang `en-us`, speed 0.92–0.95.** It's warm and friendly, and it's the channel voice. Use it for every video.
- **Upgrade from the first 6 videos:** generate **one whole paragraph per call**, not one sentence at a time, so the delivery flows naturally. Then get word and sentence timings for the captions by running faster-whisper on the generated audio.
- Gaps: about 0.5 s between paragraphs and 0.3 s before a scene change.
- Polish chain on the final voice track (gentle):
  ```
  highpass=f=70,equalizer=f=160:t=q:w=1:g=2,equalizer=f=9000:t=q:w=1:g=1.5,
  acompressor=threshold=-20dB:ratio=2.5:attack=5:release=120:makeup=2dB,loudnorm=I=-16:TP=-1.5
  ```
- Keep a **pronunciation dictionary** per story and spell names phonetically for the TTS only. Captions keep the real spelling. Known fixes:
  - Warwick → "Worrick"
  - Seppala → "SEP-uh-lah"
  - Brazier → "BRAY-zher"
  - Rébsamen → "REBB-sah-men"
  - Hachikō → "HAH-chee-koh"
  - Capitán → "Kah-pee-TAHN"
- **Music:** gentle, warm piano and pad that you generate yourself (`reference/pipeline/music.py`), so there's no copyright. Sit it about 18 dB under the voice, let it rise a little on chapter cards, and drop it to almost nothing under real-audio moments.
- Final loudness: **-14 LUFS** integrated, true peak -1.5 dB.

---

## 5. Script

- **Only true, verifiable stories.** Many viral dog stories are fake or exaggerated. Research with web search and check every fact against **2 or more reputable sources**: major news, official statements (police, navy, fire service), museums or encyclopedias.
  - If a story can't be confirmed, say so and drop it.
  - If a popular claim is wrong, **say so in the video.** It builds trust and performs well; Frida's "The Truth About Frida" chapter is the example.
- Known traps:
  - Frida's "52 lives" is wrong; it was 12 found alive and 43 recovered.
  - The viral Capitán photo shows a different dog.
  - Hachikō photos and postcards are often fake.
  - Sergeant Stubby's rank was never official.
  - Distances and ages vary between sources; say "about" or use the most-cited figure.
- **Never invent quotes.** Real quotes only, from a transcript or a cited article. If a real-audio clip has no transcript, caption it descriptively ("[ Andrea sees Madison for the first time ]") until whisper gives you the words.
- Structure:
  1. hook (section 2)
  2. title
  3. 5 chapters with chapter cards (Chapter 1…)
  4. the problem or disaster
  5. what the dog did
  6. the peak moment (rescue or reunion)
  7. recognition and aftermath
  8. emotional closing line
  9. subscribe card
  10. comment question
- Short sentences. Respectful to people involved. No graphic injury detail: say "burns on all four paws", don't show it.
- Use stock dogs of the same breed only for general moments, and label them on screen ("A blue heeler (not Max)").
- The script format is in `reference/cases/*/script.py`: a list of segments.
  - `kind`: `narr` / `chapter` / `sound` (real-audio interlude).
  - `vis`: a list of `(source, t_in, crop, credit, t_out)`, or a special visual: `("MAP_PIN",..)`, `("MAP_ROUTE","key")`, `("STAT","2,551","MILES HOME","")`, `("PHOTO","key",None,"credit")`, `("CTA",0/1)`.
  - Extend it with the new formats (split, popups, board, freeze).
- **Show me the script and a 30 s preview in both formats before the full render.** If I say "go", or don't answer, carry on and render.

---

## 6. Footage and real audio

- I supply clips through the downloader zips (section 11c). Unzip each story into `cases/<code>/footage/`.
- Tools in `reference/tools/`:
  - `sheet.py`: contact sheets
  - `cuts.py`: scene changes
  - `stt.py` and `vttwords.py`: transcripts and YouTube word timings
- **Look at every clip yourself.** Make contact sheets of frames with timestamps, then:
  - pick the best moments
  - note station logos, lower thirds, tickers, burned-in subtitles and channel watermarks
  - **crop them out.** Verify every crop rectangle against the clip's real size before rendering. We had crops leave half an AP logo and a "MY DOGS" watermark showing.
- **Real-audio interludes:** 2–4 per video, such as the owner's reaction, the rescuer, the grandmother, or the reunion. The narrator pauses, the music drops, the clip plays in the Freeze & Mark Up format, and the whisper transcript shows as **yellow subtitles**. Find clean start and end points with a loudness envelope, so a clip never starts mid-word.
- **Footage never repeats within a video.** Track the source time ranges you've used. The storyboard tool flags overlaps.
- Credit every clip and photo on screen ("Source: KOIN 6 / WISH-TV · Oregon Historical Society") and in the description.
- Prefer, in order:
  1. the original uploader or news outlet
  2. public-domain archive film (for example *Call of the West*, 1924; Alaska Film Archives)
  3. Wikimedia Commons, Openverse or Library of Congress photos
  4. Pexels stock

---

## 7. Captions, header, cards

- **Captions:** burned in, 2 lines max, about 22–26 characters per line.
  - Heavy font: Montserrat Black (in `fonts/`), or Anton or Inter Black.
  - White, with a thick black outline, and the current word in **yellow** (word-by-word highlight).
  - Test the longest line, so nothing ever overflows the safe area.
- **Header (9:16):** a fixed top bar with the hook title (e.g. "HE GUARDED THE ASHES") and a yellow line "MADISON · PARADISE 2018".
- Chapter cards use Playfair Display Black over real footage, not on empty brown.
- Facebook-safe text: dog stories rarely need censoring, but keep words like "killed" or "dead" off the thumbnail and header. Use "lost their lives" or "didn't survive" in captions.

---

## 8. Rendering (must survive interruptions)

- **One encoded .mp4 per scene**, all with identical settings: libx264 `-preset veryfast -crf 18`, or `h264_nvenc -cq 20` on the RTX GPUs, yuv420p, 30 fps.
- Join them with the concat demuxer and `-c copy`, then mux the audio with `-c:v copy`.
- **Audio sync:** the mixed audio timeline must start at exactly the same moment as the first video frame. Our timelines start at t=0.5, so we trimmed the first 0.5 s of audio.
- Write each scene to `<name>.tmp.mp4` and rename it only when ffmpeg exits 0.
- Support `RESUME=1` (skip finished scenes) and `ONLY=3,7,12` (re-render specific scenes). When you re-render one scene, rebuild the previous scene's last frame, so its crossfade still matches.
- Put crossfades **inside** a scene file.
- Use a job queue (`reference/tools/runq.sh`, or a .bat equivalent) for long renders, so closing a window doesn't lose work.
- **The 9:16 and 16:9 builders share the same scene list and audio.**

---

## 9. QC before every delivery

1. Run `qc_empty.py` on both formats, fix what it flags, and look at the first-30 s sheet.
2. Make an 8-frame strip and a 1-frame-per-4.5 s contact sheet across the whole video. Look for logos, tickers, burned-in subtitles, cut-off text, black gaps, broken crops and repeated footage.
3. Check loudness: -14 LUFS. The voice is never masked, and interludes are audible.
4. Check caption sync and line length.
5. Fact-check once more.
6. **Tell me exactly which moments to listen to** (each real-audio clip, and tricky name pronunciations) if you can't listen yourself.
7. Remind me to download the finished files, and delete big temp files.

---

## 10. Thumbnails (per video)

- **YouTube 16:9, 1280x720**, `<Dog> - YouTube Thumbnail 16x9.jpg`. Recipe in `reference/tools/thumb_dog.py`:
  - a story-colored gradient on the left
  - **the real dog's face, big and sharp**, on the right 55–60%, from the real footage or photo, with logos cropped out
  - a red "TRUE STORY" tag
  - a 2–4 word headline in Montserrat Black: white plus one yellow line, often with a number ("2,551 MILES HOME", "SHE SAVED 12 LIVES", "100+ KOALAS RESCUED")
  - a small sub-line ("17 YEARS OLD · DEAF · HALF-BLIND")
  - optionally, a yellow circle and arrow on the dog when it's in a group photo (Togo)
- **Shorts 9:16, 1080x1920**, `<Dog> - Shorts Thumbnail 9x16.jpg`: the dog's face fills the top 55%, the headline is centered below, and there are no empty areas.
- Check that the headline never covers the dog's face. We had to fix that twice.

## 11. Upload package (per video)

See `reference/seo/*.txt` for the format. Write:
- a title under 70 characters, plus 2 alternative titles
- a 2-paragraph description
- chapters with **real timestamps from the render**
- a subscribe line and the comment question
- **SOURCES**, with links, plus fact-check notes
- **FOOTAGE & PHOTO CREDITS**, including licences (CC BY, etc.)
- "Narration: AI voice (Kokoro TTS). Music: original composition."
- hashtags, a Facebook Reel caption, tags, and a **pinned comment** that asks a question

## 11b. Setup on my computer (do this first, once)

- I'm on **Windows**. One laptop has an RTX 3060 and another has an RTX 4060 with Claude Code. Make everything work there; Mac and Linux are a bonus.
- `setup.bat` installs:
  - Python packages: `kokoro-onnx soundfile numpy pillow opencv-python faster-whisper yt-dlp[default] requests imageio-ffmpeg ddgs`
  - ffmpeg
  - the Kokoro model
  - the NVIDIA cuBLAS and cuDNN wheels, for whisper on the GPU

  Fix it if anything fails.
- Fonts are in `fonts/`.
- Maps need Node.js and `npm i d3-geo topojson-client us-atlas world-atlas` (see `reference/maps/`).
- **My PC has an `SSLKEYLOGFILE` environment variable that breaks Python downloads** ("PermissionError … virtual_file.log"). Every .bat must clear it (`set "SSLKEYLOGFILE="`), and every Python script must `os.environ.pop("SSLKEYLOGFILE")` before any import that makes network requests.
- Every .bat window must **stay open no matter what**: re-launch itself with `cmd /k`. Each one also writes a log file.
- Create double-click launchers (.bat):
  - `new_story.bat <code> "<Dog Name>"`
  - `fetch.bat <code>`: downloads the footage
  - `voice.bat <code>`
  - `preview.bat <code>`: the first 30 s, both formats
  - `render.bat <code>`: full render through the queue, resumable
  - `thumbs.bat <code>`
  - `qc.bat <code>`
- Use all CPU cores. Use **h264_nvenc** on the RTX GPU when it's available.

## 11c. Getting footage: the downloader

`reference/downloader/` has the working fetcher: `FETCH_DOG_FOOTAGE.bat` plus `fetch_dog_footage.py`, which has the shot list for all 10 stories in `STORIES`.

- **If you run in Claude Code on my PC:** run the fetcher directly and use the files in place. No zips are needed.
- **If you run in a cloud session that can't reach YouTube:**
  1. Give me the .bat and the .py.
  2. I double-click the .bat, type the story numbers, and upload the zips from `DogFootage\_ZIPS_TO_UPLOAD`. Each zip is under 390 MB.
  3. Unzip them into `cases/<code>/footage/`.

**What it does:**
- **YouTube:**
  - Searches with yt-dlp.
  - Scores results, preferring news channels, local TV call signs (K***/W***), the original uploaders and official accounts.
  - Blocks compilations, reaction videos, "story" narrator channels, AI videos, and movie trailers and clips.
  - Downloads the best 1–2 matches per moment at 480p, with subtitles.
- **Stock and photos:**
  - Pexels stock clips, if a free API key is in `keys.txt`.
  - Web photos via DuckDuckGo and Bing image search. It skips Getty, Shutterstock, Alamy, Pinterest and similar, and removes duplicates by image hash.
  - Openverse CC photos, Wikimedia Commons, and the Library of Congress.
- **Transcripts:** optional faster-whisper transcripts on the GPU, with an English translation for Spanish, Ukrainian and Japanese clips.
- **Records:** writes `manifest.csv` with the source, author and licence for every file, and a `_done_searches.json`, so a re-run **skips everything already done**.

**Lessons already built in (keep them):**
- `SSLKEYLOGFILE` is removed in both the .bat and the .py.
- YouTube needs a JavaScript runtime. Use `pip install deno` and `yt-dlp[default]`; `yt-dlp[curl-cffi]` removes the impersonation warning.
- **Bot check:** the fetcher retries with cookies from Firefox, Edge or Chrome.
- **Subtitles rate-limited (429):** retry without subtitles, and after 2 failures turn subtitles off for the rest of the run.
- **Wikimedia rate limits (429), sometimes with "wait 600 s":**
  - Wait and retry when the delay is short.
  - When it's long, defer those searches to the end of the run.
  - Check that every saved file really is an image (PIL verify).
- Library of Congress returns 403 to script-like requests: send browser headers, and skip it if it still refuses.
- DuckDuckGo returns image sizes as text, so convert them to int.
- Generic searches return junk (Commons "Togo" gave maps of the country Togo, and "Nome" gave bumblebees). For searches with the dog's name, require the name in the file title.
- Keyword filters per moment stop wrong-story clips. A different missing-toddler case once slipped in.

## 12. How to work with me

- I want **minimal effort**. Start working right away, use a task list, and ask only when a choice really matters.
- For each story:
  1. research and verify
  2. script
  3. the 30 s preview in both formats
  4. full render, 9:16 first
  5. QC
  6. 16:9
  7. thumbnails
  8. upload package
- **Send each finished video as soon as it's done.** Don't wait for a batch.
- When I say "batch", queue several stories and render them back to back.
- Keep status updates short: what's done, what's rendering, and what's next.
- Always remind me to download finished videos if the workspace is temporary.
