"""Narration for the Short "What If Earth Moved Closer to the Sun?" (REDO v3 storytelling style, BATCH3).
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [
    ("hook", "Imagine Earth...", 0.45),
    ("hook_2", "drifting closer to the Sun.", 1.10),
    ("ven", "First... Venus's orbit.", 0.45),
    ("ven_2", "Almost {2×|twice} the sunlight.", 0.45),
    ("ven_3", "The oceans begin to boil.", 1.10),
    ("mer", "Now... Mercury's orbit.", 0.45),
    ("mer_2", "{~7×|Nearly seven times} the light.", 0.45),
    ("mer_3", "The rocks... glow red.", 1.10),
    ("p01", "Closer still.", 0.45),
    ("p01_2", "{100×|A hundred times} the light.", 0.45),
    ("p01_3", "The sand... melts into glass.", 1.15),
    ("skim", "And then... we skim the Sun.", 0.45),
    ("skim_2", "{50×|Fifty times} wider than today.", 0.45),
    ("skim_3", "Hot Jupiters... really orbit this close.", 0.45),
    ("skim_4", "The desert... turns to lava.", 1.15),
    ("end", "Turns out...", 0.40),
    ("end_2", "we're in just the right place.", 0.0),
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
    rep = {"2×": "twice", "~7×": "nearly 7 times", "100×": "100 times", "50×": "50 times"}
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
