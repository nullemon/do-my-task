#!/usr/bin/env bash
# final catch-up queue: waits for a log, deletes stale segments, renders whatever is listed. finalq.sh <waitlog> <VERT> <segs..>
cd /home/user/do-my-task/docs-series/09-one-light-day
S=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/09-one-light-day
L=$1; V=$2; shift 2
while [ "$(grep -c 'segs done' "$L")" -lt 1 ]; do sleep 5; done
D=seg; [ "$V" = 1 ] && D=seg_v
for s in "$@"; do rm -f $S/$D/$(printf "seg_%05d.mp4" $((s*24))); done
if [ "$V" = 1 ]; then VERT=1 bash render_segs.sh "$@"; else bash render_segs.sh "$@"; fi
