"""Narration for the Short "What If Earth Had a Second Sun?".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [
    ("hook", "What if Earth had a second Sun?", 0.20),
    ("acen", "Alpha Centauri: a golden sun, plus an orange one hundreds of times brighter than the full Moon. Some nights never get dark.", 0.20),
    ("sir", "Sirius: a blue-white blaze, plus a white dwarf: a Sun's mass, crushed to Earth's size.", 0.20),
    ("kep", "{KEPLER-16b|Kepler sixteen B}. A real planet with two suns. Double sunset, double shadows.", 0.20),
    ("alg", "Algol, the Demon Star. Every {2.87|two point eight seven} days, one star eclipses the other. Daylight fades.", 0.20),
    ("wuma", "And {W|Double-U} Ursae Majoris: two stars touching, sharing one atmosphere.", 0.25),
    ("end", "Nearly half of Sun-like stars have a partner. Ours is single.", 0.0),
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
