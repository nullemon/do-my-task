"""Narration for the Short "Your Night Sky in 1 Million Years".
Markup: {CAPTION|spoken words} shows CAPTION for the whole span of the spoken words. Each line: (key, text, pause_after_s).
Facts (see README): Ursa Major Moving Group (Merak, Phecda, Megrez, Alioth, Mizar) vs Dubhe + Alkaid; Barnard's Star
10.4"/yr, the largest proper motion of any star; Gliese 710 closest approach ~0.051 pc (~10,500 au) in ~1.29 Myr (Gaia DR3),
peak V ~ -3 (computed from its absolute magnitude) vs Sirius -1.46 today."""
import re

LINES = [
    ("hook", "The constellations aren't fixed. Watch what happens to the Big Dipper.", 0.25),
    ("ff", "Every star is moving. Barnard's Star, the fastest, shoots right across the sky.", 0.25),
    ("dip", "Five Dipper stars travel together, as a family. But Dubhe and Alkaid go their own way. "
            "In {100,000|a hundred thousand} years, the Dipper is broken.", 0.30),
    ("orion", "Orion's shoulders drift apart. Stars moving away fade out.", 0.30),
    ("gj", "And in {1.3|one point three} million years, {GLIESE 710|Gleeza seven ten} skims past the Sun, "
           "blazing brighter than any star we see today.", 0.35),
    ("end", "Every constellation you know is temporary.", 0.0),
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
    rep = {"GLIESE 710": "Gliese 710"}
    out = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]: out.append(cap)
        else:
            tail = re.findall(r"[.,?!]+$", ws[-1]); out.append(rep.get(cap, cap) + (tail[0] if tail else ""))
    return out


if __name__ == "__main__":
    print("words:", sum(len(t.split()) for _, t, _ in LINES))
    for k, t, _ in LINES: print(k, "|", " ".join(pieces(t)))
