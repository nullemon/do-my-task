"""Narration for the Short "What If You Could See Dark Matter?" (BATCH4: REDO v3 storytelling style, clean mix).
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words.
Each line: (key, text, pause_after_seconds). Pauses: 0.45 s between phrases, 1.15 s before each reveal."""
import re

LINES = [
    ("hook", "What if you could see... dark matter?", 0.50),
    ("hook2", "Tonight... just the Milky Way.", 1.15),
    ("halo", "Now... a ghostly glow swallows the galaxy.", 0.45),
    ("halo2", "{5×|Five times} more of it... than all the atoms in the universe.", 1.15),
    ("clumps", "And it's lumpy.", 0.45),
    ("clumps2", "Thousands of dark clumps... drifting around us.", 1.15),
    ("web", "And then... the cosmic web.", 0.45),
    ("web2", "Giant threads... stretching across the whole sky.", 1.15),
    ("stream", "The strangest part?", 0.50),
    ("stream2", "It's flowing through you... right now.", 0.45),
    ("stream3", "Maybe billions of particles... every second.", 1.15),
    ("end", "Blink...", 0.45),
    ("end2", "It's gone. But it never left.", 0.0),
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
    """subtitle strings aligned 1:1 with caption tokens"""
    rep = {"5×": "Five times"}
    out = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]: out.append(cap)
        else:
            tail = re.findall(r"[.,?!]+$", ws[-1]); c = rep.get(cap, cap)
            out.append(c if c.endswith(tuple(".,?!")) else c + (tail[0] if tail else ""))
    return out


if __name__ == "__main__":
    print("words:", sum(len(spoken(t).split()) for _, t, _ in LINES))
    for k, t, _ in LINES: print(k, "|", " ".join(pieces(t)))
