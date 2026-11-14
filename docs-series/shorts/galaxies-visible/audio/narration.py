"""REDO v3 storytelling narration. Narration for the Short "What If Galaxies Were Bright Enough to See?".
Premise: galaxies at their REAL angular size and place; only their surface brightness is raised to camera level.
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [   # REDO v3 storytelling (0.7 am_michael + 0.3 am_onyx @ 0.86): ~0.45 s between phrases, 1.0-1.1 s at beat changes
    ("hook", "Imagine a galaxy...", 0.45),
    ("hook2", "{6×|six times} wider than the Moon.", 0.50),
    ("hook3", "It's up there right now.", 0.45),
    ("hook4", "You just can't see it.", 1.10),
    ("m31a", "But what if... your eyes could?", 1.10),
    ("m31", "Andromeda.", 0.45),
    ("m31b", "A trillion stars.", 1.10),
    ("m33", "Then... Triangulum.", 0.45),
    ("m33b", "A whole spiral... seen face-on.", 1.00),
    ("mc", "Now... the Magellanic Clouds.", 0.45),
    ("mc2", "The large one... {20|twenty} full Moons wide.", 1.10),
    ("m51", "And the Whirlpool...", 0.45),
    ("m51b", "tiny... a third of the Moon.", 1.10),
    ("end", "They're all up there...", 0.45),
    ("end2", "this big.", 1.10),
    ("end3", "Their light is just spread too thin...", 0.45),
    ("end4", "for your eyes to see.", 0.0),
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
    rep = {"6×": "6 times"}
    out = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]: out.append(cap)
        else:
            tail = re.findall(r"[.,?!]+$", ws[-1]); out.append(rep.get(cap, cap) + (tail[0] if tail else ""))
    return out


if __name__ == "__main__":
    print("words:", sum(len(spoken(t).split()) for _, t, _ in LINES))
    for k, t, _ in LINES: print(k, "|", " ".join(pieces(t)))
