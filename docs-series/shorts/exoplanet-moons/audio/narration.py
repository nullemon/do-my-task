"""Narration for the Short "What If Strange Exoplanets Replaced Our Moon?".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (names, numbers).
Each line: (key, text, pause_after_seconds)."""
import re

S_, B_ = 0.35, 0.70        # pause between sentences / at a beat change (voice rule, 13 Nov)
LINES = [
    ("hook", "What if the strangest planets ever found replaced our Moon?", B_),
    ("moon", "Same distance, true size.", S_),
    ("moon_b", "Here's our Moon.", B_),
    ("cnc", "{55 CANCRI e|Fifty-five Cancri E.}", S_),
    ("cnc_b", "{7×|Seven times} wider, likely an ocean of lava.", B_),
    ("hd", "{HD 189733 b|H D one eight nine seven three three B.}", S_),
    ("hd_b", "Cobalt blue, where it rains glass.", B_),
    ("wasp", "{WASP-12 b|Wasp twelve B.}", S_),
    ("wasp_b", "Stretched into an egg, as its star eats it.", B_),
    ("tres", "{TrES-2 b|Tress two B.}", S_),
    ("tres_b", "Darker than coal.", B_),
    ("kelt", "{KELT-9 b|Kelt nine B.}", S_),
    ("kelt_b", "The hottest planet known.", S_),
    ("kelt_c", "Hotter than most stars.", B_),
    ("end", "Our Moon? Kind of boring.", S_),
    ("end_b", "Thankfully.", 0.0),
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
