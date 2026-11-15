#!/bin/bash
# Mux picture + clean mix + soft subtitles -> out/<name>-short.mp4 (9:16). AAC 192k, no extra audio filters.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"; NAME="$(basename "$HERE")"
SCR=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B4-$NAME
OUTF="$HERE/out/$NAME-short.mp4"
nice -n 10 ffmpeg -v error -y -i "$SCR/video_vert.mp4" -i "$SCR/audio/mix.wav" -i "$HERE/out/$NAME.srt" \
  -map 0:v -map 1:a -map 2:s -c:v copy -c:a aac -b:a 192k -ar 48000 -c:s mov_text -metadata:s:s:0 language=eng \
  -movflags +faststart "$OUTF"
ls -l "$OUTF"; ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate,bit_rate -of compact "$OUTF"
ffmpeg -hide_banner -nostats -i "$OUTF" -af ebur128=peak=true:framelog=quiet -f null - 2>&1 | grep -E "I:|Peak:"
