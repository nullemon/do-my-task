"""Narration for the Short "What If Other Moons Replaced Our Moon?".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [   # REDO v3 storytelling script: 0.7 am_michael + 0.3 am_onyx @ 0.86
    ("hook", "Imagine our Moon...", 0.50),
    ("hook_b", "swapped for other moons.", 0.45),
    ("hook_c", "Same distance... true size.", 1.00),
    ("moon", "Here's ours, for scale.", 1.00),
    ("pho", "First... Mars's moon, Phobos.", 0.50),
    ("pho_b", "Where did it go?", 0.50),
    ("pho_c", "That tiny speck.", 1.00),
    ("eur", "Europa...", 0.40),
    ("eur_b", "a cracked ball of ice.", 1.00),
    ("io", "Io...", 0.40),
    ("io_b", "covered in erupting volcanoes.", 1.00),
    ("tit", "Titan...", 0.40),
    ("tit_b", "{1.5×|one and a half times} wider... wrapped in haze.", 1.00),
    ("gan", "Then... Ganymede.", 0.45),
    ("gan_b", "The biggest moon in the solar system...", 0.40),
    ("gan_c", "wider than Mercury.", 1.00),
    ("all", "Now... all of them, at once.", 1.40),
    ("end", "And yet...", 0.50),
    ("end_b", "compared to its planet...", 0.45),
    ("end_c", "ours beats them all.", 0.0),
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
    rep = {"1.5×": "1.5 times"}
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
