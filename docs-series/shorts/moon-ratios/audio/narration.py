"""Narration for the Short "What If Our Moon Was as Big as Other Moons Are to Their Planets?".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds). Voice (REDO v3): 0.7 am_michael + 0.3 am_onyx @ 0.86; 0.45-0.5 s between phrases, 1.0-1.2 s at beats."""
import re

LINES = [
    ("hook", "Imagine our Moon...", 0.50),
    ("hook_b", "sized like other moons... to their planets.", 1.10),
    ("moon", "Today, it's over a quarter of Earth's width.", 1.10),
    ("pho", "First... Phobos.", 0.45),
    ("pho_b", "{42 KM|Forty-two kilometers.}", 0.45),
    ("pho_c", "Barely visible.", 1.10),
    ("gan", "Ganymede...", 0.45),
    ("gan_b", "a tiny dot.", 1.00),
    ("tit", "Titan...", 0.45),
    ("tit_b", "a little orange spark.", 1.00),
    ("tri", "Triton...", 0.45),
    ("tri_b", "still {5×|five times} smaller.", 1.20),
    ("cha", "And then... {CHARON|Sharon}.", 0.50),
    ("cha_b", "Half as wide as Pluto.", 0.45),
    ("cha_c", "Our Moon... nearly twice as big.", 0.50),
    ("cha_d", "A double world.", 1.20),
    ("end", "But Pluto's a dwarf planet...", 0.50),
    ("end_b", "Of all the real planets...", 0.45),
    ("end_c", "ours has the biggest moon for its size.", 0.0),
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
    rep = {"CHARON": "Charon", "42 KM": "42 kilometers", "5×": "five times"}
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
