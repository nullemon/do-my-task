"""Narration for the Short "The Dinosaur-Killer Asteroid, Seen From the Ground" (Chicxulub, 66 Myr ago).
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds). The global-firestorm idea is hedged ("maybe")."""
import re

LINES = [
    ("hook", "What if you saw the dinosaur-killer asteroid hit, from {1,000 KM|a thousand kilometers} away?", 0.20),
    ("appr", "A new star appears. {10 KM|Ten kilometers} wide, at {20 KM/S|twenty kilometers a second}.", 0.20),
    ("hit", "It strikes beyond the horizon. A flash brighter than the Sun. A fireball climbs into space.", 0.25),
    ("quake", "Minutes later, the ground heaves. Magnitude ten.", 0.20),
    ("ejecta", "Molten debris rains back from space. The sky glows red-hot, maybe hot enough to ignite forests.", 0.25),
    ("blast", "An hour in, the blast wave hits. Then soot blocks the Sun for years. Three quarters of all species vanish.", 0.45),
    ("end", "And the asteroid that wiped out the dinosaurs... is why we're here.", 0.0),
]

TOK = re.compile(r"\{([^|}]*)\|([^}]*)\}([.,?!:]*)|(\S+)")


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
    rep = {"1,000 KM": "1,000 km", "10 KM": "10 km", "20 KM/S": "20 km per second"}
    out = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]: out.append(cap)
        else:
            tail = re.findall(r"[.,?!:]+$", ws[-1]); out.append(rep.get(cap, cap) + (tail[0] if tail else ""))
    return out


if __name__ == "__main__":
    print("words:", sum(len(spoken(t).split()) for _, t, _ in LINES))
    for k, t, _ in LINES: print(k, "|", " ".join(pieces(t)))
