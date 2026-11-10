#!/usr/bin/env bash
cd /home/user/do-my-task/docs-series/08-if-the-sun-vanished
SCR=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/08-if-the-sun-vanished
for m in ice vent; do
  [[ -s $SCR/plates/${m}_depth.png ]] && continue
  echo "[$(date +%T)] $m"
  nice -n 5 /home/user/bpyenv/bin/python -c "import sys;p='blender/ocean.py';sys.argv=['blender','--','$m','96'];exec(compile(open(p).read(),p,'exec'))" 2>&1 | grep -E "Error|done"
done
echo "[$(date +%T)] all done"
