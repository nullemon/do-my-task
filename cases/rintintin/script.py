# Rin Tin Tin: script + visual plan.  Facts and sources: research.md
# Footage: his own public-domain films. W = Where the North Begins (1923, reel 1), C = Clash of the Wolves (1925)
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from shots import *
W = "film_wtnb_reel1"; C = "film_clash_archive"
CW = "Where the North Begins (1923) · public domain"
CC = "Clash of the Wolves (1925) · public domain"
def w(t0, t1, focus=(0.5, 0.5), crop=None): return F(W, t0, t1, crop=crop or WCROP, credit=CW, focus=focus)
def c(t0, t1, focus=(0.5, 0.5), crop=None): return F(C, t0, t1, crop=crop or CCROP, credit=CC, focus=focus)
WCROP = None; CCROP = dict(x0=24, y0=18, x1=552, y1=422)          # Clash print has a vignette; trim the edges
L = "film_lighthouse"; CL = "The Lighthouse by the Sea (1924) · public domain"
N = "wwi_neufchateau"; CN = "U.S. Army Signal Corps film, France 1918 · National Archives"
def l(t0, t1, focus=(0.5, 0.5)): return F(L, t0, t1, crop=dict(x0=8, y0=6, x1=312, y1=234), credit=CL, focus=focus)
def n(t0, t1, focus=(0.5, 0.5)): return F(N, t0, t1, crop=dict(x0=160, y0=0, x1=1120, y1=720), credit=CN, focus=focus)
DOGFILM = "RIN TIN TIN ON FILM"
VIS = {
 "hook1": FULL(c(90.0, 95.8), punch=True),
 "hook2": FULL(l(634.3, 638.8), punch=True),
 "hook3": FULL(c(1322.0, 1325.4), punch=True),
 "hook4": FULL(w(741.0, 747.0), punch=True),
 "title": FULL(c(2313.0, 2316.0)),
 "ch1": dict(media=c(646.0, 650.6)),
 "duncan1": SPLIT(n(7.0, 20.0), n(232.0, 245.0), chip1="AMERICAN TROOPS IN FRANCE · 1918", chip2="REAL 1918 FILM"),
 "duncan2": FULL(n(49.0, 62.0), pops=[CHIP("THE WESTERN FRONT · WINTER 1918", 0.3)]),
 "map_flirey": MAP("pin", pin="Flirey", center="Flirey", towns=[("Flirey", "FLIREY, LORRAINE", "r")], label="SEPTEMBER 15, 1918", zoom=3.2),
 "flirey1": FULL(n(63.0, 76.0), pops=[STAMP("SEPT 15, 1918", 0.3)]),
 "orphan1": FULL(c(1752.0, 1760.0), pops=[CHIP(DOGFILM, 0.3, color="dark")]),
 "names1": FULL(n(387.0, 400.0), pops=[CHIP("FRENCH CHILDREN WITH SOLDIERS · 1918", 0.3)]),
 "names2": FULL(c(1391.0, 1393.8)),
 "ch2": dict(media=c(2933.0, 2935.5)),
 "map_route": MAP("route", pts=["Flirey", "AtlanticMid", "NewYork", "LosAngeles"], towns=[("Flirey", "FRANCE", "r"), ("NewYork", "NEW YORK", "r"), ("LosAngeles", "LOS ANGELES", "l")],
                  label="1919 · FRANCE TO AMERICA", center="AtlanticMid", zoom=2.4, note="Route shown is approximate"),
 "sad1": FULL(c(1815.5, 1824.0)),
 "sad2": FULL(c(1447.0, 1455.0)),
 "train1": FULL(c(1202.8, 1207.3), punch=True),
 "train2": SPLIT(c(1876.0, 1883.0), c(1506.0, 1510.0), chip1="RIN TIN TIN", chip2="A BORN ATHLETE"),
 "train3": FULL(c(4289.5, 4292.0)),
 "leg1": FULL(c(1325.5, 1331.9)),
 "leg2": FULL(c(3480.5, 3489.8)),
 "jump1": FULL(w(762.0, 775.0)),
 "jump2": STAT("1922", "THE DOG SHOW THAT CHANGED EVERYTHING", c(2307.0, 2310.0)),
 "ch3": dict(media=c(1382.0, 1390.0)),
 "star1": FULL(w(747.0, 753.0), pops=[STAMP("WHERE THE NORTH BEGINS · 1923", 0.3)]),
 "star2": FULL(w(851.0, 858.0)),
 "act1": FULL(l(708.3, 711.3), punch=True),
 "act2": FULL(l(3023.0, 3030.0)),
 "act3": FREEZE(c(2067.0, 2072.0), at=2.2, circle=(0.62, 0.78, 0.13), label="THAT'S RINTY", chip="CLASH OF THE WOLVES · 1925"),
 "world1": STAT("24+", "FILMS STARRING RIN TIN TIN", c(2062.0, 2066.5), sub="More than two dozen films, 1922–1931"),
 "world2": FULL(c(2745.5, 2750.0), pops=[CHIP("AUDIENCES LOVED HIM", 0.3)]),
 "mortgage1": FULL(l(855.3, 859.8), pops=[CHIP("\"THE MORTGAGE LIFTER\"", 0.3)]),
 "mortgage2": SPLIT(c(3849.5, 3855.0), l(1233.0, 1237.0), chip1="CLASH OF THE WOLVES · 1925", chip2="LIGHTHOUSE BY THE SEA · 1924"),
 "talkie1": STAT("1929", "TALKING PICTURES ARRIVE", c(2492.0, 2500.5)),
 "talkie2": FULL(c(3855.0, 3860.0)),
 "ch4": dict(media=c(2742.0, 2743.8)),
 "oscar1": STAT("MYTH", "HE WON THE FIRST OSCAR", l(1230.0, 1232.5)),
 "oscar2": STAT("FACT", "NOT ONE BALLOT NAMED A DOG", w(753.0, 759.0), sub="Academy records · the award went to Emil Jannings"),
 "oscar3": FULL(w(872.0, 880.0)),
 "harlow1": STAT("MYTH", "DIED IN JEAN HARLOW'S ARMS", c(1936.5, 1938.5)),
 "tv1": STAT("1950s", "A DIFFERENT DOG ON TV", l(2874.0, 2876.8)),
 "tv2": FULL(c(1940.0, 1945.5)),
 "ch5": dict(media=c(3049.3, 3055.3)),
 "death1": FULL(l(3244.0, 3251.0), pops=[STAMP("AUGUST 10, 1932", 0.3)]),
 "death2": FULL(w(880.0, 890.0)),
 "radio1": FULL(l(711.5, 716.0)),
 "spare1": FULL(l(631.0, 634.0)),
 "paris1": FULL(l(1529.5, 1534.0), pops=[CHIP("PARIS: \"CHIEN LOUP\" · SYDNEY", 0.3)]),
 "news1": FULL(l(1604.5, 1609.0)),
 "board": BOARD([(c(2313.0, 2313.1), "THE PUPPY GROWS UP"), (n(387.0, 387.1), "FRANCE · 1918"), (w(745.0, 745.1), "THE STAR · 1923"), (l(636.0, 636.1), "MOVIE HERO")],
                notes=[("1918", "FOUND"), ("24+", "FILMS"), ("1932", "GOODBYE")]),
 "star_wof": STAT("1960", "A STAR ON THE HOLLYWOOD WALK OF FAME", w(890.0, 900.0)),
 "legend1": FULL(l(1754.0, 1758.0)),
 "closing": FULL(l(3173.5, 3178.0), punch=False),
 "cta0": CTA(0, l(1978.0, 1982.0)),
 "cta1": CTA(1, c(4282.5, 4285.0)),
}

