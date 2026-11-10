#!/bin/bash
# Mux picture + sound + soft subtitles -> out/. Usage: bash encode.sh vert|wide
# (no -shortest: with a subtitle stream it cuts the file at the last cue)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
SCR=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S5-star-dates
TAG=${1:-vert}
if [ "$TAG" = vert ]; then OUTF="$HERE/out/star-dates-short.mp4"; else OUTF="$HERE/out/star-dates-16x9.mp4"; fi
nice -n 10 ffmpeg -v error -y -i "$SCR/video_$TAG.mp4" -i "$SCR/audio/mix.wav" -i "$HERE/out/star-dates.srt" \
  -map 0:v -map 1:a -map 2:s -c:v copy -c:a aac -b:a 256k -c:s mov_text -metadata:s:s:0 language=eng \
  -movflags +faststart "$OUTF"
ls -l "$OUTF"; ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate -of compact "$OUTF"
