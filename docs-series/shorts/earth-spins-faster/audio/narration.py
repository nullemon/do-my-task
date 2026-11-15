"""Narration for the Short "What If Earth Spun Faster?" (BATCH4 / REDO v3 storytelling style).
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words.
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [   # 0.7 am_michael + 0.3 am_onyx @ 0.86 (BATCH4: clean voice, no post chain)
    ("hook", "What if Earth... spun faster?", 1.10),
    ("now", "Today, one day... takes {24 HOURS|twenty-four hours}.", 1.10),
    ("h12", "Now... {12 HOURS|twelve}.", 0.45),
    ("h12_b", "The Sun races across the sky.", 1.10),
    ("h6", "{6 HOURS|Six hours}.", 0.45),
    ("h6_b", "The oceans rush... toward the equator.", 1.10),
    ("h2", "{2 HOURS|Two hours}.", 0.45),
    ("h2_b", "Day and night... flicker past.", 0.45),
    ("h2_c", "Winds howl... and the equator bulges.", 1.20),
    ("brk", "And at just {84 MINUTES|eighty-four minutes}...", 0.50),
    ("brk_b", "at the equator... you'd weigh nothing.", 0.45),
    ("brk_c", "Earth... would start to fly apart.", 1.20),
    ("end", "{24 HOURS|Twenty-four hours}...", 0.50),
    ("end_b", "suddenly feels just right.", 0.0),
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
    rep = {"24 HOURS": "24 hours", "12 HOURS": "12 hours", "6 HOURS": "6 hours", "2 HOURS": "2 hours", "84 MINUTES": "84 minutes"}
    out = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]: out.append(cap)
        else:
            tail = re.findall(r"[.,?!]+$", ws[-1]); out.append(rep.get(cap, cap) + (tail[0] if tail else ""))
    return out


if __name__ == "__main__":
    print("words:", sum(len(spoken(t).split()) for _, t, _ in LINES))
    for k, t, _ in LINES: print(k, "|", " ".join(pieces(t)))
