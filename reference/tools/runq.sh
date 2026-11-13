#!/bin/bash
# Sequential job queue: each line of queue.txt = "<dir>|<command>"; done lines move to queue_done.txt
cd "$(dirname "$0")"
while true; do
  # wait while any other build/finish is running
  while pgrep -f "python3 (build|finish|build_wide|finish_wide).py" > /dev/null; do sleep 20; done
  line=$(head -n1 queue.txt 2>/dev/null)
  [ -z "$line" ] && { echo "QUEUE EMPTY $(date +%T)"; exit 0; }
  d=${line%%|*}; cmd=${line#*|}
  echo "START $(date +%T) $d: $cmd"
  (cd "$d" && RESUME=1 bash -c "$cmd") >> "$d/q.log" 2>&1
  rc=$?
  echo "END $(date +%T) rc=$rc $d"
  if [ $rc -eq 0 ]; then sed -i '1d' queue.txt; echo "$line" >> queue_done.txt; else echo "FAILED, stopping"; exit 1; fi
done
