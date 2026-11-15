# Smoky: script.  Facts and sources: research.md ("according to Wynne" for personal details; "often called the first therapy dog")
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from shots import *
NA = "National Archives / Internet Archive · public domain"
def c(k, a, b, cr, crop=None, focus=(0.5, 0.5)): return F(k, a, b, credit=cr, crop=crop, focus=focus)
TC = dict(x0=0, y0=0, x1=532, y1=220)            # crop burned-in timecode
def cl(a, b): return c("film_convoy_lingayen", a, b, "U.S. Navy film, Lingayen Gulf 1945 · " + NA, TC)
def la(a, b): return c("film_lingayen_action", a, b, "U.S. Navy film, Lingayen Gulf 1945 · " + NA, TC)
def li(a, b): return c("film_lingayen_invasion", a, b, "U.S. Navy film, Lingayen Gulf landing 1945 · " + NA, TC)
def ng(a, b): return c("film_new_guinea_1944", a, b, "New Guinea 1944 · " + NA, dict(x0=0, y0=0, x1=532, y1=236))
def lh(a, b): return c("vid_leyte_hospital_pows_1945", a, b, "U.S. Army film, Philippines 1945 · " + NA)
def nz(a, b): return c("vid_nadzab_paratroop_drop_1943", a, b, "'Air War in the Pacific' (1943), New Guinea · " + NA)
def ae(a, b): return c("vid_new_guinea_air_evac_1944", a, b, "U.S. Army film, New Guinea air evacuation 1944 · " + NA)
def sc(a, b): return c("vid_signal_corps_wire_1944", a, b, "'Your Job in the Signal Corps' (1944) · " + NA)
def yk(k, a, b): return c(k, a, b, "A Yorkshire terrier (not Smoky) · Wikimedia Commons · CC BY-SA")
NOTS = "A YORKIE LIKE SMOKY (NOT SMOKY)"
ST = P("stamp_phlpost", focus=(0.5, 0.5), tone="none")
VIS = {
 "hook1": FULL(yk("vid_yorkie_fastily_1", 0.0, 6.0), punch=True, pops=[CHIP(NOTS, 0.3, color="dark")]),
 "hook2": FULL(nz(231.0, 237.0), punch=True),
 "hook3": FULL(sc(238.0, 245.0), punch=True),
 "hook4": FULL(yk("vid_yorkie_stairs", 0.0, 5.2), punch=True),
 "title": FULL(P("memorial_lakewood", focus=(0.5, 0.4), z=(1.0, 1.1))),
 "ch1": dict(media=nz(128.0, 134.0)),
 "map_ng": MAP("pin", pin="Nadzab", center="Nadzab", towns=[("Nadzab", "NEW GUINEA", "r")], label="EARLY 1944 · SOUTH PACIFIC", zoom=1.2),
 "ng1": FULL(ng(444.0, 450.0), pops=[CHIP("NEW GUINEA · 1944 FILM", 0.3)]),
 "yorkie1": FULL(yk("vid_yorkie_fastily_2", 0.0, 7.0), pops=[CHIP(NOTS, 0.3, color="dark")]),
 "wynne1": FULL(nz(385.0, 391.0), pops=[CHIP("U.S. ARMY AIR FORCES · NEW GUINEA", 0.3)]),
 "wynne2": SPLIT(ae(311.0 + 7, 325.0), ST, chip1="NEW GUINEA · 1943", chip2="SMOKY ON A 2023 STAMP"),
 "helmet1": FULL(yk("vid_yorkie_dog_bed", 0.0, 9.0), pops=[CHIP(NOTS, 0.3, color="dark")]),
 "lost1": FULL(ng(385.0, 391.0)),
 "bris1": FULL(P("ward_milne_bay", focus=(0.5, 0.5), z=(1.0, 1.08)), pops=[CHIP("AN ARMY HOSPITAL WARD, 1944", 0.3)]),
 "pdsa1": FULL(sc(337.0, 343.0), pops=[STAMP("2011", 0.3)]),
 "ch2": dict(media=ae(24.0, 30.0)),
 "raid1": FULL(nz(436.0, 442.0), pops=[STAMP("12 MISSIONS", 0.3)]),
 "raid2": FULL(nz(488.0, 494.0)),
 "mascot1": SPLIT(ae(167.0, 174.0), ST, chip1="1944", chip2="CHAMPION MASCOT"),
 "hosp1": FULL(ae(263.0, 270.0), pops=[CHIP("ARMY AIR EVACUATION · NEW GUINEA 1944", 0.3)]),
 "hosp2": FULL(ae(311.0, 318.0)),
 "hosp3": FULL(lh(272.0, 279.0), pops=[CHIP("OFTEN CALLED THE FIRST THERAPY DOG", 0.3)]),
 "hosp4": FULL(yk("vid_yorkie_dog_bed", 9.0, 17.0)),
 "ch3": dict(media=li(390.0, 396.0)),
 "map_lu": MAP("pin", pin="Lingayen", center="Lingayen", towns=[("Lingayen", "LINGAYEN GULF", "r")], label="EARLY 1945 · THE PHILIPPINES", zoom=1.6),
 "land1": FULL(li(90.0, 97.0), pops=[STAMP("JANUARY 1945", 0.3)]),
 "pipe1": FULL(sc(521.0, 526.0), pops=[CHIP("A TELEGRAPH WIRE", 0.2)]),
 "pipe2": STAT("70 FT", "LONG · 8 INCHES WIDE", li(150.0, 156.0), sub="A pipe under the runway"),
 "dig1": FULL(P("airstrip_engineers", focus=(0.5, 0.5), z=(1.0, 1.08)), pops=[CHIP("ARMY ENGINEERS, PHILIPPINES 1945", 0.3)]),
 "dig2": STAT("3 DAYS", "OF DIGGING", la(89.0, 95.0)),
 "string1": FULL(sc(195.0, 202.0)),
 "stuck1": FREEZE(yk("vid_yorkie_fastily_2", 8.0, 16.0), at="@caught", circle=(0.5, 0.55, 0.22), label="KEEP GOING", speaker="Bill Wynne · Cleveland Magazine", chip=NOTS),
 "out1": FULL(yk("vid_yorkie_fastily_1", 6.0, 14.0), pops=[CHIP(NOTS, 0.3, color="dark")]),
 "out2": FULL(la(20.0, 27.0), pops=[CHIP("THE WIRE WAS THROUGH", 0.3)]),
 "ch4": dict(media=cl(194.0, 200.0)),
 "myth1": STAT("MYTH", "SAVED 250 LIVES", cl(15.0, 22.0)),
 "fact1": STAT("FACT", "SAVED DAYS OF DIGGING", li(330.0, 336.0)),
 "myth2": STAT("FACT", "FOUND IN NEW GUINEA", ng(503.0, 509.0), sub="A soldier's own dog, not an official war dog"),
 "ch5": dict(media=lh(394.0, 400.0)),
 "home1": FULL(yk("vid_yorkie_fastily_1", 14.0, 22.0), pops=[CHIP(NOTS, 0.3, color="dark")]),
 "home2": FULL(P("memorial_lakewood", focus=(0.5, 0.45), z=(1.08, 1.0)), pops=[PIN("CLEVELAND, OHIO", 0.3)]),
 "vets1": FULL(lh(212.0, 219.0)),
 "board": BOARD([(ST, "SMOKY"), (nz(385.0, 385.1), "NEW GUINEA"), (li(90.0, 90.1), "LINGAYEN"), (P("memorial_lakewood"), "CLEVELAND")],
                notes=[("4 LB", "HERO"), ("70 FT", "OF PIPE"), ("150", "AIR RAIDS")]),
 "death1": FULL(cl(223.0, 230.0), pops=[STAMP("FEBRUARY 1957", 0.3)]),
 "statue1": FULL(P("memorial_lakewood", focus=(0.5, 0.35), z=(1.0, 1.12)), pops=[CHIP("SMOKY MEMORIAL · 2005", 0.3)]),
 "wynne_end": FULL(ae(359.0, 366.0)),
 "closing": FULL(P("memorial_lakewood", focus=(0.5, 0.3), z=(1.12, 1.0))),
 "cta0": CTA(0, la(116.0, 123.0)),
 "cta1": CTA(1, li(570.0, 577.0)),
}

