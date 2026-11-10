"""Locked timeline for "THE MOON IS LEAVING" (seconds, 24 fps). Voice starts are placed against the measured Kokoro durations."""
FPS = 24
DUR = 298.0
NFR = int(round(DUR * FPS))
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/12-the-moon-is-leaving"
START = {'hook1': 1.0, 'hook2': 10.4, 'laser1': 24.5, 'laser2': 40.2, 'tide1': 60.5, 'tide2': 73.6, 'tide3': 87.9, 'day1': 96.6,
         'past1': 113.0, 'past2': 131.6, 'origin1': 145.2, 'origin2': 161.4, 'ecl1': 172.4, 'ecl2': 189.2, 'ecl3': 211.0,
         'fut1': 222.6, 'far1': 241.5, 'pay1': 261.5, 'pay2': 277.4, 'pay3': 283.8}
XF = 0.8
SHOTS = [("hook", 0.0, 23.6), ("reflector", 23.6, 39.6), ("obs", 39.6, 52.4), ("ret", 52.4, 59.6), ("tides", 59.6, 95.6),
         ("day", 95.6, 112.2), ("past", 112.2, 130.9), ("coral", 130.9, 144.4), ("origin", 144.4, 160.6), ("ancient", 160.6, 171.4),
         ("coin", 171.4, 188.6), ("eclipse", 188.6, 210.2), ("annular", 210.2, 221.8), ("future", 221.8, 240.4), ("far", 240.4, 260.4),
         ("window", 260.4, 276.6), ("leave", 276.6, 283.0), ("shadow", 283.0, 291.6), ("final", 291.6, DUR)]
