# Narration for 03 "You Are Not Sitting Still": (id, scene, pause_before_s, text).
# Start times are NOT hand-set: timeline.py packs the measured clips with these pauses and locks the timeline.
LINES = [
 ("l00", "room",   0.5, "You think you're sitting still."),
 ("l01", "room",   1.0, "You're not. Not even close."),
 ("l02", "room",   1.2, "Right now, without feeling a thing, you're moving at well over a million kilometres an hour."),
 ("l03", "room",   1.2, "Let's add it up. One level at a time. And let's keep a running count of how far you travel while you watch."),
 ("l04", "earth",  2.0, "First, the ground beneath you. Earth turns once a day, and you turn with it, sweeping around a circle that, at the equator, is forty thousand kilometres long."),
 ("l05", "earth",  1.0, "At the equator, that's about one thousand, six hundred and seventy kilometres an hour."),
 ("l06", "earth",  1.2, "Away from the equator, your circle is smaller, so you move more slowly. In London, about one thousand and forty. At the poles, almost nothing."),
 ("l07", "orbit",  2.0, "But Earth itself is moving. It circles the Sun once a year, at nearly thirty kilometres every second."),
 ("l08", "orbit",  1.0, "That's about a hundred and seven thousand kilometres an hour. London to New York in about three minutes."),
 ("l09", "helix",  1.5, "And the Sun is not standing still either. It carries every planet with it, so our real path is not a circle. It's a long, slanted spiral."),
 ("l10", "helix",  1.0, "The planets' orbits are tilted about sixty degrees to the Sun's path. Not the swirling vortex you may have seen online. The real spiral is far gentler. Each year, the Sun moves about fifty times farther than the width of Earth's orbit, so our path is stretched out, almost straight."),
 ("l11", "galaxy", 2.0, "Because the Sun is orbiting too, around the centre of the Milky Way."),
 ("l12", "galaxy", 1.0, "At roughly two hundred and thirty kilometres a second. Over eight hundred thousand kilometres an hour."),
 ("l13", "galaxy", 1.2, "Even so, one lap takes around two hundred and thirty million years. The last time the Sun was at this point in its orbit, the first dinosaurs were only just appearing."),
 ("l14", "galaxy", 1.2, "And as it circles, it drifts gently up and down through the galaxy's disk, crossing it every thirty million years or so."),
 ("l15", "cosmos", 2.0, "Then the Milky Way itself is moving, and so is every galaxy around it."),
 ("l16", "cosmos", 1.0, "All of space is filled with a faint afterglow of the Big Bang: the cosmic microwave background. Measured against it, the Sun is moving at about three hundred and seventy kilometres a second."),
 ("l17", "cosmos", 1.0, "These speeds don't simply add up. They point in different directions. But the total is still more than one point three million kilometres an hour."),
 ("l18", "cosmos", 1.2, "And our whole Local Group of galaxies, Andromeda included, is moving at about six hundred kilometres a second, drawn toward vast gatherings of galaxies: the Great Attractor, and beyond it, the Shapley Supercluster."),
 ("l19", "why",    2.0, "So why don't you feel any of it?"),
 ("l20", "why",    1.0, "Because you don't feel speed. You feel changes in speed. Speeding up. Slowing down. Turning sharply."),
 ("l21", "why",    1.0, "Almost all of this motion is smooth and steady. Galileo noticed it below deck on a ship gliding over calm water: nothing tells you you're moving. Newton made it a law."),
 ("l22", "why",    1.0, "And everything around you is moving with you. The chair. The air. The window. The whole planet. Nothing rushes past, so nothing gives it away."),
 ("l23", "end",    2.0, "Since this video began, you've travelled nearly a hundred thousand kilometres. A quarter of the way to the Moon."),
 ("l24", "end",    1.6, "You've never been still."),
 ("l25", "end",    1.0, "Not for one second."),
]
TTS_OVERRIDES = {}
PHONEME_FIXES = {}
def tts_text(t):
    for a, b in TTS_OVERRIDES.items():
        t = t.replace(a, b)
    return t
