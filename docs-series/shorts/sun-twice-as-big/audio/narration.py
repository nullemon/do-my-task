"""Narration for the Short "What If the Sun Were Bigger?" (BATCH4: REDO v3 storytelling style, clean mix).
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words.
Each line: (key, text, pause_after_seconds). Pauses: 0.45 s between phrases, 1.15 s before each reveal."""
import re

LINES = [
    ("hook", "Imagine the Sun... growing bigger.", 0.50),
    ("hook2", "Just as hot... only wider.", 1.15),
    ("x2", "First... {2×|twice} as wide.", 0.45),
    ("x2a", "Already... more light than Venus gets.", 0.45),
    ("x2b", "The sky turns white...", 0.45),
    ("x2c", "and every shadow turns sharp.", 1.15),
    ("x5", "Now... {25×|twenty-five times} the light.", 0.45),
    ("x5b", "The grass turns brown...", 0.45),
    ("x5c", "and starts to steam.", 1.15),
    ("x10", "And then... {100×|a hundred times} the light.", 0.45),
    ("x10b", "The air shimmers...", 0.45),
    ("x10c", "and the oceans... boil away.", 0.45),
    ("x10d", "Earth... becomes another Venus.", 1.15),
    ("end", "Back to normal...", 0.45),
    ("end2", "Our Sun isn't too small.", 0.45),
    ("end3", "It's just right.", 0.0),
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
    rep = {"2×": "twice", "25×": "25 times", "100×": "100 times"}
    out = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]: out.append(cap)
        else:
            tail = re.findall(r"[.,?!]+$", ws[-1]); c = rep.get(cap, cap)
            out.append(c if c.endswith(tuple(".,?!")) else c + (tail[0] if tail else ""))
    return out


if __name__ == "__main__":
    print("words:", sum(len(spoken(t).split()) for _, t, _ in LINES))
    for k, t, _ in LINES: print(k, "|", " ".join(pieces(t)))
