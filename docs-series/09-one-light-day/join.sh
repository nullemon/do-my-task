#!/usr/bin/env bash
# join.sh [v]  -> concat the 24 twelve-second segments into final/joined[_v].mp4 (stream copy) and verify the frame count
S=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/09-one-light-day
D=seg; O=joined.mp4; [ "${1:-}" = v ] && { D=seg_v; O=joined_v.mp4; }
mkdir -p $S/final; L=$S/final/concat_$D.txt; : > $L
for ((s=0; s<288; s+=12)); do f=$(printf "%s/%s/seg_%05d.mp4" $S $D $((s*24))); [[ -s $f ]] || { echo "missing $f"; exit 1; }; echo "file '$f'" >> $L; done
ffmpeg -v error -y -f concat -safe 0 -i $L -c copy -an $S/final/$O
ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames,width,height -of csv=p=0 $S/final/$O
