"""Narration for the Short "What If Galaxies Were Bright Enough to See?".
Premise: galaxies at their REAL angular size and place; only their surface brightness is raised to camera level.
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [   # pauses: ~0.35 s between sentences, ~0.7 s at each beat change (user rule, 13 Nov)
    ("hook", "There's a galaxy in our sky {6×|six times} wider than the Moon.", 0.35),
    ("hook2", "You just can't see it.", 0.7),
    ("m31a", "But what if your eyes could?", 0.35),
    ("m31", "Andromeda. A trillion stars.", 0.7),
    ("m33", "Triangulum. A face-on spiral, almost three million light-years out.", 0.7),
    ("mc", "The Magellanic Clouds. The large one spans {20|twenty} full Moons.", 0.7),
    ("m51", "The Whirlpool: tiny, a third of the Moon.", 0.7),
    ("end", "They're all up there right now, this big.", 0.35),
    ("end2", "Their light is just spread too thin.", 0.35),
    ("end3", "Your eyes aren't sensitive enough.", 0.0),
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
    rep = {"6×": "6 times"}
    out = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]: out.append(cap)
        else:
            tail = re.findall(r"[.,?!]+$", ws[-1]); out.append(rep.get(cap, cap) + (tail[0] if tail else ""))
    return out


if __name__ == "__main__":
    print("words:", sum(len(spoken(t).split()) for _, t, _ in LINES))
    for k, t, _ in LINES: print(k, "|", " ".join(pieces(t)))
