#!/usr/bin/env bash
# Re-render the throat still (it was OOM-killed earlier), then re-render H4 once the horn queue is finished.
cd /home/user/do-my-task/docs-series/04-big-bang-on-your-tv
L=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/04-big-bang-on-your-tv
nice -n 5 /home/user/bpyenv/bin/python -c "import sys;p='horn.py';sys.argv=['blender','--','still','throat','12','200'];exec(compile(open(p).read(),p,'exec'))" > $L/throat.log 2>&1
st=$?; echo "throat exit $st"
[[ $st == 0 ]] || exit 1
touch $L/plates/horn_throat.v2
while pgrep -f "run_queue.sh H1 H2 H4 H6" >/dev/null; do sleep 20; done
rm -f $L/seg/H4.mp4
./run_queue.sh H4
echo "H4 FIXED"
