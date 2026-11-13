# Madison - Camp Fire guardian. Sources: CBS News, AP, HuffPost, ABC10/KXTV, Gizmodo, Fox 9, Mercury News, The Hill.
AP = "AP"; CB = "CBS"; MY = "MYD"; ES = "ESC"; DR = "DRONE"; FW = "FOXW"
TITLE = "MADISON"
CAP_ = "Associated Press · video: Shayla Sullivan"
CCB = "CBS News · photos: Shayla Sullivan"
CMY = "ABC10 / KXTV footage"
CES = "KTVU FOX 2"
CDR = "ABC10 / KXTV"
CFW = "FOX Weather"
APC = dict(x0=150, y0=74, ymax=380)           # AP: removes 'Paradise, California' bug + credit
MYC = dict(y0=28, ymax=292)           # re-upload: removes channel logo + subtitles
DRC = dict(y0=26)                     # drone: removes station logo
FWC = dict(ymax=238)                  # Fox Weather: removes lower banners

SEG = [
 dict(kind="narr", text="When the deadliest wildfire in California's history burned his town to the ground, this dog refused to leave.",
      vis=[(ES, 23.4, None, CES, 30.0), (DR, 40.0, DRC, CDR, 52.0)]),
 dict(kind="narr", text="For almost a month, he stayed on the ashes of his home... waiting for a family who couldn't come back.",
      vis=[(AP, 47.6, None, CAP_, 53.9)]),
 dict(kind="narr", text="This is the true story of Madison.",
      vis=[(MY, 23.0, MYC, CMY, 33.8)], title=True),

 dict(kind="chapter", n=1, text="Paradise"),
 dict(kind="narr", text="Paradise, California. A town of about twenty-seven thousand people, tucked into the pine forests of the Sierra foothills.",
      vis=[("MAP_PIN", 0, None, "")]),
 dict(kind="narr", text="Andrea Gaylord lived here with her two big, gentle dogs: Madison, and his brother, Miguel.",
      vis=[(CB, 41.6, dict(ymax=306), CCB, 47.0)]),
 dict(kind="narr", text="They're Anatolian shepherd mixes. Livestock guardians, bred for thousands of years to protect their land, their animals, and their people.",
      vis=[("PHOTO", "anatolian", None, "An Anatolian shepherd (not Madison) · Photo: Zeynel Cebeci · CC BY-SA 4.0"), (AP, 16.0, None, CAP_, 18.6)]),

 dict(kind="chapter", n=2, text="The Fire"),
 dict(kind="narr", text="On the morning of November eighth, 2018, a wildfire broke out near the town.",
      vis=[(FW, 27.5, FWC, CFW, 31.5)], place="PARADISE, CA · NOV 8, 2018"),
 dict(kind="narr", text="Driven by powerful winds, it raced toward Paradise faster than anyone thought possible.",
      vis=[(ES, 0.2, None, CES, 9.0)]),
 dict(kind="narr", text="People fled for their lives, driving through walls of fire and smoke.",
      vis=[(ES, 31.0, None, CES, 38.5), (ES, 44.0, None, CES, 50.0)]),
 dict(kind="narr", text="Andrea had only minutes to get out. In the chaos, she couldn't reach her dogs.",
      vis=[(FW, 43.5, FWC, CFW, 53.0)]),
 dict(kind="narr", text="She had no choice. She had to leave them behind.",
      vis=[(ES, 56.0, None, CES, 62.0)]),

 dict(kind="chapter", n=3, text="The Town That Burned"),
 dict(kind="narr", text="The Camp Fire burned for seventeen days. When it was finally over, Paradise was almost gone.",
      vis=[("PHOTO", "landsat", None, "Camp Fire from space, Nov 8, 2018 · NASA Earth Observatory (public domain)"), (DR, 0.5, DRC, CDR, 13.0)]),
 dict(kind="narr", text="It burned about a hundred and fifty-three thousand acres. An area roughly the size of Chicago.",
      vis=[(DR, 60.0, DRC, CDR, 72.0)]),
 dict(kind="narr", text="Nearly fourteen thousand homes were destroyed. Eighty-five people lost their lives.",
      vis=[("STAT", "14,000", "HOMES DESTROYED", ""), ("STAT", "85", "LIVES LOST", "")]),
 dict(kind="narr", text="Andrea's family lost everything. Nine of their homes burned in the fire.",
      vis=[(DR, 147.0, DRC, CDR, 160.0)]),
 dict(kind="narr", text="Days later, rescuers found Miguel. He'd been taken to a shelter, eighty-five miles away. But Madison was nowhere to be found.",
      vis=[(DR, 175.0, DRC, CDR, 186.0), ("STAT", "85", "MILES AWAY · MIGUEL FOUND", "")]),

 dict(kind="chapter", n=4, text="The Guardian"),
 dict(kind="narr", text="Shayla Sullivan, a volunteer with K9 Paw Print Rescue, was working inside the fire zone, checking on animals people had left behind.",
      vis=[(MY, 34.4, MYC, CMY, 46.0)]),
 dict(kind="narr", text="Andrea asked her to look for Madison. And several days after the fire, Shayla spotted him.",
      vis=[(MY, 2.0, MYC, CMY, 8.0)]),
 dict(kind="narr", text="He was alive. Uninjured. Sitting right where his home used to be.",
      vis=[(AP, 25.2, None, CAP_, 28.9)]),
 dict(kind="narr", text="Nobody knows exactly how he survived. Shayla thinks he outran the flames, then came back as soon as he could.",
      vis=[(DR, 220.0, DRC, CDR, 232.0)]),
 dict(kind="narr", text="Because Madison had a job to do. He was guarding what was left of his family's home. Through rain, through cold, through the ashes. He would not leave.",
      vis=[(MY, 64.5, MYC, CMY, 73.0), (DR, 200.0, DRC, CDR, 212.0)]),
 dict(kind="narr", text="That's what livestock guardian dogs do. They stay with what they protect, no matter what.",
      vis=[(DR, 252.0, DRC, CDR, 262.0)]),
 dict(kind="narr", text="So Shayla kept coming back. She left food and water for him, again and again.",
      vis=[(DR, 240.0, DRC, CDR, 250.0)]),
 dict(kind="narr", text="She even left a piece of Andrea's clothing out for him, so her scent would keep his hope alive.",
      vis=[("PHOTO", "after1", None, "Paradise after the Camp Fire · Photo: Frank Schulenburg · CC BY-SA 4.0")]),
 dict(kind="narr", text="Days turned into weeks. And Madison kept waiting.",
      vis=[("STAT", "~4", "WEEKS WAITING IN THE ASHES", "")]),

 dict(kind="chapter", n=5, text="Coming Home"),
 dict(kind="narr", text="In early December, almost a month after the fire, Andrea was finally allowed back into Paradise.",
      vis=[(MY, 47.0, MYC, CMY, 63.5)], place="EARLY DECEMBER 2018"),
 dict(kind="narr", text="She came back with Miguel... and with Madison's favorite treat, a box of Wheat Thin crackers.",
      vis=[(MY, 73.5, MYC, CMY, 88.0)]),
 dict(kind="narr", text="And there he was. Waiting for her.",
      vis=[(MY, 88.2, MYC, CMY, 95.0)]),
 dict(kind="sound", src=AP, t0=0.2, t1=13.9, speaker="The reunion · natural sound",
      subs=[(0.0, 6.5, "[ Andrea sees Madison for the first time since the fire ]"), (6.5, 13.7, "[ She brought his favorite treat ]")],
      crop=APC, credit=CAP_),
 dict(kind="narr", text="Then Madison saw his brother. The two dogs ran to each other, tails wagging, together again at last.",
      vis=[(MY, 112.0, MYC, CMY, 124.0)]),
 dict(kind="narr", text="Shayla wrote: He had stayed to protect what was left of his home, and never gave up on his people. He didn't give up through the storms, or the fire.",
      vis=[(AP, 29.4, None, CAP_, 37.0), ("PHOTO", "after2", None, "Paradise after the Camp Fire · Photo: Frank Schulenburg · CC BY-SA 4.0")]),
 dict(kind="narr", text="Andrea had lost her home. But she told ABC10, you could never ask for a better animal. Shayla even set up a fundraiser to help the family rebuild.",
      vis=[(AP, 37.2, None, CAP_, 46.7)]),
 dict(kind="narr", text="Some heroes run into danger. Madison's way was different. He survived the fire... and then he stayed, guarding the only place his family would know to look for him.",
      vis=[(MY, 125.0, MYC, CMY, 150.0)]),
 dict(kind="narr", text="If Madison's story touched your heart, subscribe for more true stories of incredible dogs.",
      vis=[("CTA", 0, None, "")], cta=True),
 dict(kind="narr", text="And tell us in the comments: would your dog wait for you like Madison did?",
      vis=[("CTA", 1, None, "")], cta=True),
]
