#!/usr/bin/env bash
# Final assembly: waits for the silent master + mix, adds vignette + fine temporal grain, muxes audio + soft
# subtitles. Bitrate caps keep every file inside its size budget (disk on the shared machine is tight).
set -euo pipefail
DOC=/home/user/do-my-task/docs-series/02-what-they-see-of-us
W=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/02-what-they-see-of-us
V=$W/seg/master_silent.mp4; A=$W/what-they-see-of-us_mix.wav; S=$DOC/what-they-see-of-us.srt
O=$DOC/out; N=what-they-see-of-us
mkdir -p $O
log() { echo "[$(date '+%F %T')] $*"; }
until [[ -s $V && -s $A && -s $S ]]; do sleep 60; done
log "inputs ready"
VIG="vignette=angle=0.42:eval=init"
COMMON=(-map 0:v:0 -map 1:a:0 -map 2:s:0 -c:a aac -b:a 256k -ar 48000 -c:s mov_text -metadata:s:s:0 language=eng -disposition:s:0 0 -movflags +faststart)
enc() { local out=$1 needmb=$2; shift 2; [[ -s $out ]] && { log "skip $out"; return; }
  local free=$(df -m --output=avail $O | tail -1)
  (( free > needmb + 300 )) || { log "NOT ENOUGH DISK for $out (free ${free} MB, need ~${needmb})"; return; }
  nice -n 5 ffmpeg -v error -y -i "$V" -i "$A" -i "$S" "${COMMON[@]}" "$@" "$out.part.mp4" && mv -f "$out.part.mp4" "$out"
  log "done $out $(du -h "$out" | cut -f1) $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$out")s"; }
# 1080p master capped at 10 Mb/s so it also fits the chat budget; the -hq file is then a stream-copy of it
# (identical pictures, re-muxed). Same idea for the 4K pair (capped at 13 Mb/s < 480 MB).
enc $O/$N-1080p.mp4 400 -vf "$VIG,noise=c0s=3:c0f=t+u,format=yuv420p" -c:v libx264 -preset faster -crf 18 -maxrate 10000k -bufsize 20000k -tune film \
  -metadata title="What They See of Us"
remux() { local src=$1 out=$2 cap=$3; [[ -s $out ]] && return
  local sz=$(stat -c %s $src); if (( sz < cap*1000000 )); then
    ffmpeg -v error -y -i $src -map 0 -c copy -movflags +faststart $out.part.mp4 && mv -f $out.part.mp4 $out
    log "done $out (stream copy of $(basename $src)) $(du -h $out | cut -f1)"; else log "$src over ${cap} MB, needs a capped re-encode"; fi; }
remux $O/$N-1080p.mp4 $O/$N-1080p-hq.mp4 380
enc $O/$N-4k.mp4 480 -vf "$VIG,scale=3840:2160:flags=lanczos,noise=c0s=3:c0f=t+u,format=yuv420p" -c:v libx264 -preset veryfast -crf 20 -maxrate 13000k -bufsize 26000k -tune film \
  -metadata title="What They See of Us (4K lanczos upscale of the 1080p render)"
remux $O/$N-4k.mp4 $O/$N-4k-share.mp4 480
touch $W/ASSEMBLY_DONE; log "assembly complete"
