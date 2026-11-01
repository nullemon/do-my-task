#!/usr/bin/env bash
# Install Blender on the network volume (/workspace/blender, survives pod restarts) and check the GPU.
#
#   bash /workspace/do-my-task/ai-studio/runpod/blender.sh              # newest Blender release
#   BLENDER_VERSION=4.5.3 bash /workspace/do-my-task/ai-studio/runpod/blender.sh
#
# Then render headless:  blender -b -P script.py -- args
set -euo pipefail
WORK="${WORK:-/workspace}"
DEST="$WORK/blender"
BASE=https://download.blender.org/release
ok() { printf '  \033[32mOK\033[0m  %s\n' "$*"; }

# libraries Blender needs even without a screen
missing=""
for lib in libXi.so.6 libXxf86vm.so.1 libXfixes.so.3 libXrender.so.1 libGL.so.1 libEGL.so.1 libxkbcommon.so.0 libSM.so.6; do
  ldconfig -p | grep -q "$lib" || missing=1
done
if [ -n "$missing" ]; then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq libxi6 libxxf86vm1 libxfixes3 libxrender1 libgl1 libegl1 \
    libxkbcommon0 libsm6 libice6 libx11-6 libxext6 xz-utils >/dev/null
fi

if [ -z "${BLENDER_VERSION:-}" ]; then
  series=$(curl -fsSL "$BASE/" | grep -oE 'Blender[0-9]+\.[0-9]+/' | sort -uV | tail -1)
  BLENDER_VERSION=$(curl -fsSL "$BASE/$series" | grep -oE 'blender-[0-9]+\.[0-9]+\.[0-9]+-linux-x64\.tar\.xz' |
    sort -uV | tail -1 | sed -E 's/blender-(.*)-linux-x64.tar.xz/\1/')
fi
SERIES="Blender${BLENDER_VERSION%.*}"
DIR="$DEST/blender-$BLENDER_VERSION-linux-x64"
if [ ! -x "$DIR/blender" ]; then
  mkdir -p "$DEST"
  echo "  ..  downloading Blender $BLENDER_VERSION"
  curl -fL --progress-bar "$BASE/$SERIES/blender-$BLENDER_VERSION-linux-x64.tar.xz" -o "$DEST/blender.tar.xz"
  tar -xJf "$DEST/blender.tar.xz" -C "$DEST" && rm "$DEST/blender.tar.xz"
fi
ln -sfn "$DIR/blender" /usr/local/bin/blender
ok "Blender $BLENDER_VERSION  ($DIR)"

echo "  ..  GPU check (renders one 1080x1920 Cycles test frame)"
blender -b --factory-startup -P "$WORK/do-my-task/long-way-home/tools/gpu-check.py" 2>&1 |
  grep -E 'Compute backend|OPTIX|CUDA|Test frame|GPU OK|WARNING' || true
