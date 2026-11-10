# Narration for "THE MOON IS LEAVING". (key, subtitle text). Timing is locked after TTS (timeline.py).
LINES = [
 ("hook1", "Every year, the Moon moves about three point eight centimetres farther from the Earth. Roughly the speed at which your fingernails grow."),
 ("hook2", "It has been leaving for more than four billion years. And one day, because of it, the Earth will see its last total eclipse of the Sun."),
 ("laser1", "We know the rate because we measure it. Apollo astronauts, and two Soviet Lunokhod rovers, left reflectors on the lunar surface: panels of glass prisms that send light straight back to where it came from."),
 ("laser2", "Observatories on Earth fire laser pulses at them, and time the echo. The round trip takes about two and a half seconds. Of all the light in each pulse, only a few photons make it back. But that is enough to track the distance to the Moon to within millimetres."),
 ("tide1", "So why is it leaving? The answer is the tides. The Moon's gravity stretches the Earth, raising a bulge of ocean on the side facing it, and another on the far side."),
 ("tide2", "But the Earth spins much faster than the Moon orbits, so it carries that bulge ahead of the Moon. The bulge's own gravity tugs the Moon forward, and lifts it, very slowly, into a wider orbit."),
 ("tide3", "In return, the Moon pulls back on the bulge, like a brake. The spin the Earth loses, the Moon gains."),
 ("day1", "So our days are getting longer. Tides alone should add about two point three milliseconds every century. The measured figure, from eclipse records reaching back twenty-seven centuries, is nearer one point eight."),
 ("past1", "It does not sound like much. But run the clock backwards. Seventy million years ago, in the last days of the dinosaurs, a fossil shell recorded a year of about three hundred and seventy-two days. Each one, about twenty-three and a half hours long."),
 ("past2", "Go back roughly four hundred million years, and corals were laying down about four hundred daily growth lines every year. A day lasted less than twenty-two hours."),
 ("origin1", "And at the very beginning, about four and a half billion years ago, the leading theory says a body the size of Mars struck the young Earth. The debris gathered into a Moon that orbited more than ten times closer than it does today."),
 ("origin2", "It would have hung in the sky more than ten times wider than the Moon we know, above a world that may have turned once every few hours."),
 ("ecl1", "Which brings us to a coincidence. The Sun is about four hundred times wider than the Moon. It is also about four hundred times farther away. So in our sky, the two discs are almost exactly the same size."),
 ("ecl2", "When they line up, the Moon covers the Sun's blinding face, and almost nothing more. Beads of sunlight shine through lunar valleys. A last diamond flares. And then, the corona: the Sun's outer atmosphere, visible to the naked eye only in these few minutes."),
 ("ecl3", "But the fit is already imperfect. When the Moon is at the far end of its orbit, it is too small, and leaves a ring of sunlight. An annular eclipse."),
 ("fut1", "As the Moon retreats, those rings will become the rule. In roughly six hundred million years, though estimates vary, the Moon will cover the Sun completely for the last time. After that, every eclipse will be partial, or a ring of fire."),
 ("far1", "Will the Moon ever escape? No. The retreat would only end when the Earth's day had slowed to match the Moon's month. That would take tens of billions of years. The Sun will swell into a red giant in about five billion. The process will never finish."),
 ("pay1", "So consider the timing. For most of Earth's history, the Moon was larger than it needed to be. In the far future, it will be too small. We happen to live in between, in the long window when the Moon fits the Sun."),
 ("pay2", "It is still leaving. Three point eight centimetres this year. And the next."),
 ("pay3", "So when totality next crosses your part of the world, go and stand in the shadow. It will not always be there."),
]
TTS_OVERRIDES = {"centimetres": "centimeters", "Lunokhod": "Loonokod"}
PHONEME_FIXES = {}
def tts_text(t):
    for a, b in TTS_OVERRIDES.items():
        t = t.replace(a, b)
    return t
if __name__ == "__main__":
    import re
    w = sum(len(re.findall(r"[\w'-]+", tts_text(t))) for _, t in LINES)
    print("words", w)
