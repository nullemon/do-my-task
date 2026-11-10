"""Narration for the Short "What If Other Stars Replaced Our Sun?".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [
    ("hook", "What if our Sun was replaced by other stars? Let's start small.", 0.25),
    ("prox", "Proxima Centauri. A red dwarf, {15%|fifteen percent} of the Sun's width. Noon turns to dim red dusk, and Earth freezes.", 0.25),
    ("sir", "Sirius. Not even twice as wide, but {25×|twenty-five times} brighter. Oceans boil.", 0.25),
    ("arc", "Arcturus, an orange giant. {25×|Twenty-five times} wider, covering {13°|thirteen degrees} of sky.", 0.25),
    ("rig", "Rigel, a blue supergiant, {79×|seventy-nine times} wider. Earth? Vaporized.", 0.25),
    ("bet", "And Betelgeuse? {700×|Seven hundred times} wider, reaching past Mars. We'd be inside the star.", 0.30),
    ("end", "Welcome back, Sun.", 0.0),
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
    rep = {"15%": "15%", "25×": "25 times", "13°": "13 degrees", "79×": "79 times", "700×": "700 times"}
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
