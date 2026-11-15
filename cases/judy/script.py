# Judy: script.  Facts and sources: research.md (non-graphic; "officially registered"; hedged hell-ship wording)
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from shots import *
NA = "National Archives / Internet Archive · public domain"
def c(k, a, b, cr, crop=None, focus=(0.5, 0.5)): return F(k, a, b, credit=cr, crop=crop, focus=focus)
def pt(a, b): return c("vid_bird_dogs_pointers_1940", a, b, "'Bird Dogs' (1940) · Internet Archive · public domain")
def yz(a, b): return c("vid_panay_yangtze_1937", a, b, "Universal Newsreel 1937 · Yangtze River gunboats · public domain")
def kg(a, b): return c("vid_hms_kgv_1945", a, b, "Royal Navy warship 1945 · " + NA, crop=dict(x0=0, y0=0, x1=532, y1=226))
def al(a, b): return c("vid_hms_algonquin", a, b, "Warship at sea 1944 · " + NA)
def sg(a, b): return c("vid_japan_conquers_singapore_1942", a, b, "Singapore 1942 newsreel · Internet Archive · public domain")
def se(a, b): return c("vid_japan_conquers_se_asia", a, b, "Southeast Asia 1942 newsreel · Internet Archive · public domain")
def kr(a, b): return c("vid_kampar_river", a, b, "Kampar River, Sumatra · Wikimedia Commons · CC BY-SA")
def ps(a, b): return c("vid_padang_surrender_1945", a, b, "Japanese surrender, Padang, Sumatra 1945 · public domain")
def rp(a, b): return c("vid_released_pows_japan_1945", a, b, "Released prisoners of war 1945 · " + NA)
def rs(a, b): return c("vid_reoccupation_singapore_1945", a, b, "Reoccupation of Singapore 1945 · " + NA)
def su(a, b): return c("vid_sumatra_1944", a, b, "Sumatra 1944 · " + NA)
def ss(a, b): return c("vid_surrender_singapore_1945", a, b, "Singapore 1945 · " + NA)
def fb(a, b): return c("vid_freed_pows_bangkok_1946", a, b, "Freed prisoners 1946 · Dutch newsreel · Open Beelden · CC BY-SA")
NOTJ = "AN ENGLISH POINTER LIKE JUDY (NOT JUDY)"
JD = P("judy_on_deck", focus=(0.6, 0.6))
VIS = {
 "hook1": FULL(P("judy_on_deck", focus=(0.6, 0.62), z=(1.0, 1.1)), punch=True, pops=[CIRCLE(0.62, 0.62, 0.22, 0.6)]),
 "hook2": FULL(rp(90.0, 96.0), punch=True),
 "hook3": FULL(yz(460.0, 466.0), punch=True, pops=[STAMP("POW 81A", 0.3)]),
 "hook4": FULL(kr(9.0, 15.0), punch=True),
 "hook5": FULL(pt(165.0, 171.0), pops=[CHIP(NOTJ, 0.2, color="dark")]),
 "title": FULL(P("judy_on_deck", focus=(0.6, 0.6), z=(1.08, 1.0))),
 "ch1": dict(media=yz(591.0, 596.0)),
 "born1": MAP("pin", pin="Shanghai", center="Shanghai", towns=[("Shanghai", "SHANGHAI", "r")], label="FEBRUARY 1936 · CHINA", zoom=1.2),
 "born2": FULL(pt(99.0, 106.0), pops=[CHIP(NOTJ, 0.3, color="dark")]),
 "gnat1": FULL(yz(985.0, 992.0), pops=[CHIP("THE YANGTZE RIVER · 1937 FILM", 0.3)]),
 "gnat2": SPLIT(yz(328.0, 335.0), P("hms_gnat_1927", focus=(0.5, 0.5)), chip1="YANGTZE GUNBOAT CREWS · 1937", chip2="HMS GNAT"),
 "gnat3": FULL(pt(231.0, 238.0), pops=[CHIP(NOTJ, 0.3, color="dark")]),
 "gnat4": FULL(pt(297.0, 304.0)),
 "warn1": FULL(yz(197.0, 204.0)),
 "ch2": dict(media=su(236.0, 241.0)),
 "grass1": SPLIT(su(21.0, 28.0), P("hms_grasshopper", focus=(0.5, 0.5)), chip1="FEBRUARY 1942", chip2="HMS GRASSHOPPER"),
 "map1": MAP("route", pts=["Singapore", "Singkep", "Padang", "Medan"], towns=[("Singapore", "SINGAPORE", "r"), ("Padang", "PADANG", "l"), ("Medan", "MEDAN", "l")],
             label="1942 · SHIPWRECKED", center="Singkep", zoom=1.4, note="Route shown is approximate"),
 "bomb1": FULL(sg(30.0, 36.0), pops=[STAMP("FEBRUARY 14, 1942", 0.2)]),
 "bomb2": FULL(su(279.0, 285.0)),
 "island1": FULL(su(407.0, 414.0)),
 "island2": FULL(pt(430.0, 437.0), pops=[CHIP("SHE DUG · AND FOUND WATER", 0.3)]),
 "trek1": FULL(kr(27.0, 34.0), pops=[CHIP("SUMATRA", 0.3)]),
 "trek2": FULL(kr(63.0, 70.0)),
 "trek3": FULL(sg(89.0, 96.0), pops=[STAMP("MARCH 18, 1942", 0.3)]),
 "ch3": dict(media=kr(118.0, 124.0)),
 "frank1": FULL(c("vid_medan_1943", 58.0, 65.0, "Medan, Sumatra 1943 · Internet Archive · public domain"), pops=[PIN("MEDAN, SUMATRA", 0.3)]),
 "frank2": FULL(rp(18.0, 25.0)),
 "frank3": FREEZE(P("judy_on_deck", focus=(0.6, 0.6), z=(1.0, 1.04)), at="@survivor", circle=(0.62, 0.62, 0.2), label="THAT'S JUDY", speaker="Frank Williams · The National Archives", chip="HIS WORDS"),
 "pow1": STAT("81A", "PRISONER OF WAR NUMBER", fb(127.0, 133.0), sub="Gloegoer camp, Medan"),
 "pow2": FULL(rp(54.0, 60.0)),
 "pow3": STAT("ONE", "DOG EVER OFFICIALLY A POW", rp(233.0, 239.0), sub="in the whole of World War Two"),
 "ch4": dict(media=al(289.0, 294.0)),
 "ship1": FULL(rp(197.0, 204.0), pops=[STAMP("JUNE 1944", 0.3)]),
 "ship2": FULL(al(481.0, 488.0), pops=[CHIP("HIDDEN IN A RICE SACK", 0.3)]),
 "torp1": FULL(al(225.0, 232.0)),
 "torp2": FULL(kg(6.0, 13.0)),
 "swim1": FULL(rs(349.0, 356.0), pops=[CHIP("\"A LOT OF PEOPLE OWE THEIR LIVES TO JUDY\"", 0.4)]),
 "reunion1": FULL(fb(25.0, 31.0)),
 "reunion2": FULL(P("judy_on_deck", focus=(0.6, 0.6), z=(1.1, 1.0)), pops=[CHIP("REUNITED", 0.3)]),
 "ch5": dict(media=fb(42.0, 48.0)),
 "rail1": FULL(kr(81.0, 88.0), pops=[CHIP("THE SUMATRAN JUNGLE", 0.3)]),
 "rail2": FULL(kr(136.0, 143.0)),
 "free1": FULL(ps(3.0, 7.5), pops=[STAMP("AUGUST 1945", 0.3), CHIP("JAPANESE SURRENDER · PADANG, SUMATRA", 0.6)]),
 "free2": FULL(ss(467.0, 474.0)),
 "medal1": FULL(rs(23.0, 30.0), pops=[STAMP("MAY 1946", 0.3), POL(P("dickin_medal_simple", tone="none"), "THE DICKIN MEDAL", "@Dickin", pos="br")]),
 "medal2": FULL(ss(192.0, 199.0)),
 "myth1": STAT("MYTH", "SHE DIED IN 1960", pt(562.0 + 30, 600.0)),
 "fact1": STAT("FACT", "FEBRUARY 1950", pt(628.0, 635.0), sub="Her grave confirms it"),
 "board": BOARD([(JD, "JUDY"), (yz(460.0, 460.1), "THE YANGTZE"), (kr(9.0, 9.1), "SUMATRA"), (P("dickin_medal_simple", tone="none"), "DICKIN MEDAL")],
                notes=[("81A", "POW NUMBER"), ("2", "SHIPWRECKS"), ("1946", "MEDAL")]),
 "grave1": FULL(P("judy_grave", focus=(0.5, 0.5), z=(1.0, 1.08)), pops=[CHIP("JUDY'S MEMORIAL · BUILT BY FRANK", 0.3)]),
 "grave2": FULL(fb(144.0, 150.0)),
 "closing": FULL(P("judy_on_deck", focus=(0.6, 0.62), z=(1.0, 1.12))),
 "cta0": CTA(0, su(150.0, 157.0)),
 "cta1": CTA(1, su(322.0, 329.0)),
}

