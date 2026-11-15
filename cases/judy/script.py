# Judy: script.  Facts and sources: research.md (non-graphic; "officially registered"; hedged hell-ship wording)
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from shots import *
VIS = {}

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
