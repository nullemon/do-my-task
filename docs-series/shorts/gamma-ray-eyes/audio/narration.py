"""Narration for the Short "If Your Eyes Saw Gamma Rays, the Moon Would Outshine the Sun".
Markup: {CAPTION|spoken words} shows CAPTION for the whole span of the spoken words. Each line: (key, text, pause_after_s).
Fact check (NASA Goddard / Fermi release, 15 Aug 2019): above ~31 MeV the Moon is brighter than the Sun in gamma rays
(cosmic rays hit the airless, unmagnetised lunar surface); above ~1 GeV the Sun is brighter. An on-screen factual label
gives the energy cut."""
import re

LINES = [
    ("hook", "If your eyes could see gamma rays, the Moon would outshine the Sun.", 0.55),
    ("ir", "Infrared eyes. Anything warm glows, and the Milky Way's dust shines.", 0.45),
    ("radio", "Radio eyes. The Sun is just a modest disc, but the Milky Way blazes across the sky.", 0.45),
    ("micro", "Microwave eyes. The whole sky glows with light from the birth of the universe.", 0.55),
    ("gamma", "Gamma ray eyes. The quiet Sun nearly vanishes. But cosmic rays slam into the Moon, and it blazes.", 0.30),
    ("fermi", "NASA's Fermi telescope found the Moon outshines the Sun in gamma rays.", 0.60),
    ("end", "Your eyes only see a tiny slice of the sky.", 0.0),
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
