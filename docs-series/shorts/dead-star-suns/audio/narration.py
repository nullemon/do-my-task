"""Narration for the Short "What If Dead Stars Replaced Our Sun?".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds). Voice rule (13 Nov): am_michael @ 0.92, ~0.35 s between sentences,
~0.7 s at beat changes."""
import re

LINES = [
    ("hook", "Every star dies.", 0.35),
    ("hook_2", "What if a dead one replaced our Sun?", 0.70),
    ("wd", "A white dwarf: the Sun's mass, Earth's size.", 0.35),
    ("wd_2", "Daylight fades to twilight. Earth freezes.", 0.70),
    ("ns", "A neutron star. Noon turns to night.", 0.70),
    ("psr", "A pulsar, sweeping its beams up to {700|seven hundred} times a second.", 0.70),
    ("mag", "A magnetar.", 0.35),
    ("mag_2", "One flare from here would strip away our atmosphere.", 0.70),
    ("bd", "A black dwarf, cold and dark.", 0.35),
    ("bd_2", "None exist yet. The universe isn't old enough.", 0.70),
    ("end", "Our Sun will end as a white dwarf.", 0.0),
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
    """subtitle strings aligned 1:1 with caption tokens (numbers kept as digits)"""
    out = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]: out.append(cap)
        else:
            tail = re.findall(r"[.,?!]+$", ws[-1]); out.append(cap + (tail[0] if tail else ""))
    return out


def subtitle(text): return " ".join(pieces(text))


if __name__ == "__main__":
    print("words written:", sum(len(t.split()) for _, t, _ in LINES), "spoken:", sum(len(spoken(t).split()) for _, t, _ in LINES))
    for k, t, _ in LINES: print(k, "|", subtitle(t))
