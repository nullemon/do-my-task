# Local AI studio — brief for Claude Code

Goal: a local, free-to-run studio on the user's Alienware that does what Higgsfield Genjutsu does,
at the highest quality this machine allows:

| Job | Model (ComfyUI template) | Pack |
|---|---|---|
| Generate images | Z-Image Turbo (`image_z_image_turbo`), Qwen Image 2.1 Turbo (`image_qwen_image_2_1_turbo_t2i`) | image |
| Edit images, swap objects in stills, keep a character consistent | Qwen Image 2.1 edit (`image_qwen_image_2_1_image_edit`) | image |
| Image → video, light (8 GB cards) | Wan 2.2 5B (`video_wan2_2_5B_ti2v`) | video_light |
| Image → video, best | Wan 2.2 14B + 4-step LoRAs (`video_wan2_2_14B_i2v`) | video |
| Motion transfer (keep a clip's motion, new character/scene) | Wan Animate 2 distilled (`video_wan_animate2_distilled`) | motion |
| Character replacement in a video (works with animals) | SCAIL-2 int8 (`video_wan21_scail2_character_replacement_int8`) | motion |
| Object swap / removal in a video | Wan 2.1 VACE inpainting + SAM 3.1 masks (`video_wan_vace_inpainting`) | swap |
| Video with sound, portrait-friendly (optional) | LTX-2.3 (`video_ltx2_3_i2v`) | ltx |

`models.json` lists every file, its folder and URL (taken from ComfyUI's official templates).
`comfy_batch.py` spreads a list of jobs over several ComfyUI servers (one per GPU).
`setup-comfyui.ps1` installs ComfyUI portable on the drive with the most free space (on this laptop `D:\AI`)
and downloads the packs that suit the GPU and RAM it detects. `comfy_run.py` runs an
API-format workflow headlessly.

## The machine and how to fit big models on it

**RTX 4060 Laptop GPU with 8 GB VRAM** and **64 GB system RAM** (both confirmed), one NVMe SSD split into C: and D:, Windows 11. Most of these models are far larger than 8 GB; ComfyUI offloads weights to system RAM
automatically, which works but is slow, and the 14B models need 32 GB+ of system RAM to load at all.

- The 64 GB of RAM is what lets the 14B models run here: ComfyUI keeps what doesn't fit in the 8 GB card in
  RAM. Ask the user to close browsers and other heavy apps before long jobs (they idle at ~28 GB used).
- Default to the light paths for drafts (Z-Image Turbo, Wan 2.2 5B), then the 14B models for final shots.
- Treat motion transfer / character replacement (14B) as overnight jobs at 480p, and tell the user how long
  one clip took before queueing more. If it is impractical, say so and suggest renting a cloud GPU for those
  jobs (same workflows) rather than forcing it.

- Test at 480p, ~49–81 frames (about 2–5 s) first; go to 720p once a workflow behaves. Upscale to 1080p as a
  separate pass (try LTX's spatial upscaler or a video upscale model) rather than generating at 1080p.
- Keep the distilled / 4-step / int8 variants the templates already use; they are the speed trick.
- If you hit out-of-memory: fewer frames, lower resolution, then ComfyUI flags such as `--reserve-vram 1`
  or `--lowvram` in `run_nvidia_gpu.bat`. Close games/other GPU apps. Laptop plugged in, Performance mode.
- The VACE template uses the fp16 14B model (~32 GB). If it is too slow, look for an fp8 version of the
  same model before giving up on it.
- Only one GPU job at a time. Queue generations; never run two ComfyUI servers.

## Workflow

1. Start ComfyUI with `ai-studio\start-comfyui.ps1` (it runs `run_nvidia_gpu.bat` from its own folder; the .bat
   fails if started from anywhere else), then http://127.0.0.1:8188.
2. For each template above: open it (Workflow → Browse Templates), confirm it runs once from the UI, then
   Workflow → Export (API) to `ai-studio/workflows/<template>.json`. Record which node ids take the prompt,
   input image, input video, mask, resolution, frame count and seed in `ai-studio/workflows/README.md`.
   Browser automation (Playwright is installed in `long-way-home/`) is fine for this.
3. Batch jobs with `comfy_run.py` using ComfyUI's own Python:
   `D:\AI\ComfyUI_windows_portable\python_embeded\python.exe ai-studio\comfy_run.py --workflow ... --upload ... --set ... --out ...`

## Test plan (show the user the results as one comparison sheet + the MP4s, with seconds per job)

A. **Images**: a stylized-3D "Rusty" (old golden-retriever mix, reddish-gold coat, grey muzzle, worn red
   collar, yellow-green tennis ball) from Z-Image Turbo and Qwen Image 2.1 Turbo; then a Qwen edit that
   swaps the ball for a red frisbee and one that changes the background to a rainy gas station at night.
B. **Image → video**: animate the best Rusty image (Wan 2.2 5B; 14B only if installed) — tail wag, head tilt, rain.
C. **Motion transfer**: the user films a dog (or themselves) on a phone; drive the Rusty image with it
   (Wan Animate 2 distilled). Compare with SCAIL-2 character replacement on the same clip.
D. **Video object swap**: in a short clip, replace or remove one object with VACE inpainting + SAM 3.1.
E. Upscale the best result to 1080p vertical and report the total time.

Put results in `ai-studio/outputs/<date>-test/` (git-ignored) and a `results.md` with timings and honest
notes on where it falls short of Genjutsu.

## Working style

- The user is non-technical. Show results, not logs. Keep each update short.
- Use subagents in parallel for independent work (e.g. one exports API workflows and maps node ids, one
  prepares test inputs and prompts, one writes `LICENSES.md`), but run GPU jobs one at a time.
- Before any commercial use, check each model card's license and record it in `ai-studio/LICENSES.md`
  (Wan, Qwen Image and Z-Image are Apache-2.0 as far as we know; LTX, SCAIL-2 and SAM have their own terms).
- Only animate or swap real people with their consent.
- Commit scripts, workflow JSONs and notes; never commit model files or outputs.

## On RunPod (rented GPUs)

`runpod/setup.sh` installs everything on the network volume (`/workspace`) and starts one ComfyUI per GPU
on ports 8188, 8189, … (`runpod/start.sh`). The user's guide is `runpod/README.md`.

- Paths: ComfyUI `/workspace/ComfyUI`, Python `/workspace/venv/bin/python`, outputs `/workspace/outputs/gpuN`,
  logs `/workspace/logs`.
- With 32–96 GB of VRAM, use the quality settings: 720p (1080p on 96 GB), longer clips, `video` (Wan 2.2 14B)
  instead of `video_light`, `motion_full` (Wan Animate 2) for final motion transfer, then `upscale` (SeedVR2).
- Spread queues over every GPU with `comfy_batch.py --jobs jobs.json --auto`; write the jobs file instead of
  running jobs one by one.
- The pod bills by the hour: tell the user when a batch is done so they can stop it, and never leave a
  long job running without saying how long it will take.
