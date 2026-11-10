"""Narration for the Short "Everything That Happens in Space While You Watch This Short".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [
    ("hook", "In the next {35|thirty-five} seconds, you'll travel over {1,000 KM|a thousand kilometers}. Without moving.", 0.30),
    ("orbit", "Earth carries you around the Sun at {30 KM|thirty kilometers} a second.", 0.20),
    ("sun", "The Sun fuses {600 MILLION|six hundred million} {TONNES|tons} of hydrogen. Every second.", 0.20),
    ("dust", "About {½ KILO|half a kilo} of space dust lands on Earth each second.", 0.20),
    ("gal", "The solar system circles the galaxy at {230 KM|two hundred thirty} a second, and crosses the cosmos at {370|three hundred seventy}.", 0.20),
    ("stars", "Across the universe, thousands of stars are born each second, and about {30|thirty} explode.", 0.25),
    ("light", "The sunlight on your face left the Sun before you pressed play.", 0.30),
    ("end", "And you watched it all from right here.", 0.0),
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


REP = {"35": "35", "1,000 KM": "1,000 km", "30 KM": "30 km", "600 MILLION": "600 million", "TONNES": "tonnes",
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
