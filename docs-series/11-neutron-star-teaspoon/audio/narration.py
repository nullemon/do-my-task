# Narration for "ONE TEASPOON OF A NEUTRON STAR". (key, subtitle text). Timing is locked after TTS (timeline.py).
LINES = [
 ("hook1", "This is one teaspoon. Five millilitres. Fill it with matter from inside a neutron star, and it would outweigh a mountain."),
 ("hook2", "Billions of tonnes. More than every human being on Earth, combined. So what would it do, if you brought it home?"),
 ("hook3", "The honest answer is stranger than the question."),
 ("form1", "It begins with a giant star, at least eight times the mass of our Sun. For millions of years it shines. Then its core fills with iron, and iron gives no energy back."),
 ("form2", "The fire goes out. In less than a second, a core thousands of kilometres wide falls in on itself, to a ball about twenty kilometres across. The rest of the star is blown into space. A supernova."),
 ("size1", "What is left behind is a neutron star. Here is one, to scale, above New York. About twenty-five kilometres across. A little longer than Manhattan."),
 ("size2", "And packed inside that sphere is more mass than the entire Sun."),
 ("dens1", "Ordinary atoms are almost entirely empty space. Here, that space has been crushed out. Electrons and protons are forced together into neutrons, packed about as tightly as the inside of an atomic nucleus."),
 ("dens2", "That is where the teaspoon comes from. Near the surface, the crust is far less dense. But averaged through the whole star, five millilitres holds about two billion tonnes. Deep in the core, perhaps five billion, or more."),
 ("grav1", "Gravity at the surface is around a hundred billion times stronger than on Earth. Drop something from one metre, and it lands in about a millionth of a second, at well over a thousand kilometres per second."),
 ("grav2", "To leave again, you would need more than half the speed of light. Gravity here is strong enough to bend light itself, so you can see part of the star's far side."),
 ("spin1", "And they spin. Beams of radiation sweep out from the magnetic poles, and if one crosses the Earth, we see a pulse. A pulsar."),
 ("spin2", "The fastest one known turns seven hundred and sixteen times every second. Its equator moves at nearly a quarter of the speed of light."),
 ("mag", "Some, called magnetars, carry magnetic fields around a thousand trillion times stronger than the Earth's. The strongest magnets known."),
 ("ans1", "So. The teaspoon. Here is the problem: you could not scoop it. This matter is only that dense because the weight of an entire star is pressing down on it."),
 ("ans2", "Take a spoonful away from that gravity, and nothing holds it together. It would expand, instantly, and violently. By rough estimates, the blast would dwarf the asteroid impact that ended the age of the dinosaurs."),
 ("thought1", "But suppose, purely as a thought experiment, that it somehow stayed compressed. A bead about two centimetres wide, weighing billions of tonnes."),
 ("thought2", "Within a few metres of it, its gravity would pull on you harder than the whole Earth does. And no spoon, no floor, no bedrock could hold it up."),
 ("thought3", "It would fall straight through the ground, and the planet would barely slow it. Down to the centre in about twenty minutes. On, almost to the far side. And back. Again, and again, through the heart of the world."),
 ("kilo1", "Sometimes, though, neutron stars really do give their matter back. When two of them orbit each other, they spiral together over millions of years, and collide."),
 ("kilo2", "On the seventeenth of August, 2017, detectors on Earth felt the ripples in space from exactly that: a merger, a hundred and thirty million light-years away. Then telescopes watched the wreckage glow. A kilonova."),
 ("kilo3", "This time, the matter did escape. And as it expanded, it forged heavy elements. Gold and platinum among them: by some estimates, several times the mass of the Earth in gold alone."),
 ("gold", "So the gold in a wedding ring was very likely made like this. In the collision of dead stars."),
 ("end1", "A neutron star is the densest matter we can observe. Add a little more mass, and nothing can hold it up at all. It becomes a black hole."),
 ("end2", "So you were never going to hold a teaspoon of a neutron star. But you may already be wearing a little of one."),
]
TTS_OVERRIDES = {"2017": "twenty seventeen", "millilitres": "milliliters", "kilometres": "kilometers", "metres": "meters", "metre,": "meter,", "centimetres": "centimeters"}
PHONEME_FIXES = {}
def tts_text(t):
    for a, b in TTS_OVERRIDES.items():
        t = t.replace(a, b)
    return t
