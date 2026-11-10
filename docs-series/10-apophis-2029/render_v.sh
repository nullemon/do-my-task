#!/usr/bin/env bash
# 9:16 version: render comp_v.py segments (resume-safe). Usage: bash render_v.sh 0|1 (worker parity) | join
set -uo pipefail
cd /home/user/do-my-task/docs-series/10-apophis-2029
SCR=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/10-apophis-2029
B=(0 20 40 60 80 100 120 140 160 180 200 220 240 260 280 300 318)
if [[ $1 == join ]]; then
  mkdir -p $SCR/final; L=$SCR/final/concat_v.txt; : > $L
  for ((i=0; i<${#B[@]}-1; i++)); do f=$(printf "%s/seg_v/seg_%05d.mp4" $SCR $((${B[$i]}*24))); [[ -s $f ]] || { echo "missing $f"; exit 1; }; echo "file '$f'" >> $L; done
  ffmpeg -v error -y -f concat -safe 0 -i $L -c copy -an $SCR/final/joined_v.mp4
  ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 $SCR/final/joined_v.mp4
else
  for ((i=$1; i<${#B[@]}-1; i+=2)); do APO_VERT=1 nice -n 5 python3 comp_v.py ${B[$i]} ${B[$((i+1))]} 2>&1 | grep -v -i warning || echo "FAILED ${B[$i]}"; done
fi
echo "render_v $1 done $(date)"
