"""writes SCRIPT.md from the locked timeline and the narration"""
import sys, re; sys.path.insert(0, "audio")
import timeline as TL
from narration import LINES
PIC = dict(hook1="MARS (Blender plate, 24-degree lens): the small white Sun inside its blue glow over a rust-red rock field. Big caption `MARS SUNSETS ARE BLUE` within the first second.",
 hook2="Montage of five other horizons (Saturn, Mercury, Titan, Pluto, Jupiter), title `SUNSET ON EVERY WORLD`.",
 earth1="EARTH: sea stacks, analytic sea with glitter path, lit cloud decks. HUD: Sun 1.00 x, 8.3 light-minutes.", earth2="Same shot, the Sun sinking and reddening. Caption: Rayleigh scattering.",
 mars1="MARS: ripples, basalt blocks with long shadows, mesas and a crater rim in dust haze. HUD: 0.66 x, 12.7 light-minutes.", mars2="The disc dims into the dust; the blue aureole stays. Caption: dust scatters blue light forward.",
 merc1="MERCURY from a crater rim: cratered regolith, black sky, the Sun 3.25 x wide (perihelion size).", merc2="Time-lapse: the disc sets, stops, climbs back, sets again; stars and the corona show while it is hidden.",
 venus1="VENUS: cracked basalt slabs under a dim orange overcast; no disc, only a brighter patch of cloud.", venus2="The overcast slowly darkens; heat shimmer near the ground.",
 jup="JUPITER cloud tops: billows and towers, high haze streaks; the tiny disc sets in real time (36 degrees per hour).",
 sat="SATURN cloud tops at 14 degrees north: the rings rise out of the haze as a leaning band (C, B, Cassini division, A, Encke gap, F).",
 ura="URANUS near a pole: the Sun skims sideways along a teal cloud field and sinks; twilight glow remains. Neptune caption at the end.",
 titan1="TITAN: pebble shore of a hydrocarbon sea under orange haze, low hills across the bay.", titan2="The glow sinks and dims; the sea stays almost flat.",
 pluto1="PLUTO: pitted nitrogen-ice plain, water-ice blocks and mountains; the Sun as a point with diffraction spikes; stars.", pluto2="Blue haze layers hug the horizon as the Sun goes behind the mountains.",
 kep="IMAGINED MOON of Kepler-16 b: cracked playa, two suns (orange K dwarf, small red M dwarf), double shadows.",
 end1="Grid of the nine reconstructed horizons. `NO HUMAN HAS EVER STOOD UNDER ANY OF THESE SKIES`.", end2="EARTH again: the Sun goes all the way down. End title.")
w = sum(len(re.findall(r"[\w'-]+", t)) for _, t in LINES)
out = [f"# 13 - SUNSET ON EVERY WORLD\n", "YouTube title: **What Sunset Looks Like on Every Planet**\n",
       f"Locked script. {TL.DUR:.0f} s ({int(TL.DUR)//60}:{int(TL.DUR)%60:02d}), 24 fps, voice am_michael @ 0.94 (Kokoro). Times are the measured voice placements (`timeline.py`).",
       "Every landscape is seen through the same 24-degree lens, so the Sun's disc is drawn at its true relative size on every world.\n",
       "| time | line | picture |", "|---|---|---|"]
for k, t in LINES: out.append(f"| {TL.START[k]:6.2f}-{TL.END[k]:6.2f} | {t} | {PIC[k]} |")
out.append(f"\nNarration: {w} words.\n\nShots: " + ", ".join(f"{n} {a:.1f}-{b:.1f}" for n, a, b in TL.SHOTS))
open("SCRIPT.md", "w").write("\n".join(out) + "\n"); print("words", w)
