"""Narration for the Short "The Dinosaur-Killer Asteroid, Seen From the Ground" (Chicxulub, 66 Myr ago).
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds). The global-firestorm idea is hedged ("maybe")."""
import re

LINES = [   # REDO v3 storytelling script (75 words). Keys are <beat>_<a..d>; short.py groups them per beat.
    ("hook_a", "Imagine standing here...", 0.40),
    ("hook_b", "the day the dinosaurs died.", 1.00),
    ("appr_a", "A new star appears.", 0.50),
    ("appr_b", "{10 KM|Ten kilometers} wide.", 1.00),
    ("hit_a", "It drops... behind the horizon.", 0.50),
    ("hit_b", "Brighter than the Sun.", 0.40),
    ("hit_c", "A fireball climbs into space.", 1.00),
    ("quake_a", "Minutes later...", 0.40),
    ("quake_b", "the ground heaves.", 1.00),
    ("ejecta_a", "Molten rock rains down.", 0.50),
    ("ejecta_b", "The sky glows red-hot...", 0.40),
    ("ejecta_c", "maybe hot enough to burn forests.", 1.00),
    ("blast_a", "An hour in...", 0.40),
    ("blast_b", "the blast wave hits.", 1.00),
    ("blast_c", "Soot blocks the Sun for years.", 0.50),
    ("blast_d", "Three quarters of all species... gone.", 1.20),
    ("end_a", "And yet...", 0.45),
    ("end_b", "that asteroid... is why we're here.", 0.0),
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
