# Narration for 06 "THE 524-METRE WAVE" (Lituya Bay, Alaska, 9 July 1958).
# (shot, pause_before_s, text). Voice is generated first; start times are then derived
# sequentially (previous line end + pause * F) and locked in placement.json -> visuals + mix.
LINES = [
 ("open",   1.0, "On a summer night in 1958, the water in this bay climbed five hundred and twenty-four metres up a mountainside."),
 ("open",   1.4, "Higher than the Empire State Building. The highest wave run-up ever recorded."),
 ("map",    4.2, "Lituya Bay is a narrow fjord on the remote coast of southeast Alaska, carved by glaciers. A long gravel spit almost closes its mouth."),
 ("map",    1.2, "At its head, the bay forms a T. The crossbar is a trench along the Fairweather Fault, where the Pacific and North American plates grind past each other."),
 ("map",    1.0, "Glaciers flow down into both arms of the T."),
 ("night",  2.0, "On the ninth of July, three fishing boats lay at anchor near the entrance. It was after ten at night, but this far north in midsummer, the sun had only just set. The sky stayed pale."),
 ("night",  1.4, "On the Edrie, Howard Ulrich and his young son, Sonny. On the Badger, Bill and Vivian Swanson. On the Sunmore, Orville and Mickey Wagner."),
 ("quake",  2.4, "At about a quarter past ten, the Fairweather Fault ruptured. A magnitude seven point eight earthquake."),
 ("slide",  1.4, "At the head of the bay, in an arm called Gilbert Inlet, the shaking broke loose part of a mountain wall."),
 ("slide",  1.0, "About thirty million cubic metres of rock fell, from as high as nine hundred metres, straight into the water."),
 ("surge",  2.2, "The impact drove the water of the inlet across to the opposite shore. And up."),
 ("surge",  1.0, "It tore up the facing slope, through old spruce forest, to a height of five hundred and twenty-four metres."),
 ("surge",  1.2, "Trees were snapped off or ripped out by the roots. In places, the soil itself was scoured away, down to bare rock."),
 ("scale",  2.4, "To picture that height: the Eiffel Tower stands three hundred and thirty metres tall. The Empire State Building, to the tip of its antenna, four hundred and forty-three."),
 ("scale",  1.2, "The water went higher than both. Around eighty metres higher than the antenna."),
 ("runup",  2.4, "It's worth being precise. Five hundred and twenty-four metres is the run-up: how high the water reached on land, above sea level."),
 ("runup",  1.0, "The wave itself was lower. Laboratory models suggest roughly a hundred and fifty metres where it struck the slope. Its momentum carried it the rest of the way."),
 ("ocean",  1.8, "And it was not a classic tsunami. Those are usually born when an earthquake heaves the sea floor, and they can cross entire oceans."),
 ("ocean",  1.0, "This was a giant splash. A landslide, slamming into a narrow, enclosed bay. Catastrophic inside it. Outside, it spread out and quickly lost its power."),
 ("bay",    2.2, "From the head of the bay, the wave raced toward the entrance. Still tens of metres high. By some estimates, faster than a hundred and fifty kilometres an hour."),
 ("boats",  1.6, "Howard Ulrich saw it coming. He let out his anchor chain and turned the Edrie to face it."),
 ("boats",  1.0, "The wave lifted the boat, snapped the chain, and threw it toward the shore, then swept it back into the bay. Father and son survived."),
 ("boats",  1.4, "The Badger was carried right over the spit, out to sea. It sank. The Swansons escaped in a small skiff and were picked up by another fishing boat."),
 ("boats",  1.4, "The Sunmore had tried to run for the open ocean. It was never seen again. Orville and Mickey Wagner were lost."),
 ("miller", 3.0, "Soon after, the geologist Don Miller of the U.S. Geological Survey photographed the bay. Its shores were ringed by a sharp line: forest above, raw ground below. A trimline."),
 ("miller", 1.2, "He found older trimlines too. Giant waves had swept the bay at least four times in a little more than a century."),
 ("science",1.8, "Decades later, scientists rebuilt Gilbert Inlet as a laboratory model, at one six-hundred-and-seventy-fifth scale. Its model wave ran up to the height of the real trimline."),
 ("science",1.0, "Computer simulations since then have reproduced the run-up too."),
 ("risk",   2.4, "And the danger is not only in the past. As glaciers thin and retreat, they can leave steep valley walls without support."),
 ("risk",   1.2, "In 2015, in Taan Fiord, Alaska, a landslide sent water a hundred and ninety-three metres up a slope."),
 ("risk",   1.2, "In Barry Arm, in Prince William Sound, a slowly creeping slope of hundreds of millions of cubic metres hangs above a fjord. A worst-case model suggests run-up of more than five hundred metres. Scientists are watching it closely."),
 ("end",    2.8, "In Lituya Bay, the forest has grown back. But the line is still there, if you know where to look."),
 ("end",    1.6, "A mark on the mountain, five hundred and twenty-four metres up."),
 ("end",    1.2, "The height of one night's water."),
]
TTS_OVERRIDES = {
 "in 1958,": "in nineteen fifty-eight,",
 "In 2015,": "In twenty fifteen,",
 "Taan Fiord": "Tahn Fjord",
 "U.S.": "U.S.",
 "Ulrich": "Ulrick",
 "Sunmore": "Sun-more",
 "Edrie": "Edree",
 "run-up": "run up",
}
PHONEME_FIXES = {"fɪˈɔːɹd": "fjˈɔːɹd"}


def tts_text(t):
    for a, b in TTS_OVERRIDES.items():
        t = t.replace(a, b)
    return t


if __name__ == "__main__":
    n = sum(len(l[2].split()) for l in LINES)
    print("lines", len(LINES), "words", n)
