"""Narration for the Short "What If Betelgeuse Exploded Tonight?" (copied from ../other-suns).
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [
    ("hook", "What if Betelgeuse exploded tonight?", 0.30),
    ("neut", "First, a silent warning. Neutrinos arrive hours before the light, and detectors sound the alarm.", 0.30),
    ("boom", "Then Orion's shoulder ignites. One point, as bright as the Moon, casting sharp shadows.", 0.30),
    ("day", "Next morning, it's still there. Visible in daylight, for weeks.", 0.25),
    ("fade", "Over months, it fades from blue-white to orange-red. Orion loses its shoulder forever.", 0.25),
    ("safe", "And we're safe. It's far too distant to hurt us.", 0.30),
    ("twist", "Its light takes {550|five hundred fifty} years to get here. So it might already have happened. The light just hasn't reached us yet.", 0.0),
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
