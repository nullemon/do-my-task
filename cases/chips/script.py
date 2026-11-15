# Chips: script + visual plan.  Facts and sources: research.md   (enemy soldiers were ITALIAN; "credited with" for counts)
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from shots import *
CU = "U.S. Army film 'The Use of War Dogs' (1943) · National Archives"; CD = "War Dept Film Bulletin 35 (1942) · National Archives"
CS = "United News newsreel 'Invasion of Sicily' (1943) · National Archives"; CL = "U.S. Navy film, Licata, July 1943 · National Archives"
CK = "U.S. Army Signal Corps, Casablanca Conference 1943 · National Archives"
def u(a, b): return F("film_use_of_war_dogs", a, b, credit=CU)
def dj(a, b): return F("film_dogs_join_army", a, b, credit=CD)
def sn(a, b): return F("film_invasion_sicily_newsreel", a, b, crop=dict(x0=8, y0=6, x1=312, y1=234), credit=CS)
def li(a, b, focus=(0.5, 0.45)): return F("film_licata_invasion", a, b, crop=dict(x0=0, y0=0, x1=532, y1=228), credit=CL, focus=focus)   # burned-in timecode cropped
def k(a, b, focus=(0.5, 0.5)): return F("film_casablanca_conference_2", a, b, credit=CK, focus=focus)
CH = P("chips_colorized", focus=(0.5, 0.4))
NOTCHIPS = "ARMY WAR DOG TRAINING · 1943 (NOT CHIPS)"
VIS = {
 "hook1": FULL(P("chips_colorized", focus=(0.5, 0.4), z=(1.0, 1.10)), punch=True),
 "hook2": FULL(li(46.6, 50.5), punch=True, pops=[STAMP("JULY 10, 1943", 0.2)]),
 "hook3": FULL(u(350.0, 354.5), punch=True),
 "hook4": FULL(sn(141.6, 145.8), punch=True),
 "hook5": FULL(u(330.6, 334.5)),
 "title": FULL(u(230.0, 234.0)),
 "ch1": dict(media=u(50.0, 54.0)),
 "fam1": FULL(P("chips_colorized", focus=(0.5, 0.45), z=(1.0, 1.08)), pops=[PIN("PLEASANTVILLE, NEW YORK", 0.3)]),
 "fam2": FULL(dj(442.6, 446.5), pops=[CHIP("DOGS FOR DEFENSE · 1942", 0.3)]),
 "dfd1": FULL(u(110.2, 114.2), pops=[CHIP(NOTCHIPS, 0.3, color="dark")]),
 "dfd2": SPLIT(dj(507.4, 511.5), dj(637.0, 641.0), chip1="FAMILY DOGS JOIN THE ARMY · 1942", chip2="REAL 1942 FILM"),
 "train1": FULL(u(70.0, 74.5), pops=[CHIP(NOTCHIPS, 0.3, color="dark")]),
 "train2": FULL(u(250.5, 255.0)),
 "train3": SPLIT(u(270.5, 274.5), u(310.6, 314.5), chip1="SENTRY TRAINING", chip2="WAR DOGS · 1943"),
 "runt1": FULL(P("k9_robin_burma", focus=(0.5, 0.45), z=(1.0, 1.08)), pops=[CHIP("A FAMILY DOG DONATED TO THE ARMY (NOT CHIPS)", 0.3, color="dark")]),
 "sentry1": FULL(u(470.9, 475.0), pops=[CHIP("SENTRY DOG TRAINING · 1943", 0.3, color="dark")]),
 "sentry2": FULL(u(490.9, 495.0)),
 "torch1": FULL(sn(66.1, 70.0), pops=[STAMP("NOVEMBER 1942", 0.3)]),
 "myth1": STAT("MYTH", "HE FOUGHT GERMANS IN SICILY", sn(104.0, 108.0)),
 "fact1": STAT("FACT", "THE GUNNERS WERE ITALIAN", li(41.1, 45.0), sub="And Chips was a mix, not a purebred"),
 "ch2": dict(media=k(49.4, 53.5)),
 "map_casa": MAP("pin", pin="Casablanca", center="Casablanca", towns=[("Casablanca", "CASABLANCA", "r")], label="JANUARY 1943 · NORTH AFRICA", zoom=1.4),
 "casa1": FULL(k(9.9, 14.0), pops=[CHIP("ROOSEVELT & CHURCHILL · CASABLANCA 1943", 0.3)]),
 "casa2": FULL(k(326.3, 330.5)),
 "casa3": SPLIT(k(128.5, 132.5), k(207.6, 211.5), chip1="WINSTON CHURCHILL", chip2="THE CONFERENCE"),
 "ike1": FULL(u(90.2, 94.2)),
 "ch3": dict(media=li(30.1, 34.0)),
 "map_sicily": MAP("pin", pin="Licata", center="Licata", towns=[("Licata", "LICATA", "r")], label="JULY 10, 1943 · SICILY", zoom=2.0),
 "land1": FULL(li(13.7, 18.5), pops=[CHIP("REAL FILM · LICATA, JULY 1943", 0.3)]),
 "land2": FULL(sn(179.4, 183.5)),
 "fire1": FULL(sn(85.0, 89.0)),
 "fire2": FULL(sn(255.0, 259.0)),
 "charge1": FULL(u(370.7, 374.7), punch=True, pops=[CHIP(NOTCHIPS, 0.2, color="dark")]),
 "surr1": FULL(sn(387.2, 391.0)),
 "surr2": FULL(sn(368.3, 372.0)),
 "quote1": STAT("\"I CALLED HIM OFF\"", "PVT. JOHN ROWELL, 1943", u(290.6, 294.5)),
 "night1": FULL(u(130.2, 134.0)),
 "night2": STAT("10", "SOLDIERS CAPTURED THAT NIGHT", u(190.4, 194.4), sub="credited to Chips and his handler"),
 "ch4": dict(media=k(148.3, 152.0)),
 "medal1": FULL(P("chips_colorized", focus=(0.5, 0.35), z=(1.05, 1.12)), pops=[STAMP("SILVER STAR · PURPLE HEART", 0.3)]),
 "medal2": FULL(P("truscott_portrait", focus=(0.5, 0.35), z=(1.0, 1.08)), pops=[CHIP("MAJ. GEN. LUCIAN TRUSCOTT PRESENTED HIS AWARDS", 0.3)]),
 "back1": STAT("1944", "\"NO MORE MEDALS FOR ANIMALS\"", li(95.9, 100.0), sub="War Department ruling"),
 "back2": FULL(li(79.4, 83.5)),
 "ribbon1": FULL(li(145.2, 149.5), pops=[CHIP("HIS MEN STOOD BY HIM", 0.3)]),
 "map_war": MAP("route", pts=["Casablanca", "Licata", "Rome", "Marseille", "Berlin"], towns=[("Casablanca", "NORTH AFRICA", "l"), ("Licata", "SICILY", "r"), ("Rome", "ITALY", "r"), ("Marseille", "FRANCE", "l"), ("Berlin", "GERMANY", "r")],
                label="1942–1945 · CHIPS' WAR", center="Rome", zoom=1.3, note="Route shown is approximate"),
 "europe1": FULL(sn(292.7, 296.5)),
 "ch5": dict(media=li(68.5, 72.5)),
 "home1": FULL(P("chips_colorized", focus=(0.5, 0.45), z=(1.1, 1.0)), pops=[STAMP("DECEMBER 1945", 0.3)]),
 "home2": FULL(li(134.2, 138.5)),
 "died1": FULL(li(24.7, 28.5)),
 "board": BOARD([(CH, "CHIPS"), (k(9.9, 10.0), "CASABLANCA"), (li(16.0, 16.1), "LICATA"), (u(250.5, 250.6), "WAR DOGS")],
                notes=[("1943", "SICILY"), ("10", "CAPTURED"), ("2018", "DICKIN MEDAL")]),
 "dickin1": STAT("2018", "THE DICKIN MEDAL", sn(349.4, 353.5), sub="Awarded in London, 75 years later"),
 "dickin2": FULL(P("licata_beach_memorial", focus=(0.5, 0.5), z=(1.0, 1.08)), pops=[CHIP("LICATA BEACH MEMORIAL", 0.3)]),
 "closing": FULL(P("chips_colorized", focus=(0.5, 0.35), z=(1.0, 1.12))),
 "cta0": CTA(0, dj(593.8, 597.5)),
 "cta1": CTA(1, dj(615.4, 619.5)),
}

