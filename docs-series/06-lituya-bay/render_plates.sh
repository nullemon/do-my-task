#!/usr/bin/env bash
# Render every camera plate (forest / strip / data) at 2880x1620. Skips existing .npy. Usage: render_plates.sh [CAM...]
cd /home/user/do-my-task/docs-series/06-lituya-bay
PL=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/06-lituya-bay/plates
CAMS=${@:-"wide wide2 gilbert spur entrance after"}
for C in $CAMS; do for P in data forest strip; do
  [[ $P == strip && ( $C == wide || $C == entrance ) ]] && continue
  [[ -s $PL/${C}_${P}.npy ]] && continue
  S=6; [[ $C == top ]] && S=4
  echo "$(date +%T) $C $P"
  BTHREADS=${BTHREADS:-2} nice -n 5 /home/user/bpyenv/bin/python -c "import sys;p='scene.py';sys.argv=['blender','--','$C','$P','$S','2880','1620'];exec(compile(open(p).read(),p,'exec'))" 2>&1 | grep -E "saved|Error|Traceback"
done; done
echo "$(date +%T) PLATES DONE"
