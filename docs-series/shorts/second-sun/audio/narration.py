"""Narration for the Short "What If Earth Had a Second Sun?".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [
    ("hook", "What if Earth had a second Sun?", 0.65),
    ("acen", "Alpha Centauri: its orange partner outshines hundreds of full Moons.", 0.35),
    ("acen_2", "Some nights never get dark.", 0.65),
    ("sir", "Sirius: a blue-white blaze, and a white dwarf.", 0.35),
    ("sir_2", "A Sun's mass, the size of Earth.", 0.65),
    ("kep", "{KEPLER-16b|Kepler sixteen B}, a real planet with two suns.", 0.35),
    ("kep_2", "Double sunset. Double shadows.", 0.65),
    ("alg", "Algol, the Demon Star.", 0.35),
    ("alg_2", "Every {2.87|two point eight seven} days, one star eclipses the other.", 0.65),
    ("wuma", "{W|Double-U} Ursae Majoris. Two stars, touching.", 0.65),
    ("end", "Nearly half of Sun-like stars have a partner.", 0.35),
    ("end_2", "Ours is single.", 0.0),
]

TOK = re.compile(r"\{([^|}]*)\|([^}]*)\}([.,?!]*)|(\S+)")


def tokens(text):
    """-> list of (caption, [spoken words]) in order"""
    out = []
    for m in TOK.finditer(text):
        if m.group(4):
            w = m.group(4)
            out.append((w, [w]))
        else:
            ws = m.group(2).split(); ws[-1] += m.group(3)
            out.append((m.group(1), ws))
    return out


def spoken(text):
    return " ".join(w for _, ws in tokens(text) for w in ws)


def caption_word(w):
    """on-screen form of one spoken word: upper case, without trailing punctuation"""
    w = w.strip()
    w = re.sub(r"[.,?!:;]+$", "", w)
    return w.upper()


def pieces(text):
    """subtitle strings aligned 1:1 with caption tokens (numbers kept as digits)"""
    rep = {}
    out = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]: out.append(cap)
        else:
            tail = re.findall(r"[.,?!]+$", ws[-1]); out.append(rep.get(cap, cap) + (tail[0] if tail else ""))
    return out


def subtitle(text): return " ".join(pieces(text))


if __name__ == "__main__":
    n = sum(len(spoken(t).split()) for _, t, _ in LINES)
    print("words:", n)
    for k, t, _ in LINES: print(k, "|", subtitle(t))
