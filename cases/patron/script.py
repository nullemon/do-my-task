# Patron: script + visual plan.  Facts and sources: research.md  (say "credited with" for every count)
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from shots import *
PP = "patron_portrait_2022"
DS = "State Emergency Service of Ukraine · CC BY 4.0"
def v(k, a, b, cr=DS): return F(k, a, b, credit=cr)
def pv(a, b): return v("eod_video_chernihiv_apr2022", a, b)
def b21(a, b): return v("vid_bomb_disposal_chernihiv_21apr", a, b)
def b9(a, b): return v("vid_bomb_disposal_chernihiv_9mar", a, b)
def e20(a, b): return v("vid_eod_chernihiv_20mar", a, b)
def km(a, b): return v("vid_eod_kyiv_march_compilation", a, b, "Ministry of Internal Affairs of Ukraine · CC BY 4.0")
def nb(a, b): return v("vid_nova_basan_demining", a, b, "Ukrinform · CC BY 4.0")
def rb(a, b): return v("vid_rockets_chernihiv_beach", a, b)
def ss(a, b): return v("vid_shestovytsia_sappers", a, b)
def ti(a, b): return v("vid_trudeau_irpin_0508", a, b, "Office of the President of Ukraine · CC BY 4.0")
def mz(a, b): return v("vid_chernihiv_mazepa_house", a, b, "Chernihiv · Wikimedia Commons · CC BY-SA 4.0")
def stn(a, b): return v("vid_chernihiv_station_drone", a, b, "Chernihiv railway station · Wikimedia Commons · CC BY-SA 4.0")
REALP = "REAL VIDEO · PATRON AT WORK, 2022"

