"""Narration for the Short "What If Famous Stars Were Our Nearest Neighbour?".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [   # REDO v3 storytelling script (74 words)
    ("hook", "Imagine tonight...", 0.40),
    ("now", "our nearest {NEIGHBOUR|neighbor}, Alpha Centauri...", 0.40),
    ("now2", "was swapped for a famous star.", 1.00),
    ("sir", "First... Sirius.", 0.40),
    ("sir2", "As bright as Jupiter.", 0.90),
    ("vega", "Vega.", 0.40),
    ("vega2", "Still just a dot.", 1.00),
    ("bet", "Now... Betelgeuse.", 0.40),
    ("bet2", "Brighter than a hundred Venuses.", 0.50),
    ("bet3", "The city casts shadows.", 1.00),
    ("rig", "Rigel.", 0.40),
    ("rig2", "Almost a full Moon...", 0.40),
    ("rig3", "from one tiny point.", 0.90),
    ("den", "Deneb.", 0.40),
    ("den2", "A whole full Moon.", 1.00),
    ("eta", "And then... Eta Carinae.", 0.50),
    ("eta1", "Its great eruption...", 0.60),
    ("eta2", "Over a hundred full Moons.", 0.50),
    ("eta3", "Night turns to twilight.", 1.10),
    ("end", "Lucky for us...", 0.40),
    ("end2", "our real {NEIGHBOUR|neighbor} is a quiet one.", 0.0),
]

TOK = re.compile(r"\{([^|}]*)\|([^}]*)\}([.,?!]*)|(\S+)")


def tokens(text):
    out = []
    for m in TOK.finditer(text):
        if m.group(4):
            out.append((m.group(4), [m.group(4)]))
        else:
            ws = m.group(2).split(); ws[-1] += m.group(3)
            out.append((m.group(1), ws))
    return out


def spoken(text):
    return " ".join(w for _, ws in tokens(text) for w in ws)


def pieces(text):
    """subtitle strings aligned 1:1 with caption tokens (numbers kept as digits)"""
    out = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]: out.append(cap)
        else:
            tail = re.findall(r"[.,?!]+$", ws[-1]); out.append({"NEIGHBOUR": "neighbour"}.get(cap, cap) + (tail[0] if tail else ""))
    return out


if __name__ == "__main__":
    n = sum(len(spoken(t).split()) for _, t, _ in LINES)
    print("words:", n)
    for k, t, _ in LINES: print(k, "|", " ".join(pieces(t)))
