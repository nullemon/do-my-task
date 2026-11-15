"""Narration for the Short "What If Earth Had More Moons?" (BATCH3 / REDO v3 storytelling voice).
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words.
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [   # 0.7 am_michael + 0.3 am_onyx @ 0.86
    ("hook", "What if Earth had more moons?", 1.00),
    ("moon", "Ours... just one.", 1.10),
    ("two", "Now... a second Moon.", 0.45),
    ("two_b", "Two reflections on the lake.", 1.10),
    ("mars", "Then... {MARS-STYLE|Mars style}.", 0.45),
    ("mars_b", "A tiny moon... races across the sky.", 1.10),
    ("jup", "Now... Jupiter's four giants.", 0.45),
    ("jup_b", "Moons eclipsing moons.", 1.10),
    ("sat", "Then... a Saturn swarm.", 0.45),
    ("sat_b", "Dozens of moons... and a ring.", 1.20),
    ("all", "All of them... at once.", 1.20),
    ("phys", "The tides would turn chaotic...", 0.45),
    ("phys_b", "and some moons might collide.", 1.20),
    ("end", "And yet... long ago...", 0.50),
    ("end_b", "Earth may have had two moons...", 0.50),
    ("end_c", "that merged into one.", 0.0),
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
    rep = {"MARS-STYLE": "Mars-style"}
    out = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]: out.append(cap)
        else:
            tail = re.findall(r"[.,?!]+$", ws[-1]); out.append(rep.get(cap, cap) + (tail[0] if tail else ""))
    return out


if __name__ == "__main__":
    print("words:", sum(len(spoken(t).split()) for _, t, _ in LINES))
    for k, t, _ in LINES: print(k, "|", " ".join(pieces(t)))
