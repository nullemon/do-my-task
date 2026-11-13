# Bobbie the Wonder Dog - script + visual plan
# Sources: KOIN 6 / WISH-TV report (Oregon Historical Society archive), KGW "Digging for Old",
# Oregon Encyclopedia (Stelljes), Wikipedia "Bobbie the Wonder Dog", Call of the West (1924, public domain).
W = "WISH"      # WISH-TV copy of KOIN 6 report (no station bug)
C = "COTW"      # Call of the West (1924) - Oregon Historical Society
K = "KGWS"      # KGW Silverton travel piece (modern Silverton)

TITLE = "BOBBIE THE WONDER DOG"

# visual: (source, t_in, crop[x0,y0,x1,y1] in source pixels or None=auto, credit)
CR_WISH = "KOIN 6 / WISH-TV · Oregon Historical Society"
CR_COTW = "\"The Call of the West\" (1924) · Oregon Historical Society"
CR_KGWS = "KGW News"

SEG = [
 # ---------------- HOOK
 dict(kind="narr", text="In 1923, a family lost their dog two and a half thousand miles from home.",
      vis=[(C, 459.0, None, CR_COTW)]),
 dict(kind="narr", text="Six months later, a thin, limping collie came walking down Main Street... and right back to their door.",
      vis=[(C, 434.5, None, CR_COTW, 447.0), (W, 0.2, dict(ymax=272), CR_WISH, 11.5)]),
 dict(kind="narr", text="This is the true story of Bobbie, the Wonder Dog.",
      vis=[(W, 12.3, None, CR_WISH, 16.9)], title=True),

 # ---------------- 1
 dict(kind="chapter", n=1, text="The Road Trip"),
 dict(kind="narr", text="Silverton, Oregon. The early nineteen-twenties.",
      vis=[(W, 90.3, None, CR_WISH, 96.5)], place="SILVERTON, OREGON · 1923"),
 dict(kind="narr", text="The Brazier family runs a little café in town. And their best friend is Bobbie, a two-year-old Scotch collie mix.",
      vis=[(W, 33.2, None, CR_WISH, 38.6), (W, 39.4, None, CR_WISH, 42.5)]),
 dict(kind="narr", text="In August 1923, the family packs up their touring car for a long trip east, to visit relatives in Wolcott, Indiana.",
      vis=[(W, 46.2, None, CR_WISH, 53.5), ("MAP_OUT", 0, None, "")]),
 dict(kind="narr", text="In 1923, a trip like that was a real adventure. Rough roads, long days, and thousands of miles across the country.",
      vis=[(C, 210.5, None, CR_COTW, 217.0), (C, 218.5, None, CR_COTW, 227.5)]),
 dict(kind="narr", text="Bobbie rides along the whole way, perched right on top of the luggage, nose in the wind.",
      vis=[(W, 54.3, None, CR_WISH, 59.0), (C, 528.8, None, CR_COTW, 545.0)]),

 # ---------------- 2
 dict(kind="chapter", n=2, text="Lost in Indiana"),
 dict(kind="narr", text="Then, at a gas station in Wolcott, everything goes wrong.",
      vis=[("PHOTO", "sanborn", None, "Sanborn map of Wolcott, Indiana, 1909 · Library of Congress (public domain)")], place="WOLCOTT, INDIANA · AUGUST 1923"),
 dict(kind="sound", src=W, t0=69.26, t1=73.92, speaker="Gus Frederick, Silverton Country Historical Society",
      subs=[(0.0, 2.1, "\"Apparently he was ran off...\""), (2.1, 4.66, "\"...was chased by some local dogs.\"")],
      crop=dict(ymax=275), credit=CR_WISH),
 dict(kind="narr", text="Bobbie runs, and keeps running. Into a town he has never known, more than two thousand miles from home.",
      vis=[(C, 475.3, None, CR_COTW, 481.6)]),
 dict(kind="narr", text="The family searches for days. They put up posters. They place notices in the newspapers.",
      vis=[(C, 470.2, None, CR_COTW, 473.6), (C, 298.4, None, CR_COTW, 308.8)]),
 dict(kind="narr", text="But Bobbie is gone.",
      vis=[(C, 482.2, None, CR_COTW, 485.5)]),
 dict(kind="narr", text="Heartbroken, the Braziers drive all the way home to Oregon... without him. They're sure they will never see their dog again.",
      vis=[(C, 316.2, None, CR_COTW, 321.6), (C, 274.5, None, CR_COTW, 281.0)]),

 # ---------------- 3
 dict(kind="chapter", n=3, text="The Long Walk Home"),
 dict(kind="narr", text="Winter comes. Six months go by.",
      vis=[(K, 0.0, None, CR_KGWS, 2.95)]),
 dict(kind="narr", text="Then, on February fifteenth, 1924, one of the Brazier daughters steps out of the café... and sees a dog coming down the street.",
      vis=[(C, 490.2, None, CR_COTW, 495.6), (C, 496.0, None, CR_COTW, 499.8)], place="SILVERTON · FEBRUARY 15, 1924"),
 dict(kind="narr", text="He's thin and filthy. His fur is matted. His paws are raw, and his toenails are worn down to almost nothing.",
      vis=[(C, 452.6, None, CR_COTW, 458.8), (C, 118.2, None, CR_COTW, 125.8)]),
 dict(kind="narr", text="It's Bobbie.",
      vis=[(W, 17.3, None, CR_WISH, 21.6)]),
 dict(kind="narr", text="Somehow, all alone, he had crossed plains, deserts, rivers and mountains, including the Continental Divide, in the dead of winter.",
      vis=[("MAP_HOME", 0, None, "")]),
 dict(kind="narr", text="Think about that. No map. No roads he knew. Freezing nights, and no one to feed him except strangers along the way.",
      vis=[(C, 572.5, None, CR_COTW, 580.0), (C, 236.0, None, CR_COTW, 256.0)]),
 dict(kind="narr", text="By the family's odometer, that's two thousand, five hundred and fifty-one miles. About fourteen miles, every single day.",
      vis=[("STAT", "2,551", "MILES HOME", ""), ("STAT", "~14", "MILES A DAY · 6 MONTHS", "")]),
 dict(kind="narr", text="And when he finally got home? The family wrote down exactly what happened.",
      vis=[(W, 134.2, None, CR_WISH, 139.8)]),
 dict(kind="sound", src=W, t0=140.30, t1=144.52, speaker="Kerry Tymchuk, Oregon Historical Society",
      subs=[(0.0, 2.2, "\"They fed him a sirloin, a big bowl of cream...\""), (2.2, 4.22, "\"...and he didn't move for three days.\"")],
      crop=dict(ymax=278), credit=CR_WISH),

 # ---------------- 4
 dict(kind="chapter", n=4, text="The Wonder Dog"),
 dict(kind="narr", text="Could a dog really do that? The Oregon Humane Society set out to investigate.",
      vis=[(W, 128.3, None, CR_WISH, 133.9)]),
 dict(kind="narr", text="As the story spread, people from across the country wrote in. They had fed Bobbie, or given him a warm place to sleep, before he set off again, heading west.",
      vis=[(W, 145.0, None, CR_WISH, 150.3), (W, 236.0, None, CR_WISH, 240.6)]),
 dict(kind="narr", text="Using those letters, the investigators pieced together much of his route home. They became convinced: Bobbie really had made the journey on his own.",
      vis=[(W, 120.0, None, CR_WISH, 127.6), (C, 142.3, None, CR_COTW, 147.4)]),
 dict(kind="narr", text="Bobbie became a national sensation. Hundreds of letters arrived, addressed simply to Bobbie, the Wonder Dog. One man in Australia even sent him a box of wildflowers.",
      vis=[(W, 158.2, None, CR_WISH, 160.9), (W, 203.3, None, CR_WISH, 205.9), (W, 173.4, None, CR_WISH, 174.9)]),
 dict(kind="narr", text="He was featured in Ripley's Believe It or Not. He was given medals, keys to cities, and a jeweled collar.",
      vis=[(W, 182.3, None, CR_WISH, 188.9)]),
 dict(kind="narr", text="And within months, he starred as himself in a silent film, The Call of the West. Much of the footage in this video comes from that very film. That's the real Bobbie you're watching.",
      vis=[(C, 9.0, None, CR_COTW, 17.2), (C, 348.5, None, CR_COTW, 371.0), (C, 380.0, None, CR_COTW, 391.5)]),
 dict(kind="narr", text="At the Portland Home Show, forty thousand people came just to see him. He was even given his own little house.",
      vis=[(W, 206.3, None, CR_WISH, 208.8), (W, 282.0, None, CR_WISH, 285.5)]),

 # ---------------- 5
 dict(kind="chapter", n=5, text="Forever Home"),
 dict(kind="narr", text="Bobbie died in 1927, just three years after his incredible journey.",
      vis=[(W, 230.2, None, CR_WISH, 235.9)]),
 dict(kind="narr", text="He was buried with honors at the Oregon Humane Society in Portland. The mayor gave his eulogy. And later, Rin Tin Tin, the most famous movie dog in the world, laid a wreath at his grave.",
      vis=[(W, 220.2, None, CR_WISH, 229.5), (W, 244.0, None, CR_WISH, 245.3), (W, 249.2, None, CR_WISH, 255.6)]),
 dict(kind="narr", text="He still rests there today. Years later, some wanted to move him home to Silverton. But the family chose to leave him where Grandpa Brazier had wanted him to be.",
      vis=[(W, 298.6, None, CR_WISH, 305.4), (W, 291.2, None, CR_WISH, 294.9)]),
 dict(kind="narr", text="Today, Bobbie's story is painted across a giant mural in Silverton. There's a statue, and a replica of his little house.",
      vis=[(W, 268.2, None, CR_WISH, 276.8), ("PHOTO", "statue", None, "Photo: Only in Oregon · CC BY 2.0"), (W, 277.3, None, CR_WISH, 281.8)]),
 dict(kind="narr", text="And every year, the town holds a pet parade. The very first one, in 1932, was led by Bobbie's own son, Pal.",
      vis=[(W, 286.2, None, CR_WISH, 290.9), (W, 213.2, None, CR_WISH, 219.8)]),
 dict(kind="narr", text="Nobody knows exactly how Bobbie found his way back across a continent.",
      vis=[(C, 584.0, None, CR_COTW, 592.5)]),
 dict(kind="narr", text="But we know why. Because home isn't a place on a map. It's the people waiting for you there.",
      vis=[(W, 306.5, None, CR_WISH, 316.4)]),

 # ---------------- CTA
 dict(kind="narr", text="If Bobbie's story touched your heart, subscribe for more true stories of incredible dogs.",
      vis=[("CTA", 0, None, "")], cta=True),
 dict(kind="narr", text="And tell us in the comments: what's the most loyal thing your dog has ever done?",
      vis=[("CTA", 1, None, "")], cta=True),
]
