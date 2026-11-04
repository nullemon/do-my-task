#!/usr/bin/env bash
# Horn plates (4K stills, 12 spp + OIDN) + 41-key orbit (1280x720, 6 spp + OIDN), then the horn shots. Resume-safe.
cd /home/user/do-my-task/docs-series/04-big-bang-on-your-tv
L=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/04-big-bang-on-your-tv
run() { nice -n 5 /home/user/bpyenv/bin/python -c "import sys;p='horn.py';sys.argv=['blender','--',$1];exec(compile(open(p).read(),p,'exec'))" 2>&1 | grep -E "Saved|Error|Trace" | cut -c1-60; }
for c in wide throat low; do
  [[ -f $L/plates/horn_$c.v2 ]] && continue
  echo "$(date +%T) still $c"; run "'still','$c','12','200'" && touch $L/plates/horn_$c.v2
done
echo "$(date +%T) orbit"; run "'orbit','0','41','6','67'"
n=$(ls $L/frames/horn_orbit | wc -l); echo "orbit frames $n"
[[ $n == 41 ]] && ./run_queue.sh H1 H2 H4 H6
echo "$(date +%T) HORN DONE"
