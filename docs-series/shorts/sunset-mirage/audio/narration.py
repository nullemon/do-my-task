"""Narration for the Short "When You See the Sun Touch the Horizon, It's Already Gone".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [   # REDO v3 storytelling script: 0.7 am_michael + 0.3 am_onyx @ 0.86
    ("hook", "What if this sunset...", 0.45),
    ("hook_b", "isn't really there?", 1.10),
    ("reveal", "As it touches the ridge...", 0.45),
    ("reveal_b", "the real Sun has already set.", 1.10),
    ("how", "Air bends light.", 0.45),
    ("how_b", "Denser air curves it down to you...", 0.40),
    ("how_c", "lifting the Sun... more than its own width.", 1.10),
    ("squash", "The bottom lifts most...", 0.40),
    ("squash_b", "squashing it into an oval.", 1.00),
    ("gf", "Then... the last sliver...", 0.40),
    ("gf_b", "can flash green.", 1.20),
    ("bonus", "Your days... are minutes longer.", 1.10),
    ("myth", "And no... it's not the {8-MINUTE|eight-minute} delay.", 0.45),
    ("myth_b", "That's a myth.", 1.20),
    ("end", "Every sunset you've ever watched...", 0.50),
    ("end_b", "was a mirage.", 0.0),
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
