#!/usr/bin/env bash
# when the re-rendered end plate arrives: swap it in and (re)render the end segments in both formats
cd /home/user/do-my-task/docs-series/09-one-light-day
S=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/09-one-light-day
while [ ! -s $S/plates_new/plate_end/0000.png ]; do sleep 10; done; sleep 5
mv $S/plates/plate_end $S/plates/plate_end_old; mv $S/plates_new/plate_end $S/plates/plate_end
rm -f $S/seg_v/seg_06048.mp4 $S/seg_v/seg_06336.mp4 $S/seg_v/seg_06624.mp4 $S/seg/seg_06048.mp4 $S/seg/seg_06336.mp4 $S/seg/seg_06624.mp4
bash render_segs.sh 252 264 276
VERT=1 bash render_segs.sh 252 264 276
echo "END DONE $(date +%T)"
