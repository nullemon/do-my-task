"""Locked timeline for "ONE LIGHT-DAY FROM HOME" (seconds, 24 fps). Voice starts fixed from measured Kokoro durations."""
import os
FPS = 24
DUR = 288.0
NFR = int(DUR * FPS)
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/09-one-light-day"
START = {'hook1': 1.0, 'hook2': 8.8, 'light': 26.0, 'launch': 38.5, 'jupiter': 50.5, 'saturn': 63.0, 'pbd1': 78.0,
         'pbd2': 94.5, 'helio': 107.0, 'record1': 124.5, 'record2': 134.5, 'signal1': 150.0, 'signal2': 161.0,
         'power1': 183.0, 'power2': 199.2, 'scale1': 214.5, 'scale2': 226.5, 'scale3': 240.5, 'end1': 254.0,
         'end2': 262.5, 'end3': 274.5}
# shots: (name, t0, t1)  - cross-dissolved by XF seconds centred on the boundary
SHOTS = [("hero", 0.0, 25.5), ("light", 25.5, 38.0), ("launch", 38.0, 50.0), ("jupiter", 50.0, 62.5),
         ("saturn", 62.5, 77.5), ("pbd", 77.5, 106.5), ("helio", 106.5, 124.0), ("record", 124.0, 149.5),
         ("signal", 149.5, 163.0), ("dsn", 163.0, 182.5), ("power", 182.5, 213.5), ("scale", 213.5, 253.0),
         ("end", 253.0, 288.0)]
XF = 1.2
