#!/usr/bin/env bash
# Render compositor segments (resume-safe). Usage: bash render.sh h|v A|B|P|join   (A/B = two halves of the plate-free segments, P = plate segments)
set -uo pipefail
cd /home/user/do-my-task/docs-series/12-the-moon-is-leaving
SCR=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/12-the-moon-is-leaving
B=(0 12 24 39 53 60 72 84 96 112 121 130.5 145 152 161 171.5 180 189 199 210 222 231 240.5 250 260.5 268 277 283 291.5 298)
PL="39 130.5"
[[ $1 == v ]] && { export MOON_VERT=1; SFX=_v; } || SFX=""
isp() { for s in $PL; do [[ $s == "$1" ]] && return 0; done; return 1; }
if [[ $2 == join ]]; then
  mkdir -p $SCR/final; L=$SCR/final/concat$SFX.txt; : > $L
  for ((i=0; i<${#B[@]}-1; i++)); do f=$(python3 -c "print('%s/seg%s/seg_%05d.mp4' % ('$SCR', '$SFX', round(${B[$i]}*24)))"); [[ -s $f ]] || { echo "missing $f"; exit 1; }; echo "file '$f'" >> $L; done
  ffmpeg -v error -y -f concat -safe 0 -i $L -c copy -an $SCR/final/joined$SFX.mp4
  ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 $SCR/final/joined$SFX.mp4; exit 0
fi
n=0
for ((i=0; i<${#B[@]}-1; i++)); do
  a=${B[$i]}; b=${B[$((i+1))]}
  if isp $a; then k=P; else n=$((n+1)); [[ $((n%2)) == 1 ]] && k=A || k=B; fi
  [[ $k == "$2" ]] || continue
  nice -n 5 python3 comp.py $a $b 2>&1 | grep -v -i warning || echo "FAILED seg $a"
done
echo "render $1 $2 done $(date)"
