"""Narration for the Short "What If We Lived Inside a Star Cluster?".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [
    ("hook", "Our night sky has a few thousand stars. Now imagine living inside a star cluster.", 0.30),
    ("ple", "The Pleiades. A thousand young, blue-white stars. Dozens outshine Sirius, glowing through blue dust.", 0.30),
    ("hya", "The {HYADES|Hiadeez}. Older, with orange giants brighter than Sirius.", 0.30),
    ("ome", "Omega Centauri. {10 MILLION|Ten million} stars. Near the core, almost a million are naked-eye, thousands beat Sirius, and the night never gets dark.", 0.30),
    ("nsc", "And the galaxy's heart: a million stars within three light-years. The brightest rival the full Moon.", 0.35),
    ("end", "We live in the quiet suburbs of the galaxy. That's why our sky is dark.", 0.0),
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
    rep = {"10 MILLION": "10 million", "HYADES": "Hyades"}
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
