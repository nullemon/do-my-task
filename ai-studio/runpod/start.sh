#!/usr/bin/env bash
# Start one ComfyUI per GPU on ports 8188, 8189, ... and print the links. Safe to re-run.
set -uo pipefail
WORK="${WORK:-/workspace}"
PY="$WORK/venv/bin/python"
mkdir -p "$WORK/logs" "$WORK/outputs"
N=$(nvidia-smi -L | wc -l)
up() { curl -sf "http://127.0.0.1:$1/system_stats" >/dev/null; }

for i in $(seq 0 $((N - 1))); do
  port=$((8188 + i))
  up "$port" && continue
  (cd "$WORK/ComfyUI" && nohup "$PY" main.py --listen 0.0.0.0 --port "$port" --cuda-device "$i" \
    --output-directory "$WORK/outputs/gpu$i" >"$WORK/logs/comfyui-gpu$i.log" 2>&1 </dev/null &)
done

for i in $(seq 0 $((N - 1))); do
  port=$((8188 + i))
  for _ in $(seq 1 150); do up "$port" && break; sleep 2; done
  if [ -n "${RUNPOD_POD_ID:-}" ]; then link="https://${RUNPOD_POD_ID}-${port}.proxy.runpod.net"; else link="http://127.0.0.1:$port"; fi
  if up "$port"; then
    printf '  \033[32mGPU %s ready\033[0m  %s\n' "$i" "$link"
  else
    printf '  \033[33mGPU %s did not start\033[0m  see %s\n' "$i" "$WORK/logs/comfyui-gpu$i.log"
  fi
done
echo
echo "  Open a link above in your browser. Each GPU is its own ComfyUI, so you can run one job on each at the same time."
echo "  Spread a whole queue over all GPUs:  $PY $WORK/do-my-task/ai-studio/comfy_batch.py --jobs jobs.json --auto"
echo "  Your results are in $WORK/outputs. STOP the pod in RunPod when you're done, or it keeps billing."
