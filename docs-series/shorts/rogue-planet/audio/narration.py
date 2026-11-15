"""Narration for the Short "What If a Rogue Planet Passed Earth?" (BATCH3 / REDO v3 storytelling voice).
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words.
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [   # 0.7 am_michael + 0.3 am_onyx @ 0.86
    ("hook", "What if a rogue planet... passed Earth?", 1.00),
    ("hook_b", "A Jupiter... with no star.", 1.10),
    ("nep", "Beyond Neptune... just a star, blinking out.", 1.00),
    ("mars", "At Mars's distance... a dark speck.", 1.10),
    ("moon", "Then... the Moon's distance.", 0.45),
    ("moon_b", "A dark disc... forty Moons wide.", 0.45),
    ("moon_c", "Glowing faintly... lightning in its clouds.", 1.10),
    ("close", "Closer...", 0.45),
    ("close_b", "The tides heave. The ground shakes.", 1.10),
    ("pass", "It passes...", 0.45),
    ("pass_b", "but our orbit could be thrown off.", 1.10),
    ("odds", "The odds are tiny...", 0.45),
    ("odds_b", "but rogue planets may outnumber the stars.", 1.10),
    ("end", "Somewhere out there... one is drifting.", 0.0),
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
