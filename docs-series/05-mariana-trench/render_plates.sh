#!/usr/bin/env bash
# Floor plates (2880x1620, 32 spp + OIDN). Resume-safe.
cd /home/user/do-my-task/docs-series/05-mariana-trench
L=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/05-mariana-trench
for v in A B; do
  [[ -f $L/plates/floor_$v.done ]] && continue
  echo "$(date +%T) floor $v"
  nice -n 5 /home/user/bpyenv/bin/python -c "import sys;p='deep3d.py';sys.argv=['blender','--','floor','$v','32','150'];exec(compile(open(p).read(),p,'exec'))" 2>&1 | grep -E "Saved|Error:|Trace"
  touch $L/plates/floor_$v.done
done
echo "$(date +%T) PLATES DONE"
