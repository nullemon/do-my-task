"""Narration for the Short "What If Comets Passed as Close as the Moon?".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [
    ("hook", "What if a comet passed as close as the Moon?", 0.25),
    ("halley", "Halley's Comet. Its nucleus: a dark potato just {15|fifteen} kilometres long. But its green coma would span {15°|fifteen degrees}, its tails the whole sky.", 0.25),
    ("hb", "Hale-Bopp. A giant, {60|sixty} kilometres wide, bright enough to cast shadows.", 0.25),
    ("neo", "NEOWISE. A golden, curving dust tail, tinted by sodium.", 0.25),
    ("duck", "{67P|Sixty-seven P}, the rubber-duck comet, spitting jets.", 0.25),
    ("mcn", "And {MCNAUGHT|Mac Nawt}, brightest in forty years: a striped dust fan filling the entire sky.", 0.30),
    ("end", "Comets are dirty snowballs a few kilometres wide... with tails millions of kilometres long.", 0.0),
]

TOK = re.compile(r"\{([^|}]*)\|([^}]*)\}([.,?!]*)|(\S+)")


def tokens(text):
    """-> list of (caption, [spoken words]) in order"""
    out = []
    for m in TOK.finditer(text):
        if m.group(4):
            w = m.group(4)
            out.append((w, [w]))
        else:
            ws = m.group(2).split(); ws[-1] += m.group(3)
            out.append((m.group(1), ws))
    return out


def spoken(text):
    return " ".join(w for _, ws in tokens(text) for w in ws)


def pieces(text):
    """subtitle strings aligned 1:1 with caption tokens (numbers kept as digits)"""
    rep = {"15°": "15 degrees"}
    out = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]: out.append(cap)
        else:
            tail = re.findall(r"[.,?!]+$", ws[-1]); out.append(rep.get(cap, cap) + (tail[0] if tail else ""))
    return out


def subtitle(text): return " ".join(pieces(text))


if __name__ == "__main__":
    n = sum(len(spoken(t).split()) for _, t, _ in LINES)
    print("words:", n)
    for k, t, _ in LINES: print(k, "|", subtitle(t))
