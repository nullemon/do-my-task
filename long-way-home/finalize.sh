#!/usr/bin/env bash
# Mux the rendered frames with the soundtrack into Facebook-ready MP4s.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p deliver
# full mix (score + sound design), about -14 LUFS
ffmpeg -y -loglevel error -i out/video_silent.mp4 -i out/mix.wav \
  -map 0:v -map 1:a -c:v libx264 -preset slow -crf 19 -pix_fmt yuv420p -profile:v high -movflags +faststart \
  -af "volume=0.4dB" -c:a aac -b:a 256k -ar 48000 -shortest deliver/the-long-way-home-ep1.mp4
# sound effects only, for adding a track from Facebook's sound library when posting
ffmpeg -y -loglevel error -i deliver/the-long-way-home-ep1.mp4 -i out/sfx_only.wav \
  -map 0:v -map 1:a -c:v copy -af "volume=4dB" -c:a aac -b:a 256k -ar 48000 -shortest \
  -movflags +faststart deliver/the-long-way-home-ep1-sfx-only.mp4
# reel cover
ffmpeg -y -loglevel error -ss 58.6 -i out/video_silent.mp4 -frames:v 1 -q:v 2 deliver/cover.jpg
ls -lh deliver
