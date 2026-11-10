#!/usr/bin/env bash
# spoon (bead on / off) and ring sequences, resume-safe: every 2nd frame first (the compositor blends), then the rest.
cd /home/user/do-my-task/docs-series/11-neutron-star-teaspoon/blender
for st in "0 80 2" "1 80 2"; do
  for m in on off ring; do nice -n 5 /home/user/bpyenv/bin/python spoon.py $m $st 2>&1 | grep "rendered\|Error\|Traceback"; done
  echo "pass $st done $(date)"
done
