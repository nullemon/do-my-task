"""Narration for the Short "What If Venus Were Our Moon?" (BATCH4 / REDO v3 storytelling style).
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words.
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [   # 0.7 am_michael + 0.3 am_onyx @ 0.86 (BATCH4: clean voice, no post chain)
    ("hook", "What if Venus... were our Moon?", 1.10),
    ("moon", "Here's our Moon... small and quiet.", 1.10),
    ("ven", "Now... Venus.", 0.45),
    ("ven_b", "Three and a half times wider.", 1.10),
    ("cres", "Its thin crescent... already outshines the full Moon.", 1.10),
    ("half", "At half... {20×|twenty times} brighter.", 1.10),
    ("full", "And when it's full...", 0.45),
    ("full_b", "the light of {70|seventy} full Moons.", 0.45),
    ("full_c", "Night looks like dusk... with crisp shadows.", 1.10),
    ("hell", "But under those clouds... a world hot enough to melt lead.", 0.45),
    ("hell_b", "And its tides... would swamp our coasts.", 1.10),
    ("end", "Maybe one small Moon...", 0.45),
    ("end_b", "is just perfect.", 0.0),
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
    rep = {"20×": "twenty times", "70": "seventy"}
    out = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]: out.append(cap)
        else:
            tail = re.findall(r"[.,?!]+$", ws[-1]); out.append(rep.get(cap, cap) + (tail[0] if tail else ""))
    return out


if __name__ == "__main__":
    print("words:", sum(len(spoken(t).split()) for _, t, _ in LINES))
    for k, t, _ in LINES: print(k, "|", " ".join(pieces(t)))
