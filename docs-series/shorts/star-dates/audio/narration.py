"""Narration for the Short "Every Star You See Is a Date".
Markup: {CAPTION|spoken words} shows CAPTION for the whole span of the spoken words. Each line: (key, text, pause_after_s).
Years = 2026 - distance in light-years (HYG v4.1 / literature; see README). Betelgeuse (~550 ly, 500-650) is hedged with
"probably"; Deneb (~1,500-2,600 ly) with "roughly"."""
import re

LINES = [
    ("hook", "That star? Its light left in {2017|twenty seventeen}. That one? Probably before Columbus.", 0.30),
    ("title", "Every star you see is a date.", 0.25),
    ("list", "Arcturus? {1989|nineteen eighty-nine.} Vega? {2001|two thousand one.}", 0.30),
    ("deneb", "Deneb? Roughly the Roman Empire.", 0.35),
    ("m31", "And Andromeda? {2.5|Two and a half} million years ago, before modern humans existed.", 0.40),
    ("swirl", "The whole sky is a time machine.", 0.45),
    ("myth", "And no, almost none of them are dead. Stars live millions to billions of years. This light is mostly just centuries old.", 0.40),
    ("end", "When you look up, you're looking back in time.", 0.0),
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
    print("words:", sum(len(spoken(t).split()) for _, t, _ in LINES), "text words:", sum(len(t.split()) for _, t, _ in LINES))
    for k, t, _ in LINES: print(k, "|", " ".join(pieces(t)))
