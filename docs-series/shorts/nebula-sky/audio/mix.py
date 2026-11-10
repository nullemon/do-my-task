"""Sound for "What If Famous Nebulas Were in Our Sky?": voice chain; a soft city-night bed (distant traffic hum);
a chord pad that changes key and colour with each nebula; a rushing riser as Orion flies in; whoosh + implosion sweep +
sub thump + bloom shimmer at every swap; the Crab pulsar as a real 30-per-second click train; the bed drains to a muffled
hush for the "eye view" ghost; a phone-shutter click + hit for the camera view; white-out riser and a deep hit back into
the normal night. Ducked under the voice, two-pass loudnorm to -14 LUFS / -1 dBTP, plus the SRT.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/nebula-sky.srt"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(S.DUR * SR); tt = np.arange(N) / SR

# chord per scene: (root Hz, intervals in semitones, brightness)
CHORDS = {"night": (110.0, (0, 7, 12, 14, 19), 0.25), "orion": (130.8, (0, 4, 7, 11, 14, 19), 0.8), "ring": (164.8, (0, 3, 7, 10, 14), 0.9),
          "pill": (98.0, (0, 7, 12, 15, 19, 22), 0.6), "crab": (146.8, (0, 5, 7, 12, 17), 0.75), "car": (87.3, (0, 4, 7, 11, 12, 16, 19), 1.0)}


def chord(root, iv, bright, seed):
    r = np.random.default_rng(seed); x = np.zeros((N, 2))
    for k, s in enumerate(iv):
        f = root * 2 ** (s / 12)
        a = (0.5 if k == 0 else 0.28) * (1 if f < 600 else bright)
        for c in range(2):
            det = 1 + r.uniform(-0.002, 0.002)
            x[:, c] += a * np.sin(2 * np.pi * f * det * tt + r.uniform(0, 6.28)) * (1 + 0.25 * np.sin(2 * np.pi * r.uniform(0.1, 0.3) * tt))
    air = np.stack([A.bp(r.standard_normal(N), 1500, 7000) for _ in range(2)], 1) * 0.05 * bright
    return (x + air) * 0.05


def whoosh(t1, dur=0.6, seed=0, gain=1.0):
    out = np.zeros((N, 2)); a, b = int((t1 - dur) * SR), int(t1 * SR); n = b - a
    r = np.random.default_rng(seed); u = np.linspace(0, 1, n)
    nz = A.bp(r.standard_normal(n), 400, 5000) * u ** 2.2
    out[a:b, 0] = nz * (1 - 0.6 * u); out[a:b, 1] = nz * (0.4 + 0.6 * u)
    f = 900 * (60 / 900) ** u; ph = 2 * np.pi * np.cumsum(f) / SR
    out[a:b] += (np.sin(ph) * u ** 1.5 * 0.35)[:, None]
    return out * gain


def bloom_swell(t0, seed, gain=0.4):
    sh = A.shimmer(N, t0, min(t0 + 1.6, S.DUR - 0.1), seed=seed, gain=1.0)
    return sh * A.env(N, [(0, 0), (t0, 0), (t0 + 0.05, 1), (t0 + 1.6, 0), (S.DUR, 0)])[:, None] * gain


def pulsar(t0, t1, gain):
    """Crab pulsar: 29.6 clicks per second (its real rotation rate), each a short damped knock"""
    out = np.zeros((N, 2)); n = int(0.012 * SR); k = np.arange(n) / SR
    clk = (np.sin(2 * np.pi * 1400 * k) * 0.6 + np.sin(2 * np.pi * 380 * k)) * np.exp(-k / 0.0025)
    tp = t0
    while tp < t1:
        a = int(tp * SR)
        if a + n < N: out[a:a + n] += clk[:, None]
        tp += 1 / 29.6
    return out * gain * A.env(N, [(0, 0), (t0, 0), (t0 + 0.4, 1), (t1 - 0.2, 1), (t1, 0), (S.DUR, 0)])[:, None]


def shutter(t0, gain=0.6):
    out = np.zeros((N, 2)); r = np.random.default_rng(77)
    for dt, g in ((0.0, 1.0), (0.055, 0.7)):
        a = int((t0 + dt) * SR); n = int(0.03 * SR); k = np.arange(n) / SR
        x = A.hp(r.standard_normal(n), 2500) * np.exp(-k / 0.006) + np.sin(2 * np.pi * 2200 * k) * np.exp(-k / 0.003) * 0.5
        out[a:a + n] += (x * g)[:, None]
    return out * gain


def main():
    voice = A.build_voice(S.PL, os.path.join(S.SCR, "vo"), N, OUT)
    seq = [(0.0, "night")] + [(ts, k) for ts, k in S.SWAPS]
    bed = np.zeros((N, 2))
    for i, (ts, k) in enumerate(seq):
        te = seq[i + 1][0] if i + 1 < len(seq) else S.DUR
        root, iv, br = CHORDS[k]
        if i == 0: e = A.env(N, [(0, 0), (0.4, 1), (te - 0.45, 1), (te - 0.05, 0), (S.DUR + 1, 0)])
        elif i == len(seq) - 1: e = A.env(N, [(0, 0), (ts, 0), (ts + 0.3, 1), (S.DUR - 0.4, 1), (S.DUR, 0)])
        else: e = A.env(N, [(0, 0), (max(ts - 0.05, 0), 0), (ts + 0.25, 1), (te - 0.45, 1), (te - 0.05, 0.0), (S.DUR + 1, 0)])
        bed += chord(root, iv, br, 10 + i) * e[:, None] * (1.3 if k == "car" else 1.0)
    # city ambience: distant traffic hum, always there
    r = np.random.default_rng(5)
    city = np.stack([A.bp(r.standard_normal(N), 70, 600) for _ in range(2)], 1) * (1 + 0.3 * np.sin(2 * np.pi * 0.07 * tt))[:, None]
    bed += city * 0.10
    # Orion rushes in
    bed += A.riser(N, S.T_RUSH0 - 0.2, S.T_RUSH1, seed=21) * 1.0
    bed += whoosh(S.T_RUSH1, 1.0, seed=22, gain=0.7)
    for i, (ts, k) in enumerate(S.SWAPS):
        if k not in ("orion", "night"): bed += whoosh(ts, 0.55, seed=40 + i, gain=0.55)
        bed += A.thump(N, ts, 0.9 if k not in ("car", "night") else 1.3)
        if k != "night": bed += bloom_swell(ts + 0.02, 50 + i, 0.45 if k == "car" else 0.32)
    # Crab pulsar
    bed += pulsar(S.T_SW["crab"] + 0.5, S.T_SW["car"] - 0.25, 0.10) + pulsar(S.T_PULSAR - 0.1, S.T_SW["car"] - 0.25, 0.10)
    # Carina: a big airy drone while we're inside it
    bed += A.drone(N, root=43.65, seed=64, bright=0.35) * 1.1 * A.env(N, [(0, 0), (S.T_SW["car"], 0), (S.T_SW["car"] + 0.6, 1), (S.T_BACK - 0.05, 1.2), (S.T_BACK, 0), (S.DUR, 0)])[:, None]
    # eye view: the bed drains to a hush (muffled), the camera view snaps it back
    hush = A.env(N, [(0, 1), (S.T_FAINT, 1), (S.T_FAINT + 0.45, 0.25), (S.T_CAM - 0.02, 0.25), (S.T_CAM + 0.03, 1), (S.DUR, 1)])
    bed = A.lp(bed, 900, 2) * (1 - hush)[:, None] * 0.6 + bed * hush[:, None]
    bed += shutter(S.T_CAM, 0.9) + A.hit(N, S.T_CAM + 0.02, gain=0.35, root=65.4)
    bed += A.shimmer(N, S.T_CAM, S.T_WO0, seed=71, gain=0.25)
    # white-out back to the normal night (loops)
    bed += A.riser(N, S.T_WO0 - 0.3, S.T_BACK, seed=65) * 1.2
    bed += A.hit(N, S.T_BACK, gain=0.5, root=55.0)
    bed = A.duck(bed, voice, depth=0.45)
    mix = voice * 1.0 + bed * 0.55
    mix *= np.clip((S.DUR - tt) / 0.4, 0, 1)[:, None] * np.clip(tt / 0.03, 0, 1)[:, None]
    raw = os.path.join(OUT, "mix_raw.wav")
    sf.write(raw, mix.astype(np.float32), SR, subtype="FLOAT")
    A.loudnorm(raw, os.path.join(OUT, "mix.wav"), -14.0, -1.0); os.remove(raw)
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    A.write_srt(os.path.join(HERE, "..", "out", "nebula-sky.srt"), S.PL, lambda k: pc[k])
    print("ok", S.DUR)


if __name__ == "__main__":
    main()
