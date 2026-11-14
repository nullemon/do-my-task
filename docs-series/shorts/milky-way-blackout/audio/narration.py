"""Narration for the Short "In 1994, People Called 911 About a Strange Cloud. It Was the Milky Way."
Markup: {CAPTION|spoken words} shows CAPTION for the whole span of the spoken words. Each line: (key, text, pause_after_s).
Wording is deliberately attributed ("reportedly", "according to ... Griffith Observatory"): the story is widely told but
hard to verify in detail, so no call counts are claimed."""
import re

LINES = [
    ("hook", "Imagine Los Angeles...", 0.45),
    ("hook_2", "January {1994|nineteen ninety-four}. Before dawn.", 1.00),
    ("quake", "The Northridge earthquake hits.", 0.60),
    ("dark", "And the city... goes dark.", 1.20),
    ("look", "People step outside...", 0.40),
    ("look_2", "and look up.", 1.80),
    ("cloud", "According to Griffith Observatory, people called about a strange sky.", 0.45),
    ("cloud_2", "Some reportedly described... a silver cloud.", 1.10),
    ("twist", "It was the Milky Way.", 0.60),
    ("twist_2", "They'd never seen it.", 1.10),
    ("fact", "Today, nearly {80%|eighty percent} of North Americans can't see it from home.", 1.00),
    ("end", "But it's still there...", 0.45),
    ("end_2", "every night...", 0.40),
    ("end_3", "right above you.", 0.0),
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
    out = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]: out.append(cap)
        else:
            tail = re.findall(r"[.,?!]+$", ws[-1]); out.append(cap + (tail[0] if tail else ""))
    return out


if __name__ == "__main__":
    print("words:", sum(len(spoken(t).split()) for _, t, _ in LINES))
    for k, t, _ in LINES: print(k, "|", " ".join(pieces(t)))
