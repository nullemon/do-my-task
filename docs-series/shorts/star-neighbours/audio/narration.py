"""Narration for the Short "What If Famous Stars Were Our Nearest Neighbour?".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [
    ("hook", "What if the brightest stars in our galaxy were our nearest {NEIGHBOUR|neighbor}?", 0.70),
    ("now", "Tonight, it's Alpha Centauri.", 0.70),
    ("sir", "Sirius. As bright as Jupiter.", 0.70),
    ("vega", "Vega. Still just a dot.", 0.70),
    ("bet", "Betelgeuse. Over a hundred times brighter than Venus.", 0.35),
    ("bet2", "Now the city casts shadows.", 0.70),
    ("rig", "Rigel. Almost a full Moon, from one tiny point.", 0.70),
    ("den", "Deneb. As bright as the full Moon.", 0.70),
    ("eta", "Eta Carinae. In its {1843|eighteen forty-three} outburst, over a hundred full Moons.", 0.35),
    ("eta2", "Night turns to twilight.", 0.70),
    ("end", "Lucky for us, our neighbours are small.", 0.0),
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
            tail = re.findall(r"[.,?!]+$", ws[-1]); out.append(cap + (tail[0] if tail else ""))
    return out


if __name__ == "__main__":
    n = sum(len(spoken(t).split()) for _, t, _ in LINES)
    print("words:", n)
    for k, t, _ in LINES: print(k, "|", " ".join(pieces(t)))
