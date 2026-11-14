"""Narration for the Short "Every Star You See Is a Date".
Markup: {CAPTION|spoken words} shows CAPTION for the whole span of the spoken words. Each line: (key, text, pause_after_s).
Years = 2026 - distance in light-years (HYG v4.1 / literature; see README). Betelgeuse (~550 ly, 500-650) is hedged with
"probably"; Deneb (~1,500-2,600 ly) with "roughly"."""
import re

LINES = [
    ("hook", "Imagine... that star.", 0.45),
    ("hook_2", "Its light left in {2017|twenty seventeen}.", 0.60),
    ("hook_3", "That one?", 0.40),
    ("hook_4", "Probably before Columbus.", 1.10),
    ("title", "Every star you see... is a date.", 1.10),
    ("list", "Arcturus...", 0.40),
    ("list_2", "Vega... just decades ago.", 1.00),
    ("deneb", "Deneb... roughly the Roman Empire.", 1.10),
    ("m31", "And Andromeda?", 0.50),
    ("m31_2", "{2.5|Two and a half} million years ago.", 1.20),
    ("swirl", "The sky... is a time machine.", 1.10),
    ("myth", "Are they dead?", 0.50),
    ("myth_2", "Almost none.", 1.00),
    ("myth_3", "Stars live millions... to billions of years.", 0.45),
    ("myth_4", "This light is just centuries old.", 1.10),
    ("end", "When you look up...", 0.45),
    ("end_2", "you're looking back in time.", 0.0),
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
