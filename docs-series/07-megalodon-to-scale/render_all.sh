#!/usr/bin/env bash
# Render all compositor segments (resume-safe), two workers, then concat to the joined silent master.
# Run detached: setsid nohup bash render_all.sh > $SCR/logs/render_all.log 2>&1 < /dev/null &
set -uo pipefail
cd /home/user/do-my-task/docs-series/07-megalodon-to-scale
SCR=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/07-megalodon-to-scale
SEGS=(0 20 40 60 80 100 120 140 160 180 200 220 240 260 280 300 316)
worker() {  # $1 = parity
  for ((i=$1; i<${#SEGS[@]}-1; i+=2)); do
    nice -n 5 python3 comp.py ${SEGS[$i]} ${SEGS[$((i+1))]} || echo "FAILED seg ${SEGS[$i]}"
  done
}
worker 0 & P0=$!
worker 1 & P1=$!
wait $P0 $P1
mkdir -p $SCR/final; LIST=$SCR/final/concat.txt; : > $LIST
for ((i=0; i<${#SEGS[@]}-1; i++)); do f=$(printf "%s/seg/seg_%05d.mp4" $SCR $((${SEGS[$i]}*24))); [[ -s $f ]] || { echo "missing $f"; exit 1; }; echo "file '$f'" >> $LIST; done
ffmpeg -v error -y -f concat -safe 0 -i $LIST -c copy -an $SCR/final/joined.mp4
ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 $SCR/final/joined.mp4
echo "render_all done $(date)"
