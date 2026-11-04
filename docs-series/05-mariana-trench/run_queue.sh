#!/usr/bin/env bash
# Render a list of 24 s segments sequentially (skip existing). Usage: run_queue.sh 0 2 4 ...
cd /home/user/do-my-task/docs-series/05-mariana-trench
for s in "$@"; do echo "$(date +%T) start $s"; nice -n 5 python3 descent.py $s; echo "$(date +%T) end $s"; done
