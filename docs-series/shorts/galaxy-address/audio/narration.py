"""Narration for the Short "What If Earth Were Somewhere Else in the Galaxy?" (BATCH3, REDO v3 storytelling style).
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words.
Each line: (key, text, pause_after_seconds). Pauses: ~0.45 s between phrases, 1.0-1.2 s before each reveal."""
import re

LINES = [
    ("hook", "Imagine moving Earth...", 0.45),
    ("hook2", "to a new address in the galaxy.", 1.15),
    ("gc", "First... the galactic {CENTRE.|center.}", 0.45),
    ("gc2", "Millions of stars crowd the sky.", 0.45),
    ("gc3", "Night never gets dark.", 1.15),
    ("arm", "Now... a stellar nursery.", 0.45),
    ("arm2", "Glowing clouds... and newborn blue stars.", 1.15),
    ("halo", "Then... we rise above the disk.", 0.45),
    ("halo2", "{30,000|Thirty thousand} light-years up...", 0.45),
    ("halo3", "the whole Milky Way... hangs over us.", 1.15),
    ("void", "And now... the {BOÖTES|Bo-oh-tees} Void.", 0.45),
    ("void2", "No stars at all.", 0.45),
    ("void3", "Just a few faint galaxies... far away.", 1.15),
    ("end", "Back home...", 0.45),
    ("end2", "we got a pretty good seat.", 0.0),
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
    rep = {"CENTRE.": "centre.", "BOÖTES": "Boötes"}
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
