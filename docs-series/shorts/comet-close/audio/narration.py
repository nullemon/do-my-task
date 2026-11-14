"""REDO v3 (storytelling, 0.7 am_michael + 0.3 am_onyx @ 0.86). Narration for the Short "What If Comets Passed as Close as the Moon?".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [
    ("hook", "Imagine the Moon...", 0.45),
    ("hook2", "replaced by a comet.", 1.10),
    ("halley", "First... Halley's Comet.", 0.45),
    ("halley2", "Its heart... a dark potato.", 0.45),
    ("halley3", "But its green glow... {30|thirty} Moons wide.", 1.10),
    ("hb", "Then... Hale-Bopp.", 0.45),
    ("hb2", "So bright... you'd cast a shadow.", 1.10),
    ("neo", "Now... NEOWISE.", 0.45),
    ("neo2", "A golden tail... tinted by sodium.", 1.10),
    ("duck", "{67P|Sixty-seven P}.", 0.45),
    ("duck2", "A rubber duck... spitting jets.", 1.10),
    ("mcn", "And then... {MCNAUGHT|Mac Nawt}.", 0.45),
    ("mcn2", "Its striped tail... fills the entire sky.", 1.20),
    ("end", "All that glory...", 0.45),
    ("end2", "from a dirty snowball...", 0.40),
    ("end3", "a few kilometres wide.", 0.0),
]

TOK = re.compile(r"\{([^|}]*)\|([^}]*)\}([.,?!]*)|(\S+)")


def tokens(text):
    """-> list of (caption, [spoken words]) in order"""
    out = []
    for m in TOK.finditer(text):
        if m.group(4):
            w = m.group(4)
            out.append((w, [w]))
        else:
            ws = m.group(2).split(); ws[-1] += m.group(3)
            out.append((m.group(1), ws))
    return out


def spoken(text):
    return " ".join(w for _, ws in tokens(text) for w in ws)


def pieces(text):
    """subtitle strings aligned 1:1 with caption tokens (numbers kept as digits)"""
    rep = {"MCNAUGHT": "McNaught"}
    out = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]: out.append(cap)
        else:
            tail = re.findall(r"[.,?!]+$", ws[-1]); out.append(rep.get(cap, cap) + (tail[0] if tail else ""))
    return out


def subtitle(text): return " ".join(pieces(text))


if __name__ == "__main__":
    n = sum(len(spoken(t).split()) for _, t, _ in LINES)
    print("words:", n)
    for k, t, _ in LINES: print(k, "|", subtitle(t))
