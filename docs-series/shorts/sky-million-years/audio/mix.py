"""Sound for "Your Night Sky in 1 Million Years", locked to the picture timeline in short.py:
 - music: a dark-to-bright evolving pad (Dm - Bb - F - C ... - D) + a plucked arpeggio whose rate follows the counter's
   speed (time accelerating = notes accelerating)
 - a clock tick that speeds up with log(years per second); a wind/whoosh bed and rising tone that follow the speed too
 - riser + hit as the fast-forward starts; a Doppler pass-by for Barnard's Star
 - chimes on the labels; rubber-band twang + crack on every line snap
 - whooshes for the three sky sweeps; a long riser into Gliese 710 + a big hit and shimmer on "blazing"
 - a reverse-tape rewind sweep, then a bright hit + shimmer as the sky snaps back to 2026 (loop)
Voice chain, ducking, -14 LUFS / -1 dBTP and the SRT come from lib/audio.py.
Run: /home/user/ttsenv/bin/python audio/mix.py  -> SCR/audio/mix.wav, ../out/sky-million-years.srt"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, os.path.join(HERE, ".."), os.path.join(HERE, "..", "..")]
import numpy as np, soundfile as sf
import short as S
from narration import LINES, pieces
from lib import audio as A

OUT = os.path.join(S.SCR, "audio"); os.makedirs(OUT, exist_ok=True)
SR = A.SR; N = int(round(S.DUR * SR)); t = np.arange(N) / SR
R = np.random.default_rng(1001)
NOTE = lambda m: 440.0 * 2 ** ((m - 69) / 12)

# years-per-second curve of the counter (sampled at 100 Hz)
TS = np.arange(0, S.DUR + 0.01, 0.01)
SPD = np.array([abs(S.E_of(x + 0.02) - S.E_of(x - 0.02)) / 0.04 for x in TS])
LS = np.clip(np.log10(1 + SPD) / 6.0, 0, 1)                    # 0 (frozen) .. 1 (~1e6 yr/s)
def ls_at(x): return np.interp(x, TS, LS)


def at(x, t0):
    out = np.zeros((N, 2)); a = int(t0 * SR); n = min(len(x), N - a)
    if n > 0 and a >= 0: out[a:a + n] = x[:n]
    return out


def pan2(x, p): return np.stack([x * (1 - p), x * p], 1) * 2 ** 0.5


CH = {"Dm": (38, 50, 57, 62, 65, 69), "Bb": (34, 46, 53, 58, 62, 65), "F": (41, 53, 57, 60, 65, 69), "C": (36, 48, 55, 60, 64, 67),
      "Gm": (43, 50, 55, 58, 62, 67), "A": (45, 52, 57, 61, 64, 69), "D": (38, 50, 57, 62, 66, 69)}
SEQ = [("Dm", 0.0), ("Bb", S.T_FF0), ("F", S.LN["dip"]["start"]), ("C", S.LN["dip"]["start"] + 4.5), ("Gm", S.T_BROKEN),
       ("Bb", S.T_SW2), ("C", S.T_APART), ("F", S.T_SW3), ("A", S.wt("gj", "SKIMS")), ("D", S.wt("gj", "BLAZING")),
       ("Bb", S.LN["end"]["start"]), ("A", S.T_RW0), ("Dm", S.T_RW1)]


def chord_at(x):
    c = SEQ[0][0]
    for k, t0 in SEQ:
        if x >= t0: c = k
    return CH[c]


def pad():
    out = np.zeros((N, 2))
    for i, (ch, t0) in enumerate(SEQ):
        t1 = SEQ[i + 1][1] if i + 1 < len(SEQ) else S.DUR + 1
        a, b = int(max(0, t0 - 0.4) * SR), min(N, int((t1 + 0.8) * SR))
        if b <= a: continue
        tt = np.arange(b - a) / SR
        xf = np.clip(tt / 0.6, 0, 1) * np.clip(((b - a) / SR - tt) / 0.8, 0, 1)
        if i == 0: xf = np.clip(((b - a) / SR - tt) / 0.8, 0, 1)
        seg = np.zeros((b - a, 2))
        for j, m in enumerate(CH[ch]):
            f = NOTE(m)
            for c in range(2):
                det = 1 + (0.003 if c else -0.003) * (1 + j % 2)
                v = sum(np.sin(2 * np.pi * f * det * k * tt + R.uniform(0, 6.28)) / k ** 1.4 for k in range(1, 6))
                seg[:, c] += v * (1.0 if j < 2 else 0.5) * (1 + 0.2 * np.sin(2 * np.pi * 0.21 * tt + j))
        out[a:b] += seg * xf[:, None]
    out = A.lp(out, 2400, 2) * 0.042
    return out * (0.85 + 0.5 * ls_at(t))[:, None]


def pluck(f, dur=0.45, bright=1.0):
    n = int(dur * SR); tt = np.arange(n) / SR
    x = sum((0.6 ** (k - 1)) * bright ** (k - 1) * np.sin(2 * np.pi * f * k * tt) * np.exp(-tt * (4 + 3 * k)) for k in range(1, 6))
    return x * (1 - np.exp(-tt / 0.002))


def arp():
    """plucked arpeggio; the step rate rises from 4/s to 16/s with the counter speed"""
    out = np.zeros((N, 2)); tt = 0.6; k = 0
    pat = (2, 3, 4, 5, 4, 3, 2, 4)
    while tt < S.DUR - 0.3:
        ch = chord_at(tt); m = ch[pat[k % 8] % len(ch)] + 12
        sp = ls_at(tt)
        g = 0.085 * (0.8 if k % 2 else 1.0) * (0.7 + 0.5 * sp)
        out += at(pan2(pluck(NOTE(m), 0.45, 0.8 + 0.3 * sp), 0.3 + 0.4 * ((k * 3) % 5) / 4), tt) * g
        tt += 1.0 / (4.0 + 12.0 * sp ** 1.3); k += 1
    return A.lp(out, 7000, 2)


def tick_track():
    """clock ticks; rate follows the counter speed, fades when frozen"""
    out = np.zeros((N, 2)); tt = S.T_FF0; k = 0
    tk = np.arange(int(0.03 * SR)) / SR
    click = (np.sin(2 * np.pi * 3000 * tk) * 0.6 + A.hp(R.standard_normal(len(tk)), 2000) * 0.5) * np.exp(-tk / 0.004)
    while tt < S.T_RW1:
        sp = ls_at(tt)
        if sp > 0.05:
            a = int(tt * SR); g = 0.10 * (0.8 if k % 2 else 1.0) * min(1, sp * 3)
            p = 0.62 if k % 2 else 0.38
            out[a:a + len(click), 0] += click * g * (1 - p) * 2; out[a:a + len(click), 1] += click * g * p * 2
        tt += 1.0 / (3.0 + 22.0 * sp ** 1.5); k += 1
    return out


def speed_bed():
    """wind + rising tone that follow log(years per second)"""
    g = A.lp(ls_at(t), 3, 1)
    nz = np.stack([R.standard_normal(N), R.standard_normal(N)], 1)
    lo = A.bp(nz, 200, 1100); hi = A.bp(nz, 1800, 7500)
    wind = (lo * 0.45 + hi * 0.30 * g[:, None]) * (g ** 1.5)[:, None] * 0.55
    f = 90 * 2 ** (g * 2.5); ph = 2 * np.pi * np.cumsum(f) / SR
    tone = (np.sin(ph) + 0.3 * np.sin(2 * ph)) * g ** 2 * 0.05
    return wind + np.stack([tone, tone], 1)


def chime(t0, root, big=1.0, p=0.5):
    n = int(2.2 * SR); tt = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * NOTE(root) * m * tt) * np.exp(-tt / d) for m, a, d in ((1, 1.0, 1.2), (2.0, 0.5, 0.8), (2.76, 0.35, 0.5), (4.07, 0.2, 0.3)))
    return at(pan2(x * (1 - np.exp(-tt / 0.002)) * 0.2 * big, p), t0)


def whoosh(t0, dur=0.8, g=0.3, f0=300, f1=5000, p0=0.2, p1=0.8):
    n = int(dur * SR); u = np.linspace(0, 1, n); x = R.standard_normal(n); y = np.zeros(n)
    for i in range(10):
        a, b = i * n // 10, (i + 1) * n // 10; fc = f0 * (f1 / f0) ** (i / 10)
        y[a:b] = A.bp(x, fc * 0.7, min(fc * 1.4, 20000))[a:b]
    e = np.sin(np.pi * u) ** 2; pn = p0 + (p1 - p0) * u
    return at(np.stack([y * e * (1 - pn), y * e * pn], 1) * g * 1.4, t0)


def passby(tc, dur=1.6, g=0.35):
    """Doppler pass-by: a bright tone gliding down + noise, panning left -> right, peaking at tc"""
    n = int(dur * SR); u = np.linspace(-1, 1, n)
    f = 900 * 2 ** (-0.9 * np.tanh(u * 3)); ph = 2 * np.pi * np.cumsum(f) / SR
    e = np.exp(-(u / 0.35) ** 2)
    x = (np.sin(ph) * 0.5 + np.sin(2 * ph) * 0.2) * e + A.bp(R.standard_normal(n), 600, 6000) * e * 0.6
    pn = 0.5 + 0.45 * np.tanh(u * 2)
    return at(np.stack([x * (1 - pn), x * pn], 1) * g * 1.4, tc - dur / 2)


def snap(t0, p=0.5, g=0.5):
    """rubber band: a low twang (pitch drops) + a sharp crack"""
    n = int(0.9 * SR); tt = np.arange(n) / SR
    f = 95 * (1 + 0.6 * np.exp(-tt / 0.05)); ph = 2 * np.pi * np.cumsum(f) / SR
    tw = (np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.25 * np.sin(3 * ph)) * np.exp(-tt / 0.22) * (1 + 0.4 * np.sin(2 * np.pi * 23 * tt))
    cr = A.hp(R.standard_normal(n), 1800) * np.exp(-tt / 0.012) * 1.4
    return at(pan2((tw * 0.6 + cr) * g, p), t0 - 0.01)


def rewind_sweep(t0, t1, g=0.5):
    """reverse-tape whirr: a chirping tone sweeping up fast + filtered noise, cut at t1"""
    a, b = int(t0 * SR), int(t1 * SR); n = b - a; u = np.linspace(0, 1, n)
    f = 200 * 2 ** (u ** 1.5 * 4.0); ph = 2 * np.pi * np.cumsum(f) / SR
    chirp = np.sign(np.sin(ph * 0.5)) * 0.15 + np.sin(ph) * 0.4
    nz = A.bp(R.standard_normal(n), 500, 9000) * 0.5
    x = (chirp + nz) * (0.3 + 0.7 * u ** 1.5)
    out = np.zeros((N, 2)); out[a:b] = np.stack([x * (0.5 + 0.4 * np.sin(u * 40)), x * (0.5 - 0.4 * np.sin(u * 40))], 1) * g
    return out


def main():
    voice = A.build_voice(S.PL, os.path.join(S.SCR, "vo"), N, OUT)
    fx = np.zeros((N, 2))
    # hook: Big Dipper lights up
    fx += chime(S.T_DIP_LBL, 81, 0.9, 0.4) + chime(S.T_DIP_LBL + 0.12, 88, 0.6, 0.6) + whoosh(S.T_DIP_LBL - 0.2, 0.6, 0.12, 2000, 9000)
    # fast-forward kicks in
    fx += A.riser(N, S.T_FF0 - 1.3, S.T_FF0 + 0.05, seed=4) * 0.45 + A.thump(N, S.T_FF0 + 0.05, 0.7) + A.hit(N, S.T_FF0 + 0.05, gain=0.22, root=36.7)
    # Barnard's Star
    tb = S.wt("ff", "BARNARD'S")
    fx += chime(tb, 84, 0.9, 0.7) + passby(S.wt("ff", "ACROSS") + 0.1, 1.8, 0.35)
    # Moving group, Dubhe, Alkaid
    fx += chime(S.wt("dip", "FIVE"), 76, 0.9, 0.35) + chime(S.wt("dip", "FIVE") + 0.1, 81, 0.7, 0.65)
    fx += chime(S.wt("dip", "DUBHE"), 74, 0.8, 0.7) + chime(S.wt("dip", "ALKAID"), 72, 0.8, 0.3)
    fx += A.riser(N, S.T_BROKEN - 1.6, S.T_BROKEN - 0.05, seed=6) * 0.30
    for (seg, ts), p in zip(S.SNAPS.items(), (0.65, 0.4, 0.3, 0.35, 0.7)):
        fx += snap(ts, p, 0.55)
    fx += A.thump(N, S.T_BROKEN - 0.05, 0.6)
    # sweeps
    for ts in (S.T_SW2, S.T_SW3, S.T_SW4):
        fx += whoosh(ts - 0.05, S.SWEEP + 0.2, 0.30, 250, 6000, 0.85, 0.15)
    fx += chime(S.T_SW2 + 0.7, 79, 0.8, 0.5) + chime(S.wt("orion", "SHOULDERS"), 83, 0.7, 0.4)
    fx += A.thump(N, S.T_APART - 0.05, 0.45)
    fx += chime(S.wt("orion", "STARS"), 86, 0.5, 0.3)
    # Gliese 710
    tg, tz = S.wt("gj", "GLIESE 710"), S.wt("gj", "BLAZING")
    fx += chime(tg, 77, 1.0, 0.5) + whoosh(tg - 0.1, 0.7, 0.18, 1500, 9000)
    fx += A.riser(N, S.T_SW3 + 0.6, tz, seed=8) * 0.55
    fx += A.hit(N, tz, gain=0.45, root=36.7) + A.thump(N, tz, 1.0) + A.shimmer(N, tz, min(tz + 3.0, S.DUR), seed=12, gain=0.16)
    # end: temporary -> rewind -> snap back to 2026
    fx += A.shimmer(N, S.LN["end"]["start"], S.T_RW0, seed=13, gain=0.06)
    fx += rewind_sweep(S.T_RW0 - 0.05, S.T_RW1, 0.35)
    fx += A.thump(N, S.T_RW1, 0.9) + chime(S.T_RW1, 81, 1.2, 0.5) + chime(S.T_RW1 + 0.06, 88, 0.8, 0.5)
    fx += A.shimmer(N, S.T_RW1, S.DUR, seed=14, gain=0.10)
    music = pad() * 1.5 + arp()
    bed = A.duck(music + speed_bed() + tick_track(), voice, depth=0.45) + A.duck(fx, voice, depth=0.2)
    mix = voice * 1.0 + bed * 0.75
    mix *= np.clip((S.DUR - t) / 0.15, 0, 1)[:, None] * np.clip(t / 0.03, 0, 1)[:, None]
    raw = os.path.join(OUT, "mix_raw.wav")
    sf.write(raw, mix.astype(np.float32), SR, subtype="FLOAT")
    A.loudnorm(raw, os.path.join(OUT, "mix.wav"), -14.0, -1.0); os.remove(raw)
    import subprocess                                       # loudnorm can leave ~-0.7 dBTP: oversampled limiter to <= -1.4
    lim = os.path.join(OUT, "mix_l.wav")
    subprocess.run(["nice", "-n", "10", "ffmpeg", "-v", "error", "-y", "-i", os.path.join(OUT, "mix.wav"), "-af",
                    "aresample=192000,alimiter=limit=0.84:attack=1:release=50:level=false,aresample=48000",
                    "-c:a", "pcm_f32le", lim], check=True)
    os.replace(lim, os.path.join(OUT, "mix.wav"))
    pc = {k: pieces(txt) for k, txt, _ in LINES}
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    A.write_srt(os.path.join(HERE, "..", "out", "sky-million-years.srt"), S.PL, lambda k: pc[k], max_words=8)
    print("ok", S.DUR, N / SR)


if __name__ == "__main__":
    main()
