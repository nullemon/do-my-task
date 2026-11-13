#!/bin/bash
# Mux picture + sound + soft subtitles -> out/exoplanet-moons-short.mp4 (9:16 only).
# (no -shortest: it truncates when subtitles are muxed; the mix is exactly DUR long)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
SCR=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B2-exoplanet-moons
OUTF="$HERE/out/exoplanet-moons-short.mp4"
nice -n 10 ffmpeg -v error -y -i "$SCR/video_vert.mp4" -i "$SCR/audio/mix.wav" -i "$HERE/out/exoplanet-moons.srt" \
  -map 0:v -map 1:a -map 2:s -c:v copy -c:a aac -b:a 256k -c:s mov_text -metadata:s:s:0 language=eng \
  -movflags +faststart "$OUTF"
ls -l "$OUTF"; ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate,duration -of compact "$OUTF"
