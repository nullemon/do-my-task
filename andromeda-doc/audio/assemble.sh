#!/usr/bin/env bash
# Final assembly for "Andromeda — The Sky That's Coming".
# Waits for the four silent 60.0 s chapter masters, concatenates them (240 s), adds subtle grain + vignette,
# muxes the final audio mix (+ soft English subtitle track) and writes the 1080p master and a 4K lanczos upscale.
#
# Run detached:  setsid nohup bash assemble.sh > assemble.log 2>&1 < /dev/null &
set -euo pipefail

DOC=/home/user/do-my-task/andromeda-doc
AUD=$DOC/audio
SRC=${SRC:-/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/andromeda}
WORK=$SRC/final
MIX=$AUD/andromeda_mix.wav
SRT=$DOC/andromeda.srt
OUTDIR=${OUTDIR:-$DOC}
OUT1080=$OUTDIR/andromeda-1080p.mp4
OUT4K=$OUTDIR/andromeda-4k.mp4
POLL=${POLL:-120}
TLEN=${TLEN:-240}   # (testing only) limit encoded length
mkdir -p "$WORK"
log() { echo "[$(date '+%F %T')] $*"; }

chapter_ok() {   # complete = readable, 60.0 s (±0.05), 1440 video frames, size unchanged since last poll
  local f=$1
  [[ -s $f ]] || return 1
  local d n
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f" 2>/dev/null) || return 1
  [[ -n $d ]] || return 1
  awk -v d="$d" 'BEGIN{exit !(d>59.95 && d<60.05)}' || return 1
  n=$(ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 "$f" 2>/dev/null) || return 1
  [[ $n == 1440 ]] || { log "$f: $n packets (want 1440)"; return 1; }
  return 0
}

declare -A LASTSIZE
log "waiting for chapters in $SRC"
while true; do
  ready=0
  for i in 1 2 3 4; do
    f=$SRC/ch$i.mp4
    if chapter_ok "$f"; then
      sz=$(stat -c %s "$f")
      if [[ ${LASTSIZE[$i]:-} == "$sz" ]]; then ready=$((ready+1)); fi
      LASTSIZE[$i]=$sz
    fi
  done
  [[ $ready == 4 ]] && break
  log "ready (stable) chapters: $ready/4"
  sleep "$POLL"
done
log "all four chapters complete"

[[ -s $MIX ]] || { log "missing $MIX"; exit 1; }
[[ -s $SRT ]] || { log "missing $SRT"; exit 1; }

LIST=$WORK/concat.txt
: > "$LIST"
for i in 1 2 3 4; do echo "file '$SRC/ch$i.mp4'" >> "$LIST"; done

# Lossless-ish joined 240 s master (stream copy; all chapters share encoder settings). Re-encode fallback.
if ! ffmpeg -v error -y -f concat -safe 0 -i "$LIST" -c copy -an "$WORK/joined.mp4"; then
  log "stream-copy concat failed, re-encoding joined master"
  ffmpeg -v error -y -f concat -safe 0 -i "$LIST" -an -c:v libx264 -crf 12 -preset medium -pix_fmt yuv420p -r 24 "$WORK/joined.mp4"
fi
JD=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$WORK/joined.mp4")
log "joined duration: $JD"

# Subtle look: soft vignette, then fine temporal luma grain (grain stays sharp: added after any scaling).
VIG="vignette=angle=0.42:eval=init"
GRAIN="noise=c0s=5:c0f=t+u"

log "encoding 1080p master"
nice -n 5 ffmpeg -v error -y -i "$WORK/joined.mp4" -i "$MIX" -i "$SRT" \
  -map 0:v:0 -map 1:a:0 -map 2:s:0 \
  -vf "fps=24,scale=1920:1080:flags=lanczos,${VIG},${GRAIN},format=yuv420p" \
  -c:v libx264 -preset slow -crf 18 -profile:v high -tune film -pix_fmt yuv420p \
  -c:a aac -b:a 256k -ar 48000 \
  -c:s mov_text -metadata:s:s:0 language=eng -disposition:s:0 0 \
  -metadata title="Andromeda — The Sky That's Coming" \
  -t "$TLEN" -movflags +faststart "$OUT1080.part.mp4"
mv -f "$OUT1080.part.mp4" "$OUT1080"
log "1080p done: $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT1080") s"

log "encoding 4K (lanczos upscale of the 1080p render)"
nice -n 5 ffmpeg -v error -y -i "$WORK/joined.mp4" -i "$MIX" -i "$SRT" \
  -map 0:v:0 -map 1:a:0 -map 2:s:0 \
  -vf "fps=24,${VIG},scale=3840:2160:flags=lanczos,noise=c0s=6:c0f=t+u,format=yuv420p" \
  -c:v libx264 -preset medium -crf 20 -profile:v high -tune film -pix_fmt yuv420p \
  -c:a aac -b:a 256k -ar 48000 \
  -c:s mov_text -metadata:s:s:0 language=eng -disposition:s:0 0 \
  -metadata title="Andromeda — The Sky That's Coming (4K upscale)" \
  -t "$TLEN" -movflags +faststart "$OUT4K.part.mp4"
mv -f "$OUT4K.part.mp4" "$OUT4K"
log "4K done: $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT4K") s"

touch "$WORK/ASSEMBLY_DONE"
log "assembly complete"
