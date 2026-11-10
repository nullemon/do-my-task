# Narration for "WHAT SUNSET LOOKS LIKE ON EVERY PLANET". (key, subtitle text). Timing is locked after TTS (timeline.py).
LINES = [
 ("hook1", "On Mars, the sunset is blue. This is not an artist's guess. Rovers have photographed it."),
 ("hook2", "The same Sun sets on every world in the solar system. But no two sunsets look alike. Here they are, one by one, through the same lens."),
 ("earth1", "Start with the one we know. From Earth, the Sun is half a degree wide, and takes about two minutes to slip below the horizon."),
 ("earth2", "Air molecules scatter blue light far more than red. At noon, that scattered blue fills the sky. At sunset, the light crosses so much air that most of the blue is scattered away before it reaches you. What is left is red."),
 ("mars1", "Mars. Half as far again from the Sun, so the disc is about two thirds the size. The air is thin, less than a hundredth of Earth's, but it is full of fine, rust-coloured dust. By day, that dust turns the sky butterscotch."),
 ("mars2", "At sunset, the grains are just the right size to scatter blue light forward, in a tight cone around the Sun. So the colours are reversed: a tawny sky, and a cold blue glow."),
 ("merc1", "Mercury has almost no air. So there is no colour at all. The sky is black, even at noon, and the Sun, up to three times wider than ours, drops behind the rock with nothing to soften it."),
 ("merc2", "It takes its time. One day here lasts a hundred and seventy-six Earth days. And near its closest approach to the Sun, Mercury's orbital motion briefly outruns its spin. From some places, the Sun sets, stops, rises again, and then sets a second time."),
 ("venus1", "Venus has the opposite problem. Too much air. From the surface, under a permanent deck of sulphuric acid cloud, you never see the Sun's disc at all. Daylight is a dim orange overcast, and sunset is just that overcast, slowly going dark."),
 ("venus2", "Very slowly. Venus spins backwards, and one turn takes longer than its year. From one sunrise to the next is a hundred and seventeen Earth days. And if you could see the Sun, it would rise in the west."),
 ("jup", "The giant planets have no ground to stand on. So float at the cloud tops of Jupiter. Out here, the Sun is a fifth as wide as it is from Earth, and twenty-seven times fainter. But Jupiter spins once in under ten hours. So that tiny disc drops through the horizon in about ten seconds."),
 ("sat", "At Saturn, the Sun is a tenth the width. But it is not the Sun you would be looking at. The rings rise out of the haze and arch across the whole sky: countless pieces of ice, catching the last light."),
 ("ura", "Uranus lies on its side, and one orbit takes eighty-four years. Near a pole, the Sun circles the sky without setting for about forty-two of them, spiralling lower with every turn. When it finally touches the horizon, the tiny disc is gone within a couple of days. But the twilight can linger for years."),
 ("titan1", "Titan, Saturn's largest moon, has air thicker than Earth's, and an orange haze of organic smog. In two thousand and five, the Huygens probe landed here, among pebbles of water ice, in light about a thousand times dimmer than an Earth day."),
 ("titan2", "The haze lets red light through, and blocks the blue. So over a sea of liquid methane, the Sun never shows a clean edge. It sinks into a dull amber glow. And the dusk drags on, because one day on Titan lasts sixteen of ours."),
 ("pluto1", "And Pluto. Forty times farther out than Earth. The Sun is no longer a disc. It is a star: a single point, yet still about two hundred and fifty times brighter than our full Moon."),
 ("pluto2", "Noon on Pluto is about as bright as Earth a few minutes after sunset. NASA calls that moment Pluto time. And when New Horizons looked back, it saw layer upon layer of haze, glowing blue."),
 ("kep", "Beyond our own Sun, it gets stranger. Kepler-16b circles two stars. It is a gas giant. But from a moon of it, if it has one, you would watch two suns go down together: one orange, one small and red."),
 ("end1", "Every one of these views is a reconstruction, built from measurements. Robots have photographed a few of them. No person has ever stood under any of them."),
 ("end2", "There is only one sunset that human eyes have watched from the ground. This one. It happens every evening. It is worth looking up for."),
]
TTS_OVERRIDES = {"Kepler-16b": "Kepler sixteen bee", "Huygens": "Hoygens"}
PHONEME_FIXES = {}
def tts_text(t):
    for a, b in TTS_OVERRIDES.items():
        t = t.replace(a, b)
    return t
if __name__ == "__main__":
    import re
    w = sum(len(re.findall(r"[\w'-]+", t)) for _, t in LINES)
    print("words", w)
