"""Narration for the Short "What If Black Holes Replaced Our Sun?".
Markup: {CAPTION|spoken words} shows CAPTION on screen for the whole span of the spoken words (numbers etc.).
Each line: (key, text, pause_after_seconds)."""
import re

LINES = [
    ("hook", "What if black holes replaced our Sun?", 0.70),
    ("one", "One Sun of mass, {6 KM|six kilometers} wide.", 0.35),
    ("one.2", "Same orbit, but dark forever.", 0.70),
    ("cyg", "Cygnus {X-1|X one}, {21|twenty-one} Suns.", 0.35),
    ("cyg.2", "Earth's year would last weeks.", 0.60),
    ("sgr", "Sagittarius {A*|A star}, {4 MILLION|four million} Suns.", 0.35),
    ("sgr.2", "Its shadow spans {24°|twenty-four degrees}.", 0.60),
    ("m87", "{M87*|M eighty-seven star}, {6.5 BILLION|six and a half billion} Suns.", 0.35),
    ("m87.2", "We're inside its horizon.", 0.70),
    ("ton", "{TON 618|Ton six eighteen}, up to {66 BILLION|sixty-six billion} Suns.", 0.35),
    ("ton.2", "It would swallow our solar system.", 0.35),
    ("ton.3", "Here it is, {8,000×|eight thousand times} farther.", 0.70),
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
