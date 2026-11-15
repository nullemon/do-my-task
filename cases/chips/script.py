# Chips: script + visual plan.  Facts and sources: research.md   (enemy soldiers were ITALIAN; "credited with" for counts)
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from shots import *
VIS = {}   # filled after reviewing the films

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
 dict(kind="narr", text="In 1942, America was at war, and the Army asked families to lend their dogs. It was called Dogs for Defense. The Wrens said yes.",
      vis=["dfd1", "dfd2"]),
 dict(kind="narr", text="Chips was trained as a sentry dog, and paired with Private John Rowell, of the 3rd Infantry Division.",
      vis=["train1", "train2", "train3"]),

 dict(kind="chapter", n=2, text="Guarding Roosevelt and Churchill", bg="ch2"),
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
