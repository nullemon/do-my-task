#!/usr/bin/env bash
# Resume-safe finisher: waits for the denoised room plates, renders the room shots (skip existing),
# waits for the horn shots, then runs the assembly.
cd /home/user/do-my-task/docs-series/04-big-bang-on-your-tv
L=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/04-big-bang-on-your-tv
D=$L/dn
until [[ -f $D/wide_off.done && -f $D/wide_lit.done ]]; do sleep 30; done
./run_queue.sh R1 G > $L/fq1.log 2>&1 &
until [[ -f $D/medium_off.done && -f $D/medium_lit.done ]]; do sleep 30; done
./run_queue.sh PF > $L/fq2.log 2>&1 &
./run_queue.sh R2 S4 > $L/fq3.log 2>&1 &
wait
bash assemble.sh > $L/assemble.log 2>&1
