#!/usr/bin/env bash
# Render the 4K room plates (wide + medium; off/lit/uv). Skips existing .npy.
cd /home/user/do-my-task/docs-series/04-big-bang-on-your-tv
PL=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/04-big-bang-on-your-tv/plates
for C in wide medium; do for P in uv off lit; do
  [[ -s $PL/room_${C}_${P}.npy && $(stat -c %s $PL/room_${C}_${P}.npy) -gt 20000000 ]] && continue
  S=40; [[ $C == medium ]] && S=24; [[ $P == uv ]] && S=4
  echo "$(date +%T) $C $P"
  nice -n 5 /home/user/bpyenv/bin/python -c "import sys;p='room.py';sys.argv=['blender','--','$C','$P','$S','150'];exec(compile(open(p).read(),p,'exec'))" 2>&1 | grep -E "saved|Error"
done; done
echo "$(date +%T) PLATES DONE"
