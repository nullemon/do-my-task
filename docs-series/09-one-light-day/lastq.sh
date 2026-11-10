#!/usr/bin/env bash
# lastq.sh <waitlog> <VERT>: after <waitlog> is done render 144, then (once the DSN plate exists) 156 168 180
cd /home/user/do-my-task/docs-series/09-one-light-day
S=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/09-one-light-day
L=$1; V=$2
while [ "$(grep -c 'segs done' "$L")" -lt 1 ]; do sleep 5; done
run() { if [ "$V" = 1 ]; then VERT=1 bash render_segs.sh "$@"; else bash render_segs.sh "$@"; fi; }
run 144
while [ ! -s $S/plates/plate_dsn/0000.png ]; do sleep 10; done; sleep 5
run 156 168 180
echo "ALL DONE V=$V $(date +%T)"
