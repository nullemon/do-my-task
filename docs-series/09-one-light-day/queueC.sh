#!/usr/bin/env bash
S=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/09-one-light-day
cd /home/user/do-my-task/docs-series/09-one-light-day
while kill -0 3017 2>/dev/null; do sleep 5; done
echo "[$(date +%T)] cover finished"
THREADS=2 bash render_plates.sh plate_record plate_rtg
THREADS=2 nice -n 5 /home/user/bpyenv/bin/python -c "import sys;p='blender/dsn.py';sys.argv=['blender','--','final'];exec(compile(open(p).read(),p,'exec'))" 2>&1 | grep -i "error\|Trace\|Saved"
echo "queueC done $(date +%T)"
