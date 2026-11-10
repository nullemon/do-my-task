"""Narration for the Short "What If Planets Replaced Our Moon?".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [
    ("hook", "What if planets replaced our Moon? Same distance, true size.", 0.20),
    ("moon", "Here's our Moon, for scale.", 0.25),
    ("mars", "Mars. Twice as wide, a rusty red lantern.", 0.25),
    ("nep", "Neptune. {14×|Fourteen times} wider, a deep blue world.", 0.25),
    ("ura", "Uranus, tipped on its side, wearing faint rings.", 0.25),
    ("sat", "Saturn. Its rings stretch {40°|forty degrees} across the sky.", 0.30),
    ("jup", "And Jupiter. {41×|Forty-one times} wider than the Moon, bright enough to light the whole valley, with its own moons beside it.", 0.30),
    ("tide", "Of course, Jupiter would tear Earth apart. But what a view.", 0.35),
    ("end", "Suddenly, our Moon seems... cosy.", 0.0),
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


def pieces(text):
    """subtitle strings aligned 1:1 with caption tokens (numbers kept as digits)"""
    rep = {"14×": "14 times", "40°": "40 degrees", "41×": "41 times"}
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
