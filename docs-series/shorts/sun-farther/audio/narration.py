"""Narration for the Short "What If Earth Moved Farther from the Sun?" (REDO v3 storytelling style, BATCH3).
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [
    ("hook", "Imagine Earth...", 0.45),
    ("hook_2", "drifting away from the Sun.", 1.10),
    ("mars", "First... Mars's orbit.", 0.45),
    ("mars_2", "Less than half the sunlight.", 0.45),
    ("mars_3", "Winter... never ends.", 1.10),
    ("jup", "Now... Jupiter's orbit.", 0.45),
    ("jup_2", "The Sun shrinks... to a tiny disc.", 0.45),
    ("jup_3", "Noon... as dim as a stormy day.", 1.10),
    ("sat", "Saturn's orbit.", 0.40),
    ("sat_2", "{90×|Ninety times} dimmer.", 1.10),
    ("nep", "Then... Neptune.", 0.45),
    ("nep_2", "The Sun... is just a brilliant star.", 0.45),
    ("nep_3", "And the air itself... freezes into snow.", 1.15),
    ("oort", "Finally... the Oort cloud.", 0.45),
    ("oort_2", "Our Sun... just a bright star among many.", 1.15),
    ("end", "Come home...", 0.40),
    ("end_2", "little Earth.", 0.0),
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
    rep = {"90×": "90 times"}
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
