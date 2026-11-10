#!/usr/bin/env bash
# spoon (bead on / off) and ring sequences, resume-safe. Every 2nd frame of the 80-frame move is path-traced (the compositor
# blends between them); the bead-off pass and the ring are only rendered over the parts of the move the film uses.
cd /home/user/do-my-task/docs-series/11-neutron-star-teaspoon/blender
P=/home/user/bpyenv/bin/python
run() { nice -n 5 $P spoon.py "$@" 2>&1 | grep "rendered\|Error\|Traceback"; }
run on 0 80 2
run off 0 9 2; run off 22 35 2; run off 38 51 2
run ring 8 77 2
echo "sprites done $(date)"
