# Stubby: script + visual plan.  Facts and sources: research.md  ("Sergeant" = nickname; spy = period account; no Purple Heart)
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from shots import *
CR = dict(x0=160, y0=0, x1=1120, y1=720)      # these National Archives transfers are 4:3 inside a 16:9 frame
SC = "U.S. Army Signal Corps film · 26th Division, France 1918 · National Archives"
def cd(a, b, f=(0.5, 0.5)): return F("film_chemin_des_dames_26th", a, b, crop=CR, credit=SC, focus=f)
def tl(a, b, f=(0.5, 0.5)): return F("film_toul_seicheprey_26th", a, b, crop=CR, credit=SC, focus=f)
def am(a, b, f=(0.5, 0.5)): return F("film_aisne_marne_26th", a, b, crop=CR, credit=SC, focus=f)
def ma(a, b, f=(0.5, 0.5)): return F("film_meuse_argonne_26th", a, b, crop=CR, credit=SC, focus=f)
def nf(a, b, f=(0.5, 0.5)): return F("film_neufchateau_26th", a, b, crop=CR, credit=SC, focus=f)
def it(a, b, f=(0.5, 0.5)): return F("vid_infantry_training_1918", a, b, crop=CR, credit="U.S. Army Signal Corps, 'Infantry Training' 1918 · National Archives", focus=f)
COAT = P("stubby_coat", focus=(0.5, 0.45))
VIS = {
 "hook1": FULL(P("stubby_coat", focus=(0.5, 0.42), z=(1.0, 1.10)), punch=True),
 "hook2": FULL(it(9.3, 14.0), punch=True, pops=[STAMP("1917", 0.2)]),
 "hook3": FULL(cd(194.6, 199.0), punch=True),
 "hook4": FULL(P("nmah_mount", focus=(0.5, 0.5), z=(1.0, 1.1)), pops=[CHIP("SMITHSONIAN · WASHINGTON, D.C.", 0.3)]),
 "title": FULL(P("stubby_coat_2", focus=(0.5, 0.42), z=(1.06, 1.0))),
 "ch1": dict(media=it(46.7, 51.0)),
 "yale1": FULL(it(65.3, 69.5), pops=[CHIP("REAL 1917 TRAINING FILM", 0.3)]),
 "yale2": SPLIT(it(270.6, 275.0), it(419.9, 424.0), chip1="TRAINING CAMP · 1917", chip2="DRILL"),
 "conroy1": FULL(P("stubby_1923_news", focus=(0.5, 0.45), z=(1.0, 1.08)), pops=[CHIP("STUBBY", 0.3)]),
 "conroy2": FULL(it(121.3, 125.5)),
 "drill1": FULL(it(438.5, 443.0)),
 "drill2": FULL(it(457.2, 461.5)),
 "ch2": dict(media=nf(35.2, 40.0)),
 "ship1": FULL(it(28.0, 32.5), pops=[STAMP("OCTOBER 1917", 0.3)]),
 "ship2": MAP("route", pts=["NewHaven", "AtlanticMid", "SaintNazaire"], towns=[("NewHaven", "NEW HAVEN", "l"), ("SaintNazaire", "FRANCE", "r")], label="1917 · SMUGGLED ACROSS THE ATLANTIC",
              center="AtlanticMid", zoom=2.2, note="Route shown is approximate"),
 "salute1": FREEZE(P("stubby_coat", focus=(0.5, 0.45), z=(1.0, 1.04)), at="@saluted", circle=(0.5, 0.35, 0.2), label="STUBBY", chip="REAL PHOTO"),
 "map_front": MAP("pin", pin="ChemindesDames", center="ChemindesDames", towns=[("ChemindesDames", "CHEMIN DES DAMES", "r"), ("Seicheprey", "SEICHEPREY", "r")], label="FEBRUARY 1918 · THE FRONT", zoom=3.0),
 "front1": FULL(cd(272.5, 277.0), pops=[CHIP("26TH DIVISION · CHEMIN DES DAMES 1918", 0.3)]),
 "front2": FULL(cd(428.2, 432.5)),
 "ch3": dict(media=cd(350.3, 354.5)),
 "gas1": FULL(am(532.7, 537.0), pops=[CHIP("GAS MASKS AT THE READY", 0.3)]),
 "gas2": FULL(P("gas_masks_doughboys", focus=(0.5, 0.5), z=(1.0, 1.08))),
 "gas3": FULL(P("ww1_dog_gas_mask", focus=(0.5, 0.45), z=(1.0, 1.1)), pops=[CHIP("A WWI DOG IN A GAS MASK (NOT STUBBY)", 0.3, color="dark")]),
 "wounded1": FULL(ma(103.8, 108.0), pops=[CHIP("AMBULANCES AT THE FRONT · 1918", 0.3)]),
 "wounded2": FULL(ma(122.7, 127.0)),
 "seich1": FULL(tl(219.6, 224.0), pops=[STAMP("APRIL 1918 · SEICHEPREY", 0.3)]),
 "seich2": FULL(tl(1160.8, 1165.0)),
 "hospital1": FULL(P("stubby_coat_2", focus=(0.5, 0.5), z=(1.1, 1.0))),
 "hospital2": FULL(tl(407.9, 412.0)),
 "spy1": FULL(cd(1206.7, 1211.0), pops=[CHIP("AS REPORTED BY NEWSPAPERS OF THE DAY", 0.3, color="dark")]),
 "ch4": dict(media=am(82.5, 87.0)),
 "coat1": FREEZE(P("stubby_coat", focus=(0.5, 0.5), z=(1.0, 1.04)), at="@coat", circle=(0.5, 0.55, 0.25), label="HIS COAT", chip="CHÂTEAU-THIERRY, 1918"),
 "coat2": FULL(am(277.6, 282.0)),
 "home1": FULL(tl(1537.3, 1541.5), pops=[CHIP("26TH DIVISION MEDAL CEREMONY · 1918", 0.3)]),
 "home2": FULL(cd(2685.8, 2690.0)),
 "home3": FULL(ma(556.9, 561.0)),
 "pershing1": FULL(P("pershing_medal", focus=(0.5, 0.5), z=(1.0, 1.08)), pops=[STAMP("1921", 0.3)]),
 "pershing2": FULL(P("pershing_medal_crop", focus=(0.5, 0.45), z=(1.06, 1.0))),
 "fame1": FULL(P("stubby_1923_news", focus=(0.5, 0.4), z=(1.08, 1.0))),
 "fame2": FULL(am(352.6, 357.0)),
 "ch5": dict(media=am(502.7, 507.0)),
 "myth1": STAT("MYTH", "AN OFFICIAL SERGEANT", tl(1600.0, 1604.0)),
 "fact1": STAT("FACT", "A NICKNAME", P("stubby_coat_2", focus=(0.5, 0.4))),
 "myth2": STAT("1932", "THE PURPLE HEART WAS CREATED", ma(538.0, 542.0), sub="Six years after Stubby died"),
 "board": BOARD([(COAT, "STUBBY"), (it(65.3, 65.4), "TRAINING 1917"), (cd(272.5, 272.6), "THE FRONT"), (P("pershing_medal"), "PERSHING 1921")],
                notes=[("1917", "SMUGGLED"), ("1918", "WOUNDED"), ("1921", "MEDAL")]),
 "death1": FULL(P("nmah_case_cherami", focus=(0.5, 0.5), z=(1.0, 1.08)), pops=[STAMP("MARCH 1926", 0.3)]),
 "museum1": FULL(P("nmah_mount", focus=(0.5, 0.45), z=(1.1, 1.0)), pops=[CHIP("SMITHSONIAN · SINCE 1956", 0.3)]),
 "closing": FULL(P("stubby_coat", focus=(0.5, 0.35), z=(1.0, 1.12))),
 "cta0": CTA(0, nf(387.2, 392.0)),
 "cta1": CTA(1, am(517.7, 522.0)),
}