SEG = [
 # ---------------- HOOK
 dict(kind="narr", text="He weighs about four kilograms. Less than a bag of flour. Yet the president of Ukraine gave him a medal.",
      vis=[FULL(pv(0.5, 5.5), punch=True, pops=[CHIP(REALP, 0.2, color="dark")]),
           FULL(P("medal_trudeau_zelensky_40", focus=(0.5, 0.55), z=(1.0, 1.08)), pops=[STAMP("MAY 8, 2022", 0.2)], punch=True)], gap=0.3),
 dict(kind="narr", text="His job? Sniffing out explosives left behind in fields, roads and villages, so families can go home safely.",
      vis=[FULL(nb(20.0, 27.0), punch=True),
           SPLIT(ss(6.0, 13.0), P("shestovytsia_sappers_05", focus=(0.5, 0.5)), chip1="CHERNIHIV REGION · 2022", chip2="UKRAINE'S RESCUE SERVICE")], gap=0.3),
 dict(kind="narr", text="He's credited with helping find hundreds of them. And he became one of the most famous dogs in the world.",
      vis=[STAT("300+", "EXPLOSIVE OBJECTS FOUND", nb(110.0, 117.0), sub="with his bomb-disposal team · UNICEF, 2023"),
           FULL(P("vyshyvanka", focus=(0.5, 0.4), z=(1.0, 1.08)))], gap=0.3),
 dict(kind="narr", text="This is the true story of Patron.",
      vis=[FULL(pv(6.0, 11.0))], title=True, gap=0.8),

 # ---------------- CHAPTER 1
 dict(kind="chapter", n=1, text="A Family Dog", bg=P("vyshyvanka", focus=(0.5, 0.4))),
 dict(kind="narr", text="Patron is a Jack Russell terrier, born in July 2019. His name means cartridge, in Ukrainian.",
      vis=[SPLIT(P(PP, focus=(0.5, 0.35)), P("vyshyvanka", focus=(0.5, 0.4)), chip1="PATRON · JACK RUSSELL", chip2="\"PATRON\" = CARTRIDGE")]),
 dict(kind="narr", text="He lives with Mykhailo Iliev, a bomb-disposal specialist with Ukraine's State Emergency Service, in the Chernihiv region, in the north of the country.",
      vis=[MAP("pin", pin="Chernihiv", center="Chernihiv", towns=[("Chernihiv", "CHERNIHIV", "r"), ("Kyiv", "KYIV", "l")], label="NORTHERN UKRAINE", zoom=1.6),
           FULL(stn(0.0, 12.5), pops=[PIN("CHERNIHIV, UKRAINE", 0.3)])]),
 dict(kind="narr", text="At first, Patron was simply a family pet. Mykhailo had bought him as a puppy for his son.",
      vis=[SPLIT(mz(5.0, 13.0), P("golden_paw", focus=(0.5, 0.45)), chip1="CHERNIHIV", chip2="PATRON")]),

 # ---------------- CHAPTER 2
 dict(kind="chapter", n=2, text="The Nose", bg=P("shestovytsia_sappers_03", focus=(0.5, 0.5))),
 dict(kind="narr", text="Then, in February 2022, war came to Ukraine. When the fighting moved on, it left dangerous explosives behind, near the homes people wanted to return to.",
      vis=[FULL(e20(11.0, 18.0)), FULL(km(16.0, 23.0))]),
 dict(kind="narr", text="Patron finished special training. He learned the smell of gunpowder, and he got used to loud noises.",
      vis=[SPLIT(ss(30.0, 38.0), P(PP, focus=(0.5, 0.4)), chip1="SAPPERS AT WORK", chip2="PATRON")]),
 dict(kind="narr", text="When he smells explosives, he barks, or he simply sits and waits. Then the human experts carefully find the item, and make it safe.",
      vis=[FULL(b9(1.0, 12.0), pops=[CHIP("HE SIGNALS · HUMANS CLEAR", 0.4)])]),
 dict(kind="narr", text="His vest even has a handle on top, so Mykhailo can lift him away in an instant.",
      vis=[FREEZE(P("us_veteran_awards_1", focus=(0.5, 0.5), z=(1.0, 1.04)), at="@handle", circle=(0.5, 0.5, 0.18), label="THE HANDLE", chip="HIS VEST")]),
 dict(kind="narr", text="And there's one thing he loves more than anything. Cheese. But it was a news conference in Kyiv that made him famous around the world.",
      vis=[FULL(P(PP, focus=(0.5, 0.5), z=(1.12, 1.0)), pops=[CHIP("FAVOURITE TREAT: CHEESE", "@Cheese")]),
           FULL(ti(0.0, 9.0), pops=[PIN("KYIV REGION · MAY 8, 2022", 0.3)])]),

 # ---------------- CHAPTER 3
 dict(kind="chapter", n=3, text="The Medal", bg=P("medal_trudeau_zelensky_41", focus=(0.5, 0.5))),
 dict(kind="narr", text="On May 8th, 2022, Canada's prime minister, Justin Trudeau, was visiting Kyiv. At their joint news conference, President Volodymyr Zelensky presented awards, to a bomb-disposal expert and his dog.",
      vis=[FULL(ti(27.0, 36.0), pops=[STAMP("MAY 8, 2022", 0.2)]),
           FULL(ti(69.0, 78.0))]),
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
           FULL(rb(12.0, 22.0), pops=[CHIP("STAMP MONEY BOUGHT DEMINING EQUIPMENT", 0.3)])]),
 dict(kind="narr", text="UNICEF named him its first ever Goodwill AmbassaDOG. And by early 2023, UNICEF said Patron had helped find more than three hundred explosive objects.",
      vis=[FULL(P("unicef_youth_dialogue", focus=(0.5, 0.5), z=(1.0, 1.08)), pops=[CHIP("UNICEF · NOV 2022", 0.3)]),
           STAT("300+", "EXPLOSIVE OBJECTS", P("blinken_pets_patron", focus=(0.5, 0.5)), sub="credited, with his team · UNICEF, January 2023")]),

 # ---------------- CHAPTER 5
 dict(kind="chapter", n=5, text="The Truth About Patron", bg=P("sunak_meeting_05", focus=(0.5, 0.5))),
 dict(kind="narr", text="You may have seen posts calling him an army dog. He isn't. He works with the State Emergency Service, a civilian rescue service.",
      vis=[STAT("MYTH", "AN ARMY DOG", ti(101.0, 108.0)), STAT("FACT", "CIVILIAN RESCUE SERVICE", P(PP, focus=(0.5, 0.4)))]),
 dict(kind="narr", text="And he never works alone. Patron sniffs. The human experts make it safe. Being small makes him less likely to set off a mine, but it never makes the work safe.",
      vis=[SPLIT(b21(10.0, 20.0), P("us_veteran_awards_1", focus=(0.5, 0.5)), chip1="THE TEAM", chip2="PATRON")]),
 dict(kind="narr", text="In December 2024, false reports online said he had died. The rescue service answered right away. Patron is perfectly fine.",
      vis=[SPLIT(b21(48.0, 56.0), P("power_usaid_2023", focus=(0.5, 0.5)), chip1="STILL ON DUTY", chip2="PATRON · 2023")]),
 dict(kind="narr", text="Let's look at everything he's done. A family pet. A medal from a president. A stamp that bought a demining machine. And hundreds of explosives found, with his team.",
      vis=[BOARD([(P(PP, focus=(0.5, 0.35)), "FAMILY PET"), (P("medal_trudeau_zelensky_40"), "THE MEDAL"), (P("stamp_dog_patron", tone="none"), "THE STAMP"),
                  (P("okhmatdyt_01"), "TEACHING KIDS")], notes=[("4 KG", "OF COURAGE"), ("300+", "FOUND"), ("$500K", "RAISED")])]),
 dict(kind="narr", text="And in 2026, according to his official Instagram, Patron became a father. Of seven puppies.",
      vis=[FULL(P("vyshyvanka", focus=(0.5, 0.4), z=(1.0, 1.1)), pops=[STAMP("2026: 7 PUPPIES", "@father")])]),
 dict(kind="narr", text="He's small enough to lift with one hand. But he helped make his homeland safer, one sniff at a time.",
      vis=[FULL(nb(40.0, 50.0))], gap=1.0),
 dict(kind="narr", text="If this story made you smile, subscribe for more true stories of incredible dogs.",
      vis=[CTA(0, nb(60.0, 66.0))]),
 dict(kind="narr", text="And tell us in the comments. What is your dog's secret talent?",
      vis=[CTA(1, km(244.0, 250.0))], gap=1.2),
]
