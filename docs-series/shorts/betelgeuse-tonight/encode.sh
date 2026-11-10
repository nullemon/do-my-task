#!/bin/bash
# Mux picture + sound + soft subtitles -> out/ (copied from ../other-suns). Usage: bash encode.sh vert|wide
# (no -shortest: it truncates when subtitles are muxed; the mix is exactly DUR long)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
SCR=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S9-betelgeuse
TAG=${1:-vert}
case "$TAG" in
  vert) OUTF="$HERE/out/betelgeuse-tonight-short.mp4" ;;
  wide) OUTF="$HERE/out/betelgeuse-tonight-16x9.mp4" ;;
esac
nice -n 10 ffmpeg -v error -y -i "$SCR/video_$TAG.mp4" -i "$SCR/audio/mix.wav" -i "$HERE/out/betelgeuse-tonight.srt" \
  -map 0:v -map 1:a -map 2:s -c:v copy -c:a aac -b:a 256k -c:s mov_text -metadata:s:s:0 language=eng \
  -movflags +faststart "$OUTF"
ls -l "$OUTF"; ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate,duration -of compact "$OUTF"
