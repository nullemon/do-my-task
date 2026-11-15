#!/bin/bash
# Mux picture + sound + soft subtitles -> out/rogue-planet-short.mp4 (9:16 only).
# No -shortest (it truncates when subtitles are muxed; the mix is exactly DUR long). Low-pass at 17 kHz before AAC.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
SCR=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B3-rogue-planet
OUTF="$HERE/out/rogue-planet-short.mp4"
nice -n 10 ffmpeg -v error -y -i "$SCR/video_vert.mp4" -i "$SCR/audio/mix.wav" -i "$HERE/out/rogue-planet.srt" \
  -map 0:v -map 1:a -map 2:s -c:v copy -af lowpass=f=17000 -c:a aac -b:a 256k -c:s mov_text -metadata:s:s:0 language=eng \
  -movflags +faststart "$OUTF"
ls -l "$OUTF"; ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate,duration -of compact "$OUTF"
ffmpeg -hide_banner -nostats -i "$OUTF" -af ebur128=peak=true:framelog=quiet -f null - 2>&1 | grep -E "I:|Peak:" 
