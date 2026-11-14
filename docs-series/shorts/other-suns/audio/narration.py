"""Narration for the Short "What If Other Stars Replaced Our Sun?".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [
    ("hook", "Imagine our Sun...", 0.50),
    ("hook_2", "replaced by another star.", 1.00),
    ("prox", "First... Proxima Centauri.", 0.45),
    ("prox_2", "A red dwarf. Noon turns to dim red dusk...", 0.40),
    ("prox_3", "and Earth freezes.", 1.00),
    ("sir", "Now... Sirius.", 0.40),
    ("sir_2", "Not even twice as wide... but {25×|twenty-five times} brighter.", 0.40),
    ("sir_3", "The oceans boil.", 1.00),
    ("arc", "Arcturus. An orange giant...", 0.45),
    ("arc_2", "covering {13°|thirteen degrees} of sky.", 1.00),
    ("rig", "And then... Rigel.", 0.40),
    ("rig_2", "A blue supergiant, {79×|seventy-nine times} wider.", 0.50),
    ("rig_3", "Earth... vaporized.", 1.00),
    ("bet", "Finally... Betelgeuse.", 0.40),
    ("bet_2", "So big... it would reach past Mars.", 0.45),
    ("bet_3", "We'd be inside the star.", 1.10),
    ("end", "Welcome back...", 0.35),
    ("end_2", "little Sun.", 0.0),
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
