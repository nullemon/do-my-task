# Narration for "ONE LIGHT-DAY FROM HOME". (key, subtitle text). Timing is locked after TTS (timeline.py).
LINES = [
 ("hook1", "The most distant thing humans have ever built is about to be one full day away. At the speed of light."),
 ("hook2", "On the eighteenth of November, twenty twenty-six, by NASA's calculation, Voyager 1 reaches one light-day from Earth. Nearly twenty-six billion kilometres."),
 ("light", "Light crosses to the Moon in just over a second. To the Sun, in eight minutes. To Neptune, in about four hours. To Voyager: twenty-four."),
 ("launch", "It left on the fifth of September, nineteen seventy-seven, on a Titan rocket from Cape Canaveral. A machine built to last five years."),
 ("jupiter", "Eighteen months later it swept past Jupiter, and found volcanoes erupting on the moon Io: the first active volcanoes ever seen beyond Earth."),
 ("saturn", "In November nineteen eighty, Saturn. A close pass by its giant moon, Titan, bent Voyager's path up and out of the plane of the planets. No more worlds lay ahead."),
 ("pbd1", "But in nineteen ninety, at the urging of the astronomer Carl Sagan, its cameras were turned around one last time. From six billion kilometres away, Earth was a point of light, smaller than a single pixel."),
 ("pbd2", "A pale blue dot, Sagan called it. A mote of dust, suspended in a sunbeam. Half an hour later, the cameras were switched off for good."),
 ("helio", "Voyager kept going. In August twenty twelve, it crossed the boundary where the wind from the Sun gives way to the thin gas between the stars. It became the first human-made object in interstellar space."),
 ("record1", "Bolted to its side is a message. A gold-plated copper record, with instructions for playing it engraved on the cover."),
 ("record2", "It holds a hundred and fifteen images, greetings in fifty-five languages, the sounds of surf, thunder, birdsong and whales, and ninety minutes of music, from Bach to Chuck Berry."),
 ("signal1", "And Voyager is still talking to us. Its transmitter has a power of about twenty-three watts. Roughly that of a refrigerator light bulb."),
 ("signal2", "By the time that signal reaches Earth, it is far weaker than a billionth of a billionth of a watt. To hear it, NASA's Deep Space Network uses dishes seventy metres across, in California, Spain and Australia. The data trickles in at a hundred and sixty bits per second."),
 ("power1", "Its electricity comes from the heat of decaying plutonium, and every year there are about four watts less. So the team has been switching things off, one by one. Of ten science instruments, two are still running."),
 ("power2", "This year, engineers shut down one more, and reworked the power system to buy some time. Every command now takes a day to arrive. The answer takes another day to come back."),
 ("scale1", "So here is the scale of it. Almost fifty years of flight, at about seventeen kilometres every second. And the distance covered is one light-day."),
 ("scale2", "The nearest star is more than four light-years away. That is over fifteen hundred light-days. At Voyager's speed, the journey would take about seventy-five thousand years."),
 ("scale3", "And Voyager is not even heading that way. In about forty thousand years, it will drift within a light-year and a half of another star, and sail on."),
 ("end1", "Probably within the next ten years, the power will fall too low, and Voyager will go quiet."),
 ("end2", "But it will not stop. Nothing out there will slow it down. And the record on its side is expected to last a billion years."),
 ("end3", "One light-day from home. And still going."),
]
TTS_OVERRIDES = {"Voyager 1": "Voyager One", "Io:": "Eye-oh:"}
PHONEME_FIXES = {}
def tts_text(t):
    for a, b in TTS_OVERRIDES.items():
        t = t.replace(a, b)
    return t
if __name__ == "__main__":
    import re
    print("words", sum(len(re.findall(r"[\w'-]+", t)) for _, t in LINES))
