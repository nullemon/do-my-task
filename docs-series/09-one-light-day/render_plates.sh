#!/usr/bin/env bash
# Render all Voyager plates sequentially (resume-safe). setsid nohup bash render_plates.sh > $SCR/logs/plates.log 2>&1 &
cd /home/user/do-my-task/docs-series/09-one-light-day
for s in ${@:-plate_heroA plate_cover plate_record plate_sig plate_rtg plate_end plate_heroB plate_fly plate_thumb}; do
  echo "[$(date +%T)] $s"
  THREADS=${THREADS:-3} nice -n 5 /home/user/bpyenv/bin/python -c "import sys;p='blender/voyager.py';sys.argv=['blender','--','$s'];exec(compile(open(p).read(),p,'exec'))" 2>&1 | grep -i "error\|Trace\|rendered"
done
echo "[$(date +%T)] plates done"
