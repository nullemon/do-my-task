"""Narration for the Short "The Biggest Explosions in the Universe, Seen From Earth" (BATCH4: REDO v3 storytelling
style, clean voice). Markup: {CAPTION|spoken words}. Each line: (key, text, pause_after_seconds)."""
import re

LINES = [
    ("hook", "Imagine the biggest explosions...", 0.50),
    ("hook_2", "in our sky.", 1.20),
    ("sn", "A supernova, a thousand light years away.", 0.50),
    ("sn_2", "A hundred times brighter than Venus.", 1.20),
    ("kn", "Two dead stars collide...", 0.50),
    ("kn_2", "forging gold.", 1.20),
    ("grb", "A gamma-ray burst...", 0.50),
    ("grb_2", "billions of light years away.", 0.50),
    ("grb_3", "A faint spark.", 1.20),
    ("mag", "A magnetar flare...", 0.50),
    ("mag_2", "brighter than the full Moon. In gamma rays.", 1.20),
    ("qso", "And a quasar.", 0.50),
    ("qso_2", "Now... at our galaxy's heart.", 1.20),
    ("qso_3", "Brighter than the Sun? No...", 0.50),
    ("qso_4", "almost a full Moon, in one tiny point.", 1.20),
    ("end", "Lucky us...", 0.50),
    ("end_2", "they're far away.", 0.0),
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
