# Local AI studio (Alienware)

Open-source equivalents of Higgsfield Genjutsu, running locally in ComfyUI: image generation and editing,
image-to-video, motion transfer, character replacement and video object swap.

1. `powershell -ExecutionPolicy Bypass -File ai-studio\setup-comfyui.ps1` (picks your roomiest drive and the packs your GPU can run; safe to re-run)
2. `powershell -ExecutionPolicy Bypass -File ai-studio\start-comfyui.ps1` and open http://127.0.0.1:8188
3. In Claude Code: "Read ai-studio/CLAUDE.md and run the test plan."

`models.json` lists the files per pack (image, video, motion, swap, ltx). `comfy_run.py` runs exported
API-format workflows from the command line.

Renting bigger GPUs: see `runpod/README.md` (one command sets up the same studio on RunPod).
