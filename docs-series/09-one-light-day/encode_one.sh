#!/usr/bin/env bash
# Encode ONE deliverable from the joined silent master (vignette + temporal grain added here).
# Usage: setsid nohup bash encode_one.sh hq|4k > log 2>&1 &
set -euo pipefail
DOC=/home/user/do-my-task/docs-series/09-one-light-day
SCR=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/09-one-light-day
J=$SCR/final/joined.mp4; MIX=$SCR/audio/mix_onelightday.wav; SRT=$DOC/one-light-day.srt; OUT=$DOC/out
mkdir -p "$OUT"
VIG="vignette=angle=0.42:eval=init"
META=(-metadata title="One Light-Day From Home" -c:s mov_text -metadata:s:s:0 language=eng -disposition:s:0 0)
IN=(-i "$J" -i "$MIX" -i "$SRT" -map 0:v:0 -map 1:a:0 -map 2:s:0)
A=(-c:a aac -b:a 256k -ar 48000)
case $1 in
 hq) F=one-light-day-1080p-hq.mp4; V=(-vf "${VIG},noise=c0s=6:c0f=t+u,format=yuv420p" -c:v libx264 -preset slow -crf 17 -maxrate 9.5M -bufsize 19M -tune film -profile:v high -pix_fmt yuv420p); X=();;
 4k) F=one-light-day-4k.mp4; V=(-vf "${VIG},scale=3840:2160:flags=lanczos,noise=c0s=7:c0f=t+u,format=yuv420p" -c:v libx264 -preset fast -crf 20 -maxrate 19M -bufsize 38M -tune film -profile:v high -pix_fmt yuv420p); X=(-metadata comment="3840x2160 lanczos upscale of a 1920x1080 render");;
esac
echo "[$(date '+%T')] start $F"
nice -n 5 ffmpeg -v error -y "${IN[@]}" "${V[@]}" "${A[@]}" "${META[@]}" "${X[@]}" -movflags +faststart "$OUT/${F%.mp4}.part.mp4"
mv -f "$OUT/${F%.mp4}.part.mp4" "$OUT/$F"
echo "[$(date '+%T')] done $F $(stat -c %s "$OUT/$F")"
