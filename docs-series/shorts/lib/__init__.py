"""Reusable pipeline for ground-level 'What if ... the sky' Shorts (vertical 1080x1920 + 16:9 recomposition).
Modules: core (math, Layout), foreground (RGBA plate relighting), sky (day sky, sun, stars, lensing), text (captions/HUD),
post (camera, bloom, tonemap, encoder), voice (Kokoro with word timings), audio (voice chain, sound design, loudness, SRT).
Run with /home/user/ttsenv/bin/python; see README.md in this folder.
"""