SEG = [
 dict(kind="narr", text="She weighed just four pounds. And an entire airfield was waiting on her.",
      vis=["hook1", "hook2"], gap=0.25),
 dict(kind="narr", text="Her job? Crawl through seventy feet of dark, narrow pipe, dragging a wire behind her. No soldier could fit. Only she could.",
      vis=["hook3", "hook4"], gap=0.3),
 dict(kind="narr", text="This is the true story of Smoky.",
      vis=["title"], title=True, gap=0.8),

 dict(kind="chapter", n=1, text="The Foxhole", bg="ch1"),
 dict(kind="narr", text="Early 1944. New Guinea, in the South Pacific. American soldiers found a tiny dog, alone in a jungle foxhole.",
      vis=["map_ng", "ng1"]),
 dict(kind="narr", text="She was a Yorkshire terrier, about seven inches tall. Nobody knew how she got there.",
      vis=["yorkie1"]),
 dict(kind="narr", text="At first, some soldiers thought she belonged to enemy troops. But she didn't understand commands in Japanese, or in English.",
      vis=["lost1"]),
 dict(kind="narr", text="According to Corporal Bill Wynne, an Army Air Forces photographer, he bought her for two Australian pounds. The seller wanted the money for a poker game.",
      vis=["wynne1", "wynne2"]),
 dict(kind="narr", text="He named her Smoky. And he washed her in his helmet.",
      vis=["helmet1"]),

 dict(kind="chapter", n=2, text="The Champion", bg="ch2"),
 dict(kind="narr", text="Smoky went everywhere with Wynne. She's credited with twelve missions, and she lived through about a hundred and fifty air raids, and a typhoon.",
      vis=["raid1", "raid2"]),
 dict(kind="narr", text="In 1944, a military magazine named her the champion mascot of the Southwest Pacific.",
      vis=["mascot1"]),
 dict(kind="narr", text="Then Wynne fell ill with dengue fever. His friends brought Smoky to the hospital. And the nurses had an idea.",
      vis=["hosp1", "hosp2"]),
 dict(kind="narr", text="They took her from ward to ward, to cheer up the wounded soldiers. She's often called the first therapy dog on record.",
      vis=["hosp3", "hosp4"]),

 dict(kind="narr", text="Later, in Australia, Smoky and Wynne visited Army and Navy hospitals in Brisbane, bringing smiles to wounded men.",
      vis=["bris1"]),

 dict(kind="chapter", n=3, text="Seventy Feet of Darkness", bg="ch3"),
 dict(kind="narr", text="Early 1945. The Americans had landed at Lingayen Gulf, in the Philippines, and built an airfield on Luzon.",
      vis=["map_lu", "land1"]),
 dict(kind="narr", text="But they had a problem. A telegraph wire had to run under the runway, through a pipe seventy feet long, and only eight inches wide. Parts of it were filled with sand.",
      vis=["pipe1", "pipe2"]),
 dict(kind="narr", text="Digging up the runway would take about three days, and put the airfield, and the men on it, at risk.",
      vis=["dig1", "dig2"]),
 dict(kind="narr", text="So Bill Wynne tied a string to Smoky's collar. He went to the far end of the pipe, and called her.",
      vis=["string1"]),
 dict(kind="narr", text="About ten feet in, the string got caught. Wynne later said, I called and pleaded with her to keep going.",
      vis=["stuck1"]),
 dict(kind="narr", text="Then, out of the dark, he saw two little eyes. Smoky crawled out the other end. The wire was pulled through, in minutes.",
      vis=["out1", "out2"]),

 dict(kind="chapter", n=4, text="The Truth About Smoky", bg="ch4"),
 dict(kind="narr", text="You may read that Smoky saved two hundred and fifty lives. That number isn't documented. What she really did was save days of dangerous digging.",
      vis=["myth1", "fact1"]),
 dict(kind="narr", text="And she wasn't found in the Philippines. She was found in New Guinea. She was never an official war dog either. She was a soldier's own dog.",
      vis=["myth2"]),

 dict(kind="chapter", n=5, text="Home to Cleveland", bg="ch5"),
 dict(kind="narr", text="After the war, Smoky came home with Wynne to Cleveland, Ohio. She was on the front page of the newspaper, and performed tricks on television.",
      vis=["home1", "home2"]),
 dict(kind="narr", text="And she kept visiting hospitals, cheering up veterans, for years.",
      vis=["vets1"]),
 dict(kind="narr", text="In 2011, the British charity PDSA honored Smoky with a certificate for animal bravery, for what she did at Lingayen Gulf.",
      vis=["pdsa1"]),
 dict(kind="narr", text="Let's look at her whole journey. A jungle foxhole. A hundred and fifty air raids. Hospital wards. And seventy feet of darkness.",
      vis=["board"]),
 dict(kind="narr", text="Smoky died in her sleep in February 1957. Wynne buried her in a World War Two ammunition box. In 2005, a bronze statue of Smoky sitting in a soldier's helmet was placed over the spot.",
      vis=["death1", "statue1"]),
 dict(kind="narr", text="Bill Wynne lived to be ninety-nine. He never forgot the tiny dog from the foxhole.",
      vis=["wynne_end"]),
 dict(kind="narr", text="She weighed four pounds. But her heart was enormous.",
      vis=["closing"], gap=1.0),
 dict(kind="narr", text="If Smoky's story amazed you, subscribe for more true stories of incredible dogs.",
      vis=["cta0"]),
 dict(kind="narr", text="And tell us in the comments. What's the bravest thing your small dog has ever done?",
      vis=["cta1"], gap=1.2),
]

def resolve():
    for s in SEG:
        if "vis" in s: s["vis"] = [VIS[v] if isinstance(v, str) else v for v in s["vis"]]
        if isinstance(s.get("bg"), str): s["bg"] = VIS[s["bg"]].get("media", VIS[s["bg"]])

resolve()
