#!/usr/bin/env bash
# Final assembly for "65 DAYS": concat the silent shot segments, add vignette + fine temporal grain,
# mux the -14 LUFS mix + soft English subtitles, write 1080p master, 1080p-hq (<=380 MB), 4K upscale, 4K share (<=480 MB).
# Run detached: setsid nohup bash assemble.sh > assemble.log 2>&1 < /dev/null &
set -euo pipefail
DOC=/home/user/do-my-task/docs-series/01-65-days
SCR=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/01-65-days
SEG=$SCR/segments; WORK=$SCR/final; OUT=$DOC/out
MIX=$SCR/audio/mix_65days.wav; SRT=$DOC/65-days.srt
mkdir -p "$WORK" "$OUT"
log() { echo "[$(date '+%F %T')] $*"; }
LIST=$WORK/concat.txt; : > "$LIST"
for s in open orbit landA diagram landB moon landC dive black orbitdg title; do
  [[ -s $SEG/$s.mp4 ]] || { log "missing $SEG/$s.mp4"; exit 1; }
  echo "file '$SEG/$s.mp4'" >> "$LIST"
done
ffmpeg -v error -y -f concat -safe 0 -i "$LIST" -c copy -an "$WORK/joined.mp4"
N=$(ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 "$WORK/joined.mp4")
log "joined: $N frames ($(ffprobe -v error -show_entries format=duration -of csv=p=0 "$WORK/joined.mp4") s)"
VIG="vignette=angle=0.40:eval=init"
META=(-metadata title="65 Days — If Earth Stopped Orbiting" -c:s mov_text -metadata:s:s:0 language=eng -disposition:s:0 0)
MAP=(-map 0:v:0 -map 1:a:0 -map 2:s:0)
A=(-c:a aac -b:a 256k -ar 48000)
if [[ ! -s $OUT/65-days-1080p.mp4 ]]; then
log "1080p master"
nice -n 5 ffmpeg -v error -y -i "$WORK/joined.mp4" -i "$MIX" -i "$SRT" "${MAP[@]}" \
  -vf "${VIG},noise=c0s=5:c0f=t+u,format=yuv420p" -c:v libx264 -preset slow -crf 18 -tune film -profile:v high -pix_fmt yuv420p \
  "${A[@]}" "${META[@]}" -movflags +faststart "$OUT/65-days-1080p.part.mp4"
mv -f "$OUT/65-days-1080p.part.mp4" "$OUT/65-days-1080p.mp4"; fi
if [[ ! -s $OUT/65-days-1080p-hq.mp4 ]]; then
log "1080p hq (<=380 MB)"
nice -n 5 ffmpeg -v error -y -i "$WORK/joined.mp4" -i "$MIX" -i "$SRT" "${MAP[@]}" \
  -vf "${VIG},noise=c0s=5:c0f=t+u,format=yuv420p" -c:v libx264 -preset slow -crf 18 -maxrate 10M -bufsize 20M -tune film -profile:v high -pix_fmt yuv420p \
  "${A[@]}" "${META[@]}" -movflags +faststart "$OUT/65-days-1080p-hq.part.mp4"
mv -f "$OUT/65-days-1080p-hq.part.mp4" "$OUT/65-days-1080p-hq.mp4"; fi
if [[ ! -s $OUT/65-days-4k.mp4 ]]; then
log "4K (lanczos UPSCALE of the 1080p render)"
nice -n 5 ffmpeg -v error -y -i "$WORK/joined.mp4" -i "$MIX" -i "$SRT" "${MAP[@]}" \
  -vf "${VIG},scale=3840:2160:flags=lanczos,noise=c0s=6:c0f=t+u,format=yuv420p" -c:v libx264 -preset medium -crf 20 -tune film -profile:v high -pix_fmt yuv420p \
  "${A[@]}" "${META[@]}" -metadata comment="3840x2160 lanczos upscale of a 1920x1080 render" -movflags +faststart "$OUT/65-days-4k.part.mp4"
mv -f "$OUT/65-days-4k.part.mp4" "$OUT/65-days-4k.mp4"; fi
if [[ ! -s $OUT/65-days-4k-share.mp4 ]]; then
log "4K share (<=480 MB, 2-pass 13.5 Mb/s)"
cd "$WORK"
nice -n 5 ffmpeg -v error -y -i "$WORK/joined.mp4" -vf "${VIG},scale=3840:2160:flags=lanczos,noise=c0s=6:c0f=t+u,format=yuv420p" \
  -c:v libx264 -preset medium -b:v 13.5M -pass 1 -passlogfile "$WORK/p4k" -an -f mp4 /dev/null
nice -n 5 ffmpeg -v error -y -i "$WORK/joined.mp4" -i "$MIX" -i "$SRT" "${MAP[@]}" \
  -vf "${VIG},scale=3840:2160:flags=lanczos,noise=c0s=6:c0f=t+u,format=yuv420p" -c:v libx264 -preset medium -b:v 13.5M -maxrate 20M -bufsize 30M -pass 2 -passlogfile "$WORK/p4k" -tune film -pix_fmt yuv420p \
  "${A[@]}" "${META[@]}" -metadata comment="3840x2160 lanczos upscale of a 1920x1080 render" -movflags +faststart "$OUT/65-days-4k-share.part.mp4"
mv -f "$OUT/65-days-4k-share.part.mp4" "$OUT/65-days-4k-share.mp4"; fi
ls -la "$OUT"; log "done"
