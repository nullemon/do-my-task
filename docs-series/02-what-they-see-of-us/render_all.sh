#!/usr/bin/env bash
# Render the film in resumable 240-frame chunks with 3 parallel workers (each chunk pipes raw frames to x264),
# then join the chunks (stream copy) into the silent master.
set -uo pipefail
cd "$(dirname "$0")"
SEG=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/02-what-they-see-of-us/seg
mkdir -p $SEG
NF=$(python3 -c "import json;print(json.load(open('timeline.json'))['nframes'])")
CH=240; NCH=$(( (NF + CH - 1) / CH ))
worker() {   # worker k takes chunks k, k+3, k+6, ...
  for ((c=$1; c<NCH; c+=3)); do
    out=$(printf "%s/c%03d.mp4" $SEG $c)
    [[ -s $out ]] && continue
    a=$((c*CH)); b=$(( (c+1)*CH )); (( b > NF )) && b=$NF
    for try in 1 2 3; do
      nice -n 5 python3 comp.py --start $a --end $b --out $out >> $SEG/w$1.log 2>&1 && break
      echo "chunk $c failed (try $try)" >> $SEG/w$1.log
    done
  done
}
worker 0 & worker 1 & worker 2 & wait
: > $SEG/list.txt
for ((c=0; c<NCH; c++)); do printf "file '%s/c%03d.mp4'\n" $SEG $c >> $SEG/list.txt; done
ffmpeg -v error -y -f concat -safe 0 -i $SEG/list.txt -c copy $SEG/master_silent.mp4.part.mp4 && mv $SEG/master_silent.mp4.part.mp4 $SEG/master_silent.mp4
echo "joined: $(ffprobe -v error -count_packets -select_streams v:0 -show_entries stream=nb_read_packets -of csv=p=0 $SEG/master_silent.mp4) frames"
