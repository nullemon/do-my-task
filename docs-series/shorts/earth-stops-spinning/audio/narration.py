"""Narration for the Short "What If Earth Stopped Spinning?" (BATCH4 clean sound).
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words.
Each line: (key, text, pause_after_seconds). Story style (REDO_V3), voice 0.7 am_michael + 0.3 am_onyx @ 0.86."""
import re

LINES = [
    ("hook", "What if Earth...", 0.45),
    ("hook_b", "stopped spinning?", 1.05),
    ("day", "Right now, this farm is racing east...", 0.45),
    ("day_b", "and you feel nothing.", 1.10),
    ("stop", "Stop it suddenly...", 0.45),
    ("stop_b", "and the air keeps going.", 0.45),
    ("stop_c", "Winds of over {1,600|sixteen hundred} kilometres an hour.", 0.45),
    ("stop_d", "Everything... flattened.", 1.15),
    ("slow", "Stop it slowly...", 0.45),
    ("slow_b", "and the Sun freezes in the sky.", 0.45),
    ("slow_c", "One day... lasts six months.", 1.10),
    ("night", "Then... the long night.", 0.45),
    ("night_b", "Six months of stars... and frost.", 1.10),
    ("sea", "Even the oceans move...", 0.45),
    ("sea_b", "draining toward the poles.", 1.15),
    ("end", "So tonight...", 0.45),
    ("end_b", "be glad the ground keeps spinning.", 0.0),
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
