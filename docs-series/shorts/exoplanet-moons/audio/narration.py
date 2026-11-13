"""Narration for the Short "What If Strange Exoplanets Replaced Our Moon?".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (names, numbers).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [
    ("hook", "What if the strangest planets ever found replaced our Moon?", 0.12),
    ("moon", "Same distance, true size. Here's our Moon.", 0.15),
    ("cnc", "{55 CANCRI e|Fifty-five Cancri E.} {7×|Seven times} wider, likely a glowing ocean of lava.", 0.15),
    ("hd", "{HD 189733 b|H D one eight nine seven three three B.} {47×|Forty-seven times} wider. Cobalt blue, and it rains glass, sideways.", 0.15),
    ("wasp", "{WASP-12 b|Wasp twelve B.} Stretched into an egg, as its star slowly eats it.", 0.15),
    ("tres", "{TrES-2 b|Tress two B.} Darker than coal. A giant shadow, blotting out stars.", 0.15),
    ("kelt", "{KELT-9 b|Kelt nine B.} The hottest planet known. {4,300 °C|Forty-three hundred degrees,} hotter than most stars.", 0.25),
    ("end", "Our Moon? Kind of boring. Thankfully.", 0.0),
]

TOK = re.compile(r"\{([^|}]*)\|([^}]*)\}([.,?!]*)|(\S+)")
REP = {"55 CANCRI e": "55 Cancri e", "7×": "7 times", "HD 189733 b": "HD 189733 b", "47×": "47 times",
       "7,000 KM/H": "7,000 km/h", "WASP-12 b": "WASP-12 b", "TrES-2 b": "TrES-2 b", "KELT-9 b": "KELT-9 b",
       "4,300 °C": "4,300 °C"}


def tokens(text):
    """-> list of (caption, [spoken words]) in order"""
    out = []
    for m in TOK.finditer(text):
        if m.group(4):
            w = m.group(4); out.append((w, [w]))
        else:
            ws = m.group(2).split(); ws[-1] += m.group(3); out.append((m.group(1), ws))
    return out


def spoken(text):
    return " ".join(w for _, ws in tokens(text) for w in ws)


def pieces(text):
    """subtitle strings aligned 1:1 with caption tokens (numbers kept as digits)"""
    out = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]: out.append(cap)
        else:
            tail = re.findall(r"[.,?!]+$", ws[-1]); out.append(REP.get(cap, cap) + (tail[0] if tail else ""))
    return out


def subtitle(text): return " ".join(pieces(text))


if __name__ == "__main__":
    n = sum(len(spoken(t).split()) for _, t, _ in LINES)
    print("words:", n)
    for k, t, _ in LINES: print(k, "|", subtitle(t))
