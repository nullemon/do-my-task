#!/usr/bin/env bash
# Render all compositor segments (resume-safe), two workers, then concat to the joined silent master.
# Run detached: setsid nohup bash render_all.sh > $SCR/logs/render_all.log 2>&1 < /dev/null &      (VERT=1 for 9:16)
set -uo pipefail
cd /home/user/do-my-task/docs-series/13-sunset-on-every-world
SCR=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/13-sunset-on-every-world
DUR=$(python3 -c "import timeline as T; print(int(T.DUR))")
SEGS=($(seq 0 9 $((DUR-1))) $DUR)
SD=seg; J=joined.mp4; [[ "${VERT:-0}" == 1 ]] && { SD=seg_v; J=joined_v.mp4; }
python3 comp.py stills > $SCR/logs/${SD}_stills.log 2>&1
worker() {
  for ((i=$1; i<${#SEGS[@]}-1; i+=2)); do
    python3 comp.py ${SEGS[$i]} ${SEGS[$((i+1))]} > $SCR/logs/${SD}_${SEGS[$i]}.log 2>&1 || echo "FAILED seg ${SEGS[$i]}"
  done
}
worker 0 & P0=$!
worker 1 & P1=$!
wait $P0 $P1
mkdir -p $SCR/final; LIST=$SCR/final/concat_$SD.txt; : > $LIST
for ((i=0; i<${#SEGS[@]}-1; i++)); do f=$(printf "%s/%s/seg_%05d.mp4" $SCR $SD $((${SEGS[$i]}*24))); [[ -s $f ]] || { echo "missing $f"; exit 1; }; echo "file '$f'" >> $LIST; done
ffmpeg -v error -y -f concat -safe 0 -i $LIST -c copy -an $SCR/final/$J
ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 $SCR/final/$J
echo "render_all done $(date)"
