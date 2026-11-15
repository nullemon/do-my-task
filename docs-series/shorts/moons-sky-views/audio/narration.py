"""Narration for the Short "The Sky From Other Moons" (BATCH4 clean sound).
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words.
Each line: (key, text, pause_after_seconds). Story style (REDO_V3), voice 0.7 am_michael + 0.3 am_onyx @ 0.86."""
import re

LINES = [
    ("hook", "Imagine standing on another moon...", 0.45),
    ("hook_b", "and looking up.", 1.10),
    ("eur", "From Europa...", 0.45),
    ("eur_b", "Jupiter fills the sky.", 0.45),
    ("eur_c", "{24×|Twenty-four times} wider than our Moon.", 1.10),
    ("tit", "From Titan...", 0.45),
    ("tit_b", "Saturn hides behind an orange haze.", 0.45),
    ("tit_c", "Rise above it... and there it is, rings and all.", 1.10),
    ("tri", "From Triton...", 0.45),
    ("tri_b", "Neptune. A deep blue giant.", 1.10),
    ("cha", "From Charon...", 0.45),
    ("cha_b", "Pluto hangs in one spot... and never moves.", 1.10),
    ("pho", "And from Phobos...", 0.45),
    ("pho_b", "Mars.", 0.45),
    ("pho_c", "{80×|Eighty times} wider than our Moon.", 1.20),
    ("end", "Back home...", 0.45),
    ("end_b", "our Moon looks tiny.", 0.45),
    ("end_c", "But it's ours.", 0.0),
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
            tail = re.findall(r"[.,?!]+$", ws[-1]); out.append(cap + (tail[0] if tail else ""))
    return out


if __name__ == "__main__":
    print("words:", sum(len(spoken(t).split()) for _, t, _ in LINES))
