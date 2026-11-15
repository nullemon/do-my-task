# Bretagne: script.  Facts and sources: research.md  (respectful; never imply she found survivors; "last known"; no photo of her is free -> labelled context)
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from shots import *
FE = "FEMA Urban Search & Rescue (not Bretagne) · public domain"
def mu(a, b): return F("vid_fema_usar_k9_broll_maui", a, b, credit=FE)
def lw(a, b): return F("vid_fema_usar_k9_la_wildfire", a, b, credit=FE)
def wa(a, b): return F("vid_fema_usar_maui_wa_tf1", a, b, credit=FE)
def gs(a, b): return F("vid_golden_swimming", a, b, credit="A golden retriever (not Bretagne) · Wikimedia Commons · CC BY")
NB = "SEARCH DOGS AT WORK TODAY (NOT BRETAGNE)"
GZ = P("navy_aerial_gz", focus=(0.5, 0.5))
VIS = {
 "hook1": FULL(lw(43.0, 50.0), punch=True, pops=[CHIP(NB, 0.3, color="dark")]),
 "hook2": FULL(mu(456.0, 463.0), punch=True),
 "hook3": FULL(P("navy_aerial_gz", focus=(0.5, 0.5), z=(1.0, 1.1)), punch=True, pops=[STAMP("SEPTEMBER 2001", 0.3)]),
 "title": FULL(gs(0.0, 6.0), pops=[CHIP("A GOLDEN RETRIEVER (NOT BRETAGNE)", 0.3, color="dark")]),
 "ch1": dict(media=gs(6.0, 11.0)),
 "map_tx": MAP("pin", pin="Houston", center="Houston", towns=[("Houston", "HOUSTON, TEXAS", "r")], label="1999 · TEXAS", zoom=1.0),
 "puppy1": FULL(gs(11.0, 18.0)),
 "train1": FULL(wa(25.0, 32.0), pops=[CHIP("SEARCH DOG TRAINING NEVER STOPS", 0.3)]),
 "train2": FULL(mu(120.0, 127.0)),
 "first1": FULL(mu(216.0, 222.0)),
 "dc1": FULL(mu(192.0, 199.0), pops=[CHIP("DISASTER CITY · COLLEGE STATION, TEXAS", 0.3)]),
 "young1": FULL(wa(33.0, 40.0)),
 "study1": FULL(mu(144.0, 151.0)),
 "ch2": dict(media=P("navy_bucket_brigade", focus=(0.5, 0.5))),
 "ny1": FULL(P("navy_bucket_brigade", focus=(0.5, 0.5), z=(1.0, 1.08)), pops=[STAMP("SEPTEMBER 2001", 0.3)]),
 "ny2": STAT("~300", "SEARCH DOGS AT THE 9/11 SITES", mu(264.0, 270.0)),
 "search1": FULL(mu(312.0, 319.0), pops=[CHIP(NB, 0.3, color="dark")]),
 "search2": FULL(mu(360.0, 367.0)),
 "quote1": STAT("\"ANYBODY\"", "WE COULD FIND SOMEBODY", mu(408.0, 415.0), sub="Denise Corliss · Smithsonian Magazine"),
 "comfort1": FULL(wa(47.0, 54.0)),
 "comfort2": FULL(wa(54.0, 61.0), pops=[CHIP("A HEAD ON A FIREFIGHTER'S LAP", 0.3)]),
 "ch3": dict(media=mu(504.0, 509.0)),
 "katrina1": FULL(mu(168.0, 175.0), pops=[STAMP("IVAN · RITA · KATRINA", 0.3)]),
 "katrina2": FULL(wa(64.0, 71.0)),
 "retire1": FULL(gs(18.0, 25.0)),
 "read1": FULL(gs(25.0, 30.0), pops=[CHIP("A PATIENT EAR · A SOFT PAW", 0.3)]),
 "read2": FULL(lw(56.0, 62.0)),
 "memorial1": FULL(P("navy_aerial_gz", focus=(0.35, 0.5), z=(1.1, 1.0)), pops=[STAMP("2014 · BACK IN NEW YORK", 0.3)]),
 "memorial2": FULL(mu(552.0, 558.0)),
 "ch4": dict(media=lw(30.0, 35.0)),
 "myth1": STAT("MYTH", "THE VIRAL GROUND ZERO PHOTOS", P("navy_tired_dog", focus=(0.5, 0.5))),
 "fact1": FREEZE(P("navy_rescue_dog_carried", focus=(0.5, 0.5), z=(1.0, 1.04)), at="@other", circle=(0.5, 0.45, 0.18), label="NOT BRETAGNE", chip="NOT BRETAGNE · A DIFFERENT DOG"),
 "myth2": STAT("FACT", "TEXAS TASK FORCE ONE", wa(73.0, 80.0)),
 "ch5": dict(media=gs(30.0, 34.0)),
 "bday1": FULL(lw(18.0, 25.0)),
 "bday2": STAT("16", "YEARS OLD", mu(440.0, 446.0), sub="A birthday in New York City"),
 "last1": FULL(lw(62.0, 68.0), pops=[STAMP("JUNE 6, 2016", 0.3)]),
 "last2": FULL(mu(240.0, 246.0)),
 "flag1": FULL(wa(81.0, 88.0), pops=[CHIP("THEY LINED UP TO SALUTE HER", 0.3)]),
 "flag2": FULL(mu(288.0, 294.0)),
 "family1": STAT("\"A HERO\"", "AND IS FAMILY", lw(36.0, 42.0), sub="Cy-Fair Volunteer Fire Department"),
 "board": BOARD([(GZ, "GROUND ZERO 2001"), (mu(312.0, 312.1), "SEARCH DOG"), (gs(25.0, 25.1), "READING DOG"), (wa(81.0, 81.1), "THE SALUTE")],
                notes=[("2", "YEARS OLD AT 9/11"), ("3", "HURRICANES"), ("16", "YEARS")]),
 "closing": FULL(mu(520.0, 527.0)),
 "cta0": CTA(0, mu(336.0, 342.0)),
 "cta1": CTA(1, mu(384.0, 390.0)),
}

