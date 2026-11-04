#!/usr/bin/env bash
# Final assembly for 04 "The Big Bang is on your TV".
# Concatenates the shot segments (stream copy), adds vignette + fine temporal grain, muxes the mix and a
# soft English subtitle track, and writes 1080p master, 1080p-hq (<=380 MB), 4K upscale and 4K-share (<=480 MB).
# Run detached:  setsid nohup bash assemble.sh > $SCR/assemble.log 2>&1 < /dev/null &
set -euo pipefail
DOC=/home/user/do-my-task/docs-series/04-big-bang-on-your-tv
SCR=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/04-big-bang-on-your-tv
SEG=$SCR/seg
OUT=$DOC/out
MIX=$SCR/mix.wav
SRT=$DOC/bigbang-tv.srt
NAME=bigbang-tv
mkdir -p "$OUT"
log() { echo "[$(date '+%F %T')] $*"; }
SHOTS="R1 R2 PF S1 S2 S3 S4 H1 H2 H3 H4 H5 H6 M G"
for s in $SHOTS; do until [[ -s $SEG/$s.mp4 ]]; do sleep 30; done; done
: > "$SCR/concat.txt"
for s in $SHOTS; do
  [[ -s $SEG/$s.mp4 ]] || { log "missing segment $s"; exit 1; }
  echo "file '$SEG/$s.mp4'" >> "$SCR/concat.txt"
done
# no joined intermediate on disk (disk is tight): every encode reads the concat list directly
tot=0; for s in $SHOTS; do n=$(ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 "$SEG/$s.mp4"); tot=$((tot+n)); done
log "segments: $tot frames (want 6480)"
[[ $tot == 6480 ]] || { log "frame count mismatch"; exit 1; }
IN=(-f concat -safe 0 -i "$SCR/concat.txt")

VIG="vignette=angle=0.40:eval=init"
GRAIN="noise=c0s=5:c0f=t+u"
META=(-metadata title="The Big Bang Is on Your TV" -c:a aac -b:a 256k -ar 48000
      -c:s mov_text -metadata:s:s:0 language=eng -disposition:s:0 0 -movflags +faststart)

if [[ ! -s $OUT/$NAME-1080p.mp4 ]]; then
log "1080p master + hq"
nice -n 5 ffmpeg -v error -y "${IN[@]}" -i "$MIX" -i "$SRT" \
  -filter_complex "[0:v]fps=24,${VIG},${GRAIN},format=yuv420p,split=2[a][b]" \
  -map "[a]" -map 1:a -map 2:s -c:v libx264 -preset slow -crf 18 -profile:v high -tune film "${META[@]}" -t 270 "$OUT/$NAME-1080p.part.mp4" \
  -map "[b]" -map 1:a -map 2:s -c:v libx264 -preset slow -crf 18 -maxrate 10M -bufsize 20M -profile:v high -tune film "${META[@]}" -t 270 "$OUT/$NAME-1080p-hq.part.mp4"
mv -f "$OUT/$NAME-1080p.part.mp4" "$OUT/$NAME-1080p.mp4"; mv -f "$OUT/$NAME-1080p-hq.part.mp4" "$OUT/$NAME-1080p-hq.mp4"
fi
log "1080p done"

if [[ ! -s $OUT/$NAME-4k.mp4 ]]; then
log "4K (lanczos UPSCALE of the 1080p render) + 4K-share"
nice -n 5 ffmpeg -v error -y "${IN[@]}" -i "$MIX" -i "$SRT" \
  -filter_complex "[0:v]fps=24,${VIG},scale=3840:2160:flags=lanczos,noise=c0s=6:c0f=t+u,format=yuv420p,split=2[a][b]" \
  -map "[a]" -map 1:a -map 2:s -c:v libx264 -preset fast -crf 20 -profile:v high "${META[@]}" -metadata comment="4K lanczos upscale of a 1080p render" -t 270 "$OUT/$NAME-4k.part.mp4" \
  -map "[b]" -map 1:a -map 2:s -c:v libx264 -preset fast -crf 20 -maxrate 13M -bufsize 26M -profile:v high "${META[@]}" -metadata comment="4K lanczos upscale of a 1080p render" -t 270 "$OUT/$NAME-4k-share.part.mp4"
mv -f "$OUT/$NAME-4k.part.mp4" "$OUT/$NAME-4k.mp4"; mv -f "$OUT/$NAME-4k-share.part.mp4" "$OUT/$NAME-4k-share.mp4"
fi
ls -la "$OUT"
log "assembly complete"
