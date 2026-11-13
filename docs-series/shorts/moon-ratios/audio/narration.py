"""Narration for the Short "What If Our Moon Was as Big as Other Moons Are to Their Planets?".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds). Voice: am_michael @ 0.92; ~0.35 s between sentences, ~0.7 s at beats."""
import re

LINES = [
    ("hook", "Our Moon is huge compared to Earth.", 0.35),
    ("hook_b", "But what if it matched other moons?", 0.70),
    ("moon", "Today, it's {27%|twenty-seven percent} of Earth's width.", 0.70),
    ("pho", "Match Phobos and Mars: {42 KM|forty-two kilometers.}", 0.35),
    ("pho_b", "Barely visible.", 0.70),
    ("gan", "Ganymede and Jupiter: a tiny dot.", 0.70),
    ("tit", "Titan and Saturn: a little orange spark.", 0.70),
    ("tri", "Triton and Neptune: still {5×|five times} smaller.", 0.70),
    ("cha", "But {CHARON|Sharon} is half as wide as Pluto.", 0.35),
    ("cha_b", "Nearly twice our Moon.", 0.35),
    ("cha_c", "A double world.", 0.70),
    ("end", "Pluto's a dwarf planet.", 0.35),
    ("end_b", "Of all the planets, ours has the biggest moon for its size.", 0.0),
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
    rep = {"27%": "27 percent", "CHARON": "Charon", "42 KM": "42 kilometers", "5×": "five times"}
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
