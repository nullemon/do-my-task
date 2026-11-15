"""Narration for the Short "What If the Moon Exploded?" (BATCH4 / REDO v3 storytelling style).
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words.
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [   # 0.7 am_michael + 0.3 am_onyx @ 0.86 (BATCH4: clean voice, no post chain)
    ("hook", "What if the Moon... exploded?", 1.10),
    ("moon", "There it is... calm over the lake.", 1.10),
    ("flash", "Then... a flash.", 0.45),
    ("crack", "It cracks... into glowing pieces.", 1.10),
    ("ring", "Over days... the pieces spread along its orbit...", 0.45),
    ("ring_b", "into a ring around Earth.", 1.10),
    ("rain", "But some pieces fall.", 0.45),
    ("rain_b", "Meteors streak across the sky... for years.", 0.45),
    ("rain_c", "A hard rain.", 1.20),
    ("final", "And then... a bright ring... arcing over us... for ages.", 0.50),
    ("tide", "No more eclipses... and gentler tides.", 1.20),
    ("end", "Look up tonight...", 0.50),
    ("end_b", "and be glad... it's still in one piece.", 0.0),
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
            tail = re.findall(r"[.,?!]+$", ws[-1]); out.append(rep.get(cap, cap) + (tail[0] if tail else ""))
    return out


if __name__ == "__main__":
    print("words:", sum(len(spoken(t).split()) for _, t, _ in LINES))
    for k, t, _ in LINES: print(k, "|", " ".join(pieces(t)))