SEG = [
 dict(kind="narr", text="In the Second World War, thousands of men were registered as prisoners of war. Only one dog ever was.",
      vis=["hook1", "hook2"], gap=0.25),
 dict(kind="narr", text="Her number was 81A. She survived two shipwrecks, a crocodile, and three years in prison camps.",
      vis=["hook3", "hook4"], gap=0.3),
 dict(kind="narr", text="And she saved the life of the man who saved hers.",
      vis=["hook5"], gap=0.3),
 dict(kind="narr", text="This is the true story of Judy.",
      vis=["title"], title=True, gap=0.8),

 dict(kind="chapter", n=1, text="The Ship's Dog", bg="ch1"),
 dict(kind="narr", text="Judy was born in February 1936, in a kennel in Shanghai. A liver and white English pointer.",
      vis=["born1", "born2"]),
 dict(kind="narr", text="She became the mascot of a Royal Navy gunboat, HMS Gnat, patrolling the Yangtze River in China.",
      vis=["gnat1", "gnat2"]),
 dict(kind="narr", text="She was a terrible gun dog. She kept falling overboard. But she was brilliant at one thing. She could hear danger coming, long before the sailors could.",
      vis=["gnat3", "gnat4"]),
 dict(kind="narr", text="She barked at river pirates, and at enemy planes, giving the crew precious seconds of warning.",
      vis=["warn1"]),

 dict(kind="chapter", n=2, text="Shipwrecked", bg="ch2"),
 dict(kind="narr", text="In 1939, Judy moved with her crew to a new gunboat, HMS Grasshopper. And in February 1942, as Singapore was about to fall, the ship tried to escape.",
      vis=["grass1", "map1"]),
 dict(kind="narr", text="On February 14th, Japanese planes bombed the Grasshopper. The crew abandoned ship. Judy was trapped below decks, until a sailor went back and pulled her out.",
      vis=["bomb1", "bomb2"]),
 dict(kind="narr", text="The survivors reached a small island. There was no fresh water. Then Judy started digging. And she found a freshwater spring.",
      vis=["island1", "island2"]),
 dict(kind="narr", text="They crossed to Sumatra and trekked for hundreds of miles through the jungle. On the way, Judy was wounded by a crocodile. But they were too late. On March 18th, 1942, they were captured.",
      vis=["trek1", "trek2", "trek3"]),

 dict(kind="chapter", n=3, text="Prisoner 81A", bg="ch3"),
 dict(kind="narr", text="In a prison camp at Medan, a young RAF airman named Frank Williams noticed a starving dog. He shared his tiny bowl of rice with her.",
      vis=["frank1", "frank2"]),
 dict(kind="narr", text="Frank later said, I realised that even though she was thin, she was a survivor. From that day, they were never apart.",
      vis=["frank3"]),
 dict(kind="narr", text="According to Frank, he persuaded the camp commander to register Judy as an official prisoner of war. Her number was 81A. It meant she had a right to rations, and a better chance to survive.",
      vis=["pow1", "pow2"]),
 dict(kind="narr", text="She is the only dog known to have been officially registered as a prisoner of war in the whole of World War Two. But the hardest part was still ahead.",
      vis=["pow3"]),

 dict(kind="chapter", n=4, text="The Rice Sack", bg="ch4"),
 dict(kind="narr", text="In June 1944, the prisoners were put on a ship to be moved. Dogs were not allowed. So Frank hid Judy in a rice sack. She stayed completely silent for hours.",
      vis=["ship1", "ship2"]),
 dict(kind="narr", text="Then the ship was torpedoed. Frank pushed Judy out through a porthole, into the sea. Many on board did not survive.",
      vis=["torp1", "torp2"]),
 dict(kind="narr", text="In the water, Judy swam to struggling men, bringing them floating wreckage to hold on to. One survivor said, a lot of people owe their lives to Judy.",
      vis=["swim1"]),
 dict(kind="narr", text="Frank was sent to another camp. He thought she was dead. Then he walked in, and there she was. He said he couldn't believe his eyes.",
      vis=["reunion1", "reunion2"]),

 dict(kind="chapter", n=5, text="Free at Last", bg="ch5"),
 dict(kind="narr", text="For another year, the prisoners were forced to build a railway through the jungle. Judy stayed by Frank's side. Food was scarce, and many fell ill.",
      vis=["rail1", "rail2"]),
 dict(kind="narr", text="In August 1945, the war ended. Frank smuggled Judy onto a troopship home to England.",
      vis=["free1", "free2"]),
 dict(kind="narr", text="In May 1946, Judy was awarded the Dickin Medal, often called the animals' Victoria Cross. Her citation praised her magnificent courage and endurance in Japanese prison camps.",
      vis=["medal1", "medal2"]),
 dict(kind="narr", text="Some websites say Judy died in 1960. That's wrong. She died in February 1950, in Tanzania, where she had moved with Frank. She was almost fourteen.",
      vis=["myth1", "fact1"]),
 dict(kind="narr", text="Let's look at her whole journey. A ship's dog on the Yangtze. Two shipwrecks. Prisoner 81A. And a medal for courage.",
      vis=["board"]),
 dict(kind="narr", text="Frank buried her in his RAF jacket, and built a memorial stone with his own hands. His wife later said Judy had saved his life, again and again.",
      vis=["grave1", "grave2"]),
 dict(kind="narr", text="He shared his rice with her. She gave him a reason to survive.",
      vis=["closing"], gap=1.0),
 dict(kind="narr", text="If Judy's story moved you, subscribe for more true stories of incredible dogs.",
      vis=["cta0"]),
 dict(kind="narr", text="And tell us in the comments. Would your dog stay by your side through anything?",
      vis=["cta1"], gap=1.2),
]

def resolve():
    for s in SEG:
        if "vis" in s: s["vis"] = [VIS[v] if isinstance(v, str) else v for v in s["vis"]]
        if isinstance(s.get("bg"), str): s["bg"] = VIS[s["bg"]].get("media", VIS[s["bg"]])

resolve()
