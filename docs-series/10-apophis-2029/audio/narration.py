# Narration for "FRIDAY THE 13TH, 2029" (asteroid Apophis). (key, subtitle text). Timing is locked after TTS (timeline.py).
LINES = [
 ("hook1", "On Friday the thirteenth of April, 2029, a mountain of rock will pass between the Earth and its own satellites."),
 ("hook2", "It will not hit us. We have known that for years. And that is exactly what makes this night unlike any other in history."),
 ("disc1", "The story begins in June 2004, at Kitt Peak in Arizona. Three astronomers catch a faint new asteroid, and then lose it."),
 ("disc2", "That December, it is found again. And the orbit calculations turn alarming."),
 ("scare", "For a few days, the odds of an impact on the thirteenth of April, 2029, climb to two point seven percent. One chance in thirty-seven. It reaches level four on the Torino scale, the highest rating any asteroid has ever been given."),
 ("name", "It is later named Apophis, after the Egyptian serpent of chaos."),
 ("relief1", "But a number like that measures what we don't know. Every new observation narrows the range of possible paths. Within days, older images turn up, and the Earth slips outside that range. 2029 is safe."),
 ("relief2", "Smaller risks lingered for later decades. Then, in March 2021, radar tracked Apophis precisely enough to settle it. No impact, for at least a hundred years."),
 ("size1", "So what is it? A stony asteroid, about three hundred and forty metres across. Radar suggests it is elongated, perhaps two lobes joined together. It tumbles slowly, about once every thirty hours."),
 ("size2", "Here it is beside the Eiffel Tower, at the same scale."),
 ("scale1", "Now, the distance. This is the Earth. Out here, about thirty-six thousand kilometres up, is the ring of geostationary satellites, the ones that carry television and weather pictures."),
 ("scale2", "And far beyond them, ten times farther, the Moon."),
 ("pass1", "Apophis will arrive at about six kilometres per second, and pass roughly thirty-two thousand kilometres above the surface. Inside the satellite ring. About a tenth of the way to the Moon."),
 ("rare", "An asteroid this large is thought to come this close only once in several thousand years."),
 ("view1", "And you will be able to see it. No telescope needed. That evening, across Europe, Africa and western Asia, around two billion people will be able to look up into a clear, dark sky, and find it."),
 ("view2", "A point of light, about as bright as the stars of the Little Dipper, drifting through the constellations. At its fastest, it will cross the width of the full Moon in under a minute."),
 ("view3", "It will not look like a rock. Just a star that refuses to stay still."),
 ("grav1", "For Apophis, the encounter changes everything. Earth's gravity will bend its path, and widen its orbit around the Sun. Its year will stretch from about nine tenths of ours, to nearly one point two."),
 ("grav2", "The pull may also change the way it tumbles, and could even set off small landslides on its surface. Nobody knows for sure. Which is why we are going."),
 ("miss1", "NASA's OSIRIS-APEX, the spacecraft that brought home pieces of asteroid Bennu, is already on its way, due to arrive just after the flyby, if its funding survives."),
 ("miss2", "Europe's Ramses, approved in late 2025 and now being built, is due to launch in 2028 and arrive two months early, to watch the before, and the after. A Japanese probe is planned to fly past, too."),
 ("hypo1", "And if it had been on target? To be clear, this will not happen. But a rock this size would strike with the energy of roughly a thousand megatons of TNT: more than twenty times the most powerful bomb ever detonated."),
 ("hypo2", "Enough to devastate a whole region. Not enough to end civilisation."),
 ("end1", "Instead, we get something no generation has had before. A large asteroid will pass this close, and we have known for years, almost to the minute, where it will be."),
 ("end2", "Our ancestors might have seen an omen. A wandering star, on Friday the thirteenth."),
 ("end3", "We will see a rock, on a path we worked out long in advance."),
 ("end4", "So, on the thirteenth of April, 2029, if the sky is clear, look up. And watch it miss."),
]
TTS_OVERRIDES = {
 "2029": "twenty twenty-nine", "2004": "two thousand and four", "2021": "twenty twenty-one", "2025": "twenty twenty-five",
 "2028": "twenty twenty-eight", "OSIRIS-APEX": "OSIRIS Apex",
 "civilisation": "civilization", "TNT": "T N T",
}
PHONEME_FIXES = {"ɐpˈɑːfɪz": "ɐpˈɑːfɪs", "ɹˈæmsᵻz": "ɹˈæmsiːz"}
def tts_text(t):
    for a, b in TTS_OVERRIDES.items():
        t = t.replace(a, b)
    return t
if __name__ == "__main__":
    import re
    w = sum(len(re.findall(r"[\w'-]+", tts_text(t))) for _, t in LINES)
    print("words", w)
