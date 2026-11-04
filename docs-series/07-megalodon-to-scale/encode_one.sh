#!/usr/bin/env bash
# Encode ONE deliverable from the joined silent master (resume-safe: skips if the final file exists).
# Usage: setsid nohup bash encode_one.sh 1080p|hq|4k|share > log 2>&1 &
set -euo pipefail
DOC=/home/user/do-my-task/docs-series/07-megalodon-to-scale
SCR=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/07-megalodon-to-scale
J=$SCR/final/joined.mp4; MIX=$SCR/audio/mix_megalodon.wav; SRT=$DOC/megalodon-to-scale.srt; OUT=$DOC/out
mkdir -p "$OUT"
VIG="vignette=angle=0.40:eval=init"
META=(-metadata title="Megalodon to Scale" -c:s mov_text -metadata:s:s:0 language=eng -disposition:s:0 0)
IN=(-i "$J" -i "$MIX" -i "$SRT" -map 0:v:0 -map 1:a:0 -map 2:s:0)
A=(-c:a aac -b:a 256k -ar 48000)
UP=(-metadata comment="3840x2160 lanczos upscale of a 1920x1080 render")
case $1 in
 1080p) F=megalodon-to-scale-1080p.mp4; V=(-vf "${VIG},noise=c0s=5:c0f=t+u,format=yuv420p" -c:v libx264 -preset medium -crf 18 -tune film -profile:v high -pix_fmt yuv420p); X=();;
 hq)    F=megalodon-to-scale-1080p-hq.mp4; V=(-vf "${VIG},noise=c0s=5:c0f=t+u,format=yuv420p" -c:v libx264 -preset medium -crf 18 -maxrate 10M -bufsize 20M -tune film -profile:v high -pix_fmt yuv420p); X=();;
 4k)    F=megalodon-to-scale-4k.mp4; V=(-vf "${VIG},scale=3840:2160:flags=lanczos,noise=c0s=6:c0f=t+u,format=yuv420p" -c:v libx264 -preset veryfast -crf 20 -tune film -profile:v high -pix_fmt yuv420p); X=("${UP[@]}");;
 share) F=megalodon-to-scale-4k-share.mp4; V=(-vf "${VIG},scale=3840:2160:flags=lanczos,noise=c0s=6:c0f=t+u,format=yuv420p" -c:v libx264 -preset veryfast -b:v 13.5M -maxrate 16M -bufsize 32M -tune film -pix_fmt yuv420p); X=("${UP[@]}");;
esac
[[ -s $OUT/$F ]] && { echo "exists $F"; exit 0; }
echo "[$(date '+%T')] start $F"
nice -n 5 ffmpeg -v error -y "${IN[@]}" "${V[@]}" "${A[@]}" "${META[@]}" "${X[@]}" -movflags +faststart "$OUT/${F%.mp4}.part.$1.mp4"
mv -f "$OUT/${F%.mp4}.part.$1.mp4" "$OUT/$F"
echo "[$(date '+%T')] done $F $(stat -c %s "$OUT/$F")"
