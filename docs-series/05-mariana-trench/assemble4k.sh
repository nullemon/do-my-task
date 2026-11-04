#!/usr/bin/env bash
# 4K-only part of the final assembly (run in parallel with assemble.sh)
# Final assembly for 05 "Falling into the Mariana Trench".
# Concatenates the shot segments (stream copy), adds vignette + fine temporal grain, muxes the mix and a
# soft English subtitle track, and writes 1080p master, 1080p-hq (<=380 MB), 4K upscale and 4K-share (<=480 MB).
# Run detached:  setsid nohup bash assemble.sh > $SCR/assemble.log 2>&1 < /dev/null &
set -euo pipefail
DOC=/home/user/do-my-task/docs-series/05-mariana-trench
SCR=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/05-mariana-trench
SEG=$SCR/seg
OUT=$DOC/out
MIX=$SCR/mix.wav
SRT=$DOC/mariana-trench.srt
NAME=mariana-trench
mkdir -p "$OUT"
log() { echo "[$(date '+%F %T')] $*"; }
SHOTS="s00 s01 s02 s03 s04 s05 s06 s07 s08 s09 s10 s11 s12 s13 s14"
for s in $SHOTS; do until [[ -s $SEG/$s.mp4 ]]; do sleep 30; done; done
: > "$SCR/concat.txt"
for s in $SHOTS; do
  [[ -s $SEG/$s.mp4 ]] || { log "missing segment $s"; exit 1; }
  echo "file '$SEG/$s.mp4'" >> "$SCR/concat.txt"
done
# no joined intermediate on disk (disk is tight): every encode reads the concat list directly
tot=0; for s in $SHOTS; do n=$(ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 "$SEG/$s.mp4"); tot=$((tot+n)); done
log "segments: $tot frames (want 8448)"
[[ $tot == 8448 ]] || { log "frame count mismatch"; exit 1; }
IN=(-f concat -safe 0 -i "$SCR/concat.txt")

VIG="vignette=angle=0.40:eval=init"
GRAIN="noise=c0s=5:c0f=t+u"
META=(-metadata title="Falling into the Mariana Trench" -c:a aac -b:a 256k -ar 48000
      -c:s mov_text -metadata:s:s:0 language=eng -disposition:s:0 0 -movflags +faststart)

if [[ ! -s $OUT/$NAME-4k.mp4 || -f $OUT/.4k_placeholder ]]; then
log "4K (lanczos UPSCALE of the 1080p render) + 4K-share"
nice -n 5 ffmpeg -v error -y "${IN[@]}" -i "$MIX" -i "$SRT" \
  -filter_complex "[0:v]fps=24,${VIG},scale=3840:2160:flags=lanczos,noise=c0s=6:c0f=t+u,format=yuv420p,split=2[a][b]" \
  -map "[a]" -map 1:a -map 2:s -c:v libx264 -preset ultrafast -crf 20 -profile:v high "${META[@]}" -metadata comment="4K lanczos upscale of a 1080p render" -t 352 "$OUT/$NAME-4k.part.mp4" \
  -map "[b]" -map 1:a -map 2:s -c:v libx264 -preset ultrafast -crf 20 -maxrate 10M -bufsize 20M -profile:v high "${META[@]}" -metadata comment="4K lanczos upscale of a 1080p render" -t 352 "$OUT/$NAME-4k-share.part.mp4"
mv -f "$OUT/$NAME-4k.part.mp4" "$OUT/$NAME-4k.mp4"; mv -f "$OUT/$NAME-4k-share.part.mp4" "$OUT/$NAME-4k-share.mp4"; rm -f "$OUT/.4k_placeholder"
fi
ls -la "$OUT"
log "assembly complete"
