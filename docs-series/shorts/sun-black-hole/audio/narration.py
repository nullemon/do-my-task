"""Narration for the Short "What If the Sun Became a Black Hole?".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [
    ("hook", "If the Sun became a black hole right now, you wouldn't notice.", 0.22),
    ("delay", "For {8 MIN|eight minutes} {AND 20 SEC|and twenty seconds}, its last light keeps arriving.", 0.22),
    ("then", "Then the Sun just", 0.40),
    ("out", "goes out.", 0.45),
    ("twi", "No sunset. No twilight.", 0.18),
    ("sky", "The blue sky is scattered sunlight, so day turns black, and stars come out at noon.", 0.30),
    ("orbit", "Earth's orbit? Unchanged. Same mass, same gravity.", 0.25),
    ("bh", "The black hole is only {6 KM|six kilometers} wide.", 0.12),
    ("scope", "Through a telescope, you'd see starlight bending around it.", 0.30),
    ("cold", "Then the cold. In a week, below {−18°C|minus eighteen}. In a year, {−73°C|minus seventy-three}.", 0.30),
    ("end", "And Earth keeps orbiting perfectly. A frozen world, circling a hole you can't even see.", 0.0),
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


def subtitle(text):
    """plain subtitle text (SRT): spoken words, numbers as digits"""
    parts = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]:
            parts.append(cap)
        else:
            tail = re.findall(r"[.,?!]+$", ws[-1])
            c = cap.replace("8 MIN", "8 minutes").replace("AND 20 SEC", "and 20 seconds").replace("6 KM", "6 km")
            parts.append(c + (tail[0] if tail else ""))
    return " ".join(parts)


if __name__ == "__main__":
    n = sum(len(spoken(t).split()) for _, t, _ in LINES)
    print("words:", n)
    for k, t, _ in LINES: print(k, "|", subtitle(t))
