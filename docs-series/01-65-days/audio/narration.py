# Narration for "65 DAYS". Each entry: (key, text shown in subtitles). Timing is locked after TTS (timeline.py).
LINES = [
 ("hook1", "If the Earth suddenly stopped moving around the Sun, we would fall into it."),
 ("hook2", "It would take about sixty-five days."),
 ("setup1", "Right now, Earth is racing along its orbit at thirty kilometres every second. That sideways speed is the only thing that keeps us from falling in."),
 ("setup2", "Nothing could actually stop a planet. This is a thought experiment. But suppose that tonight, somehow, it simply stopped."),
 ("day1", "Day one. The Sun rises, exactly as it always has."),
 ("day1b", "We are already falling. By tonight we're moving at half a kilometre per second, and no one can feel a thing."),
 ("day10", "Day ten. We've fallen two million kilometres. The Sun is two percent wider. Nobody could tell."),
 ("seasons", "Without an orbit, the seasons freeze. Wherever it was summer, it stays summer."),
 ("day30", "Day thirty. A whole month has gone by, and we've covered only one seventh of the way."),
 ("day30b", "But sunlight is already a third stronger. On a rough estimate, the world is heading toward an average of nearly forty degrees Celsius."),
 ("accel1", "Here's the cruel part. Gravity grows stronger the closer you get, so the fall keeps speeding up."),
 ("accel2", "The first half of the distance takes fifty-three days. The second half takes less than twelve."),
 ("venus", "Day forty-two. We cross the orbit of Venus. Sunlight is twice as strong as when we started."),
 ("venusb", "Across most of the planet, simply being outdoors would now be deadly."),
 ("mercury", "Day fifty-seven. Mercury's orbit. It took fifty-seven days to get here. From here to the Sun: one more week."),
 ("moon", "The Moon is still with us. In these last days, the Sun's pull begins to tear it away from Earth. But it can't escape. It's falling too."),
 ("flips", "By the end of day sixty, sunlight is twelve times stronger. Day sixty-two: twenty-five times. Day sixty-three: nearly fifty."),
 ("hours13", "Sixty-four days have passed. Thirteen hours remain. We're moving at a hundred and fifty kilometres every second."),
 ("hours8", "Eight hours left. The Sun is nearly twenty times wider than it used to be."),
 ("oceans", "Even now, the oceans haven't boiled away. They're too deep. All the sunlight Earth absorbs on the entire fall could boil off only the top fifteen metres or so."),
 ("hour1", "One hour left. The Sun is seventy times wider than it used to be."),
 ("granules", "If anyone could still look, they'd see its surface churning: cells of glowing plasma, each about the size of a country."),
 ("tides", "In the final minutes, the Sun's tides would begin to stretch the planet itself."),
 ("impact", "We arrive at more than six hundred kilometres per second, almost exactly the speed you'd need to escape the Sun. At that speed, Earth crosses its own width in twenty seconds."),
 ("after", "And the Sun would barely notice. Earth is less than a three-hundred-thousandth of its mass."),
 ("end1", "None of this will happen. But here is the strange part: we are falling toward the Sun right now."),
 ("end2", "We always have been. An orbit is just a fall, with enough sideways speed to keep missing."),
 ("end3", "For four and a half billion years, Earth has been falling around the Sun, and missing."),
]
TTS_OVERRIDES = {}
PHONEME_FIXES = {}
def tts_text(t):
    for a, b in TTS_OVERRIDES.items():
        t = t.replace(a, b)
    return t
