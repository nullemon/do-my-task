"""Narration for the Short "When You See the Sun Touch the Horizon, It's Already Gone".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [
    ("hook", "This Sun isn't really there.", 0.30),
    ("reveal", "When it touches the horizon, the real Sun has already set, completely below the ridge.", 0.25),
    ("how", "Air bends light. Near the ground it's denser, so sunlight curves down to you, lifting the Sun's image by more than its own width.", 0.35),
    ("squash", "The bottom edge lifts most, squashing the Sun into an oval. Then, on a clear evening, the last sliver can flash green.", 0.85),
    ("bonus", "Your days are a few minutes longer because of it.", 0.25),
    ("myth", "And no, it's not the {8-MINUTE|eight-minute} light delay. That's a myth.", 0.30),
    ("end", "Every sunset you've ever watched... was a mirage.", 0.0),
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
    rep = {"8-MINUTE": "8-minute"}
    out = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]: out.append(cap)
        else:
            tail = re.findall(r"[.,?!]+$", ws[-1]); out.append(rep.get(cap, cap) + (tail[0] if tail else ""))
    return out


if __name__ == "__main__":
    print("words:", sum(len(spoken(t).split()) for _, t, _ in LINES))
    for k, t, _ in LINES: print(k, "|", " ".join(pieces(t)))
