"""Narration for the Short "If the 1859 Solar Storm Hit Today".
Markup: {CAPTION|spoken words} shows CAPTION for the whole span of the spoken words. Each line: (key, text, pause_after_s).
Modern impacts are phrased with "could" (Lloyd's 2013 scenario range), never "would"."""
import re

LINES = [
    ("hook", "In {1859|eighteen fifty-nine}, the Sun fired the biggest storm in recorded history. If it hit today...", 0.30),
    ("flare", "Richard Carrington saw a white flare. {17.6|Seventeen point six} hours later, it hit Earth.", 0.20),
    ("erupt", "The sky erupted.", 0.25),
    ("aurora", "Auroras reached the Caribbean. People read newspapers by their light. Telegraphs sparked and shocked operators.", 0.30),
    ("grid", "Today, it could burn out transformers. Cities could go dark for months.", 0.15),
    ("nosig", "No phones. No {GPS|G P S}.", 0.35),
    ("cost", "Damage could reach trillions of dollars. In {2012|twenty twelve}, one this big missed us by about nine days.", 0.40),
    ("end", "It's only a matter of when.", 0.0),
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