SEG = [
 dict(kind="narr", text="September 1918. On the Western Front, an American soldier walked into a bombed-out kennel.",
      vis=["hook1"], gap=0.25),
 dict(kind="narr", text="Inside, he found a starving mother dog, and five tiny puppies, too young to even open their eyes.",
      vis=["hook2", "hook3"], gap=0.3),
 dict(kind="narr", text="Five years later, one of those puppies was one of the biggest movie stars in America.",
      vis=["hook4"], gap=0.3),
 dict(kind="narr", text="This is the true story of Rin Tin Tin.",
      vis=["title"], title=True, gap=0.8),

 dict(kind="chapter", n=1, text="The War Puppy", bg="ch1"),
 dict(kind="narr", text="His rescuer was Corporal Lee Duncan, an American airman with the 135th Aero Squadron, in France.",
      vis=["duncan1", "duncan2"]),
 dict(kind="narr", text="According to Duncan, it happened near the village of Flirey, in Lorraine, on September 15th, 1918. The village had been shattered by war.",
      vis=["map_flirey", "flirey1"]),
 dict(kind="narr", text="Duncan had spent part of his own childhood in an orphanage. He couldn't leave the puppies behind.",
      vis=["orphan1"]),
 dict(kind="narr", text="He kept two of them, a boy and a girl. He named them after a pair of good-luck dolls that French children gave to soldiers. Rin Tin Tin, and Nanette.",
      vis=["names1", "names2"]),

 dict(kind="chapter", n=2, text="Coming Home", bg="ch2"),
 dict(kind="narr", text="When the war ended, Duncan managed to bring both puppies home on a ship to America.",
      vis=["map_route"]),
 dict(kind="narr", text="But soon after they arrived, little Nanette caught pneumonia, and died. Rin Tin Tin was all he had left.",
      vis=["sad1", "sad2"]),
 dict(kind="narr", text="Duncan took him home to Los Angeles, and trained him. Rinty was a born athlete. He could run, climb, and jump.",
      vis=["train1", "train2", "train3"]),
 dict(kind="narr", text="Once, Rinty broke a leg in an accident. Duncan set it himself, and nursed him back to health, for months.",
      vis=["leg1", "leg2"]),
 dict(kind="narr", text="Then, at a dog show in 1922, a cameraman filmed one of his amazing jumps. And Lee Duncan had an idea.",
      vis=["jump1", "jump2"]),

 dict(kind="chapter", n=3, text="The Star", bg="ch3"),
 dict(kind="narr", text="That same year, Rinty got his first small film role. And in 1923, Warner Brothers made him the star of Where the North Begins.",
      vis=["star1", "star2"]),
 dict(kind="narr", text="It was a hit. Audiences had never seen a dog act like this. On screen, he ran through snow, crossed rivers, and came to the rescue.",
      vis=["act1", "act2", "act3"]),
 dict(kind="narr", text="He made more than two dozen films. People around the world lined up to see him, from Paris to Sydney.",
      vis=["world1", "world2"]),
 dict(kind="narr", text="In Paris, cinemas billed him as Chien Loup, the wolf dog. In Sydney, his name was up in lights.",
      vis=["paris1"]),
 dict(kind="narr", text="Inside the studio, they called him the mortgage lifter. He's often credited with helping keep the young Warner Brothers studio afloat.",
      vis=["mortgage1", "mortgage2"]),

 dict(kind="narr", text="When talking pictures arrived, Warner Brothers let him go, in 1929. But Rinty kept working, in adventure serials, and even on his own radio show.",
      vis=["talkie1", "talkie2"]),

 dict(kind="chapter", n=4, text="The Truth About the Oscar", bg="ch4"),
 dict(kind="narr", text="You may have heard that Rin Tin Tin won the very first Oscar for Best Actor, and that the Academy took it away because he was a dog.",
      vis=["oscar1"]),
 dict(kind="narr", text="It isn't true. The signed ballots from 1928 still exist. Not a single one mentions a dog. The award went to Emil Jannings.",
      vis=["oscar2", "oscar3"]),
 dict(kind="narr", text="And the famous story that he died in the arms of actress Jean Harlow? That was invented by the press.",
      vis=["harlow1"]),

 dict(kind="narr", text="And the Rin Tin Tin on television in the 1950s? That was a different dog. Later dogs carried the famous name. But there was only one original.",
      vis=["tv1", "tv2"]),

 dict(kind="chapter", n=5, text="Goodbye, Rinty", bg="ch5"),
 dict(kind="narr", text="The truth is gentler. On August 10th, 1932, Rin Tin Tin died at Lee Duncan's home in Los Angeles. He was about thirteen.",
      vis=["death1", "death2"]),
 dict(kind="narr", text="Radio stations interrupted their programs to share the news. And newspapers across the country reported it.",
      vis=["radio1", "news1"]),
 dict(kind="narr", text="Let's look at his whole journey. A bombed kennel. A ship to America. A dog show. And more than two dozen films.",
      vis=["board"]),
 dict(kind="narr", text="Today, he has his own star on the Hollywood Walk of Fame. The puppy from the battlefield became a legend.",
      vis=["star_wof", "legend1"]),
 dict(kind="narr", text="A lonely soldier saved a puppy. And that puppy gave him a whole new life.",
      vis=["closing"], gap=1.0),
 dict(kind="narr", text="If you loved Rinty's story, subscribe for more true stories of incredible dogs.",
      vis=["cta0"]),
 dict(kind="narr", text="And tell us in the comments. Could your dog be a movie star? What's their best trick?",
      vis=["cta1"], gap=1.2),
]

def resolve():
    for s in SEG:
        if "vis" in s: s["vis"] = [VIS[v] if isinstance(v, str) else v for v in s["vis"]]
        if isinstance(s.get("bg"), str): s["bg"] = VIS[s["bg"]]["media"] if VIS[s["bg"]].get("media") else VIS[s["bg"]]

resolve()
