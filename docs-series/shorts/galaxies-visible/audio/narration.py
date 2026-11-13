"""Narration for the Short "What If Galaxies Were Bright Enough to See?".
Premise: galaxies at their REAL angular size and place; only their surface brightness is raised to camera level.
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [
    ("hook", "There's a galaxy in our sky {6×|six times} wider than the full Moon. You just can't see it.", 0.25),
    ("m31", "But what if your eyes could? Andromeda. A trillion stars, {2.5|two and a half} million light-years away.", 0.25),
    ("m33", "Triangulum, a face-on spiral, almost three million light-years out.", 0.2),
    ("mc", "Down south, the Magellanic Clouds. The large one spans {20|twenty} full Moons, its Tarantula Nebula glowing pink.", 0.2),
    ("m51", "The Whirlpool is tiny, a third of the Moon, {30|thirty} million light-years away.", 0.25),
    ("end", "They're all up there right now, this big. Their light is just spread too thin. Your eyes aren't sensitive enough.", 0.0),
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
