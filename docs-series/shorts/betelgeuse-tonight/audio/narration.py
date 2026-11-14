"""REDO v3 storytelling narration. Narration for the Short "What If Betelgeuse Exploded Tonight?" (copied from ../other-suns).
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [   # REDO v3 storytelling (0.7 am_michael + 0.3 am_onyx @ 0.86): ~0.45 s between phrases, 1.0-1.1 s at beat changes
    ("hook", "Imagine Betelgeuse...", 0.45),
    ("hook2", "exploding tonight.", 1.10),
    ("neut", "First... a silent warning.", 0.45),
    ("neut2", "Neutrinos arrive... hours before the light.", 0.45),
    ("neut3", "Detectors sound the alarm.", 1.10),
    ("boom", "And then...", 0.50),
    ("boom2", "Orion's shoulder ignites.", 0.50),
    ("boom3", "One point... as bright as the Moon,", 0.40),
    ("boom4", "casting sharp shadows.", 1.10),
    ("day", "Next morning...", 0.40),
    ("day2", "it's still there. In daylight.", 1.00),
    ("fade", "Over months... it fades away.", 0.45),
    ("fade2", "Orion loses its shoulder... forever.", 1.10),
    ("safe", "And we're safe...", 0.40),
    ("safe2", "it's far too distant.", 1.10),
    ("twist", "Its light... is {550|five hundred fifty} years old.", 1.00),
    ("twist2", "So... it might already have happened.", 0.0),
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
    rep = {"550": "550"}
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
