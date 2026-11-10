#!/usr/bin/env bash
# Render compositor segments (resume-safe). Usage: bash render_all.sh h|v 0|1 (worker parity)   |   bash render_all.sh h|v join
# Run detached: setsid nohup bash render_all.sh h 0 > $SCR/logs/h0.log 2>&1 < /dev/null &
set -uo pipefail
cd /home/user/do-my-task/docs-series/11-neutron-star-teaspoon
SCR=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/11-neutron-star-teaspoon
B=(0 12 22 32 42 52 62 75 88 100 110 122 136 148 158 169 182 192 199 210 221 229 237 249 260 270 280 288 299 313)
if [[ $1 == v ]]; then export NS_VERT=1; SEG=seg_v; J=joined_v.mp4; else SEG=seg; J=joined.mp4; fi
if [[ $2 == join ]]; then
  mkdir -p $SCR/final; L=$SCR/final/concat_$1.txt; : > $L
  for ((i=0; i<${#B[@]}-1; i++)); do f=$(printf "%s/%s/seg_%05d.mp4" $SCR $SEG $((${B[$i]}*24))); [[ -s $f ]] || { echo "missing $f"; exit 1; }; echo "file '$f'" >> $L; done
  ffmpeg -v error -y -f concat -safe 0 -i $L -c copy -an $SCR/final/$J
  ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 $SCR/final/$J
else
  for ((i=$2; i<${#B[@]}-1; i+=2)); do nice -n 5 python3 comp.py ${B[$i]} ${B[$((i+1))]} 2>&1 | grep -v -i warning || echo "FAILED ${B[$i]}"; done
fi
echo "render_all $1 $2 done $(date)"
