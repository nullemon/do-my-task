# Narration for "IF THE SUN VANISHED RIGHT NOW". (key, subtitle text). Timing is locked after TTS (timeline.py).
LINES = [
 ("hook1", "The Sun has just vanished. And for eight minutes and twenty seconds, you will not notice a thing."),
 ("hook2", "Not exploded. Not burned out. Simply gone. This is what happens next, minute by minute."),
 ("still", "For now, nothing changes. The Sun is still up there in the sky, shining. You are looking at light that had already left it, and that light takes eight minutes and twenty seconds to cross the gap."),
 ("grav", "Stranger still, the Earth keeps circling a star that is no longer there. Gravity is not instant. Changes in it travel at the speed of light, too. So for eight minutes, our planet orbits an empty point in space."),
 ("dark", "Eight minutes, twenty seconds. The last light arrives. And the whole day side of the Earth goes dark at once."),
 ("line", "At the same moment, the Sun's pull lets go. The Earth stops curving, and leaves in a straight line, at about thirty kilometres every second. The Moon comes with us."),
 ("moon", "But the Moon only ever shone by reflected sunlight. Within about two seconds, it fades out."),
 ("plan1", "The planets shine the same way. But they are far away, and their last reflected light is still travelling towards us. So they linger."),
 ("plan2", "Venus and Mars go out within about half an hour. Jupiter keeps shining for more than an hour. Saturn, for more than two."),
 ("stars", "Then, only the stars are left. They are suns in their own right. And they haven't noticed a thing."),
 ("photo", "On the ground, photosynthesis stops. Every plant on Earth, and the plankton in the sea, has lost its only source of energy. Small plants die within weeks. Large trees, living on stored sugar, might last for years, if they didn't freeze first."),
 ("cold1", "Because the cold comes quickly. With nothing to replace it, the planet's heat leaks away into space."),
 ("cold2", "These are rough estimates. But within about a week, the average surface temperature falls below freezing. The most quoted figure is around minus eighteen degrees Celsius. Within a year, around minus seventy. Colder than a winter at the South Pole."),
 ("human", "A few people might hold out, gathered around heat that never came from the Sun: nuclear reactors, and the warmth of the Earth itself."),
 ("ocean", "The oceans freeze over, from the top down. But ice floats, and it insulates. Beneath that lid, kilometres of water stay liquid. By one estimate, for hundreds of thousands of years."),
 ("vents", "And down there, in the dark, some life would barely notice. Around hydrothermal vents, microbes live on chemical energy rising from inside the planet. Of everything alive on Earth, they have the best chance of carrying on."),
 ("air1", "Above the ice, it keeps getting colder. Eventually, and here the estimates run from decades to far longer, the air itself begins to condense."),
 ("air2", "At normal pressure, oxygen turns liquid at minus one hundred and eighty-three degrees. Nitrogen follows, at minus one hundred and ninety-six. The sky falls as rain. Then, as snow."),
 ("floor", "Millions of years on, the Earth settles near minus two hundred and forty degrees, held just above absolute zero by the slow leak of heat from its own interior."),
 ("drift", "And so the Earth drifts on. A dark, frozen world. One more wanderer among the stars."),
 ("real1", "None of this is going to happen. A star cannot simply disappear. The laws of physics do not let that much matter and energy vanish."),
 ("real2", "Our Sun is about halfway through its life, with roughly five billion years of steady light still ahead."),
 ("end", "So tomorrow morning, when it rises, remember: that light is eight minutes old. And everything alive here depends on it."),
]
TTS_OVERRIDES = {}
PHONEME_FIXES = {}
def tts_text(t):
    for a, b in TTS_OVERRIDES.items():
        t = t.replace(a, b)
    return t
if __name__ == "__main__":
    import re
    w = sum(len(re.findall(r"[\w'-]+", t)) for _, t in LINES)
    print("words", w)
