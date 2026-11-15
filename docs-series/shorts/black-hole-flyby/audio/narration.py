"""Narration for the Short "What If a Black Hole Passed Through the Solar System?" (BATCH4 clean sound).
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words.
Each line: (key, text, pause_after_seconds). Story style (REDO_V3), voice 0.7 am_michael + 0.3 am_onyx @ 0.86."""
import re

LINES = [
    ("hook", "What if a black hole...", 0.45),
    ("hook_b", "passed through the solar system?", 1.05),
    ("bh", "Ten times the Sun's mass...", 0.45),
    ("bh_b", "only sixty kilometres wide.", 0.45),
    ("bh_c", "You can't see it...", 0.45),
    ("bh_d", "but the stars behind it... bend.", 1.10),
    ("nep", "It crosses Neptune's orbit...", 0.45),
    ("nep_b", "and the planets wobble.", 1.10),
    ("sun", "It swings past the Sun...", 0.45),
    ("sun_b", "glowing faintly with stolen gas.", 1.10),
    ("earth", "And Earth's orbit...", 0.45),
    ("earth_b", "is stretched... or flung away.", 1.10),
    ("gone", "Then it's gone.", 1.10),
    ("end", "The odds are almost zero...", 0.45),
    ("end_b", "but our galaxy hides a hundred million of them.", 0.0),
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


if __name__ == "__main__":
    print("words:", sum(len(spoken(t).split()) for _, t, _ in LINES))
