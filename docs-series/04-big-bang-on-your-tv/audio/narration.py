# Narration for 04 "THE BIG BANG IS ON YOUR TV".
# (shot, pause_before_s, text). Voice is generated first; absolute start times are then derived
# sequentially (previous line end + pause) and locked in placement.json -> timeline for the visuals.
LINES = [
 ("room",   1.0, "Some of this static is left over from the Big Bang."),
 ("room",   2.2, "If you grew up with an old television, you've seen it. Between the channels: a hissing, crawling snow."),
 ("room",   1.6, "Most of it was made right here on Earth. Warm electronics inside the set. Distant transmitters. Even the Sun."),
 ("room",   1.4, "But a tiny part of it, often quoted as about one percent, though it was never precisely measured, came from much, much farther away."),
 ("push",   1.6, "It is the oldest light in the universe."),
 ("fog",    3.2, "Go back nearly fourteen billion years. The young universe is a hot, dense fog of charged particles. Light can't travel far before it's scattered."),
 ("fog",    1.4, "Then, about three hundred and eighty thousand years after the Big Bang, the fog cools to around three thousand degrees."),
 ("fog",    1.2, "Electrons settle onto atoms. And for the first time, light breaks free."),
 ("fog",    1.2, "The whole universe glows like the surface of a cool star: a dull orange light, everywhere at once."),
 ("stretch",2.4, "That light has been travelling ever since. And as space expanded, it stretched the light along with it."),
 ("stretch",1.2, "Orange became red. Red became infrared. The waves grew about a thousand times longer, until the glow was invisible: microwaves."),
 ("stretch",1.4, "Today it is just two point seven degrees above absolute zero. And it reaches us from every direction in the sky."),
 ("stretch",1.4, "Roughly four hundred of these ancient photons fill every cubic centimetre of space. Including the room you're sitting in."),
 ("stretch",1.6, "An old TV antenna, tuned to nothing, catches a faint whisper of it."),
 ("horn",   2.4, "In 1964, at Bell Labs in New Jersey, Arno Penzias and Robert Wilson were testing a giant horn-shaped antenna."),
 ("horn",   1.0, "It had been built to catch faint signals from the first communication satellites. It was one of the quietest radio receivers on Earth."),
 ("horn",   1.2, "They found a faint hiss they couldn't get rid of. Day or night. Whichever way they pointed it."),
 ("horn",   1.2, "They even evicted a pair of nesting pigeons, and cleaned out what Penzias politely called \"white dielectric material\"."),
 ("horn",   1.4, "The hiss remained. Nearby, at Princeton, physicists had been preparing to search for exactly this: the afterglow of a hot beginning."),
 ("horn",   1.2, "When their leader, Robert Dicke, heard about the Bell Labs hiss, he reportedly told his team: \"Boys, we've been scooped.\""),
 ("horn",   1.2, "In 1978, Penzias and Wilson shared the Nobel Prize in Physics."),
 ("map",    2.4, "Since then, the COBE, WMAP and Planck spacecraft have mapped this glow across the whole sky."),
 ("map",    1.2, "It is almost perfectly smooth. Its tiny ripples, about one part in a hundred thousand, are the seeds of everything that came later."),
 ("map",    1.2, "The warmer and cooler spots trace places that were very slightly denser or thinner than average. Over billions of years, gravity pulled the denser places together."),
 ("map",    1.0, "Galaxies. Stars. Planets. Us."),
 ("return", 2.6, "Today, analog television is gone from most of the world. The United States switched off full-power analog broadcasts in 2009. The UK finished in 2012."),
 ("return", 1.2, "And with it, this little window to the beginning of time quietly disappeared from our homes."),
 ("end",    5.0, "The oldest light in the universe."),
 ("end",    1.4, "And we used to just change the channel."),
]
TTS_OVERRIDES = {
 "In 1964,": "In nineteen sixty-four,",
 "In 1978,": "In nineteen seventy-eight,",
 "in 2009.": "in two thousand and nine.",
 "in 2012.": "in twenty twelve.",
 "Dicke": "Dicky",
 "COBE": "Koh-bee",
 "WMAP": "W-map",
 "Big Bang": "Big Bang",
 "analog": "analog",
 "the UK": "the U.K.",
}
PHONEME_FIXES = {}
def tts_text(t):
    for a, b in TTS_OVERRIDES.items():
        t = t.replace(a, b)
    return t
