"""Narration for the Short "What If the Moon Got Closer?".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [
    ("hook", "What if the Moon got closer? Much closer?", 0.15),
    ("today", "Here's today's Moon, for scale.", 0.20),
    ("d200", "{200,000|Two hundred thousand} kilometers: twice as wide, tides {7×|seven times} stronger.", 0.15),
    ("d100", "{100,000|A hundred thousand:} {57×|fifty-seven times.} Oceans surge inland.", 0.15),
    ("d50", "{50,000|Fifty thousand:} {450×|four hundred fifty times.} Quakes, volcanoes, and every crater in sharp detail.", 0.15),
    ("d20", "{20,000|Twenty thousand.} Tides kilometers high. Moonlight hundreds of times brighter.", 0.20),
    ("roche", "{18,000|Eighteen thousand:} the {ROCHE|Roshe} limit. Earth's gravity rips the Moon into a ring.", 1.70),
    ("end", "In reality, it's drifting away: {3.8 CM|three point eight centimeters} a year.", 0.0),
]

TOK = re.compile(r"\{([^|}]*)\|([^}]*)\}([.,?!:]*)|(\S+)")


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
    rep = {"7×": "7 times", "57×": "57 times", "450×": "450 times", "3.8 CM": "3.8 centimeters", "ROCHE": "Roche"}
    out = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]: out.append(cap)
        else:
            tail = re.findall(r"[.,?!:]+$", ws[-1]); c = rep.get(cap, cap)
            out.append(c + (tail[0] if tail and not c.endswith(tail[0]) else ""))
    return out


def subtitle(text): return " ".join(pieces(text))


if __name__ == "__main__":
    n = sum(len(spoken(t).split()) for _, t, _ in LINES)
    print("words:", n)
    for k, t, _ in LINES: print(k, "|", subtitle(t)); print("   ", spoken(t))
