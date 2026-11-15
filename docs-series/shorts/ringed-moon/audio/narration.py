"""Narration for the Short "What If the Moon Had Rings?" (BATCH4: REDO v3 storytelling style, clean voice).
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words.
Each line: (key, text, pause_after_seconds). Pauses 0.4-0.5 s between phrases, 1.0-1.2 s before reveals."""
import re

LINES = [
    ("hook", "What if our Moon...", 0.50),
    ("hook_2", "had rings?", 1.20),
    ("now", "Tonight, it looks like this.", 1.20),
    ("ring", "Now... give it Saturn's rings.", 0.50),
    ("ring_2", "Rising over the mountains...", 0.50),
    ("ring_3", "more than twice as wide as the Moon.", 0.50),
    ("ring_4", "A silver halo.", 1.20),
    ("shad", "The rings cast a shadow...", 0.50),
    ("shad_2", "a dark stripe across its face.", 1.20),
    ("edge", "Sometimes they turn edge-on...", 0.50),
    ("edge_2", "a razor-thin line of light.", 1.20),
    ("light", "And on snowy nights...", 0.50),
    ("light_2", "moonlight is five times brighter.", 0.50),
    ("light_3", "The whole village glows.", 1.20),
    ("end", "Then... they're gone.", 0.50),
    ("end_2", "And our Moon... looks a little lonely.", 0.0),
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


def caption_word(w):
    """on-screen form of one spoken word: upper case, without trailing punctuation"""
    w = w.strip()
    w = re.sub(r"[.,?!:;]+$", "", w)
    return w.upper()


def pieces(text):
    """subtitle strings aligned 1:1 with caption tokens (numbers kept as digits)"""
    rep = {}
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