SEG = [
 dict(kind="narr", text="July 1943. On a beach in Sicily, American soldiers were pinned down by a hidden machine gun.",
      vis=["hook1", "hook2"], gap=0.25),
 dict(kind="narr", text="Then a family dog from New York broke free, and charged straight at it.",
      vis=["hook3"], gap=0.3),
 dict(kind="narr", text="He was given medals for bravery. And then, the Army said dogs weren't allowed to have them.",
      vis=["hook4", "hook5"], gap=0.3),
 dict(kind="narr", text="This is the true story of Chips.",
      vis=["title"], title=True, gap=0.8),

 dict(kind="chapter", n=1, text="The Family Dog", bg="ch1"),
 dict(kind="narr", text="Chips was a German shepherd mix, who lived with the Wren family in Pleasantville, New York.",
      vis=["fam1", "fam2"]),
 dict(kind="narr", text="A neighbouring family had given him to the Wrens as a puppy. Years later, John Wren remembered him as the runt of the litter.",
      vis=["runt1"]),
 dict(kind="narr", text="In 1942, America was at war, and the Army asked families to lend their dogs. It was called Dogs for Defense. The Wrens said yes.",
      vis=["dfd1", "dfd2"]),
 dict(kind="narr", text="Chips was trained as a sentry dog, and paired with Private John Rowell, of the 3rd Infantry Division.",
      vis=["train1", "train2", "train3"]),

 dict(kind="narr", text="A sentry dog's job was to stay alert, especially at night, and warn his handler the moment anyone came close.",
      vis=["sentry1", "sentry2"]),

 dict(kind="chapter", n=2, text="Guarding Roosevelt and Churchill", bg="ch2"),
 dict(kind="narr", text="In November 1942, Chips and the 3rd Infantry Division sailed into Operation Torch, the Allied landings in North Africa.",
      vis=["torch1"]),
 dict(kind="narr", text="He went with his unit to North Africa. And in January 1943, he was one of the sentries at the Casablanca Conference.",
      vis=["map_casa", "casa1"]),
 dict(kind="narr", text="There, President Roosevelt and Prime Minister Churchill met to plan the next stage of the war. And Chips was on guard.",
      vis=["casa2", "casa3"]),
 dict(kind="narr", text="The story goes that he even nipped General Eisenhower's hand, when the general reached down to pet him.",
      vis=["ike1"]),

 dict(kind="chapter", n=3, text="The Beach at Licata", bg="ch3"),
 dict(kind="narr", text="On July 10th, 1943, the 3rd Infantry Division landed near Licata, on the southern coast of Sicily.",
      vis=["map_sicily", "land1", "land2"]),
 dict(kind="narr", text="As Chips and Rowell moved inland, a machine gun opened fire from a small hut. The men were pinned down.",
      vis=["fire1", "fire2"]),
 dict(kind="narr", text="Chips broke free from his handler, and ran straight into the gunfire.",
      vis=["charge1"]),
 dict(kind="narr", text="The shooting stopped. Moments later, an Italian soldier came out, with Chips holding on tight. Then three more came out, with their hands up.",
      vis=["surr1", "surr2"]),
 dict(kind="narr", text="Rowell later said, I called him off, before he could kill the man.",
      vis=["quote1"]),
 dict(kind="narr", text="Chips had a scalp wound, and powder burns. The medics patched him up. And that same night, on guard duty, he's credited with helping capture ten more soldiers.",
      vis=["night1", "night2"]),

 dict(kind="chapter", n=4, text="Medals for a Dog", bg="ch4"),
 dict(kind="narr", text="Chips was recommended for the Distinguished Service Cross. He was awarded the Silver Star, and the Purple Heart.",
      vis=["medal1", "medal2"]),
 dict(kind="narr", text="Then came the backlash. A veterans' leader protested to the president that medals were for people. The Army ruled that no more medals would be given to animals.",
      vis=["back1", "back2"]),
 dict(kind="narr", text="But his own soldiers didn't care. They gave him an unofficial ribbon, covered in battle stars.",
      vis=["ribbon1"]),
 dict(kind="narr", text="Chips served all the way through the war. North Africa. Sicily. Italy. France. And Germany.",
      vis=["map_war", "europe1"]),

 dict(kind="narr", text="Some stories say Chips fought German soldiers on that beach. In fact, the men in the machine gun nest were Italian. And he wasn't a purebred, as in the Disney film. He was a mix.",
      vis=["myth1", "fact1"]),

 dict(kind="chapter", n=5, text="Home Again", bg="ch5"),
 dict(kind="narr", text="In December 1945, Chips came home to Pleasantville, and to the Wren family. Little John Wren was about four years old.",
      vis=["home1", "home2"]),
 dict(kind="narr", text="But their time together was short. Chips died in 1946, only months after coming home.",
      vis=["died1"]),
 dict(kind="narr", text="Let's look at his whole journey. A family pet. A sentry at Casablanca. A charge on a Sicilian beach. And medals the Army said a dog couldn't keep.",
      vis=["board"]),
 dict(kind="narr", text="In 2018, seventy-five years later, Chips was finally awarded the Dickin Medal, in London. And John Wren, the little boy who welcomed him home, was there.",
      vis=["dickin1", "dickin2"]),
 dict(kind="narr", text="He went to war as a family pet. He came home a hero.",
      vis=["closing"], gap=1.0),
 dict(kind="narr", text="If Chips' story moved you, subscribe for more true stories of incredible dogs.",
      vis=["cta0"]),
 dict(kind="narr", text="And tell us in the comments. Would your dog be brave, or hide under the bed?",
      vis=["cta1"], gap=1.2),
]

def resolve():
    for s in SEG:
        if "vis" in s: s["vis"] = [VIS[v] if isinstance(v, str) else v for v in s["vis"]]
        if isinstance(s.get("bg"), str): s["bg"] = VIS[s["bg"]].get("media", VIS[s["bg"]])

resolve()
