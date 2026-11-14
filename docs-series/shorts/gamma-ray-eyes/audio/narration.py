"""Narration for the Short "If Your Eyes Saw Gamma Rays, the Moon Would Outshine the Sun".
Markup: {CAPTION|spoken words} shows CAPTION for the whole span of the spoken words. Each line: (key, text, pause_after_s).
Fact check (NASA Goddard / Fermi release, 15 Aug 2019): above ~31 MeV the Moon is brighter than the Sun in gamma rays
(cosmic rays hit the airless, unmagnetised lunar surface); above ~1 GeV the Sun is brighter. An on-screen factual label
gives the energy cut."""
import re

LINES = [   # REDO v3 storytelling script: 0.7 am_michael + 0.3 am_onyx @ 0.86
    ("hook", "Imagine your eyes saw gamma rays.", 0.50),
    ("hook_b", "The Moon would outshine the Sun.", 1.10),
    ("ir", "First... infrared eyes.", 0.45),
    ("ir_b", "Warm things glow... even the galaxy's dust.", 1.10),
    ("radio", "Radio eyes.", 0.45),
    ("radio_b", "The Sun dims...", 0.40),
    ("radio_c", "but the Milky Way roars.", 1.10),
    ("micro", "Microwave eyes.", 0.45),
    ("micro_b", "The whole sky glows... with the Big Bang's afterglow.", 1.20),
    ("gamma", "And then... gamma rays.", 0.50),
    ("gamma_b", "The quiet Sun... nearly vanishes.", 0.50),
    ("gamma_c", "Cosmic rays slam into the Moon...", 0.45),
    ("gamma_d", "and it blazes.", 1.10),
    ("fermi", "NASA's Fermi telescope confirmed it.", 1.10),
    ("end", "Your eyes...", 0.45),
    ("end_b", "see a tiny slice of the sky.", 0.0),
]

TOK = re.compile(r"\{([^|}]*)\|([^}]*)\}([.,?!]*)|(\S+)")


def tokens(text):
    out = []
    for m in TOK.finditer(text):
        if m.group(4): out.append((m.group(4), [m.group(4)]))
        else:
            ws = m.group(2).split(); ws[-1] += m.group(3); out.append((m.group(1), ws))
    return out


def spoken(text): return " ".join(w for _, ws in tokens(text) for w in ws)


def pieces(text):
    """subtitle strings aligned 1:1 with caption tokens"""
    out = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]: out.append(cap)
        else:
            tail = re.findall(r"[.,?!]+$", ws[-1]); out.append(cap + (tail[0] if tail else ""))
    return out


if __name__ == "__main__":
    print("words:", sum(len(spoken(t).split()) for _, t, _ in LINES))
    for k, t, _ in LINES: print(k, "|", " ".join(pieces(t)))
