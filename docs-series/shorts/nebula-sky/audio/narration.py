"""Narration for the Short "What If Famous Nebulas Were in Our Sky?".
Premise: each nebula moved to 15 light-years from Earth (the distance of our nearer stellar neighbours), real size kept.
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [
    ("hook", "What if the Orion Nebula was as close as our nearest stars? It would span {77°|seventy-seven degrees} of sky.", 0.25),
    ("ring", "The Ring Nebula, a dying star's last breath, {7|seven} full Moons wide.", 0.2),
    ("pill", "The Pillars of Creation, {4|four} light-years tall, rising over the city.", 0.2),
    ("crab", "The Crab Nebula, an exploded star, its pulsar flashing {30×|thirty times} a second.", 0.2),
    ("car", "And Carina, over {200|two hundred} light-years wide. We'd be inside it.", 0.3),
    ("eye", "Even up close, they'd look fainter to your eyes than in photos, but your phone camera would see this.", 0.3),
    ("end", "They're all out there right now, just very far away.", 0.0),
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
    rep = {"77°": "77 degrees", "30×": "30 times"}
    out = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]: out.append(cap)
        else:
            tail = re.findall(r"[.,?!]+$", ws[-1]); out.append(rep.get(cap, cap) + (tail[0] if tail else ""))
    return out


if __name__ == "__main__":
    print("words:", sum(len(spoken(t).split()) for _, t, _ in LINES))
    for k, t, _ in LINES: print(k, "|", " ".join(pieces(t)))
