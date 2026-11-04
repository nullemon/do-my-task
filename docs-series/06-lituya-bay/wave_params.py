"""Per-frame camera crop + wave front for shot B1 (shared by wave.py and the compositor)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shots
from common import clamp_center, FPS
SCR = shots.SCR
t0, t1, _ = shots.SHOTS["B1"]
f0, f1 = shots.frames_of("B1")
wp, hp = 2880, 1620
class _P: pass
P = _P(); P.wp, P.hp = wp, hp
fr = []
for f in range(f0, f1):
    t = (f + 0.5) / FPS
    z, cx, cy = shots.move(P, t, t0, t1, 1.05, 1.14, (0.5, 0.55), (0.5, 0.5))
    cx, cy = clamp_center((hp, wp), z, cx, cy)
    tau = shots.B1_TAU0 + (t - t0) * shots.B1_RATE
    fr.append(dict(f=f, t=t, z=z, cx=cx, cy=cy, tau=tau, yf=shots.front_y_km(tau) * 1000.0))
json.dump(dict(wp=wp, hp=hp, frames=fr), open(os.path.join(SCR, "wave_params.json"), "w"))
print(len(fr), "frames", f0, f1)
