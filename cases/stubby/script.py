# Stubby: script + visual plan.  Facts and sources: research.md  ("Sergeant" = nickname; spy = period account; no Purple Heart)
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from shots import *
VIS = {}

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
