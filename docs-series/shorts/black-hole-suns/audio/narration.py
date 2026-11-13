"""Narration for the Short "What If Black Holes Replaced Our Sun?".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [
    ("hook", "What if black holes replaced our Sun? Let's start small.", 0.12),
    ("one", "One Sun of mass, {6 KM|six kilometers} wide. Same gravity, same orbit. But it's dark forever.", 0.12),
    ("cyg", "Cygnus {X-1|X one}, {21|twenty-one} Suns. Earth's year would last weeks.", 0.12),
    ("sgr", "Sagittarius {A*|A star}. {4 MILLION|Four million} Suns. Its shadow spans {24°|twenty-four degrees}.", 0.12),
    ("m87", "{M87*|M eighty-seven star}. {6.5 BILLION|Six and a half billion} Suns. Its horizon is four times past Neptune. We're inside.", 0.12),
    ("ton", "And {TON 618|Ton six eighteen}? Up to {66 BILLION|sixty-six billion} Suns. It would swallow our solar system, so here it is {8,000×|eight thousand times} farther.", 0.50),
    ("end", "Suddenly, the Sun seems... kind.", 0.0),
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


REP = {"6 KM": "6 kilometers", "21": "21", "4 MILLION": "4 million", "24°": "24 degrees", "6.5 BILLION": "6.5 billion",
       "66 BILLION": "66 billion", "8,000×": "8,000 times", "X-1": "X-1", "A*": "A*", "M87*": "M87*", "TON 618": "TON 618"}


def pieces(text):
    """subtitle strings aligned 1:1 with caption tokens"""
    out = []
    for cap, ws in tokens(text):
        if len(ws) == 1 and cap == ws[0]: out.append(cap)
        else:
            tail = re.findall(r"[.,?!]+$", ws[-1]); out.append(REP.get(cap, cap) + (tail[0] if tail else ""))
    return out


if __name__ == "__main__":
    print("words:", sum(len(spoken(t).split()) for _, t, _ in LINES))
    for k, t, _ in LINES: print(k, "|", " ".join(pieces(t)))
