# Bretagne: script.  Facts and sources: research.md  (respectful; never imply she found survivors; "last known"; no photo of her is free -> labelled context)
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from shots import *
VIS = {}

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
