#!/usr/bin/env python3
"""Generate config/sounds/ring.wav and chime.wav (16-bit mono 44.1 kHz, stdlib only).

    python tools/make_sounds.py            # writes config/sounds/
    python tools/make_sounds.py --out DIR

ring.wav  ~2 s telephone-style ring: two bursts of a fast trill between two tones,
          near full scale, meant to be looped until dismissed.
chime.wav ~0.8 s pleasant two-note "ding-dong" for normal alerts.
Output is deterministic, so re-running produces identical files.
"""

from __future__ import annotations

import argparse
import math
import struct
import wave
from pathlib import Path

RATE = 44100
FULL_SCALE = 32767


def _write(path: Path, samples: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = b"".join(struct.pack("<h", int(round(max(-1.0, min(1.0, s)) * FULL_SCALE))) for s in samples)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(frames)


def _envelope(i: int, n: int, fade: int) -> float:
    """Linear fade in/out over `fade` samples so bursts start and stop without clicks."""
    if i < fade:
        return i / fade
    if i > n - fade:
        return max(0.0, (n - i) / fade)
    return 1.0


def ring_samples(
    tones: tuple[float, float] = (1300.0, 1650.0),
    trill_hz: float = 20.0,
    pattern: tuple[tuple[float, float], ...] = ((0.55, 0.15), (0.55, 0.75)),
    peak: float = 0.95,
) -> list[float]:
    """Bursts of a trill alternating between two tones (like an electronic phone ringer).

    1.3-1.65 kHz is where small laptop speakers are loudest and the ear most sensitive.
    The oscillator phase runs continuously across tone switches, so there are no clicks.
    A little 3rd harmonic makes it cut through background noise.
    """
    out: list[float] = []
    fade = int(RATE * 0.006)
    switch_every = int(RATE / (2 * trill_hz))       # samples per tone segment
    phase = 0.0
    for on, off in pattern:
        n_on = int(RATE * on)
        for i in range(n_on):
            f = tones[(i // switch_every) % 2]
            phase += 2 * math.pi * f / RATE
            s = math.sin(phase) + 0.25 * math.sin(3 * phase)
            out.append(s * _envelope(i, n_on, fade))
        out.extend([0.0] * int(RATE * off))
    top = max(abs(s) for s in out) or 1.0
    return [peak * s / top for s in out]


def chime_samples(
    notes: tuple[tuple[float, float], ...] = ((1318.51, 0.0), (1046.50, 0.26)),   # E6 then C6
    length: float = 0.8,
    peak: float = 0.6,
) -> list[float]:
    """Two bell-like notes (decaying partials), overlapping slightly, with a short fade at the end."""
    n = int(RATE * length)
    out = [0.0] * n
    partials = ((1.0, 1.0), (2.0, 0.35), (3.0, 0.12))
    attack = int(RATE * 0.004)
    for freq, start in notes:
        s0 = int(RATE * start)
        for i in range(n - s0):
            t = i / RATE
            env = math.exp(-t * 6.0) * (min(1.0, i / attack) if attack else 1.0)
            v = sum(a * math.sin(2 * math.pi * freq * m * t) * math.exp(-t * 3.0 * (m - 1)) for m, a in partials)
            out[s0 + i] += env * v
    fade = int(RATE * 0.05)
    for i in range(fade):
        out[n - 1 - i] *= i / fade
    top = max(abs(s) for s in out) or 1.0
    return [peak * s / top for s in out]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent / "config" / "sounds")
    args = parser.parse_args(argv)
    for name, samples in (("ring.wav", ring_samples()), ("chime.wav", chime_samples())):
        path = args.out / name
        _write(path, samples)
        print(f"wrote {path} ({len(samples) / RATE:.2f} s, {path.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
