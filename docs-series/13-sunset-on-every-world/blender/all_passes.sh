#!/usr/bin/env bash
# all four passes of one world (resume-safe unless FORCE=1): bash blender/all_passes.sh <world> [spp]
PD=${PLATES:-/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/13-sunset-on-every-world/plates}
S=/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/13-sunset-on-every-world
cd /home/user/do-my-task/docs-series/13-sunset-on-every-world
for p in beauty albedo normal depth; do
  [[ -s $PD/$1_$p.png && "${FORCE:-0}" != 1 ]] && continue
  spp=${2:-64}; [[ $p != beauty ]] && spp=12
  echo "[$(date +%T)] $1 $p"; bash blender/run.sh $1 $p $spp | grep -E "Error|error|done|Traceback" 
done
