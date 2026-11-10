#!/usr/bin/env bash
# spoon (bead on / off) and ring sequences, resume-safe. Run detached.
cd /home/user/do-my-task/docs-series/11-neutron-star-teaspoon/blender
for m in on off ring; do nice -n 5 /home/user/bpyenv/bin/python spoon.py $m 0 80 2>&1 | grep "rendered\|Error\|Traceback"; done
echo "sprites done $(date)"
