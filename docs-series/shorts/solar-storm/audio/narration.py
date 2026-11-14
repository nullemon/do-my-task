"""REDO v3 storytelling narration. Narration for the Short "If the 1859 Solar Storm Hit Today".
Markup: {CAPTION|spoken words} shows CAPTION for the whole span of the spoken words. Each line: (key, text, pause_after_s).
Modern impacts are phrased with "could" (Lloyd's 2013 scenario range), never "would"."""
import re

LINES = [   # REDO v3 storytelling (0.7 am_michael + 0.3 am_onyx @ 0.86): ~0.4 s between phrases, 0.9-1.0 s at beat changes (fits 50 s)
    ("hook", "Imagine the Sun...", 0.40),
    ("hook2", "firing the biggest storm on record.", 1.00),
    ("hook3", "In {1859|eighteen fifty-nine}... it did.", 1.00),
    ("flare", "A white flare...", 0.40),
    ("flare2", "{17.6|Seventeen point six} hours later...", 0.40),
    ("flare3", "it hit Earth.", 1.00),
    ("erupt", "The sky... erupted.", 1.00),
    ("aurora", "Auroras reached the Caribbean.", 0.40),
    ("aurora2", "People read by their light.", 0.40),
    ("aurora3", "Telegraphs sparked.", 1.00),
    ("grid", "Imagine it today.", 0.40),
    ("grid2", "Transformers could burn out.", 0.40),
    ("grid3", "Cities... dark for months.", 0.45),
    ("nosig", "No phones.", 0.40),
    ("nosig2", "No {GPS|G P S}.", 1.00),
    ("cost", "Trillions... in damage.", 1.00),
    ("cost2", "In {2012|twenty twelve}...", 0.40),
    ("cost3", "one this big... missed us by days.", 1.00),
    ("end", "It's only a matter...", 0.40),
    ("end2", "of when.", 0.00),
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
