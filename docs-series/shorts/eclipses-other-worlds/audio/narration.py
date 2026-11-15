"""Narration for the Short "What Eclipses Look Like on Other Worlds".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words.
Each line: (key, text, pause_after_seconds). REDO v3 storytelling style (0.7 am_michael + 0.3 am_onyx @ 0.86)."""
import re

LINES = [
    ("hook", "Imagine standing here...", 0.45),
    ("hook_b", "watching the Sun go dark.", 1.05),
    ("earth", "On Earth... the Moon slides in.", 0.45),
    ("earth_b", "A perfect fit.", 1.10),
    ("mars", "On Mars... Phobos.", 0.45),
    ("mars_b", "Too small to cover the Sun...", 0.40),
    ("mars_c", "just a bite.", 1.05),
    ("moon", "From the Moon...", 0.40),
    ("moon_b", "Earth blocks the Sun.", 0.45),
    ("moon_c", "Its edge glows red...", 0.40),
    ("moon_d", "every sunrise and sunset, at once.", 1.10),
    ("io", "From Io...", 0.40),
    ("io_b", "Jupiter swallows the Sun whole.", 1.15),
    ("sat", "And behind Saturn...", 0.45),
    ("sat_b", "the rings light up.", 0.50),
    ("sat_c", "That tiny dot?", 0.50),
    ("sat_d", "That's us.", 1.15),
    ("end", "Somewhere in that dot...", 0.45),
    ("end_b", "is this beach.", 0.0),
]

TOK = re.compile(r"\{([^|}]*)\|([^}]*)\}([.,?!]*)|(\S+)")


def tokens(text):
    out = []
    for m in TOK.finditer(text):
        if m.group(4): out.append((m.group(4), [m.group(4)]))
        else:
            ws = m.group(2).split(); ws[-1] += m.group(3); out.append((m.group(1), ws))
    return out


def spoken(text): return " ".join(w for _, ws in tokens(text) for w in ws)


def pieces(text):
    out = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]: out.append(cap)
        else:
            tail = re.findall(r"[.,?!]+$", ws[-1]); out.append(cap + (tail[0] if tail else ""))
    return out


def subtitle(text): return " ".join(pieces(text))


if __name__ == "__main__":
    print("words:", sum(len(spoken(t).split()) for _, t, _ in LINES))
    for k, t, _ in LINES: print(k, "|", subtitle(t))
