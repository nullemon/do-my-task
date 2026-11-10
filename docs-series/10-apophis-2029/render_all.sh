#!/usr/bin/env bash
# Render compositor segments (resume-safe). Usage: bash render_all.sh noast|ast|join
#   noast : segments that do not need the Blender asteroid sprites     ast : the rest     join : concat to the silent master
# Run detached: setsid nohup bash render_all.sh noast > $SCR/logs/noast.log 2>&1 < /dev/null &
set -uo pipefail
cd /home/user/do-my-task/docs-series/10-apophis-2029
SCR=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/10-apophis-2029
B=(0 11.5 23 40 58 65 80 94 105.5 117.5 135 150 165 180 195 210 223 239 255.5 270 285 297.5 304.5 318)
NOAST="23 40 65 80 117.5 135 150 165 180 195 255.5 270 285 304.5"
is_noast() { for s in $NOAST; do [[ $s == "$1" ]] && return 0; done; return 1; }
case ${1:-} in
 noast|ast)
  for ((i=0; i<${#B[@]}-1; i++)); do
    a=${B[$i]}; b=${B[$((i+1))]}
    if is_noast $a; then k=noast; else k=ast; fi
    [[ $k == "$1" ]] || continue
    nice -n 5 python3 comp.py $a $b 2>&1 | grep -v -i warning || echo "FAILED seg $a"
  done;;
 join)
  mkdir -p $SCR/final; L=$SCR/final/concat.txt; : > $L
  for ((i=0; i<${#B[@]}-1; i++)); do
    f=$(python3 -c "print('%s/seg/seg_%05d.mp4' % ('$SCR', round(${B[$i]}*24)))"); [[ -s $f ]] || { echo "missing $f"; exit 1; }; echo "file '$f'" >> $L
  done
  ffmpeg -v error -y -f concat -safe 0 -i $L -c copy -an $SCR/final/joined.mp4
  ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 $SCR/final/joined.mp4;;
esac
echo "render_all $1 done $(date)"
