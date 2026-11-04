#!/usr/bin/env bash
# Second stage (used for the delivered files): waits for the graded 1080p master, then derives
#   -1080p-hq   (bitrate-capped for chat, <= 380 MB)
#   -4k         (lanczos UPSCALE of the graded master, crf 21)
#   -4k-share   (bitrate-capped upscale, <= 480 MB)
# Grain/vignette are already in the master, so they are not re-applied (saves CPU and disk on a shared box).
set -euo pipefail
S=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/03-you-are-not-sitting-still
D=/home/user/do-my-task/docs-series/03-you-are-not-sitting-still; OUT=$D/out; N=you-are-not-sitting-still
M=$OUT/$N-1080p.mp4
log() { echo "[$(date '+%F %T')] $*"; }
# (master is produced by final.sh)
[[ -s $M ]] || mv -f "$M.part.mp4" "$M"
log "master $(du -h "$M" | cut -f1)"
MAP=(-map 0:v:0 -map 0:a:0 -map 0:s:0 -c:a copy -c:s copy -movflags +faststart)
enc() { local out=$1; shift; [[ -s $out ]] && return; nice -n 5 ffmpeg -v error -y -i "$M" "$@" "${MAP[@]}" "$out.part.mp4"; mv -f "$out.part.mp4" "$out"; log "done $out $(du -h "$out" | cut -f1)"; }
enc "$OUT/$N-1080p-hq.mp4" -c:v libx264 -preset medium -b:v 9000k -maxrate 13000k -bufsize 18000k -tune film -pix_fmt yuv420p -metadata title="You Are Not Sitting Still"
enc "$OUT/$N-4k-share.mp4" -vf "scale=3840:2160:flags=lanczos" -c:v libx264 -preset veryfast -b:v 12000k -maxrate 17000k -bufsize 24000k -tune film -pix_fmt yuv420p -metadata title="You Are Not Sitting Still (4K lanczos upscale)"
enc "$OUT/$N-4k.mp4" -vf "scale=3840:2160:flags=lanczos" -c:v libx264 -preset veryfast -crf 21 -tune film -pix_fmt yuv420p -metadata title="You Are Not Sitting Still (4K lanczos upscale)"
touch "$S/ASSEMBLY_DONE"; log "assembly complete"
