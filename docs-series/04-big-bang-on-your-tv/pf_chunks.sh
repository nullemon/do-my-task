#!/usr/bin/env bash
# Render PF as three parallel chunks (resume-safe per chunk), then join them losslessly into PF.mp4.
cd /home/user/do-my-task/docs-series/04-big-bang-on-your-tv
SEG=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/04-big-bang-on-your-tv/seg
for c in PFa PFb PFc; do ./run_queue.sh $c & done; wait
for c in PFa PFb PFc; do [[ -s $SEG/$c.mp4 ]] || { echo "missing $c"; exit 1; }; echo "file '$SEG/$c.mp4'"; done > $SEG/pf_list.txt
ffmpeg -v error -y -f concat -safe 0 -i $SEG/pf_list.txt -c copy $SEG/PF.tmp.mp4 && mv $SEG/PF.tmp.mp4 $SEG/PF.mp4
echo "PF joined $(ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 $SEG/PF.mp4) frames"
