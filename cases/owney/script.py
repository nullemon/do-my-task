# Owney: script + visual plan.  Facts and sources: research.md
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "lib"))
from shots import *
OP = "owney_portrait"
LOC = "Library of Congress Paper Print Collection"
def lo(k, a, b, credit=None, focus=(0.5, 0.5)): return F(k, a, b, credit=credit or (LOC + " · " + k.replace("loc_", "").replace("_", " ")), focus=focus)
def bd(a, b): return F("vid_black_diamond_1900", a, b, credit="New Black Diamond Express (Edison, 1900) · Library of Congress / public domain")

SEG = [
 dict(kind="narr", text="In 1895, a scruffy little mutt walked up the gangway of a mail ship, with no ticket. And he sailed all the way around the world.",
      vis=[FULL(P(OP, focus=(0.5, 0.35), z=(1.0, 1.10)), punch=True),
           FULL(lo("loc_pilot_boats_ny", 25.0, 31.0, credit=LOC + " · Pilot boats in New York harbor, 1899"), pops=[STAMP("1895", 0.3)], punch=True)], gap=0.3),
 dict(kind="narr", text="He had ridden the mail trains for years. More than a hundred and forty thousand miles. And every town he visited gave him a souvenir.",
      vis=[FULL(lo("loc_throwing_mail_bags", 22.0, 30.0, credit=LOC + " · Throwing mail into bags, U.S.P.O., 1903"), pops=[POL(P("tag_corn_palace", tone="none"), "HIS REAL TAG · 1891", 0.8, pos="br")]),
           STAT("140,000+", "MILES BY MAIL", P("owney_with_tags", focus=(0.5, 0.5)))], gap=0.3),
 dict(kind="narr", text="This is the true story of Owney.",
      vis=[FULL(P("owney_portrait_1895", focus=(0.5, 0.35), z=(1.05, 1.0)))], title=True, gap=0.8),

 dict(kind="chapter", n=1, text="The Post Office Dog", bg=lo("loc_collecting_mail", 26.0, 32.0)),
 dict(kind="narr", text="In 1888, a small terrier mix turned up at the post office in Albany, New York. He probably came with a clerk who later moved away. But the dog stayed.",
      vis=[SPLIT(lo("loc_loading_mail_car", 40.0, 48.0, credit=LOC + " · Loading mail car, 1903"), P("albany_post_office_1915", focus=(0.5, 0.5)), chip1="THE MAIL · 1900s FILM", chip2="ALBANY POST OFFICE"),
           FULL(lo("loc_collecting_mail", 17.0, 23.0, credit=LOC + " · Collecting mail, U.S.P.O., 1903"), pops=[CHIP("REAL 1903 POST OFFICE FILM", 0.3)])]),
 dict(kind="narr", text="The workers named him Owney. And Owney fell in love with one thing. The mailbags.",
      vis=[SPLIT(lo("loc_throwing_mail_bags", 56.0, 64.0, credit=LOC + " · Mailbags, 1903"), P("owney_mailsack_illus", focus=(0.5, 0.5)), chip1="THE MAILBAGS", chip2="OWNEY ON A MAILBAG")]),
 dict(kind="narr", text="The clerks gave him a collar, with a tag that read: Owney, Post Office, Albany, New York.",
      vis=[FULL(P("owney_portrait", focus=(0.5, 0.45), z=(1.1, 1.0)), pops=[CHIP("\"OWNEY, POST OFFICE, ALBANY, N.Y.\"", 0.4)])]),
 dict(kind="narr", text="He slept on them. And when the bags were loaded onto wagons, and then onto trains, Owney went with them.",
      vis=[FULL(lo("loc_wagons_loading", 20.0, 28.0, credit=LOC + " · Wagons loading mail, U.S.P.O., 1903"), pops=[CHIP("MAIL WAGONS · 1903", 0.3)]),
           FULL(lo("loc_loading_mail_car", 20.0, 28.0, credit=LOC + " · Loading mail car, U.S.P.O., 1903"), pops=[CHIP("MAILBAGS ONTO THE TRAIN", 0.3)])]),

 dict(kind="chapter", n=2, text="The Lucky Dog", bg=lo("loc_throwing_mail_bags", 40.0, 48.0)),
 dict(kind="narr", text="Owney became the mascot of the Railway Mail Service. He rode inside the mail cars, where clerks sorted letters as the train rolled across America.",
      vis=[FULL(lo("loc_routing_mail", 21.0, 29.0, credit=LOC + " · Routing mail, U.S.P.O., 1903")), FULL(P("owney_mail_carrier", focus=(0.5, 0.45), z=(1.0, 1.08)), pops=[CHIP("OWNEY WITH A MAIL CLERK", 0.3)])]),
 dict(kind="narr", text="The clerks loved him. Some believed no train he rode would ever be wrecked. And at every stop, people added a tag to his collar.",
      vis=[SPLIT(lo("loc_overland_express", 18.0, 25.0, credit=LOC + " · Overland Express arriving at Helena, Mont., 1897"), P("tag_boston_albany", focus=(0.5, 0.5), tone="none"), chip1="A MAIL TRAIN ARRIVES · 1897", chip2="HIS TAG: BOSTON & ALBANY R.P.O."),
           SPLIT(P("tag_houston", focus=(0.5, 0.5), tone="none"), P("tag_woodburys_lunch", focus=(0.5, 0.5), tone="none"), chip1="HOUSTON, TEXAS", chip2="A LUNCH TOKEN · 1892")]),
 dict(kind="narr", text="Medals. Hotel keys. Railway tokens. Even a token for five cents at a bar. His collar became so heavy that the Postmaster General, John Wanamaker, gave him a harness to carry them all.",
      vis=[FREEZE(P("owney_with_tags", focus=(0.5, 0.5), z=(1.0, 1.04)), at="@harness", circle=(0.5, 0.55, 0.22), label="THE HARNESS", chip="REAL PHOTO"),
           FULL(P("tag_5_cents_bar", focus=(0.5, 0.5), z=(1.0, 1.1), tone="none"), pops=[CHIP("\"GOOD FOR 5 CENTS\"", 0.3)])]),
 dict(kind="narr", text="Today, three hundred and seventy-two of his tags survive. But his greatest adventure was still ahead.",
      vis=[STAT("372", "OF HIS TAGS SURVIVE", lo("loc_routing_mail", 30.0, 38.0), sub="Smithsonian National Postal Museum")]),

 dict(kind="narr", text="His travels even took him across the borders, into Mexico and Canada.",
      vis=[FULL(lo("loc_overland_express", 32.0, 40.0, credit=LOC + " · Overland Express, 1897"))]),

 dict(kind="chapter", n=3, text="Around the World", bg=P("tacoma_waterfront_1892", focus=(0.5, 0.5))),
 dict(kind="narr", text="On August 19th, 1895, Owney left Tacoma, Washington, aboard the mail steamer Victoria. He carried his own bag, and letters of introduction.",
      vis=[SPLIT(lo("loc_pilot_boats_ny", 46.0, 53.0, credit=LOC + " · Ships in harbor, 1899"), P("tacoma_waterfront_1892", focus=(0.5, 0.5)), chip1="AUGUST 19, 1895", chip2="TACOMA, WASHINGTON · 1892")]),
 dict(kind="narr", text="He sailed to Japan, and China. Then Singapore. Through the Suez Canal, to Algiers, and the Azores. And then home to New York.",
      vis=[MAP("route", pts=["Tacoma", "PacificMid", "Yokohama", "HongKong", "Singapore", "IndianMid", "PortSaid", "Algiers", "Azores", "NewYork"],
               towns=[("Tacoma", "TACOMA", "l"), ("Yokohama", "JAPAN", "r"), ("HongKong", "CHINA", "l"), ("Singapore", "SINGAPORE", "r"),
                      ("PortSaid", "SUEZ", "r"), ("Algiers", "ALGIERS", "r"), ("Azores", "AZORES", "l"), ("NewYork", "NEW YORK", "r")],
               label="1895 · AROUND THE WORLD", note="Route shown is approximate", zoom=1.0)]),
 dict(kind="narr", text="Newspapers reported that in Japan, he was even given a passport. The whole trip took about four months.",
      vis=[STAT("~4", "MONTHS AROUND THE WORLD", lo("loc_pilot_boats_ny", 39.0, 46.0, credit=LOC + " · New York harbor, 1899"), sub="Back in America by the end of December 1895")]),
 dict(kind="narr", text="By the end of December, he was back in America. A famous dog, with a harness full of medals from all over the world.",
      vis=[SPLIT(lo("loc_philadelphia_express", 15.0, 21.0, credit=LOC + " · Philadelphia Express, 1897"), P("owney_with_tags", focus=(0.5, 0.45)), chip1="BACK ON THE RAILS", chip2="OWNEY AND HIS MEDALS")]),

 dict(kind="chapter", n=4, text="The Last Journey", bg=bd(14.0, 20.0)),
 dict(kind="narr", text="But by 1897, Owney was old, and tired, and sometimes grumpy. In June that year, in Toledo, Ohio, after biting a clerk, the old dog was put down.",
      vis=[FULL(lo("loc_train_mailbag", 18.0, 30.0, credit=LOC + " · Train taking up mail bag, U.S.P.O., 1903"), pops=[STAMP("JUNE 11, 1897", 0.3)])]),
 dict(kind="narr", text="The railway mail clerks were heartbroken. So they paid, out of their own pockets, to have him preserved. They wanted him to stay with the mail, forever.",
      vis=[FULL(P("owney_museum_display", focus=(0.5, 0.45), z=(1.0, 1.08)))]),

 dict(kind="chapter", n=5, text="The Truth About Owney", bg=P("owney_museum_front", focus=(0.5, 0.45))),
 dict(kind="narr", text="Many stories say he was a stray who wandered in, on a cold night. But the Smithsonian's research suggests he probably had an owner, a postal clerk, who moved away.",
      vis=[STAT("MYTH", "A STRAY ON A COLD NIGHT", P("albany_post_office_1915", focus=(0.5, 0.5))), STAT("FACT", "PROBABLY A CLERK'S DOG", P(OP, focus=(0.5, 0.4)))]),
 dict(kind="narr", text="And no, he never wore a thousand tags at once. Only a few could fit on his harness at a time. The rest were kept safe.",
      vis=[STAT("MYTH", "1,000 TAGS AT ONCE", lo("loc_mail_coach_ford", 66.0, 72.0, credit=LOC + " · Old mail coach at ford, 1903")),
           STAT("FACT", "A FEW AT A TIME", P("tag_houston", focus=(0.5, 0.5), tone="none"))]),
 dict(kind="narr", text="Let's look at his whole journey. Albany. The mail trains. A trip around the world. And a museum, where he still sits today.",
      vis=[BOARD([(P(OP, focus=(0.5, 0.35)), "OWNEY"), (P("rpo_interior_1909"), "THE MAIL CARS"), (P("tacoma_wharves_1892"), "TACOMA 1895"),
                  (P("owney_museum_front"), "THE MUSEUM")], notes=[("140K+", "MILES"), ("372", "TAGS LEFT"), ("~4", "MONTHS AT SEA")])]),
 dict(kind="narr", text="In 1904, Owney was put on show at the World's Fair in St. Louis. And in 1911, he went to the Smithsonian.",
      vis=[FULL(bd(25.0, 33.0), pops=[STAMP("1904 · ST. LOUIS", 0.3)])]),
 dict(kind="narr", text="Since 1993, Owney has been at the Smithsonian's National Postal Museum in Washington. And in 2011, the Postal Service put him on a stamp.",
      vis=[FULL(P("owney_museum_front", focus=(0.5, 0.45), z=(1.0, 1.1)), pops=[PIN("NATIONAL POSTAL MUSEUM", 0.3)]),
           FULL(P("owney_museum_medals", focus=(0.5, 0.5), z=(1.08, 1.0)), pops=[STAMP("2011: HIS OWN STAMP", 0.3)])]),
 dict(kind="narr", text="In 2011, a taxidermist spent about a month restoring him, so he could keep greeting visitors for many years to come.",
      vis=[SPLIT(lo("loc_wagons_loading", 45.0, 53.0, credit=LOC + " · Wagons loading mail, 1903"), P("owney_museum_medals", focus=(0.5, 0.5)), chip1="THE MAIL ROLLS ON", chip2="RESTORED · 2011")]),
 dict(kind="narr", text="He never had a ticket. But everywhere he went, people made him feel at home.",
      vis=[FULL(P("owney_portrait_1895", focus=(0.5, 0.35), z=(1.0, 1.12)))], gap=1.0),
 dict(kind="narr", text="If you loved Owney's story, subscribe for more true stories of incredible dogs.",
      vis=[CTA(0, lo("loc_collecting_mail", 40.0, 48.0))]),
 dict(kind="narr", text="And tell us in the comments. Where would your dog travel, if they could go anywhere?",
      vis=[CTA(1, lo("loc_routing_mail", 50.0, 58.0))], gap=1.2),
]
