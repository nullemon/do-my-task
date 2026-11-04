# Narration for "MEGALODON TO SCALE". (key, subtitle text). Timing is locked after TTS (timeline.py).
LINES = [
 ("hook1", "Megalodon. The largest predatory shark that has ever lived."),
 ("hook2", "But how big was it, really? Let's find out, with everything drawn to true scale."),
 ("diver", "First, a ruler. A diver: about one point eight metres tall. Every animal you'll see is drawn to the same scale as this person."),
 ("bull", "A bull shark. The largest females reach around three and a half metres."),
 ("gw1", "A great white. Most adults are four to five metres long. The biggest reliably measured, about six."),
 ("gw2", "For a long time, this was the shape scientists imagined for megalodon: a great white, scaled up."),
 ("bus", "A school bus. Twelve metres."),
 ("ws", "A whale shark, the largest fish alive today. Big adults reach about twelve metres. The largest reliable record is close to nineteen. It feeds on plankton."),
 ("orca", "An orca. Large males reach about eight metres. Today, it is the ocean's top predator."),
 ("hump", "A humpback whale. Around fifteen metres, with flippers a third as long as its body."),
 ("megA", "And now... megalodon."),
 ("megB", "Here is the honest part. No complete skeleton has ever been found. A shark's skeleton is cartilage, and cartilage rarely fossilises. What survives are teeth, and a few rare columns of vertebrae."),
 ("teeth", "The teeth are enormous. The largest are around eighteen centimetres long, about the length of a human hand."),
 ("est1", "For decades, size estimates scaled a great white up from those teeth: fifteen metres, eighteen, perhaps twenty."),
 ("est2", "Then came a column of a hundred and forty-one vertebrae from Belgium, all from one animal. Eleven metres of backbone, without its head or tail."),
 ("age", "Growth rings in those vertebrae, like the rings of a tree, say this shark was about forty-six years old when it died."),
 ("est3", "Studies in twenty twenty-four and twenty twenty-five argued that megalodon was not a giant great white at all. It was probably longer and slimmer, closer in shape to a lemon shark."),
 ("best", "On that reading, the Belgian shark was about sixteen metres long. That is our best-grounded figure for a real individual."),
 ("ceil", "Larger ones certainly existed. A single huge vertebra from Denmark suggests some may have reached twenty-four metres. The researchers call that the upper limit the evidence can support. Most were smaller."),
 ("time", "Megalodon lived from about twenty-three million to three point six million years ago, in warm seas across much of the world."),
 ("bite", "Computer models suggest a bite of more than ten tonnes of force. But those are models, built by scaling up a great white."),
 ("warm", "Chemistry locked in its teeth suggests it was partly warm-blooded, about seven degrees warmer than the water around it. A powerful engine, that needed enormous amounts of food."),
 ("ext", "Then, it vanished. The likely causes: a cooling climate and falling seas that shrank the shallow nurseries where its young were born; changes in the whales it hunted; and a newcomer competing for the same prey. The great white."),
 ("myth", "And it is gone. It is not hiding in the deep. Its pups grew up in shallow coastal water, and its teeth fill the fossil record, until about three and a half million years ago. Then, nothing. The television specials that said otherwise were fiction."),
 ("twist", "But megalodon was not the largest animal of all time."),
 ("blue", "That animal is alive today. The blue whale. Up to about thirty metres long, and well over a hundred tonnes."),
 ("peru", "In twenty twenty-three, a fossil whale from Peru, Perucetus, was proposed as possibly even heavier. Later work challenged that estimate. For now, the blue whale still holds the record."),
 ("end1", "The largest predator the sea has ever known is gone."),
 ("end2", "For almost twenty million years, it passed over everything in the ocean."),
 ("end3", "Then, one day, it didn't."),
]
TTS_OVERRIDES = {
 "Perucetus": "Peru-seetus",
 "fossilises": "fossilizes",
}
PHONEME_FIXES = {}
def tts_text(t):
    for a, b in TTS_OVERRIDES.items():
        t = t.replace(a, b)
    return t
if __name__ == "__main__":
    import re
    w = sum(len(re.findall(r"[\w'-]+", t)) for _, t in LINES)
    print("words", w)
