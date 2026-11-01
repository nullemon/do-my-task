# Story episodes: 80s cartoon (or any style) from your own story

Claude turns your story into a shot list with every prompt written out. You make the pictures and clips in
ComfyUI, and `make_episode.py` assembles the episode: camera pans done in code, the 80s finish (hand-drawn 12 fps,
faded colour, grain, gate weave), title, captions that work with the sound off, voices, music ducked under the
voices, sound effects, at -14 LUFS for Facebook, 1080 x 1920.

| File | What it does |
|---|---|
| `story_to_episode.py` | Your story → `episode.json` + `shotlist.md` per episode (Claude, your API credits; about $0.10–0.30 a run) |
| `pick.py` | Copies your newest ComfyUI result into the episode folder under the right name |
| `make_episode.py` | Builds `final.mp4` + `cover.jpg`. Missing shots show as labelled cards, so you can preview any time |

## One-time setup on the pod

1. **Claude API key** (never paste it in a chat). In RunPod: **Settings → Secrets → Create Secret**, name it
   `anthropic_key`, paste the key. Then **Pods → your pod → Edit Pod → Environment Variables → Add**:
   key `ANTHROPIC_API_KEY`, value `{{ RUNPOD_SECRET_anthropic_key }}` → Save (the pod restarts; your files stay).
2. **Update and download the music + sound-effect models** (about 36 GB), in the pod's terminal:

   ```bash
   pkill -f "main.py --listen"; curl -fsSL https://raw.githubusercontent.com/nullemon/do-my-task/claude/sharp-wright-ft6mhj/ai-studio/runpod/setup.sh | PACKS="audio" bash
   ```

   Add `ltx25` (talking shots with sound) and `infinitetalk` (lip-sync) inside the quotes if your volume has room.

## Make an episode

Write your story in a text file (any length) and upload it to `/workspace`, e.g. `/workspace/my_story.txt`. Then:

```bash
cd /workspace/do-my-task/ai-studio/cartoon
/workspace/venv/bin/python story_to_episode.py /workspace/my_story.txt --episodes 3 --style american80s
```

`--style anime80s` for the 80s anime look, or your own words (`--style "black ink stickman doodles" --look clean`).
It creates `/workspace/episodes/ep01`, `ep02`, … each with a **shotlist.md**. Open it in JupyterLab and work down it:

1. **Characters:** make a model sheet for each character with **Z-Image** using the prompts in shotlist.md.
2. **Pictures:** for each shot, run its picture prompt in **Z-Image** (1088 × 1920), then
   `/workspace/venv/bin/python pick.py ep01 1` (shot number) to copy the newest result in as `shot01.png`.
3. **Acting shots** (marked *animate*): load that picture into **Wan 2.2 14B Image to Video** (720 × 1280, 5 s,
   turbo on for tries) with the motion prompt, then `pick.py ep01 1` again (it saves `shot01.mp4` and keeps the png).
   For an exact start and end pose use **Wan 2.2 14B First-Last Frame** instead.
4. **Voices:** record the lines on your phone, upload to `ep01/voice/` as `shot01.m4a`, `shot02.m4a`, … (or one
   `narration.m4a` for the whole episode).
5. **Music:** run the music prompt in **ACE-Step 1.5 XL Turbo**, then `pick.py ep01 music`.
6. **Sound effects (optional):** each shot's effect in **Stable Audio 3.0**, then `pick.py ep01 sfx 4`.
7. **Build:** `/workspace/venv/bin/python make_episode.py ep01` → `/workspace/episodes/ep01/final.mp4`.
   Options: `--look 80s-anime`, `--look clean` (no retro finish), `--frame tv` (4:3 "old TV" picture).

Edited the story or a prompt? Edit `/workspace/episodes/series.json` and run
`story_to_episode.py --from-json /workspace/episodes/series.json` to rebuild the folders (no Claude call).

## Which model for each step

| Step | Free (your pod) | Paid (Partner Nodes) |
|---|---|---|
| Script, shot list, prompts, captions | Claude (`story_to_episode.py`) | — |
| Character sheets, shot pictures | Z-Image, Qwen Image 2.1 (+ Edit to change a picture) | Nano Banana 2.1, GPT Image 2.5 |
| Same look every shot | LoRA trained on your character sheets (next step) | — |
| Wide shots, camera pans, holds | `make_episode.py` (code, no AI wobble) | — |
| Acting shots | Wan 2.2 14B Image to Video / First-Last Frame | Seedance 2.5, Kling 4.0 |
| Talking shots with sound | LTX-2.5 (`ltx25` pack) | — |
| Voices | Your own recordings | Eleven v4 |
| Lip-sync | InfiniteTalk (`infinitetalk` pack) | Sync 3 |
| Music | ACE-Step 1.5 XL Turbo (`audio` pack), MiniMax Music 3 (`music3`) | — |
| Sound effects | Stable Audio 3.0 (`audio` pack) | Mirelo |
| 80s finish, titles, captions, mix | `make_episode.py` | — |
| Sharpen | SeedVR2 (`upscale` pack) | Topaz |

## Keeping it from looking like AI slop

- Most shots are pans and holds on strong paintings; animate only the acting moments, one simple action each.
- Run each acting shot 2–3 times and keep the best; cut away from mistakes.
- Real voices beat robotic ones. Original music means no muted videos.
- Avoid close-ups of hands, crowds, fast spins and text inside pictures.
