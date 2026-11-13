# Frida - Mexican Navy rescue dog. Sources: Wikipedia (BBC/Reuters/Guardian refs), AFP via The Citizen, NBC, CBS SF, Mental Floss, Mexico News Daily, AP via Bangkok Post.
S = "SEMAR"; CB = "CBBC"; CS = "CBS"; NY = "NYT"; RT = "RET"; ST = "STATUE"; MI = "MIL"
TITLE = "FRIDA"
CSE = "Mexican Navy (SEMAR) via Storyful / KCAU"
CCB = "CBBC Newsround"
CCS = "CBS News"
CNY = "The New York Times"
CMI = "MILENIO"
SEC = dict(ymax=338)
CBC = dict(ymax=292)
CSC = dict(ymax=296)
NYC = dict(y0=32, ymax=288)
MIC = dict(y0=40, ymax=266)
STC = dict(x1=548, ymax=262)
RTC = dict(x0=270, x1=500, ymax=328)

SEG = [
 dict(kind="narr", text="When a powerful earthquake brought down buildings across Mexico City, people trapped under the rubble waited for one sound.",
      vis=[(NY, 26.2, NYC, CNY, 31.9), (CB, 25.3, CBC, CCB, 32.6)]),
 dict(kind="narr", text="A bark. From a yellow Labrador in goggles and little boots.",
      vis=[(S, 9.2, SEC, CSE, 10.9), (S, 5.2, SEC, CSE, 8.9)]),
 dict(kind="narr", text="This is the true story of Frida.",
      vis=[(S, 28.2, SEC, CSE, 30.9)], title=True),

 dict(kind="chapter", n=1, text="The Navy Dog"),
 dict(kind="narr", text="Frida was born on April twelfth, 2009, and joined the Mexican Navy's canine unit as a search and rescue dog.",
      vis=[(S, 57.2, SEC, CSE, 60.9), (S, 31.2, SEC, CSE, 35.9)]),
 dict(kind="narr", text="Labradors make great search dogs. A powerful nose, endless energy, and they'll work all day for a toy or a treat.",
      vis=[(S, 36.2, SEC, CSE, 39.9)]),
 dict(kind="narr", text="Her job was to find people. Specifically, people who were still alive, buried under collapsed buildings. When she smelled someone, she was trained to bark.",
      vis=[(CS, 11.2, CSC, CCS, 17.9), (S, 47.2, SEC, CSE, 49.9)]),
 dict(kind="narr", text="To protect her, the navy gave her special gear. Goggles to shield her eyes from dust. A harness. And boots, so broken glass and sharp metal couldn't cut her paws.",
      vis=[(CB, 0.1, CBC, CCB, 2.9), (S, 19.2, SEC, CSE, 22.9), (CB, 12.2, CBC, CCB, 15.9)]),
 dict(kind="narr", text="With her handler, she was sent to disasters far from home: the earthquake in Haiti in 2010, and later to Ecuador, where in 2017 she searched through a deadly landslide.",
      vis=[(CS, 28.2, CSC, CCS, 30.9), (S, 40.2, SEC, CSE, 43.9)]),

 dict(kind="chapter", n=2, text="September 19"),
 dict(kind="narr", text="Then, on September nineteenth, 2017, disaster struck at home.",
      vis=[("MAP_PIN", 0, None, "")]),
 dict(kind="narr", text="A magnitude seven point one earthquake hit central Mexico. In Mexico City, buildings swayed... and then fell.",
      vis=[(NY, 0.1, NYC, CNY, 7.9), (NY, 8.1, NYC, CNY, 11.9)], place="MEXICO CITY · SEPT 19, 2017"),
 dict(kind="narr", text="Dust filled the streets. Thousands of people ran outside, searching for their families.",
      vis=[(NY, 33.2, NYC, CNY, 37.9), ("PHOTO", "quake1", None, "Mexico City, Sept 2017 · Photo: ProtoplasmaKid · CC BY-SA 4.0")]),
 dict(kind="narr", text="Just hours earlier, the city had held an earthquake drill.",
      vis=[(NY, 12.2, NYC, CNY, 16.9)]),
 dict(kind="narr", text="Strangely, it happened on the anniversary of the terrible 1985 earthquake. And hundreds of people lost their lives.",
      vis=[(NY, 44.2, NYC, CNY, 49.9), ("PHOTO", "quake2", None, "Mexico City, Sept 2017 · Photo: AntoFran · CC BY-SA 4.0")]),
 dict(kind="narr", text="Under the broken concrete, people were still alive. Every hour mattered.",
      vis=[("PHOTO", "rebsamen", None, "Colegio Enrique Rébsamen · Photo: Wotancito · CC BY-SA 4.0")]),

 dict(kind="chapter", n=3, text="Hope in the Rubble"),
 dict(kind="narr", text="The navy's dogs went in. And Frida went to work.",
      vis=[(CB, 5.2, CBC, CCB, 8.9), (CB, 9.2, CBC, CCB, 11.9)]),
 dict(kind="narr", text="She climbed over the ruins, nose down, carefully moving through gaps too small and too dangerous for people.",
      vis=[(CS, 7.2, CSC, CCS, 10.9), (S, 47.0, SEC, CSE, 46.95)][:1] + [(CB, 33.0, CBC, CCB, 33.0)][:0]),
 dict(kind="narr", text="Her handler, Petty Officer Israel Arauz, put it simply: Frida is a specialist in detecting people alive under rubble.",
      vis=[(CS, 31.2, CSC, CCS, 33.9), (S, 11.2, SEC, CSE, 14.9)]),
 dict(kind="narr", text="She was among the rescuers at the collapsed Enrique Rébsamen school, where crews worked day and night.",
      vis=[(CB, 26.0, CBC, CCB, 25.9)][:0] + [(NY, 50.2, NYC, CNY, 50.1)][:0] + [(CS, 21.2, CSC, CCS, 26.9)]),
 dict(kind="narr", text="Rescuers would go quiet and wait. Because if Frida barked, it meant someone under there was still alive.",
      vis=[(CS, 17.9, CSC, CCS, 19.9), (S, 1.2, SEC, CSE, 4.9)]),
 dict(kind="narr", text="Photos of her in her goggles spread across the world. The navy's posts were shared thousands of times. In a country in grief, Frida became a symbol of hope.",
      vis=[(S, 44.2, SEC, CSE, 46.9), (S, 17.2, SEC, CSE, 18.9), ("PHOTO", "frida", None, "Photo: Gobierno de la Ciudad de México · CC BY 4.0")]),

 dict(kind="chapter", n=4, text="The Truth About Frida"),
 dict(kind="narr", text="You may have seen posts saying Frida saved fifty-two lives. That number is exaggerated.",
      vis=[("STAT", "52", "LIVES? NOT QUITE", "")]),
 dict(kind="narr", text="According to the Mexican Navy, over her whole career, Frida took part in fifty-five rescue operations.",
      vis=[("STAT", "55", "RESCUE OPERATIONS", "")]),
 dict(kind="narr", text="She found twelve people alive. And she found forty-three people who didn't survive, so their families could finally bring them home.",
      vis=[("STAT", "12", "PEOPLE FOUND ALIVE", ""), ("STAT", "43", "BROUGHT HOME TO THEIR FAMILIES", "")]),
 dict(kind="narr", text="Twelve lives. Twelve people who got to go home, because of one dog's nose.",
      vis=[(S, 69.2, SEC, CSE, 70.9), (CB, 16.2, CBC, CCB, 19.9)]),

 dict(kind="chapter", n=5, text="Her Bark Gave Hope"),
 dict(kind="narr", text="In 2018, a bronze statue of Frida was unveiled in the city of Puebla.",
      vis=[(ST, 35.2, STC, CMI, 38.9), (ST, 57.0, STC, CMI, 59.9)]),
 dict(kind="narr", text="And in June 2019, at ten years old, Frida retired. The navy held a ceremony in her honor, with sailors and rescuers lined up to salute her.",
      vis=[(S, 51.2, SEC, CSE, 52.9), (S, 53.2, SEC, CSE, 55.9)], place="RETIREMENT · JUNE 2019"),
 dict(kind="sound", src=RT, t0=128.0, t1=137.5, speaker="Natural sound · Frida's retirement ceremony",
      subs=[(0.0, 9.5, "[ The navy honors Frida at her retirement ceremony ]")],
      crop=RTC, credit=CMI),
 dict(kind="narr", text="Her retirement gift? A chew toy.",
      vis=[(S, 64.2, SEC, CSE, 68.9)]),
 dict(kind="narr", text="Frida spent her final years resting, after a life spent searching. She died in November 2022, at thirteen years old.",
      vis=[(S, 61.0, SEC, CSE, 63.9)]),
 dict(kind="narr", text="Today, you can still find Frida painted on walls across Mexico City. A reminder of the dog who never stopped searching.",
      vis=[("PHOTO", "mural", None, "Mural of Frida, Mexico City · Photo: Kylelovesyou · CC0")]),
 dict(kind="narr", text="The navy said goodbye with words all of Mexico understood: her bark always gave hope.",
      vis=[(MI, 40.2, MIC, CMI, 41.9) ][:0] + [(CB, 20.2, CBC, CCB, 24.9)]),

 dict(kind="narr", text="If Frida's story touched your heart, subscribe for more true stories of incredible dogs.",
      vis=[("CTA", 0, None, "")], cta=True),
 dict(kind="narr", text="And tell us in the comments: which hero dog should we cover next?",
      vis=[("CTA", 1, None, "")], cta=True),
]
