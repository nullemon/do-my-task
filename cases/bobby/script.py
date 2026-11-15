# Greyfriars Bobby: script + visual plan.  research.md: legend vs record must be clear on screen
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from shots import *
B = "bobby_photo_ngs"
CC = "Wikimedia Commons · CC BY / CC BY-SA"
def v(k, a, b, cr=CC, crop=None): return F(k, a, b, credit=cr, crop=crop)
def gun(a, b): return v("vid_castle_gun_salute", a, b, "Edinburgh Castle gun salute · " + CC)
def e50(a, b): return v("vid_scotland_1950_edinburgh_princes_st", a, b, "'Scotland' (1950) · National Archives · public domain")
def hp(a, b): return v("vid_scotland_1950_holyrood_pipers", a, b, "'Scotland' (1950) · National Archives · public domain")
def wk(a, b): return v("vid_walking_edinburgh_4k", a, b, "Walking Edinburgh's Old Town · " + CC)
def ct(a, b): return v("vid_edinburgh_castle_4k", a, b, "Edinburgh Old Town · " + CC, crop=dict(x0=0, y0=0, x1=1280, y1=590))
def rm(a, b): return v("vid_royal_mile", a, b, "The Royal Mile, Edinburgh · " + CC)
def bp(a, b): return v("vid_bagpiper_high_court", a, b, "Piper on the Royal Mile · " + CC)
def mc(a, b): return v("vid_mercat_cross_royal_mile", a, b, "Royal Mile, Edinburgh · " + CC)

