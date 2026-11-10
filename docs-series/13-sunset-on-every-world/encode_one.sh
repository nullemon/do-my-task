#!/usr/bin/env bash
# One deliverable from the joined silent master + mix + SRT (vignette + temporal grain added here). Usage: bash encode_one.sh hq|4k|vertical
set -euo pipefail
DOC=/home/user/do-my-task/docs-series/13-sunset-on-every-world
SCR=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/13-sunset-on-every-world
J=$SCR/final/joined.mp4; MIX=$SCR/audio/mix.wav; SRT=$DOC/sunset-on-every-world.srt; OUT=$DOC/out
mkdir -p "$OUT"; cp -f "$SRT" "$OUT/sunset-on-every-world.srt"
VIG="vignette=angle=0.38:eval=init"
META=(-metadata title="What Sunset Looks Like on Every Planet" -c:s mov_text -metadata:s:s:0 language=eng -disposition:s:0 0)
IN=(-i "$J" -i "$MIX" -i "$SRT" -map 0:v:0 -map 1:a:0 -map 2:s:0)
A=(-c:a aac -b:a 256k -ar 48000)
case $1 in
 hq) F=sunset-on-every-world-1080p-hq.mp4; V=(-vf "${VIG},noise=c0s=5:c0f=t+u,format=yuv420p" -c:v libx264 -preset medium -crf 17 -maxrate 8.4M -bufsize 17M -tune film -profile:v high -pix_fmt yuv420p); X=();;
 vertical) J=$SCR/final/joined_v.mp4; IN=(-i "$J" -i "$MIX" -i "$SRT" -map 0:v:0 -map 1:a:0 -map 2:s:0); F=sunset-on-every-world-vertical.mp4; V=(-vf "${VIG},noise=c0s=5:c0f=t+u,format=yuv420p" -c:v libx264 -preset medium -crf 17 -maxrate 8.4M -bufsize 17M -tune film -profile:v high -pix_fmt yuv420p); X=(-metadata comment="1080x1920 recomposition (not a crop of the 16:9 master)");;
 4k) F=sunset-on-every-world-4k.mp4; V=(-vf "${VIG},scale=3840:2160:flags=lanczos,noise=c0s=6:c0f=t+u,format=yuv420p" -c:v libx264 -preset veryfast -crf 20 -maxrate 16.5M -bufsize 33M -tune film -profile:v high -pix_fmt yuv420p); X=(-metadata comment="3840x2160 lanczos upscale of a 1920x1080 render");;
esac
echo "[$(date '+%T')] start $F"
ffmpeg -v error -y "${IN[@]}" "${V[@]}" "${A[@]}" "${META[@]}" "${X[@]}" -movflags +faststart "$OUT/${F%.mp4}.part.mp4"
mv -f "$OUT/${F%.mp4}.part.mp4" "$OUT/$F"
echo "[$(date '+%T')] done $F $(stat -c %s "$OUT/$F")"
