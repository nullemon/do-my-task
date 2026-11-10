#!/usr/bin/env bash
# waits for the plate queue, then renders the DSN plate
S=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/09-one-light-day
cd /home/user/do-my-task/docs-series/09-one-light-day
while ! grep -q "plates done" $S/logs/plates.log; do sleep 10; done
THREADS=3 nice -n 5 /home/user/bpyenv/bin/python -c "import sys;p='blender/dsn.py';sys.argv=['blender','--','final'];exec(compile(open(p).read(),p,'exec'))" 2>&1 | grep -i "error\|Trace\|Saved"
echo "dsn done $(date +%T)"
