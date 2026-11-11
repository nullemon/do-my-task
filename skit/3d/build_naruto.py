"""Naruto build = generic pipeline with the 'naruto' spec.
Run: xvfb-run -a blender -b -P build_naruto.py   (writes naruto.blend/.glb, previews, sprites, turntable frames)"""
import os, sys
sys.argv = [sys.argv[0], "--", "naruto", "--build", "--previews", "--sprites", "--turntable"]
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_character.py")).read())
