#!/usr/bin/env bash
# Horn plates (4K stills) + orbit frames (1280x720, 6 spp). Skips existing.
cd /home/user/do-my-task/docs-series/04-big-bang-on-your-tv
PL=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/04-big-bang-on-your-tv/plates
run() { nice -n 5 /home/user/bpyenv/bin/python -c "import sys;p='horn.py';sys.argv=['blender','--',$1];exec(compile(open(p).read(),p,'exec'))" 2>&1 | grep -E "Saved|Error|frame" | cut -c1-60; }
for c in wide throat low; do
  if [[ $(python3 -c "from PIL import Image;print(Image.open('$PL/horn_$c.png').size[0])" 2>/dev/null) != 3840 ]]; then
    echo "$(date +%T) still $c"; run "'still','$c','16','200'"; fi
done
echo "$(date +%T) orbit"; run "'orbit','0','121','6','67'"
echo "$(date +%T) HORN DONE"
