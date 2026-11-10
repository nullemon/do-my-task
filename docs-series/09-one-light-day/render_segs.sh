#!/usr/bin/env bash
# Render compositor segments (12 s each, resume-safe). Usage: render_segs.sh <start_s> [<start_s> ...]
cd /home/user/do-my-task/docs-series/09-one-light-day
for s in "$@"; do nice -n 5 python3 comp.py $s $((s+12)) || echo "FAILED $s"; done
echo "segs done: $* $(date +%T)"
