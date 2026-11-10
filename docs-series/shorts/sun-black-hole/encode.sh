#!/bin/bash
# Mux picture + sound + soft subtitles -> out/. Usage: bash encode.sh vert|wide|locked_vert|locked_wide
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
SCR=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S1-sun-black-hole
TAG=${1:-vert}
case "$TAG" in
  vert) OUTF="$HERE/out/sun-black-hole-short.mp4" ;;
  wide) OUTF="$HERE/out/sun-black-hole-16x9.mp4" ;;
  locked_vert) OUTF="$HERE/out/sun-black-hole-short-locked.mp4" ;;
  locked_wide) OUTF="$HERE/out/sun-black-hole-16x9-locked.mp4" ;;
  vfx_vert) OUTF="$HERE/out/sun-black-hole-short.mp4" ;;
  vfx_wide) OUTF="$HERE/out/sun-black-hole-16x9.mp4" ;;
esac
MIX="$SCR/audio/mix.wav"; case "$TAG" in locked_*) MIX="$SCR/audio/mix_locked.wav" ;; vfx_*) MIX="$SCR/audio/mix_vfx.wav" ;; esac
nice -n 10 ffmpeg -v error -y -i "$SCR/video_$TAG.mp4" -i "$MIX" -i "$HERE/out/sun-black-hole.srt" \
  -map 0:v -map 1:a -map 2:s -c:v copy -c:a aac -b:a 256k -c:s mov_text -metadata:s:s:0 language=eng \
  -movflags +faststart "$OUTF"
ls -l "$OUTF"; ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate -of compact "$OUTF"
