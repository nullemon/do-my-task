# Hachikō: script + visual plan.  Facts and sources: research.md
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from shots import *

SEG = [
 # ---------------- HOOK (format 2: full screen + pop-ups)
 dict(kind="narr", text="Every evening, a dog walked to a Tokyo train station to meet the man he loved.",
      vis=[FULL(P("photo34", focus=(0.5, 0.42), z=(1.0, 1.10)), punch=True)], gap=0.25),
 dict(kind="narr", text="One day, the man didn't come home. But the dog kept coming back. Every single day. For almost ten years.",
      vis=[FULL(P("onwatch", focus=(0.30, 0.62), z=(1.0, 1.08)), punch=True),
           FULL(P("yaekohachi", focus=(0.62, 0.6), z=(1.04, 1.12)), pops=[STAMP("1925 → 1935", 0.2)], punch=True)], gap=0.3),
 dict(kind="narr", text="Some people chased him away. Others thought he was just a stray. And then, one newspaper story changed everything.",
      vis=[SPLIT(P("paw", focus=(0.6, 0.45)), P("famweb", focus=(0.45, 0.62)), chip1="SHIBUYA STATION · c.1933", chip2="THE REAL HACHI"),
           FULL(P("stuffed35", focus=(0.5, 0.5), z=(1.0, 1.1)), pops=[STAMP("OCT 4, 1932", "@newspaper")])], gap=0.3),
 dict(kind="narr", text="This is the true story of Hachikō.",
      vis=[FULL(P("portrait", focus=(0.5, 0.4), z=(1.0, 1.08)))], title=True, gap=0.8),

 # ---------------- CHAPTER 1
 dict(kind="chapter", n=1, text="A Gift From Akita", bg=P("photo34", focus=(0.5, 0.5))),
 dict(kind="narr", text="He was born in November 1923, near the town of Ōdate, in the snowy north of Japan. A white Akita puppy.",
      vis=[MAP("pin", pin="Odate", center="Odate", towns=[("Odate", "ŌDATE, AKITA", "r")], label="NOVEMBER 1923 · NORTHERN JAPAN", zoom=1.5)],
      place=None),
 dict(kind="narr", text="In January 1924, at about fifty days old, he was put on a train to Tokyo. The journey took around twenty hours.",
      vis=[MAP("route", pts=["Odate", "Morioka", "Sendai", "Tokyo"], towns=[("Odate", "ŌDATE", "r"), ("Tokyo", "TOKYO", "l")],
               label="JANUARY 1924 · BY TRAIN", counter=(20, "HOURS ON A TRAIN"), note="Route shown is approximate")]),
 dict(kind="narr", text="Waiting for him was Professor Hidesaburō Ueno. He taught agricultural engineering at Tokyo Imperial University. And he adored dogs.",
      vis=[SPLIT(P("ueno2", focus=(0.5, 0.35)), P("portrait", focus=(0.5, 0.35)), chip1="PROF. HIDESABURŌ UENO", chip2="HACHI")]),
 dict(kind="narr", text="He named the puppy Hachi, which means eight in Japanese. The kō came later, an affectionate title people added to his name.",
      vis=[FULL(P("photo34", focus=(0.5, 0.3), z=(1.12, 1.02)), pops=[CHIP("HACHI = \"EIGHT\"", 0.6)])]),

 # ---------------- CHAPTER 2
 dict(kind="chapter", n=2, text="The Station", bg=P("onwatch", focus=(0.3, 0.5))),
 dict(kind="narr", text="The family later remembered a daily routine. Ueno often took the train from Shibuya Station. And in the evening, Hachi would be there to meet him.",
      vis=[FULL(P("onwatch", focus=(0.65, 0.4), pan=((0.75, 0.4), (0.3, 0.6)), z=(1.0, 1.06)), pops=[PIN("SHIBUYA STATION, TOKYO", 0.3)])]),
 dict(kind="narr", text="For about sixteen months, that was their life together. Then came May 21st, 1925.",
      vis=[SPLIT(P("ueno2", focus=(0.5, 0.4)), P("paw", focus=(0.65, 0.4))), STAT("16", "MONTHS TOGETHER", P("famweb", focus=(0.4, 0.7)))]),
 dict(kind="narr", text="That afternoon, at the university, Professor Ueno suffered a sudden stroke and died. He was fifty-three. He never came back to the station.",
      vis=[FULL(P("ueno2", focus=(0.5, 0.42), z=(1.0, 1.1)), pops=[STAMP("MAY 21, 1925", 0.2)])]),
 dict(kind="narr", text="Hachi waited there that evening. And the next. And the next.",
      vis=[FREEZE(P("onwatch", focus=(0.3, 0.6), z=(1.0, 1.04)), at="@next", circle=(0.30, 0.66, 0.22), label="STILL WAITING", chip="SHIBUYA · c.1933")]),

 # ---------------- CHAPTER 3
 dict(kind="chapter", n=3, text="Nine Years", bg=P("yaekohachi", focus=(0.65, 0.6))),
 dict(kind="narr", text="Hachi was sent to live with relatives, and later with Ueno's gardener, Kikusaburō Kobayashi, not far from Shibuya.",
      vis=[FULL(P("famweb", focus=(0.4, 0.6), z=(1.0, 1.08)), pops=[CHIP("HACHI IN THE 1930s", 0.4)])]),
 dict(kind="narr", text="But he kept slipping away. Back to the station. Day after day. Season after season.",
      vis=[FULL(P("onwatch", focus=(0.3, 0.6), z=(1.1, 1.0)), punch=True), STAT("3,500+", "DAYS AT THE STATION", P("onwatch", focus=(0.6, 0.4)), sub="May 1925 – March 1935")]),
 dict(kind="narr", text="Not everyone was kind. Some people kicked him, or drew on his face. But others fed him and watched over him.",
      vis=[SPLIT(P("paw", focus=(0.3, 0.45)), P("yaekohachi", focus=(0.5, 0.6)), chip1="SHIBUYA · c.1933", chip2="FRIENDS AT THE STATION")]),
 dict(kind="narr", text="Hachi grew old. One of his ears began to droop. And still, he waited. But that wasn't the most amazing part of his story.",
      vis=[FREEZE(P("portrait", focus=(0.5, 0.3), z=(1.0, 1.05)), at="@ears", circle=(0.67, 0.13, 0.13), label="THE DROOPING EAR", chip="c.1934")]),

 # ---------------- CHAPTER 4
 dict(kind="chapter", n=4, text="Japan Finds Out", bg=P("paw", focus=(0.6, 0.5))),
 dict(kind="narr", text="Hirokichi Saitō was an expert on Japanese dog breeds. He first saw Hachi in 1928, and he couldn't forget him.",
      vis=[FULL(P("taxiderm", focus=(0.4, 0.6), z=(1.0, 1.08)), pops=[CHIP("1928", 0.3)])]),
 dict(kind="narr", text="On October 4th, 1932, the Tokyo Asahi Shimbun newspaper told Hachi's story. Almost overnight, the old dog at Shibuya became famous across Japan.",
      vis=[FULL(P("paw", focus=(0.55, 0.45), z=(1.0, 1.1)), pops=[STAMP("OCT 4, 1932", 0.2), POL(P("portrait"), "TOKYO ASAHI SHIMBUN", "@famous", pos="br")])]),
 dict(kind="narr", text="People came from far away just to see him. Teachers and parents held him up as an example of loyalty.",
      vis=[SPLIT(P("yaekohachi", focus=(0.6, 0.6)), P("famweb", focus=(0.4, 0.5)))]),
 dict(kind="narr", text="In April 1934, a bronze statue of Hachi was unveiled at Shibuya Station. And Hachi himself was there to see it.",
      vis=[FULL(P("photo34", focus=(0.5, 0.45), z=(1.0, 1.08)), pops=[STAMP("APRIL 21, 1934", 0.2)])]),

 # ---------------- CHAPTER 5
 dict(kind="chapter", n=5, text="Together Again", bg=P("grave", focus=(0.45, 0.4))),
 dict(kind="narr", text="On March 8th, 1935, Hachi was found on a street near the station. He had died in the early hours. He was eleven years old.",
      vis=[FULL(P("portrait", focus=(0.5, 0.45), z=(1.08, 1.0)), pops=[STAMP("MARCH 8, 1935", 0.2)])]),
 dict(kind="narr", text="For decades, people said he died from eating yakitori skewers. But in 2011, scientists at the University of Tokyo examined his preserved organs. The real cause was cancer, and heartworm. The skewers had not killed him.",
      vis=[STAT("MYTH", "SKEWERS KILLED HIM", P("stuffed35", focus=(0.5, 0.5))),
           STAT("FACT", "CANCER + HEARTWORM", P("portrait", focus=(0.5, 0.5)), sub="University of Tokyo study, 2011")]),
 dict(kind="narr", text="Japan mourned him. At Aoyama Cemetery in Tokyo, a monument to Hachi stands right beside the professor's grave.",
      vis=[FULL(P("grave", focus=(0.45, 0.45), z=(1.0, 1.08)), pops=[PIN("AOYAMA CEMETERY, TOKYO", 0.3)])]),
 dict(kind="narr", text="His body was preserved. You can still see him today, at the National Museum of Nature and Science in Tokyo.",
      vis=[FULL(P("stuffed35", focus=(0.5, 0.45))), FULL(P("museum", focus=(0.35, 0.5), z=(1.0, 1.1)), pops=[CHIP("NATIONAL MUSEUM OF NATURE AND SCIENCE", 0.3)])]),
 dict(kind="narr", text="Let's look at the whole journey. One puppy. A twenty-hour train ride. Sixteen months with the man he loved. And almost ten years of waiting.",
      vis=[BOARD([(P("puppy"), "THE PUPPY"), (P("ueno2", focus=(0.5, 0.35)), "PROF. UENO"), (P("onwatch", focus=(0.3, 0.6)), "SHIBUYA"), (P("portrait", focus=(0.5, 0.3)), "HACHI")],
                 notes=[("20", "HOURS"), ("16", "MONTHS"), ("~10", "YEARS")])]),
 dict(kind="narr", text="The first statue was melted down during the war. In 1948, the sculptor's son made a new one. Today it's one of the most famous meeting places in the world.",
      vis=[FULL(P("wall", focus=(0.5, 0.5), z=(1.0, 1.06), crop=(0, 0, 1920, 1330))), FULL(P("shibuya23", focus=(0.5, 0.5), z=(1.0, 1.08)), pops=[CHIP("SHIBUYA TODAY", 0.3)])]),
 dict(kind="narr", text="And in 2015, eighty years after his death, the University of Tokyo unveiled one more statue. Hachi, leaping up to greet his professor. Together, at last.",
      vis=[SPLIT(P("ueno2", focus=(0.5, 0.4)), P("photo34", focus=(0.5, 0.3)), chip1="PROF. UENO", chip2="HACHI")]),
 dict(kind="narr", text="He never understood why the professor didn't come home. He only knew where to wait.",
      vis=[FULL(P("photo34", focus=(0.5, 0.35), z=(1.0, 1.12)))], gap=1.0),
 dict(kind="narr", text="If this story touched you, subscribe for more true stories of incredible dogs.",
      vis=[CTA(0, P("portrait", focus=(0.5, 0.4)))]),
 dict(kind="narr", text="And tell us in the comments. What's the most loyal thing your dog has ever done?",
      vis=[CTA(1, P("paw", focus=(0.6, 0.45)))], gap=1.2),
]
