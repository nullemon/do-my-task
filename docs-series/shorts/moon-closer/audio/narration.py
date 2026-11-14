"""Narration for the Short "What If the Moon Got Closer?".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [
    ("hook", "Imagine the Moon...", 0.50),
    ("hook_b", "creeping closer.", 1.00),
    ("today", "Here it is today.", 1.00),
    ("d200", "Now... twice as wide.", 0.45),
    ("d200_b", "The tides... {7×|seven times} stronger.", 1.00),
    ("d100", "Closer... tides {57×|fifty-seven times} stronger.", 0.45),
    ("d100_b", "The oceans surge inland.", 1.00),
    ("d50", "And then... the ground shakes.", 0.45),
    ("d50_b", "Volcanoes wake. Every crater... in sharp detail.", 1.00),
    ("d20", "Closer...", 0.50),
    ("d20_b", "It fills the sky. Tides... kilometers high.", 1.00),
    ("roche", "Until... the {ROCHE|Roshe} limit.", 0.50),
    ("roche_b", "Earth's gravity rips it apart... into a ring.", 1.10),
    ("end", "In reality... it's drifting away.", 0.40),
    ("end_b", "{3.8 CM|Three point eight centimeters} a year.", 0.45),
    ("end_c", "Saying goodbye... very slowly.", 0.0),
]

TOK = re.compile(r"\{([^|}]*)\|([^}]*)\}([.,?!:]*)|(\S+)")


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
    rep = {"7×": "7 times", "57×": "57 times", "3.8 CM": "3.8 centimeters", "ROCHE": "Roche"}
    out = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]: out.append(cap)
        else:
            tail = re.findall(r"[.,?!:]+$", ws[-1]); c = rep.get(cap, cap)
            out.append(c + (tail[0] if tail and not c.endswith(tail[0]) else ""))
    return out


def subtitle(text): return " ".join(pieces(text))


if __name__ == "__main__":
    n = sum(len(spoken(t).split()) for _, t, _ in LINES)
    print("words:", n)
    for k, t, _ in LINES: print(k, "|", subtitle(t)); print("   ", spoken(t))
