"""Numbers for "What If the Moon Had Rings?" (printed by: /home/user/ttsenv/bin/python science.py).
Saturn's main rings scaled by radius to the Moon; angular sizes at the mean Earth-Moon distance; Roche limit; the light
the rings would add at full Moon (ring I/F from Cassini/Voyager-era photometry, rounded)."""
import math

R_MOON, D_MOON = 1737.4, 384400.0                  # km
R_SAT = 60268.0                                    # Saturn's equatorial radius (km)
RINGS_KM = dict(C=(74658, 92000), B=(92000, 117580), CD=(117580, 122170), A=(122170, 136775))   # edges (km)
F_RING = 140180.0
OPEN_DEG = 26.7                                    # Saturn's maximum ring opening (its axial tilt), borrowed
IF = dict(C=0.10, B=0.50, CD=0.05, A=0.35)         # ring I/F near opposition (rounded, B ring brightest)
P_MOON = 0.12                                      # Moon's geometric albedo (full-Moon disc-averaged I/F)

def ang(r_km): return 2 * math.degrees(math.atan(r_km / D_MOON))
k_out = RINGS_KM["A"][1] / R_SAT
moon_deg = 2 * math.degrees(math.asin(R_MOON / D_MOON))
ring_deg = ang(k_out * R_MOON)
roche_ice = 2.44 * R_MOON * (3.34 / 0.92) ** (1 / 3)
hill = D_MOON * (0.0123 / 3) ** (1 / 3)
s = math.sin(math.radians(OPEN_DEG))
ring_light = sum(math.pi * ((b / R_SAT) ** 2 - (a / R_SAT) ** 2) * s * IF[k] for k, (a, b) in RINGS_KM.items())
moon_light = math.pi * 1.0 * P_MOON
# part of the rings hidden behind the Moon ~ the part of the Moon hidden behind the rings: they roughly cancel
GAIN = (moon_light + ring_light) / moon_light

if __name__ == "__main__":
    print(f"A-ring outer edge / Saturn radius = {k_out:.3f}  (F ring {F_RING / R_SAT:.3f})")
    print(f"Moon: {moon_deg:.3f} deg wide;  rings (A-ring edge x Moon radius = {k_out * R_MOON:,.0f} km): {ring_deg:.3f} deg across")
    print(f"ratio rings/Moon width = {ring_deg / moon_deg:.2f}")
    print(f"Roche limit for ice around the Moon (fluid) = {roche_ice:,.0f} km = {roche_ice / R_MOON:.2f} Moon radii (rings end at {k_out:.2f})")
    print(f"Moon's Hill sphere ~ {hill:,.0f} km = {hill / R_MOON:.0f} Moon radii")
    print(f"ring light / Moon light at full Moon, rings open {OPEN_DEG} deg = {ring_light / moon_light:.2f}; total moonlight x{GAIN:.1f}")