SEG = [
 dict(kind="narr", text="For fourteen years, Edinburgh believed this little dog never left his master's grave.",
      vis=[FULL(P("bobby_photo_ngs_crop", focus=(0.5, 0.45), z=(1.0, 1.10)), punch=True)], gap=0.25),
 dict(kind="narr", text="They gave him a collar, a statue, and a place in history. But then, a historian made a shocking claim. There may have been two Bobbys.",
      vis=[FULL(P("collar", focus=(0.5, 0.5), z=(1.0, 1.1)), pops=[CHIP("HIS REAL COLLAR · 1867", 0.2)], punch=True),
           FULL(gun(19.0, 25.0), punch=True),
           SPLIT(P(B, focus=(0.5, 0.45)), P("bobby_traill_family_crop", focus=(0.5, 0.5)), chip1="BOBBY?", chip2="...OR ANOTHER DOG?")], gap=0.3),
 dict(kind="narr", text="So what really happened? This is the true story of Greyfriars Bobby.",
      vis=[FULL(P("bobby_photo_ngs_alt", focus=(0.5, 0.45), z=(1.05, 1.0)))], title=True, gap=0.8),

 dict(kind="chapter", n=1, text="The Legend", bg=P("kirkyard_1840s_hill_adamson", focus=(0.5, 0.5))),
 dict(kind="narr", text="Edinburgh, Scotland, in the 1800s. In the heart of the Old Town lies Greyfriars Kirkyard, an old churchyard full of crowded tombs.",
      vis=[MAP("pin", pin="Edinburgh", center="Edinburgh", towns=[("Edinburgh", "EDINBURGH", "r")], label="SCOTLAND · 1860s", zoom=1.3),
           FULL(e50(296.0, 303.0), pops=[CHIP("EDINBURGH ON FILM", 0.3)])]),
 dict(kind="narr", text="According to the traditional story, a police night watchman named John Gray died in 1858, and was buried here.",
      vis=[SPLIT(wk(30.0, 38.0), P("kirkyard_1840s_met", focus=(0.5, 0.5)), chip1="EDINBURGH'S OLD TOWN", chip2="GREYFRIARS KIRKYARD · 1840s")]),
 dict(kind="narr", text="His little terrier, Bobby, refused to leave the grave. The story goes that he slept there in every kind of weather, for fourteen years.",
      vis=[FREEZE(P(B, focus=(0.5, 0.45), z=(1.0, 1.04)), at="@refused", circle=(0.5, 0.5, 0.22), label="THAT'S BOBBY", chip="REAL PHOTO · c.1865")]),
 dict(kind="narr", text="Every day, they said, when the one o'clock gun fired from the castle, Bobby trotted out for a meal at a coffee house nearby.",
      vis=[FULL(gun(4.0, 11.0), pops=[CHIP("THE CASTLE GUN", 0.3)]), FULL(P("traill_coffee_house_1865", focus=(0.5, 0.5), z=(1.0, 1.08)), pops=[CHIP("TRAILL'S COFFEE HOUSE · 1865", 0.3)])]),

 dict(kind="chapter", n=2, text="What We Know", bg=P("collar", focus=(0.5, 0.5))),
 dict(kind="narr", text="Here is what the records do show. In the 1860s, a small terrier called Bobby really did live in and around Greyfriars Kirkyard.",
      vis=[SPLIT(wk(110.0, 118.0), P("bobby_photo_ngs_alt", focus=(0.5, 0.45)), chip1="AROUND GREYFRIARS TODAY", chip2="DOCUMENTED: BOBBY")]),
 dict(kind="narr", text="The neighbours fed him, especially John Traill, who ran the coffee house. His family later gave Bobby's dinner dish to the Museum of Edinburgh.",
      vis=[SPLIT(P("bobby_traill_family", focus=(0.5, 0.5)), P("traill_coffee_house_1865", focus=(0.5, 0.5)), chip1="BOBBY WITH THE TRAILL FAMILY · 1868", chip2="THE COFFEE HOUSE")]),
 dict(kind="narr", text="In 1867, a new law meant dogs without a licence could be destroyed. Bobby had no owner. So the Lord Provost of Edinburgh, Sir William Chambers, paid for his licence himself.",
      vis=[STAT("1867", "A NEW DOG LAW", e50(618.0, 625.0), sub="Unlicensed dogs could be destroyed."),
           FREEZE(P("collar", focus=(0.5, 0.5), z=(1.0, 1.04)), at="@himself", circle=(0.5, 0.5, 0.25), label="HIS REAL COLLAR", chip="MUSEUM OF EDINBURGH")]),
 dict(kind="narr", text="He gave Bobby a brass collar. It says, Greyfriars Bobby, from the Lord Provost, 1867, licensed. And you can still see it today.",
      vis=[SPLIT(rm(0.0, 13.0), P("collar_crop", focus=(0.5, 0.5)), chip1="THE ROYAL MILE", chip2="\"FROM THE LORD PROVOST 1867\"")]),

 dict(kind="chapter", n=3, text="Goodbye, Bobby", bg=P("bobby_grave_geograph", focus=(0.5, 0.5))),
 dict(kind="narr", text="Bobby died on January 14th, 1872. And Scotland's newspaper, The Scotsman, printed an obituary, for a dog. It was reprinted as far away as London.",
      vis=[SPLIT(e50(350.0, 357.0), P("bobby_photo_ngs_crop", focus=(0.5, 0.45)), chip1="EDINBURGH CASTLE", chip2="JANUARY 14, 1872")]),
 dict(kind="narr", text="He was buried just inside the gate of Greyfriars Kirkyard. A dog, resting among the people of Edinburgh.",
      vis=[SPLIT(ct(305.0, 312.0), P("bobby_grave_geograph", focus=(0.5, 0.5)), chip1="EDINBURGH", chip2="BOBBY'S GRAVE")]),
 dict(kind="narr", text="A year later, a wealthy admirer, Baroness Burdett-Coutts, paid for a bronze statue of Bobby, on a drinking fountain, with a low basin, for thirsty dogs.",
      vis=[FULL(P("statue_fountain_pd", focus=(0.5, 0.45), z=(1.0, 1.08)), pops=[STAMP("1873", 0.3)]),
           SPLIT(wk(188.0, 196.0), P("statue_closeup", focus=(0.5, 0.4)), chip1="CANDLEMAKER ROW TODAY", chip2="THE STATUE")]),
 dict(kind="narr", text="In 1981, Bobby got his own headstone. It reads, let his loyalty and devotion be a lesson to us all.",
      vis=[FULL(P("bobby_headstone_1981", focus=(0.5, 0.5), z=(1.0, 1.1)), pops=[STAMP("1981", 0.3)])]),

 dict(kind="chapter", n=4, text="Two Bobbys?", bg=P("statue_rain", focus=(0.5, 0.45))),
 dict(kind="narr", text="But in 2011, historian Jan Bondeson argued that the legend was a clever business story. Bobby, he said, was a stray who was fed in the kirkyard, and the tale was good for the coffee house, and for the visitors it brought.",
      vis=[STAT("2011", "A HISTORIAN'S CLAIM", ct(176.0, 183.0), sub="Jan Bondeson"),
           FULL(wk(412.0, 420.0))]),
 dict(kind="narr", text="He went further. He said the first Bobby died around 1867, and a younger dog quietly took his place.",
      vis=[SPLIT(P(B, focus=(0.5, 0.45)), P("bobby_traill_family_crop", focus=(0.5, 0.5)), chip1="DOG 1?", chip2="DOG 2?")]),
 dict(kind="narr", text="Others disagree. In 2024, a researcher who studied the old photographs argued that they all show the same dog.",
      vis=[SPLIT(mc(0.0, 11.5), P("bobby_patterson_possible", focus=(0.5, 0.5)), chip1="EDINBURGH TODAY", chip2="THE DEBATE CONTINUES")]),

 dict(kind="chapter", n=5, text="The Truth About Bobby", bg=P("nose_rubbing", focus=(0.5, 0.5))),
 dict(kind="narr", text="So here's what we can say. There's no record that proves a fourteen-year vigil at one grave. And Auld Jock, the shepherd from the Disney film, comes from a novel, not from history.",
      vis=[STAT("MYTH", "AULD JOCK THE SHEPHERD", P("kirkyard_1840s_met", focus=(0.5, 0.5))), STAT("FACT", "FROM A 1912 NOVEL", P("bobby_photo_ngs_alt", focus=(0.5, 0.45)))]),
 dict(kind="narr", text="And rubbing the statue's nose for luck is not an old tradition. It's a modern tourist habit, and it has worn the bronze away.",
      vis=[FULL(P("nose_rubbing", focus=(0.5, 0.5), z=(1.0, 1.1)), pops=[STAMP("PLEASE DON'T RUB", 0.4)])]),
 dict(kind="narr", text="In 2013, the council even had to repair the statue's nose, and asked visitors to stop rubbing it. Within days, someone had scratched it again.",
      vis=[SPLIT(wk(700.0, 708.0), P("statue_rain", focus=(0.5, 0.45)), chip1="EDINBURGH TODAY", chip2="2013 · NOSE REPAIRED")]),
 dict(kind="narr", text="Let's look at what's real. A little terrier. A neighbourhood that fed him. A collar from the Lord Provost. And a whole city that loved him.",
      vis=[BOARD([(P(B, focus=(0.5, 0.45)), "BOBBY · c.1865"), (P("bobby_traill_family"), "THE TRAILLS"), (P("collar"), "THE COLLAR"),
                  (P("statue_fountain_pd"), "THE STATUE")], notes=[("1867", "LICENSED"), ("1872", "DIED"), ("1873", "STATUE")])]),
 dict(kind="narr", text="Maybe he guarded a grave. Maybe he was just a stray, who found a whole city to care for him. Either way, Edinburgh never forgot him.",
      vis=[FULL(hp(190.0, 198.0))], gap=1.0),
 dict(kind="narr", text="If you enjoyed Bobby's story, subscribe for more true stories of incredible dogs.",
      vis=[CTA(0, bp(0.0, 8.0))]),
 dict(kind="narr", text="And tell us in the comments. Was Bobby loyal, or a lovable stray with a great story? What do you think?",
      vis=[CTA(1, wk(560.0, 568.0))], gap=1.2),
]
