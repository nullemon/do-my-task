#!/usr/bin/env bash
# Resume-safe final stage (after the container restart): 1080p graded master from joined.mp4, then assemble2.sh.
# Each output is written as *.part.mp4 and renamed only when complete; existing finished files are skipped.
set -euo pipefail
S=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/03-you-are-not-sitting-still
D=/home/user/do-my-task/docs-series/03-you-are-not-sitting-still; OUT=$D/out; N=you-are-not-sitting-still
M=$OUT/$N-1080p.mp4
log() { echo "[$(date '+%F %T')] $*"; }
if [[ ! -s $M ]]; then
  rm -f "$M.part.mp4"
  nice -n 5 ffmpeg -v error -y -i "$S/joined.mp4" -i "$S/audio/mix.wav" -i "$D/$N.srt" \
    -map 0:v:0 -map 1:a:0 -map 2:s:0 -vf "vignette=angle=0.42:eval=init,noise=c0s=5:c0f=t+u,format=yuv420p" \
    -c:v libx264 -preset medium -crf 18 -tune film -pix_fmt yuv420p -c:a aac -b:a 256k -ar 48000 \
    -c:s mov_text -metadata:s:s:0 language=eng -disposition:s:0 0 -t 270 -movflags +faststart \
    -metadata title="You Are Not Sitting Still" "$M.part.mp4"
  mv -f "$M.part.mp4" "$M"
fi
log "1080p master $(du -h "$M" | cut -f1)"
for f in "$OUT"/*.part.mp4; do [[ -e $f ]] && rm -f "$f"; done
bash "$D/visuals/assemble2.sh"
