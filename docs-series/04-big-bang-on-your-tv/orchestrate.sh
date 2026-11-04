#!/usr/bin/env bash
# Waits for plates and launches dependent shot renders (each queue sequential, skip-existing).
cd /home/user/do-my-task/docs-series/04-big-bang-on-your-tv
L=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/04-big-bang-on-your-tv
big() { [[ -s $1 && $(stat -c %s $1) -gt 20000000 ]]; }
(
  until big $L/plates/room_wide_lit.npy; do sleep 30; done
  ./run_queue.sh R1 G
  until big $L/plates/room_medium_lit.npy; do sleep 30; done
  ./run_queue.sh R2 S4 PF
) > $L/queue2.log 2>&1 &
(
  until grep -q "^.*orbit" $L/horn.log; do sleep 30; done
  ./run_queue.sh H1 H4 H6
  until grep -q "HORN DONE" $L/horn.log; do sleep 30; done
  ./run_queue.sh H2
) > $L/queue3.log 2>&1 &
wait
