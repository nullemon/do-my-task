#!/usr/bin/env bash
# Final assembly: concat 27 silent parts -> grain + vignette -> mux mix + soft subtitles -> 4 deliverables.
# Run detached: setsid nohup bash assemble.sh > assemble.log 2>&1 < /dev/null &
set -euo pipefail
S=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/03-you-are-not-sitting-still
D=/home/user/do-my-task/docs-series/03-you-are-not-sitting-still
OUT=$D/out; mkdir -p "$OUT"
MIX=$S/audio/mix.wav; SRT=$D/you-are-not-sitting-still.srt
NAME=you-are-not-sitting-still
TITLE="You Are Not Sitting Still"
log() { echo "[$(date '+%F %T')] $*"; }
for k in $(seq 0 26); do f=$(printf "%s/parts/part_%02d.mp4" "$S" "$k"); [[ -s $f ]] || { log "missing $f"; exit 1; }; done
: > "$S/concat.txt"; for k in $(seq 0 26); do printf "file '%s/parts/part_%02d.mp4'\n" "$S" "$k" >> "$S/concat.txt"; done
ffmpeg -v error -y -f concat -safe 0 -i "$S/concat.txt" -c copy -an "$S/joined.mp4"
log "joined: $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$S/joined.mp4") s"
VIG="vignette=angle=0.42:eval=init"; GRAIN="noise=c0s=5:c0f=t+u"
COMMON=(-map 0:v:0 -map 1:a:0 -map 2:s:0 -c:a aac -b:a 256k -ar 48000 -c:s mov_text -metadata:s:s:0 language=eng -disposition:s:0 0 -t 270 -movflags +faststart)
enc() { # out vf vcodec-args... (title)
  local out=$1 vf=$2 t=$3; shift 3
  [[ -s $out ]] && { log "exists $out"; return; }
  nice -n 5 ffmpeg -v error -y -i "$S/joined.mp4" -i "$MIX" -i "$SRT" -vf "$vf" "$@" "${COMMON[@]}" -metadata title="$t" "$out.part.mp4"
  mv -f "$out.part.mp4" "$out"; log "done $out $(du -h "$out" | cut -f1)"
}
enc "$OUT/$NAME-1080p.mp4" "${VIG},${GRAIN},format=yuv420p" "$TITLE" -c:v libx264 -preset slow -crf 18 -tune film -pix_fmt yuv420p
enc "$OUT/$NAME-1080p-hq.mp4" "${VIG},${GRAIN},format=yuv420p" "$TITLE" -c:v libx264 -preset slow -b:v 9500k -maxrate 14000k -bufsize 20000k -tune film -pix_fmt yuv420p
enc "$OUT/$NAME-4k.mp4" "${VIG},scale=3840:2160:flags=lanczos,noise=c0s=6:c0f=t+u,format=yuv420p" "$TITLE (4K lanczos upscale)" -c:v libx264 -preset medium -crf 20 -tune film -pix_fmt yuv420p
enc "$OUT/$NAME-4k-share.mp4" "${VIG},scale=3840:2160:flags=lanczos,noise=c0s=6:c0f=t+u,format=yuv420p" "$TITLE (4K lanczos upscale)" -c:v libx264 -preset medium -b:v 12500k -maxrate 18000k -bufsize 26000k -tune film -pix_fmt yuv420p
touch "$S/ASSEMBLY_DONE"; log "assembly complete"
