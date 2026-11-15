#!/bin/bash
# BATCH4 mux: picture + clean mix (lib.mix_clean, already -14 LUFS / -1.5 dBTP) + soft subtitles -> out/ringed-moon-short.mp4
# AAC 192k. GAIN (dB, default 0) trims the loudness if AAC moves it. No -shortest (it truncates with subtitles).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
SCR=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B4-ringed-moon
OUTF="$HERE/out/ringed-moon-short.mp4"
nice -n 10 ffmpeg -v error -y -i "$SCR/video_vert.mp4" -i "$SCR/audio/mix.wav" -i "$HERE/out/ringed-moon.srt" \
  -map 0:v -map 1:a -map 2:s -c:v copy -af "volume=${GAIN:-0}dB" -c:a aac -b:a 192k -c:s mov_text -metadata:s:s:0 language=eng \
  -movflags +faststart "$OUTF"
ls -l "$OUTF"; ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate,duration,bit_rate -of compact "$OUTF"
ffmpeg -hide_banner -nostats -i "$OUTF" -af ebur128=peak=true:framelog=quiet -f null - 2>&1 | grep -E "I:|Peak:" | tail -2
