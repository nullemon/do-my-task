"""Narration for the Short "The Skies of Earth-Like Exoplanets".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words.
Each line: (key, text, pause_after_seconds). REDO v3 storytelling style (0.7 am_michael + 0.3 am_onyx @ 0.86)."""
import re

LINES = [
    ("hook", "Imagine this farm...", 0.45),
    ("hook_b", "on another world.", 1.05),
    ("prox", "{PROXIMA B|Proxima B}.", 0.40),
    ("prox_b", "A red sun, three times wider...", 0.40),
    ("prox_c", "and it flares.", 1.05),
    ("trap", "{TRAPPIST-1E|Trappist one E}.", 0.40),
    ("trap_b", "A salmon-pink sun...", 0.40),
    ("trap_c", "and neighbour worlds in the daytime sky.", 1.05),
    ("k16", "{KEPLER-16B|Kepler sixteen B}...", 0.40),
    ("k16_b", "two suns.", 1.05),
    ("k186", "{KEPLER-186F|Kepler one eighty-six F}.", 0.40),
    ("k186_b", "Noon feels like golden hour...", 0.40),
    ("k186_c", "so plants might grow dark... to soak it up.", 1.05),
    ("k452", "{KEPLER-452B|Kepler four fifty-two B}...", 0.40),
    ("k452_b", "Earth's older cousin.", 0.40),
    ("k452_c", "A slightly bigger, brighter Sun.", 1.15),
    ("end", "It feels like home...", 0.45),
    ("end_b", "but it's {1,800|eighteen hundred} light-years away.", 0.0),
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
    out = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]: out.append(cap)
        else:
            rep = {"PROXIMA B": "Proxima b", "TRAPPIST-1E": "TRAPPIST-1e", "KEPLER-16B": "Kepler-16b", "KEPLER-186F": "Kepler-186f",
                   "KEPLER-452B": "Kepler-452b"}
            tail = re.findall(r"[.,?!]+$", ws[-1]); out.append(rep.get(cap, cap) + (tail[0] if tail else ""))
    return out


def subtitle(text): return " ".join(pieces(text))


if __name__ == "__main__":
    print("words:", sum(len(spoken(t).split()) for _, t, _ in LINES))
    for k, t, _ in LINES: print(k, "|", subtitle(t))
