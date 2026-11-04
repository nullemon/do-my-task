#!/usr/bin/env bash
# Second worker: claims a shot by writing a 1-byte placeholder at the final segment path (the other queue skips
# non-empty segments); Writer.close() replaces it with the real file. Skips shots already started elsewhere.
cd /home/user/do-my-task/docs-series/06-lituya-bay
SEG=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/06-lituya-bay/seg
for s in "$@"; do
  [[ -s $SEG/$s.mp4 || -e $SEG/$s.mp4.part.mp4 ]] && { echo "skip $s"; continue; }
  printf x > $SEG/$s.mp4
  echo "$(date +%T) start $s"; nice -n 5 python3 shots.py --force $s; echo "$(date +%T) end $s"
done
echo "$(date +%T) QUEUE DONE"
