"""Narration for the Short "What If Other Moons Replaced Our Moon?".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [
    ("hook", "What if other moons replaced our Moon? Same distance, true size.", 0.20),
    ("moon", "Here's our Moon, for scale.", 0.25),
    ("pho", "Mars's moon Phobos. Where did it go? That speck. You'd barely see it.", 0.25),
    ("eur", "Europa. Slightly smaller, a cracked ball of ice.", 0.20),
    ("io", "Io. A little bigger, and covered in erupting volcanoes.", 0.20),
    ("tit", "Titan. {1.5×|One and a half times} wider, wrapped in thick orange haze.", 0.20),
    ("gan", "Ganymede. The biggest moon in the solar system, even wider than Mercury.", 0.30),
    ("all", "Now imagine all of them at once.", 1.60),
    ("end", "Still, compared to its planet, ours is the biggest moon of any planet.", 0.0),
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
