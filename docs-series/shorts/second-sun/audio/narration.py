"""Narration for the Short "What If Earth Had a Second Sun?".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [
    ("hook", "Imagine...", 0.50),
    ("hook_2", "a second Sun.", 1.10),
    ("acen", "Alpha Centauri.", 0.50),
    ("acen_2", "Its orange partner outshines hundreds of full Moons.", 0.50),
    ("acen_3", "Some nights... never get dark.", 1.10),
    ("sir", "Now... Sirius.", 0.50),
    ("sir_2", "A blue-white blaze... and a white dwarf.", 0.45),
    ("sir_3", "A Sun's mass... the size of Earth.", 1.10),
    ("kep", "And then... {KEPLER-16b|Kepler sixteen B}.", 0.50),
    ("kep_2", "Double sunset... double shadows.", 1.10),
    ("alg", "Algol... the Demon Star.", 0.45),
    ("alg_2", "Every three days... one star eclipses the other.", 1.10),
    ("wuma", "{W|Double-U} Ursae Majoris.", 0.45),
    ("wuma_2", "Two stars... touching.", 1.10),
    ("end", "Nearly half of Sun-like stars have a partner.", 0.50),
    ("end_2", "Ours...", 0.45),
    ("end_3", "is alone.", 0.0),
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
