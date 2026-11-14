"""Narration for the Short "Your Night Sky in 1 Million Years".
Markup: {CAPTION|spoken words} shows CAPTION for the whole span of the spoken words. Each line: (key, text, pause_after_s).
Facts (see README): Ursa Major Moving Group (Merak, Phecda, Megrez, Alioth, Mizar) vs Dubhe + Alkaid; Barnard's Star
10.4"/yr, the largest proper motion of any star; Gliese 710 closest approach ~0.051 pc (~10,500 au) in ~1.29 Myr (Gaia DR3),
peak V ~ -3 (computed from its absolute magnitude) vs Sirius -1.46 today."""
import re

LINES = [   # REDO v3 storytelling script (75 words). Keys are <beat>_<a..e>; short.py groups them per beat.
    ("hook_a", "Imagine the sky... fast-forwarded.", 0.40),
    ("hook_b", "Watch the Big Dipper.", 1.00),
    ("ff_a", "Every star... moves.", 0.40),
    ("ff_b", "Barnard's Star, the fastest...", 0.40),
    ("ff_c", "shoots across the sky.", 1.00),
    ("dip_a", "Most Dipper stars travel together... a family.", 0.50),
    ("dip_b", "But Dubhe and Alkaid...", 0.40),
    ("dip_c", "go their own way.", 0.60),
    ("dip_d", "In {100,000|a hundred thousand} years...", 0.40),
    ("dip_e", "the Dipper is broken.", 1.10),
    ("orion_a", "Orion's shoulders... drift apart.", 0.50),
    ("orion_b", "Stars moving away fade.", 1.00),
    ("gj_a", "In {1.3|one point three} million years...", 0.50),
    ("gj_b", "{GLIESE 710|Gleeza seven ten}... skims past the Sun.", 0.50),
    ("gj_c", "Blazing brighter than Sirius.", 1.20),
    ("end_a", "Every constellation you know...", 0.45),
    ("end_b", "is temporary.", 0.0),
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
