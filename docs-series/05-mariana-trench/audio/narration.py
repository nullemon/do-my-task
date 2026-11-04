# Narration for 05 "FALLING INTO THE MARIANA TRENCH".
# (tag, pause_before_s, text). The tag names the beat; some tags are also depth keys used by the
# descent timeline (see timeline.py: DEPTH_AT_LINE). Voice is generated first; start times are then
# derived from the measured clip lengths and locked in placement.json.
LINES = [
 ("surf",    0.6, "This is the surface of the western Pacific, above the Mariana Trench."),
 ("surf",    1.0, "The bottom is almost eleven kilometres straight down."),
 ("fall",    1.4, "Let's fall."),
 ("epi",     2.6, "The sunlight zone. The top two hundred metres of the ocean, where there is enough light for drifting plant life to grow."),
 ("epi",     1.2, "Every ten metres of water adds roughly one more atmosphere of pressure."),
 ("m40",     1.2, "Forty metres. The limit for recreational scuba divers."),
 ("red",     1.2, "Red light has already been absorbed. Everything is turning blue."),
 ("meso",    2.0, "Two hundred metres. The twilight zone."),
 ("m253",    1.0, "Two hundred and fifty-three metres. The deepest a person has gone on a single breath: Herbert Nitsch, riding a weighted sled, in 2012."),
 ("meso2",   1.6, "Down here, the light is too faint for anything to grow. So animals make their own."),
 ("lantern", 1.0, "Lanternfish glow along their bellies, matching the dim light from above, so that hunters below can't see their shadows."),
 ("squid",   1.6, "Somewhere in this zone lives the giant squid. It was first filmed in the deep in 2012, about six hundred metres down."),
 ("burj",    1.6, "Eight hundred and twenty-eight metres. The world's tallest building would now be completely under water."),
 ("dark",    1.6, "And at around a thousand metres, the last trace of sunlight is gone."),
 ("dark2",   1.4, "From here on, it is night. It has always been night."),
 ("bathy",   2.8, "The midnight zone. The pressure is a hundred times what it was at the surface, and the water is only a few degrees above freezing."),
 ("bio",     1.4, "Yet about three quarters of the animals seen in these dark waters can make light."),
 ("atolla",  1.0, "A jellyfish flashes a spinning ring of blue. A burglar alarm, some scientists think, to call in bigger predators against whatever is attacking it."),
 ("angler",  1.4, "An anglerfish dangles a glowing lure: a fin spine, tipped with light-making bacteria."),
 ("gulper",  1.2, "A gulper eel drifts by, almost all mouth, with a tiny light at the tip of its tail."),
 ("whale",   1.6, "Two kilometres. Sperm whales dive this deep to hunt squid, on a single breath."),
 ("everest", 1.6, "And if Mount Everest stood on the floor of this trench, its summit would be right about here. Two kilometres below the waves."),
 ("everest2",1.0, "We still have almost nine kilometres of mountain to fall past."),
 ("titanic", 2.0, "Three thousand eight hundred metres. The wreck of the Titanic. Only a third of the way down."),
 ("abyss",   2.4, "Four thousand metres. The abyss. Much of the deep ocean floor lies around here: four, five, six kilometres down."),
 ("abyss2",  1.0, "But beneath us, the floor has fallen away."),
 ("dumbo",   1.4, "A dumbo octopus, flapping its ear-like fins. They have been seen almost seven kilometres down."),
 ("hadal",   2.4, "Six thousand metres. The hadal zone, named after Hades, the Greek underworld."),
 ("hadal2",  1.2, "Trenches form where one of Earth's plates sinks beneath another. Here, the Pacific plate is sliding, very slowly, down into the planet."),
 ("snail",   2.0, "Eight thousand metres. Snailfish: small, pale, soft-bodied. In 2022, one was filmed at eight thousand three hundred and thirty-six metres. The deepest fish ever seen."),
 ("snail2",  1.2, "Not far below, scientists think, no fish can survive. The chemistry that protects their cells from the pressure reaches its limit."),
 ("trieste", 2.6, "In 1960, Jacques Piccard and Don Walsh came down here in the bathyscaphe Trieste. On the way, a window cracked with a bang. They kept going, and spent twenty minutes on the bottom."),
 ("cameron", 1.4, "Nobody returned for fifty-two years. Then, in 2012, James Cameron came down alone."),
 ("vescovo", 1.4, "And from 2019, Victor Vescovo dived here again and again, in a submersible built to be used over and over, and he brought others with him."),
 ("bottom",  2.8, "Ten thousand, nine hundred and thirty-five metres, give or take a few."),
 ("bottom2", 1.0, "The bottom of Challenger Deep. The deepest known place on Earth."),
 ("press",   1.6, "The pressure is about eleven hundred times what it is at the surface. More than a tonne on every square centimetre."),
 ("cold",    1.2, "The water is about two degrees. And no sunlight has ever reached it."),
 ("amph",    1.8, "And still, there is life. Amphipods, scavengers related to beach sandhoppers, swarm over anything that sinks from above."),
 ("moon",    2.8, "For half a century, more people had walked on the Moon than had ever come here. That is no longer true."),
 ("moon2",   1.2, "Dozens have now made the dive. One of them, Kathy Sullivan, had also walked in space."),
 ("space",   1.4, "But we have still sent far more people into space than to the bottom of our own ocean."),
 ("end",     2.6, "Eleven kilometres. Less than a ten-minute drive, if it were a road."),
 ("end2",    1.6, "And almost no one has ever been here."),
]
TTS_OVERRIDES = {
 "in 2012.": "in twenty twelve.",
 "in 2012,": "in twenty twelve,",
 "In 2022,": "In twenty twenty-two,",
 "In 1960,": "In nineteen sixty,",
 "in 2012, James": "in twenty twelve, James",
 "Then, in 2012,": "Then, in twenty twelve,",
 "from 2019,": "from twenty nineteen,",
 "Nitsch": "Nitch",
 "Piccard": "Pickard",
 "Vescovo": "Vescovo",
 "bathyscaphe": "bathy-scaff",
 "Trieste": "Tree-est",
 "hadal": "hay-dal",
 "Hades": "Hay-deez",
 "metres": "meters",
 "kilometres": "kilometers",
 "centimetre": "centimeter",
}
PHONEME_FIXES = {"tɹˈiːˌiːˌɛstˈiː": "tɹiːˈɛst"}


def tts_text(t):
    for a, b in TTS_OVERRIDES.items():
        t = t.replace(a, b)
    return t


if __name__ == "__main__":
    print(sum(len(l[2].split()) for l in LINES), "words,", len(LINES), "lines")