SEG = [
 dict(kind="narr", text="June 2016. Two lines of firefighters stood outside a vet clinic in Texas. As an old golden retriever walked slowly between them, they saluted.",
      vis=["hook1", "hook2"], gap=0.25),
 dict(kind="narr", text="Fifteen years earlier, she had searched the ruins of the World Trade Center.",
      vis=["hook3"], gap=0.3),
 dict(kind="narr", text="She's believed to be the last known search dog from Ground Zero. This is the true story of Bretagne.",
      vis=["title"], title=True, gap=0.8),

 dict(kind="chapter", n=1, text="The Puppy", bg="ch1"),
 dict(kind="narr", text="Bretagne was born on August 25th, 1999. At eight weeks old, she met Denise Corliss, an electrician and volunteer firefighter near Houston, Texas.",
      vis=["map_tx", "puppy1"]),
 dict(kind="narr", text="Denise trained her as a search and rescue dog. Twenty to thirty hours a week. By about age two, she was certified, and she joined Texas Task Force One.",
      vis=["train1", "train2"]),
 dict(kind="narr", text="She trained at a place called Disaster City, in College Station, Texas, where rescue teams practice in real ruins.",
      vis=["dc1"]),
 dict(kind="narr", text="Her very first mission would be the hardest one of all.",
      vis=["first1"]),

 dict(kind="chapter", n=2, text="Ground Zero", bg="ch2"),
 dict(kind="narr", text="September 11th, 2001. Within days, Texas Task Force One was sent to New York. About three hundred search dogs worked at the 9/11 sites.",
      vis=["ny1", "ny2"]),
 dict(kind="narr", text="Bretagne was two years old. For about two weeks, she searched the rubble in twelve-hour shifts.",
      vis=["search1", "search2"]),
 dict(kind="narr", text="Denise later said, I really believed we could find somebody, anybody, if we could just get to the right void space.",
      vis=["quote1"]),
 dict(kind="narr", text="But Bretagne had another gift. Exhausted firefighters would stop to pet her. Denise remembered her walking right up to one firefighter, lying down, and resting her head on his lap.",
      vis=["comfort1", "comfort2"]),

 dict(kind="chapter", n=3, text="A Life of Service", bg="ch3"),
 dict(kind="narr", text="After 9/11, Bretagne kept serving. She searched after Hurricane Ivan, Hurricane Rita, and Hurricane Katrina.",
      vis=["katrina1", "katrina2"]),
 dict(kind="narr", text="Around age nine, she retired from disaster work. But she didn't stop helping.",
      vis=["retire1"]),
 dict(kind="narr", text="She became a reading dog at a local elementary school. Children who struggled to read aloud would read to her. She gave them a patient ear, and a soft paw.",
      vis=["read1", "read2"]),
 dict(kind="narr", text="She also helped train younger search dogs. And in 2014, she was a finalist for the Hero Dog Awards.",
      vis=["young1"]),
 dict(kind="narr", text="In 2014, she returned to New York, to the 9/11 Memorial. Denise said, she walked to the edge of it and she stopped, turned, and she came back down.",
      vis=["memorial1", "memorial2"]),

 dict(kind="chapter", n=4, text="The Truth About Bretagne", bg="ch4"),
 dict(kind="narr", text="You may have seen viral photos of a golden retriever sleeping on a stretcher at Ground Zero, captioned as Bretagne. Those photos show other dogs.",
      vis=["myth1", "fact1"]),
 dict(kind="narr", text="And she was not with Pennsylvania's team. She served with Texas Task Force One. Her team was there to search for survivors, and to bring families answers.",
      vis=["myth2"]),

 dict(kind="chapter", n=5, text="The Salute", bg="ch5"),
 dict(kind="narr", text="For her sixteenth birthday, she was taken to New York City. Her name even went up on a billboard in Times Square.",
      vis=["bday1", "bday2"]),
 dict(kind="narr", text="But by June 2016, her kidneys were failing. On June 6th, Denise walked her into the vet in Cypress, Texas, one last time.",
      vis=["last1", "last2"]),
 dict(kind="narr", text="Firefighters and search and rescue teammates lined the path, and saluted. When she came out, she was covered with an American flag.",
      vis=["flag1", "flag2"]),
 dict(kind="narr", text="Her fire department said, Bretagne was a civil servant, a hero, and is family.",
      vis=["family1"]),
 dict(kind="narr", text="Even after she was gone, she kept helping. She became part of a long-running scientific study of the 9/11 search dogs.",
      vis=["study1"]),
 dict(kind="narr", text="Let's look at her whole life. Ground Zero at two years old. Three hurricanes. A school full of young readers. And a final salute.",
      vis=["board"]),
 dict(kind="narr", text="She went where people were hurting. And she made them feel a little less alone.",
      vis=["closing"], gap=1.0),
 dict(kind="narr", text="If Bretagne's story touched you, subscribe for more true stories of incredible dogs.",
      vis=["cta0"]),
 dict(kind="narr", text="And tell us in the comments. Do you know a hero dog? Tell us their name.",
      vis=["cta1"], gap=1.2),
]

def resolve():
    for s in SEG:
        if "vis" in s: s["vis"] = [VIS[v] if isinstance(v, str) else v for v in s["vis"]]
        if isinstance(s.get("bg"), str): s["bg"] = VIS[s["bg"]].get("media", VIS[s["bg"]])

resolve()
