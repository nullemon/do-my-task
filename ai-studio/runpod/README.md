# AI studio on RunPod (rented GPUs)

Same ComfyUI and models as the laptop, on a rented RTX 5090 (32 GB) or RTX PRO 6000 (96 GB),
and as many GPUs at once as you rent. RunPod's screens change now and then, so a button label may differ
slightly from what's written here.

## Costs (check RunPod's pricing page, they change)

| What | Price | When you pay |
|---|---|---|
| Network volume (your saved models and results) | about $0.07 per GB per month, so 400 GB ≈ $28/month | always, even with no pod running |
| RTX 5090 (32 GB) | about $0.50–1.00 per hour | only while a pod is running |
| RTX PRO 6000 (96 GB) | about $1–2.50 per hour | only while a pod is running |

You need at least one hour of the GPU's price in your balance to start a pod. If the balance reaches $0,
RunPod stops your pods (the network volume keeps your files).

## One-time setup

1. **Account and credit:** sign up at runpod.io → **Billing** → add $25. Turn on the low-balance alert.
2. **Network volume:** **Storage → Network Volume → New**. Pick a data center that shows **RTX PRO 6000**
   and/or **RTX 5090** as available, size **400 GB** (all packs) or **250 GB** (fewer packs), name it `ai-studio`.
3. **First pod (downloads the models):** **Pods → Deploy**.
   - Select your `ai-studio` network volume at the top; the GPU list then shows only that data center.
   - For this first run pick a cheap GPU such as **RTX 5090**. Downloading doesn't need the big one.
   - Template: RunPod's **PyTorch** template (any recent 2.x).
   - **Edit** the template: **Expose HTTP Ports** → keep `8888` and add `8188,8189,8190,8191`.
     Container disk 50 GB is plenty.
   - **Deploy On-Demand**.
4. **Open a terminal:** when the pod says Running, click **Connect** → **JupyterLab** (port 8888) →
   **Terminal**. Paste:

   ```bash
   curl -fsSL https://raw.githubusercontent.com/nullemon/do-my-task/claude/sharp-wright-ft6mhj/ai-studio/runpod/setup.sh | bash
   ```

   The first run downloads about 320 GB of models (roughly 20–60 minutes at data-center speed) and ends with
   `GPU 0 ready  https://<pod>-8188.proxy.runpod.net`. Open that link: it's ComfyUI, same as on the laptop.

## Every time after that

1. **Pods → Deploy** with the same network volume. Pick the GPU you want: **RTX PRO 6000** for the heavy
   video models, or **GPU count 2–4** to run several jobs at once (one ComfyUI per GPU, ports 8188, 8189, …).
   Same template and ports as above.
2. Connect → JupyterLab → Terminal → paste the **same command**. It takes a minute or two now.
3. Open the `GPU … ready` links.
4. **When you're done: Stop the pod** (Pods → Stop). Otherwise it keeps billing by the hour.

## Let Claude Code drive it

In the pod's terminal:

```bash
cd /workspace/do-my-task && ~/.local/bin/claude
```

It shows a login link; open it on your laptop and paste the code back. Then, for example:

> Read ai-studio/CLAUDE.md. We're on RunPod with big GPUs: use the full-quality settings. Run the test plan
> A–E at 720p, and use comfy_batch.py --auto to spread the jobs over every GPU.

## Getting your results

Everything lands in `/workspace/outputs` (one folder per GPU). In JupyterLab's file browser, right-click a
file → **Download**. For everything at once, in the terminal: `cd /workspace && zip -r outputs.zip outputs`,
then download `outputs.zip`.

## Good to know

- Anyone with a `proxy.runpod.net` link can use your ComfyUI while the pod runs. Don't share the links.
- Files in `/workspace` survive; everything else on the pod is wiped when it stops.
- If setup says PyTorch can't use the GPU, that machine's driver is too old: stop the pod and deploy another.
