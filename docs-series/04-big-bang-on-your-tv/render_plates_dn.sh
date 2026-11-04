#!/usr/bin/env bash
# Denoised (OIDN) re-render of the room light passes, one camera per invocation. Resume: skips passes marked done.
cd /home/user/do-my-task/docs-series/04-big-bang-on-your-tv
D=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/04-big-bang-on-your-tv/dn
C=$1
for P in off lit; do
  [[ -f $D/${C}_${P}.done ]] && continue
  echo "$(date +%T) $C $P"
  nice -n 5 /home/user/bpyenv/bin/python -c "import sys;p='room.py';sys.argv=['blender','--','$C','$P','16','150'];exec(compile(open(p).read(),p,'exec'))" 2>&1 | grep -E "saved|Error"
  [[ ${PIPESTATUS[0]} == 0 ]] && touch $D/${C}_${P}.done
done
echo "$(date +%T) $C DN DONE"