SEG = [
 dict(kind="narr", text="In 1917, a stray dog with a stubby little tail wandered into an army camp in Connecticut.",
      vis=["hook1"], gap=0.25),
 dict(kind="narr", text="Pets were banned. So a young soldier hid him under his coat, and smuggled him all the way to the trenches of France.",
      vis=["hook2", "hook3"], gap=0.3),
 dict(kind="narr", text="Today, that little stray stands in the Smithsonian.",
      vis=["hook4"], gap=0.3),
 dict(kind="narr", text="This is the true story of Stubby.",
      vis=["title"], title=True, gap=0.8),

 dict(kind="chapter", n=1, text="The Stray", bg="ch1"),
 dict(kind="narr", text="Summer, 1917. Soldiers of the 102nd Infantry, part of the 26th Yankee Division, were training at Yale, in New Haven.",
      vis=["yale1", "yale2"]),
 dict(kind="narr", text="A brindle stray of unknown breed began hanging around the camp. A young soldier named Robert Conroy took a liking to him, and named him Stubby, for his short tail.",
      vis=["conroy1", "conroy2"]),
 dict(kind="narr", text="Stubby learned the bugle calls and the drills. And Conroy taught him to salute, by raising his paw.",
      vis=["drill1", "drill2"]),

 dict(kind="chapter", n=2, text="Smuggled to War", bg="ch2"),
 dict(kind="narr", text="In October 1917, the regiment sailed for France. Dogs weren't allowed. So Conroy wrapped Stubby in his coat, and a crewman helped hide him in the ship's coal bin.",
      vis=["ship1", "ship2"]),
 dict(kind="narr", text="When an officer finally found him, the story goes that Stubby sat up, and saluted. He was allowed to stay.",
      vis=["salute1"]),
 dict(kind="narr", text="In February 1918, the division reached the front lines, at the Chemin des Dames.",
      vis=["map_front", "front1", "front2"]),

 dict(kind="chapter", n=3, text="Under Fire", bg="ch3"),
 dict(kind="narr", text="Stubby was caught in a gas attack, and survived. After that, he could smell gas early. When he barked, the men put on their masks.",
      vis=["gas1", "gas2", "gas3"]),
 dict(kind="narr", text="He's credited with finding wounded soldiers in no man's land, and barking until help arrived.",
      vis=["wounded1", "wounded2"]),
 dict(kind="narr", text="In April 1918, at Seicheprey, Stubby himself was hit by shrapnel from a grenade. Conroy reportedly carried him to the medics.",
      vis=["seich1", "seich2"]),
 dict(kind="narr", text="He spent weeks in hospital. And while he recovered, he went from bed to bed, visiting the other wounded men.",
      vis=["hospital1", "hospital2"]),
 dict(kind="narr", text="Newspapers of the day reported that he once caught a German soldier, holding him by the seat of his pants until help came.",
      vis=["spy1"]),

 dict(kind="chapter", n=4, text="A Hero Comes Home", bg="ch4"),
 dict(kind="narr", text="After the town of Château-Thierry was retaken, local women sewed Stubby a coat, to carry his medals and stripes.",
      vis=["coat1", "coat2"]),
 dict(kind="narr", text="When the war ended, Stubby came home with his regiment, and marched in parades.",
      vis=["home1", "home2", "home3"]),
 dict(kind="narr", text="In 1921, General John Pershing, the commander of the American army in France, pinned a gold medal on him.",
      vis=["pershing1", "pershing2"]),
 dict(kind="narr", text="He met presidents. And when Conroy studied law at Georgetown, Stubby became the football team's mascot, nudging a ball around the field at halftime.",
      vis=["fame1", "fame2"]),

 dict(kind="chapter", n=5, text="The Truth About Stubby", bg="ch5"),
 dict(kind="narr", text="You'll often hear him called Sergeant Stubby. But that rank was never official. It was a nickname.",
      vis=["myth1", "fact1"]),
 dict(kind="narr", text="And he never received a Purple Heart. The modern medal wasn't created until 1932, six years after he died.",
      vis=["myth2"]),
 dict(kind="narr", text="Let's look at his whole journey. A stray at Yale. A secret voyage. The trenches of France. And a hero's welcome home.",
      vis=["board"]),
 dict(kind="narr", text="In March 1926, Stubby died of old age, with Conroy beside him. Conroy never owned another dog. And in 1956, he gave Stubby to the Smithsonian, where he still stands today.",
      vis=["death1", "museum1"]),
 dict(kind="narr", text="He was a stray nobody wanted. He became a dog a whole nation loved.",
      vis=["closing"], gap=1.0),
 dict(kind="narr", text="If Stubby's story moved you, subscribe for more true stories of incredible dogs.",
      vis=["cta0"]),
 dict(kind="narr", text="And tell us in the comments. What would your dog do, if you were in danger?",
      vis=["cta1"], gap=1.2),
]

def resolve():
    for s in SEG:
        if "vis" in s: s["vis"] = [VIS[v] if isinstance(v, str) else v for v in s["vis"]]
        if isinstance(s.get("bg"), str): s["bg"] = VIS[s["bg"]].get("media", VIS[s["bg"]])

resolve()
