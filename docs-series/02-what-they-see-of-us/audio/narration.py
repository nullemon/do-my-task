# Narration lines (key, text). Timing is locked to measured voice durations in timeline.py.
LINES = [
 ("hook",   "Somewhere out there, right now, it is still nineteen ninety."),
 ("light",  "Light doesn't arrive all at once. It travels. And every moment that has ever happened on Earth is still travelling outward, at three hundred thousand kilometres a second."),
 ("chase",  "So let's chase it. And at every star we pass, we'll ask one question: what do they see of us, right now?"),
 ("moon",   "The Moon sees Earth as it was one point three seconds ago."),
 ("sun",    "The Sun, eight minutes and twenty seconds ago."),
 ("dot",    "Six billion kilometres out, Earth is a pale blue dot. Then it's lost in the glare of the Sun."),
 ("proxima","Proxima Centauri, our nearest star, four point two light-years away, sees the summer of twenty twenty-two. The James Webb telescope has just opened its eyes."),
 ("sirius", "Sirius, the brightest star in our night sky: early twenty eighteen."),
 ("vega",   "Vega, twenty-five light-years: late two thousand and one. The space station has had people aboard for about a year."),
 ("arct",   "Arcturus, thirty-seven light-years. And here is something strange. Arcturus is seeing Earth from early nineteen ninety, around the very month Voyager turned back and photographed that pale blue dot."),
 ("caph",   "Caph, in Cassiopeia, fifty-five light-years: nineteen seventy-two. The last year anyone walked on the Moon."),
 ("radio",  "Around a hundred light-years, we cross the edge of something: our first radio broadcasts, from the nineteen twenties. Beyond this line, no one could have heard us. And even inside it, our signals are almost certainly far too faint to pick out."),
 ("dubhe",  "Dubhe, in the Big Dipper, a hundred and twenty-three light-years. Give or take a couple of years, the first aeroplane is lifting off a beach in North Carolina."),
 ("polaris","Polaris, the North Star, about four hundred and forty-six light-years: around fifteen eighty. Ships are crossing oceans, steering by this very star. No one has ever looked through a telescope."),
 ("betel",  "Betelgeuse, roughly five hundred and fifty light-years, though that distance is uncertain by a hundred or so. It sees the fourteen hundreds, or the fifteen hundreds. Cathedrals, and the first printing presses."),
 ("orion",  "The Orion Nebula, about thirteen hundred light-years: around the year seven hundred. Maya cities are at their height."),
 ("deneb",  "Deneb is a mystery. It might be fourteen hundred light-years away, or twenty-six hundred. Either way, it sees the classical world. Rome rising, or Rome falling."),
 ("vycma",  "V Y Canis Majoris, about thirty-nine hundred light-years. The Great Pyramid is already centuries old. And on an island in the Arctic, the last woolly mammoths are still alive."),
 ("twist",  "Of course, no one out there could really watch any of this. To make out details just a couple of kilometres across from Proxima Centauri, you would need a telescope as wide as the Earth. From farther away, wider still. The light is there. Seeing it is another matter."),
 ("gc",     "Twenty-seven thousand light-years: the heart of our galaxy. Earth is in an ice age. Glaciers bury much of the northern continents, and mammoths roam the plains below them."),
 ("lmc",    "The Large Magellanic Cloud, a hundred and sixty thousand light-years. Our species is young, and lives almost entirely in Africa."),
 ("m31",    "And Andromeda, two and a half million light-years away, sees an Earth with no humans at all. Only our distant ancestors, shaping some of the first stone tools."),
 ("dino",   "Sixty-six million light-years out, the asteroid is still falling."),
 ("end1",   "Everything we've ever done is still travelling outward."),
 ("end2",   "Somewhere, it's still happening."),
]
TTS_OVERRIDES = {
 "Caph,": "Kaff,",
 "Dubhe,": "Dubbee,",
 "Betelgeuse,": "Beetlejuice,",
 "Deneb ": "Dennebb ",
 "V Y Canis Majoris": "Vee Why, Kaynis Majoris",
 "Maya": "Myah",
}
PHONEME_FIXES = {}
def tts_text(t):
    for a, b in TTS_OVERRIDES.items():
        t = t.replace(a, b)
    return t
