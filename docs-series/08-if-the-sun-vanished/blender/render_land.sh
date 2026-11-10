#!/usr/bin/env bash
# all landscape plates, sequential, resume-safe.  setsid nohup bash blender/render_land.sh > $SCR/logs/land.log 2>&1 &
cd /home/user/do-my-task/docs-series/08-if-the-sun-vanished
SCR=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/08-if-the-sun-vanished
for job in "rock depth 8" "rock mirror 8" "snow depth 8" "rock sun 64" "rock amb 64" "snow amb 64" "snow sun 64"; do
  set -- $job
  [[ -s $SCR/plates/land_$1_$2.png ]] && continue
  echo "[$(date +%T)] $job"
  nice -n 5 /home/user/bpyenv/bin/python -c "import sys;p='blender/landscape.py';sys.argv=['blender','--','$1','$2','$3'];exec(compile(open(p).read(),p,'exec'))" 2>&1 | grep -E "Error|done"
done
echo "[$(date +%T)] all done"
