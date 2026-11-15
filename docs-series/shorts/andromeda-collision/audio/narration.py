"""Narration for the Short "The Night Andromeda Hits Us" (BATCH3, REDO v3 storytelling style).
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words.
Each line: (key, text, pause_after_seconds). Pauses: ~0.45 s between phrases, 1.0-1.2 s before each reveal."""
import re

LINES = [
    ("hook", "See that faint smudge?", 0.45),
    ("hook2", "That's Andromeda... {6|six} full Moons wide.", 0.45),
    ("hook3", "And it's heading our way.", 1.15),
    ("g2", "Two billion years from now...", 0.45),
    ("g2b", "it's {10|ten} full Moons wide.", 1.15),
    ("g3", "Then... it looms across the sky.", 1.15),
    ("g4", "And the galaxies may collide.", 0.45),
    ("g4b", "Gas crashes together... new stars ignite everywhere.", 0.45),
    ("g4c", "But the stars themselves... almost never hit.", 1.15),
    ("g5", "Finally... one giant galaxy. Milkomeda.", 0.45),
    ("g5b", "By then... our Sun will be dying.", 1.15),
    ("end", "Will it really happen?", 0.45),
    ("end2", "New studies say... it's a coin flip.", 0.0),
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
    rep = {}
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
