#!/usr/bin/env bash
# Render a list of shots sequentially into segments (skip existing). Usage: run_queue.sh SHOT...
cd /home/user/do-my-task/docs-series/06-lituya-bay
SEG=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/06-lituya-bay/seg
for s in "$@"; do
  [[ -s $SEG/$s.mp4 ]] && { echo "skip $s"; continue; }
  echo "$(date +%T) start $s"; nice -n 5 python3 shots.py $s; echo "$(date +%T) end $s"
done
echo "$(date +%T) QUEUE DONE"
