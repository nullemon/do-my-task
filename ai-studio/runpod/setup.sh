#!/usr/bin/env bash
# One-command ComfyUI studio on a RunPod GPU pod. Everything lives on the network volume (/workspace),
# so run this same command every time you start a pod: the first run downloads the models, later runs
# take a minute or two and just start ComfyUI.
#
#   curl -fsSL https://raw.githubusercontent.com/nullemon/do-my-task/claude/sharp-wright-ft6mhj/ai-studio/runpod/setup.sh | bash
#
# Fewer packs:  curl ... | PACKS="image video upscale" bash
set -euo pipefail
WORK="${WORK:-/workspace}"
PACKS="${PACKS:-image video motion motion_full swap upscale refsheet ltx}"
REPO="${REPO:-https://github.com/nullemon/do-my-task.git}"
BRANCH="${BRANCH:-claude/sharp-wright-ft6mhj}"
step() { printf '\n\033[1;36m== %s\033[0m\n' "$*"; }
ok() { printf '  \033[32mOK\033[0m  %s\n' "$*"; }
warn() { printf '  \033[33m!!\033[0m  %s\n' "$*"; }

main() {
  step "GPUs and storage"
  command -v nvidia-smi >/dev/null || { warn "No NVIDIA GPU here. Deploy a GPU pod and run this again."; exit 1; }
  nvidia-smi --query-gpu=index,name,memory.total,driver_version --format=csv,noheader | sed 's/^/  /'
  DRIVER_MAJOR=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1 | cut -d. -f1)
  mkdir -p "$WORK"
  if [ "$(df -P "$WORK" | awk 'NR==2{print $1}')" = "$(df -P / | awk 'NR==2{print $1}')" ]; then
    warn "$WORK is not a separate volume, so everything is deleted when this pod stops. Attach a network volume."
  fi
  ok "$(df -h "$WORK" | awk 'NR==2{print $4}') free in $WORK"

  step "System tools"
  missing=""
  for c in git aria2c ffmpeg curl; do command -v "$c" >/dev/null || missing="$missing $c"; done
  if [ -n "$missing" ] || ! python3 -c 'import ensurepip' 2>/dev/null; then
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq git aria2 ffmpeg curl python3-venv >/dev/null
  fi
  ok "git, aria2, ffmpeg"

  step "Project files"
  if [ -d "$WORK/do-my-task/.git" ]; then
    git -C "$WORK/do-my-task" pull -q --ff-only || warn "could not update do-my-task (keeping the current copy)"
  else
    git clone -q -b "$BRANCH" "$REPO" "$WORK/do-my-task"
  fi
  ok "$WORK/do-my-task"

  step "ComfyUI and PyTorch"
  if [ -f "$WORK/ComfyUI/main.py" ]; then
    git -C "$WORK/ComfyUI" pull -q --ff-only || warn "could not update ComfyUI (keeping the current copy)"
  else
    git clone -q https://github.com/comfyanonymous/ComfyUI "$WORK/ComfyUI"
  fi
  PY="$WORK/venv/bin/python"
  [ -x "$PY" ] || python3 -m venv "$WORK/venv"
  "$PY" -m pip install -q --upgrade pip wheel
  torch_ok() { "$PY" -c 'import torch,sys; sys.exit(0 if torch.cuda.is_available() and torch.ones(1).cuda().sum().item() == 1 else 1)' >/dev/null 2>&1; }
  if ! torch_ok; then
    if [ "${DRIVER_MAJOR:-0}" -ge 580 ]; then builds="cu130 cu128"; else builds="cu128"; fi
    for cu in $builds; do
      "$PY" -m pip install -q --force-reinstall torch torchvision torchaudio --index-url "https://download.pytorch.org/whl/$cu" && torch_ok && break
    done
  fi
  torch_ok || { warn "PyTorch can't use this machine's GPU (driver $DRIVER_MAJOR). Stop the pod, pick another, run again."; exit 1; }
  "$PY" -m pip install -q -r "$WORK/ComfyUI/requirements.txt"
  ok "$("$PY" -c 'import torch; print("PyTorch", torch.__version__, "CUDA", torch.version.cuda)')"

  step "Models: $PACKS"
  # shellcheck disable=SC2086
  "$PY" "$WORK/do-my-task/ai-studio/runpod/fetch_models.py" --comfy "$WORK/ComfyUI" --packs $PACKS ||
    warn "some downloads did not finish; run this same command again to resume"

  step "Claude Code"
  if command -v claude >/dev/null || [ -x "$HOME/.local/bin/claude" ]; then
    ok "already installed"
  elif curl -fsSL https://claude.ai/install.sh | bash >/dev/null 2>&1; then
    ok "installed: run  ~/.local/bin/claude  inside $WORK/do-my-task"
  else
    warn "Claude Code did not install (optional; ComfyUI still works)"
  fi

  step "Starting ComfyUI on every GPU"
  bash "$WORK/do-my-task/ai-studio/runpod/start.sh"
}

main "$@" </dev/null
