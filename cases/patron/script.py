# Patron: script + visual plan.  Facts and sources: research.md  (say "credited with" for every count)
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from shots import *
PP = "patron_portrait_2022"

SEG = [
 # ---------------- HOOK
 dict(kind="narr", text="He weighs about four kilograms. Less than a bag of flour. Yet the president of Ukraine gave him a medal.",
      vis=[FULL(P(PP, focus=(0.5, 0.4), z=(1.0, 1.10)), punch=True),
           FULL(P("medal_trudeau_zelensky_40", focus=(0.5, 0.55), z=(1.0, 1.08)), pops=[STAMP("MAY 8, 2022", 0.2)], punch=True)], gap=0.3),
 dict(kind="narr", text="His job? Sniffing out explosives left behind in fields, roads and villages, so families can go home safely.",
      vis=[FULL(P("shestovytsia_sappers_03", focus=(0.5, 0.5), z=(1.0, 1.1)), punch=True),
           SPLIT(P("eod_ukraine_aug2022", focus=(0.5, 0.5)), P("shestovytsia_sappers_05", focus=(0.5, 0.5)), chip1="CHERNIHIV REGION · 2022", chip2="UKRAINE'S RESCUE SERVICE")], gap=0.3),
 dict(kind="narr", text="He's credited with helping find hundreds of them. And he became one of the most famous dogs in the world.",
      vis=[STAT("300+", "EXPLOSIVE OBJECTS FOUND", P("eod_chernihiv_oct2022", focus=(0.5, 0.5)), sub="with his bomb-disposal team · UNICEF, 2023"),
           FULL(P("vyshyvanka", focus=(0.5, 0.4), z=(1.0, 1.08)))], gap=0.3),
 dict(kind="narr", text="This is the true story of Patron.",
      vis=[FULL(P(PP, focus=(0.5, 0.35), z=(1.05, 1.0)))], title=True, gap=0.8),

 # ---------------- CHAPTER 1
 dict(kind="chapter", n=1, text="A Family Dog", bg=P("vyshyvanka", focus=(0.5, 0.4))),
 dict(kind="narr", text="Patron is a Jack Russell terrier, born in July 2019. His name means cartridge, in Ukrainian.",
      vis=[SPLIT(P(PP, focus=(0.5, 0.35)), P("vyshyvanka", focus=(0.5, 0.4)), chip1="PATRON · JACK RUSSELL", chip2="\"PATRON\" = CARTRIDGE")]),
 dict(kind="narr", text="He lives with Mykhailo Iliev, a bomb-disposal specialist with Ukraine's State Emergency Service, in the Chernihiv region, in the north of the country.",
      vis=[MAP("pin", pin="Chernihiv", center="Chernihiv", towns=[("Chernihiv", "CHERNIHIV", "r"), ("Kyiv", "KYIV", "l")], label="NORTHERN UKRAINE", zoom=1.6),
           FULL(P("chernihiv_st_catherine_2011", focus=(0.5, 0.5), z=(1.0, 1.08)), pops=[PIN("CHERNIHIV, UKRAINE", 0.3)])]),
 dict(kind="narr", text="At first, Patron was simply a family pet. Mykhailo had bought him as a puppy for his son.",
      vis=[FULL(P("golden_paw", focus=(0.5, 0.45), z=(1.0, 1.08)))]),

 # ---------------- CHAPTER 2
 dict(kind="chapter", n=2, text="The Nose", bg=P("shestovytsia_sappers_03", focus=(0.5, 0.5))),
 dict(kind="narr", text="Then, in February 2022, war came to Ukraine. When the fighting moved on, it left dangerous explosives behind, near the homes people wanted to return to.",
      vis=[FULL(P("eod_chernihiv_oct2022", focus=(0.5, 0.5), z=(1.0, 1.08))), FULL(P("demining_chernihiv_2023_03", focus=(0.5, 0.5), z=(1.08, 1.0)))]),
 dict(kind="narr", text="Patron finished special training. He learned the smell of gunpowder, and he got used to loud noises.",
      vis=[SPLIT(P("shestovytsia_sappers_05", focus=(0.5, 0.5)), P(PP, focus=(0.5, 0.4)), chip1="TRAINING", chip2="PATRON")]),
 dict(kind="narr", text="When he smells explosives, he barks, or he simply sits and waits. Then the human experts carefully find the item, and make it safe.",
      vis=[FULL(P("eod_ukraine_aug2022", focus=(0.5, 0.5), z=(1.0, 1.1)), pops=[CHIP("HE SIGNALS · HUMANS CLEAR", 0.4)])]),
 dict(kind="narr", text="His vest even has a handle on top, so Mykhailo can lift him away in an instant.",
      vis=[FREEZE(P("us_veteran_awards_1", focus=(0.5, 0.5), z=(1.0, 1.04)), at="@handle", circle=(0.5, 0.5, 0.18), label="THE HANDLE", chip="HIS VEST")]),
 dict(kind="narr", text="And there's one thing he loves more than anything. Cheese. But it was a news conference in Kyiv that made him famous around the world.",
      vis=[FULL(P(PP, focus=(0.5, 0.5), z=(1.12, 1.0)), pops=[CHIP("FAVOURITE TREAT: CHEESE", "@Cheese")]),
           FULL(P("medal_trudeau_zelensky_33", focus=(0.5, 0.5), z=(1.0, 1.08)), pops=[PIN("KYIV", 0.3)])]),

 # ---------------- CHAPTER 3
 dict(kind="chapter", n=3, text="The Medal", bg=P("medal_trudeau_zelensky_41", focus=(0.5, 0.5))),
 dict(kind="narr", text="On May 8th, 2022, Canada's prime minister, Justin Trudeau, was visiting Kyiv. At their joint news conference, President Volodymyr Zelensky presented awards, to a bomb-disposal expert and his dog.",
      vis=[FULL(P("medal_trudeau_zelensky_33", focus=(0.5, 0.45), z=(1.08, 1.0)), pops=[STAMP("MAY 8, 2022", 0.2)]),
           FULL(P("medal_trudeau_zelensky_41", focus=(0.5, 0.5), z=(1.0, 1.08)))]),
 dict(kind="narr", text="Mykhailo received the Order for Courage. And Patron received a medal, for dedicated service.",
      vis=[FREEZE(P("medal_trudeau_zelensky_40", focus=(0.5, 0.5), z=(1.0, 1.04)), at="@Patron", circle=(0.5, 0.7, 0.16), label="THAT'S PATRON", chip="KYIV · MAY 2022")]),
 dict(kind="narr", text="As the cameras rolled, Patron barked. Trudeau laughed, and patted his pockets, as if he was looking for a treat.",
      vis=[FULL(P("medal_trudeau_zelensky_42", focus=(0.5, 0.5), z=(1.0, 1.1)), punch=True)]),
 dict(kind="narr", text="Zelensky called him a small, but very famous sapper.",
      vis=[STAT("\"SMALL BUT VERY FAMOUS\"", "PRESIDENT ZELENSKY", P("medal_trudeau_zelensky_41", focus=(0.5, 0.5)), sub="(translated)")]),

 # ---------------- CHAPTER 4
 dict(kind="chapter", n=4, text="A Hero for Children", bg=P("okhmatdyt_01", focus=(0.5, 0.5))),
 dict(kind="narr", text="Patron has another job, and it may be even more important. He teaches children how to stay safe.",
      vis=[SPLIT(P("okhmatdyt_01", focus=(0.5, 0.5)), P("okhmatdyt_02", focus=(0.5, 0.5)), chip1="OKHMATDYT CHILDREN'S HOSPITAL · KYIV", chip2="SAFETY LESSON")]),
 dict(kind="narr", text="At a children's hospital in Kyiv, he helped share a simple rule. Don't approach. Don't touch. Call 101.",
      vis=[FULL(P("okhmatdyt_03", focus=(0.5, 0.5), z=(1.0, 1.08)), pops=[STAMP("DON'T TOUCH · CALL 101", "@rule")])]),
 dict(kind="narr", text="Later that year, Ukraine's postal service put him on a stamp. It raised about five hundred thousand dollars. Most of it bought a demining machine, and the rest went to animal shelters.",
      vis=[FULL(P("irpin_stamp_day_01", focus=(0.5, 0.5), z=(1.0, 1.08)), pops=[POL(P("stamp_dog_patron", tone="none"), "THE STAMP · 2022", 0.6, pos="br")]),
           FULL(P("demining_machine_2023_01", focus=(0.5, 0.5), z=(1.0, 1.08)), pops=[CHIP("BOUGHT WITH STAMP MONEY", 0.3)])]),
 dict(kind="narr", text="UNICEF named him its first ever Goodwill AmbassaDOG. And by early 2023, UNICEF said Patron had helped find more than three hundred explosive objects.",
      vis=[FULL(P("unicef_youth_dialogue", focus=(0.5, 0.5), z=(1.0, 1.08)), pops=[CHIP("UNICEF · NOV 2022", 0.3)]),
           STAT("300+", "EXPLOSIVE OBJECTS", P("blinken_pets_patron", focus=(0.5, 0.5)), sub="credited, with his team · UNICEF, January 2023")]),

 # ---------------- CHAPTER 5
 dict(kind="chapter", n=5, text="The Truth About Patron", bg=P("sunak_meeting_05", focus=(0.5, 0.5))),
 dict(kind="narr", text="You may have seen posts calling him an army dog. He isn't. He works with the State Emergency Service, a civilian rescue service.",
      vis=[STAT("MYTH", "AN ARMY DOG", P("sunak_meeting_05", focus=(0.5, 0.5))), STAT("FACT", "CIVILIAN RESCUE SERVICE", P(PP, focus=(0.5, 0.4)))]),
 dict(kind="narr", text="And he never works alone. Patron sniffs. The human experts make it safe. Being small makes him less likely to set off a mine, but it never makes the work safe.",
      vis=[SPLIT(P("eod_chernihiv_oct2022", focus=(0.5, 0.5)), P("us_veteran_awards_1", focus=(0.5, 0.5)), chip1="THE TEAM", chip2="PATRON")]),
 dict(kind="narr", text="In December 2024, false reports online said he had died. The rescue service answered right away. Patron is perfectly fine.",
      vis=[FULL(P("power_usaid_2023", focus=(0.5, 0.5), z=(1.0, 1.08)), pops=[STAMP("FAKE NEWS · DEC 2024", 0.3)])]),
 dict(kind="narr", text="Let's look at everything he's done. A family pet. A medal from a president. A stamp that bought a demining machine. And hundreds of explosives found, with his team.",
      vis=[BOARD([(P(PP, focus=(0.5, 0.35)), "FAMILY PET"), (P("medal_trudeau_zelensky_40"), "THE MEDAL"), (P("stamp_dog_patron", tone="none"), "THE STAMP"),
                  (P("okhmatdyt_01"), "TEACHING KIDS")], notes=[("4 KG", "OF COURAGE"), ("300+", "FOUND"), ("$500K", "RAISED")])]),
 dict(kind="narr", text="And in 2026, according to his official Instagram, Patron became a father. Of seven puppies.",
      vis=[FULL(P("vyshyvanka", focus=(0.5, 0.4), z=(1.0, 1.1)), pops=[STAMP("2026: 7 PUPPIES", "@father")])]),
 dict(kind="narr", text="He's small enough to lift with one hand. But he helped make his homeland safer, one sniff at a time.",
      vis=[FULL(P(PP, focus=(0.5, 0.35), z=(1.0, 1.12)))], gap=1.0),
 dict(kind="narr", text="If this story made you smile, subscribe for more true stories of incredible dogs.",
      vis=[CTA(0, P("golden_paw", focus=(0.5, 0.45)))]),
 dict(kind="narr", text="And tell us in the comments. What is your dog's secret talent?",
      vis=[CTA(1, P("vyshyvanka", focus=(0.5, 0.45)))], gap=1.2),
]
