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
WCROP = None; CCROP = None
VIS = {}   # filled after reviewing the films: name -> media

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
 dict(kind="narr", text="Then, at a dog show in 1922, a cameraman filmed one of his amazing jumps. And Duncan had an idea.",
      vis=["jump1", "jump2"]),

 dict(kind="chapter", n=3, text="The Star", bg="ch3"),
 dict(kind="narr", text="That same year, Rinty got his first small film role. And in 1923, Warner Brothers made him the star of Where the North Begins.",
      vis=["star1", "star2"]),
 dict(kind="narr", text="It was a hit. Audiences had never seen a dog act like this. On screen, he ran through snow, crossed rivers, and came to the rescue.",
      vis=["act1", "act2", "act3"]),
 dict(kind="narr", text="He made more than two dozen films. People around the world lined up to see him, from Paris to Sydney.",
      vis=["world1", "world2"]),
 dict(kind="narr", text="Inside the studio, they called him the mortgage lifter. He's often credited with helping keep the young Warner Brothers studio afloat.",
      vis=["mortgage1", "mortgage2"]),

 dict(kind="chapter", n=4, text="The Truth About the Oscar", bg="ch4"),
 dict(kind="narr", text="You may have heard that Rin Tin Tin won the very first Oscar for Best Actor, and that the Academy took it away because he was a dog.",
      vis=["oscar1"]),
 dict(kind="narr", text="It isn't true. The signed ballots from 1928 still exist. Not a single one mentions a dog. The award went to Emil Jannings.",
      vis=["oscar2", "oscar3"]),
 dict(kind="narr", text="And the famous story that he died in the arms of actress Jean Harlow? That was invented by the press.",
      vis=["harlow1"]),

 dict(kind="chapter", n=5, text="Goodbye, Rinty", bg="ch5"),
 dict(kind="narr", text="The truth is gentler. On August 10th, 1932, Rin Tin Tin died at Lee Duncan's home in Los Angeles. He was about thirteen.",
      vis=["death1", "death2"]),
 dict(kind="narr", text="Radio stations interrupted their programs to share the news.",
      vis=["radio1"]),
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
