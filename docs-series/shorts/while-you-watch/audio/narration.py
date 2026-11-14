"""Narration for the Short "Everything That Happens in Space While You Watch This Short".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [   # REDO v3 storytelling script: 0.7 am_michael + 0.3 am_onyx @ 0.86
    ("hook", "Imagine sitting still...", 0.50),
    ("hook_b", "for the next {45|forty-five} seconds.", 1.20),
    ("orbit", "You'd still fly {1,000 KM|a thousand kilometers}...", 0.50),
    ("orbit_b", "around the Sun.", 1.20),
    ("sun", "Meanwhile... the Sun fuses {600 MILLION|six hundred million} {TONNES|tons} of hydrogen.", 0.50),
    ("sun_b", "Every second.", 1.20),
    ("dust", "Space dust rains down.", 1.15),
    ("gal", "Our solar system races around the galaxy...", 0.50),
    ("cmb", "and across the cosmos.", 1.20),
    ("stars", "Thousands of stars are born...", 0.50),
    ("sn", "and about {30|thirty} explode... every second.", 1.20),
    ("light", "The sunlight on your face...", 0.50),
    ("light_b", "left the Sun before you pressed play.", 1.20),
    ("end", "And you saw it all...", 0.60),
    ("end_b", "from right here.", 0.0),
]

TOK = re.compile(r"\{([^|}]*)\|([^}]*)\}([.,?!]*)|(\S+)")


def tokens(text):
    out = []
    for m in TOK.finditer(text):
        if m.group(4):
            w = m.group(4); out.append((w, [w]))
        else:
            ws = m.group(2).split(); ws[-1] += m.group(3); out.append((m.group(1), ws))
    return out


def spoken(text): return " ".join(w for _, ws in tokens(text) for w in ws)


REP = {"45": "45", "1,000 KM": "1,000 km", "30 KM": "30 km", "600 MILLION": "600 million", "TONNES": "tonnes",
       "½ KILO": "half a kilo", "230 KM": "230 km", "370": "370", "30": "30"}


def pieces(text):
    """subtitle strings aligned 1:1 with caption tokens"""
    out = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]: out.append(cap)
        else:
            tail = re.findall(r"[.,?!]+$", ws[-1]); out.append(REP.get(cap, cap) + (tail[0] if tail else ""))
    return out


def subtitle(text): return " ".join(pieces(text))


if __name__ == "__main__":
    print("words:", sum(len(spoken(t).split()) for _, t, _ in LINES))
    for k, t, _ in LINES: print(k, "|", subtitle(t))
