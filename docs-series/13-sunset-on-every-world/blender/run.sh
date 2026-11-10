#!/usr/bin/env bash
# one pass of one world: bash blender/run.sh <world> <pass> <spp>   (env RES, NU, THREADS)
cd /home/user/do-my-task/docs-series/13-sunset-on-every-world
/home/user/bpyenv/bin/python -c "import sys;p='blender/world.py';sys.argv=['blender','--','$1','$2','$3'];exec(compile(open(p).read(),p,'exec'))" 2>&1 | grep -vE "^Fra:|^$|Saved:| Time:"
