#!/usr/bin/env bash
# Render composite parts (10 s each, 27 parts) with skip-existing. Parts 2-5 need the Earth loop: wait for it.
# Usage: render_parts.sh "0 1 6 7 ..."
cd /home/user/do-my-task/docs-series/03-you-are-not-sitting-still/visuals
for k in $1; do
  if [[ $k -ge 2 && $k -le 5 ]]; then
    until [[ $(ls /tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/03-you-are-not-sitting-still/earth_frames/*.png 2>/dev/null | wc -l) -ge 288 ]] && ! kill -0 $(cat /tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/03-you-are-not-sitting-still/earth.pid) 2>/dev/null; do sleep 20; done
  fi
  nice -n 8 /usr/bin/python3 -I compose.py --part $k --parts 27
done
