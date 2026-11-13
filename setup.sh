#!/bin/bash
# One-time setup (Mac / Linux)
cd "$(dirname "$0")"
unset SSLKEYLOGFILE
python3 -m pip install -U kokoro-onnx soundfile numpy pillow opencv-python "yt-dlp[default,curl-cffi]" deno requests imageio-ffmpeg ddgs faster-whisper
command -v ffmpeg >/dev/null || { command -v brew >/dev/null && brew install ffmpeg || sudo apt-get install -y ffmpeg; }
mkdir -p models
B=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
[ -f models/kokoro-v1.0.onnx ] || curl -L -o models/kokoro-v1.0.onnx $B/kokoro-v1.0.onnx
[ -f models/voices-v1.0.bin ] || curl -L -o models/voices-v1.0.bin $B/voices-v1.0.bin
(cd lib/maps && npm i d3-geo topojson-client world-atlas) || true
echo "Done. Open this folder in Claude Code and say: Read PROMPT.md and set everything up."
