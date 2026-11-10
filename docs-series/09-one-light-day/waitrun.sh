#!/usr/bin/env bash
# waitrun.sh <logfile-to-wait-for 'segs done'> <VERT 0|1> <segs...>
cd /home/user/do-my-task/docs-series/09-one-light-day
L=$1; V=$2; shift 2
while ! grep -q "segs done" "$L"; do sleep 5; done
if [ "$V" = 1 ]; then VERT=1 bash render_segs.sh "$@"; else bash render_segs.sh "$@"; fi
