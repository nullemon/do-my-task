# Smoky: script.  Facts and sources: research.md ("according to Wynne" for personal details; "often called the first therapy dog")
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from shots import *
VIS = {}

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

 dict(kind="chapter", n=3, text="Seventy Feet of Darkness", bg="ch3"),
 dict(kind="narr", text="Early 1945. The Americans had landed at Lingayen Gulf, in the Philippines, and built an airfield on Luzon.",
      vis=["map_lu", "land1"]),
 dict(kind="narr", text="But they had a problem. A telegraph wire had to run under the runway, through a pipe seventy feet long, and only eight inches wide. Parts of it were filled with sand.",
      vis=["pipe1", "pipe2"]),
 dict(kind="narr", text="Digging up the runway would take about three days, and put the airfield, and the men on it, at risk.",
      vis=["dig1", "dig2"]),
 dict(kind="narr", text="So Wynne tied a string to Smoky's collar. He went to the far end of the pipe, and called her.",
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
