# Togo - 1925 serum run. Sources: Wikipedia (Togo; 1925 serum run, citing The Cruelest Miles), Britannica (Balto), NPS, AKC, ADN, americacomesalive, Time.
AF = "AFA"; WK = "WKYC"; SM = "SMI"
TITLE = "TOGO"
CAF = "Alaska Film Archives, University of Alaska Fairbanks"
CWK = "WKYC Channel 3"
CSM = "Smithsonian Channel"
WKC = dict(ymax=300)
SMC = dict(ymax=420)

SEG = [
 dict(kind="narr", text="In the winter of 1925, children in a remote Alaskan town began to die.",
      vis=[(WK, 26.2, WKC, CWK, 30.9)]),
 dict(kind="narr", text="The only medicine was nearly seven hundred miles away. And no plane could fly.",
      vis=[(SM, 46.2, SMC, CSM, 52.9)]),
 dict(kind="narr", text="The dog who ran the longest, most dangerous part of the journey was twelve years old. And almost nobody remembers his name.",
      vis=[(AF, 92.2, None, CAF, 99.9)]),
 dict(kind="narr", text="This is the true story of Togo.",
      vis=[("PHOTO", "seppala_dogs", None, "Leonhard Seppala with his sled dogs · public domain (CC0)")], title=True),

 dict(kind="chapter", n=1, text="The Troublemaker"),
 dict(kind="narr", text="Togo was born in 1913, in the kennel of a famous Norwegian-born musher named Leonhard Seppala.",
      vis=[(AF, 26.2, None, CAF, 37.9)]),
 dict(kind="narr", text="As a puppy, he was small, sickly, and full of mischief. Seppala didn't think he'd ever make a sled dog, so he gave him away as a pet.",
      vis=[("PHOTO", "seppala_kneel", None, "Seppala with his dogs · Seattle Post-Intelligencer (public domain)")]),
 dict(kind="narr", text="Togo had other plans. The story goes that he leapt through a window, and ran straight back to Seppala's kennel.",
      vis=[(AF, 38.2, None, CAF, 48.9)]),
 dict(kind="narr", text="On his very first day in harness, the young dog ran seventy-five miles. Unheard of, for a puppy.",
      vis=[(AF, 80.2, None, CAF, 89.9)]),
 dict(kind="narr", text="He became Seppala's lead dog. Together, they won race after race, including Alaska's toughest, the All Alaska Sweepstakes.",
      vis=[("PHOTO", "seppala_win", None, "Seppala, winner of the All Alaska Sweepstakes · Lomen Bros. (public domain)"), (AF, 102.2, None, CAF, 109.9)]),

 dict(kind="chapter", n=2, text="Nome, 1925"),
 dict(kind="narr", text="January 1925. Nome, Alaska. A gold rush town on the edge of the Bering Sea, cut off from the world by ice and snow.",
      vis=[("PHOTO", "nome1", None, "Nome, Alaska, c. 1910 · public domain"), ("PHOTO", "nome2", None, "Nome, Alaska · public domain")], place="NOME, ALASKA · JANUARY 1925"),
 dict(kind="narr", text="Then, children started getting sick. It was diphtheria, a deadly disease, and the town's supply of antitoxin serum was not enough.",
      vis=[(WK, 16.2, WKC, CWK, 19.9), (WK, 32.2, WKC, CWK, 34.7)]),
 dict(kind="narr", text="The nearest serum was in Anchorage. It could go by train to the town of Nenana. But from there, it was six hundred and seventy-four miles to Nome.",
      vis=[("MAP_ROUTE", "relay", None, "")]),
 dict(kind="narr", text="The few planes in Alaska had been taken apart for the winter, and it was far too cold to fly. There was only one way left. Dogs.",
      vis=[(WK, 42.2, WKC, CWK, 48.9)]),
 dict(kind="narr", text="Twenty mushers and around a hundred and fifty sled dogs would carry the serum in a relay, passing it from team to team, day and night.",
      vis=[("STAT", "20", "MUSHERS · ~150 DOGS · 674 MILES", ""), (SM, 56.2, SMC, CSM, 62.9)]),

 dict(kind="chapter", n=3, text="The Longest Run"),
 dict(kind="narr", text="Seppala was chosen for the hardest part. And he chose his lead dog: Togo. Twelve years old. Old for a sled dog.",
      vis=[(AF, 50.2, None, CAF, 61.9)]),
 dict(kind="narr", text="They raced out of Nome, heading east to meet the serum coming the other way. A hundred and seventy miles, in about three days.",
      vis=[("MAP_ROUTE", "togo_out", None, "")]),
 dict(kind="narr", text="On January thirty-first, near Shaktoolik, they met musher Henry Ivanoff, took the serum, and turned straight around.",
      vis=[(AF, 144.2, None, CAF, 152.9)]),
 dict(kind="narr", text="To save precious time, Seppala took the shortcut: straight across the frozen sea ice of Norton Sound. Ice that could crack and drift out to sea at any moment.",
      vis=[(AF, 116.2, None, CAF, 127.9), ("MAP_ROUTE", "togo_back", None, "")]),
 dict(kind="narr", text="The temperature was around thirty below zero. With the wind, it felt like minus eighty-five. In the dark and the storm, Seppala trusted Togo to find the trail.",
      vis=[("STAT", "-85", "°F WIND CHILL", ""), (AF, 128.2, None, CAF, 139.9)]),
 dict(kind="narr", text="And Togo did. He led the team across the ice and on to Golovin, where they handed the serum to the next musher.",
      vis=[(AF, 152.9, None, CAF, 166.0)]),
 dict(kind="narr", text="In total, Togo's team covered about two hundred and sixty-one miles. No other team in the relay came close.",
      vis=[("STAT", "261", "MILES · TOGO'S TEAM", ""), ("STAT", "55", "MILES · BALTO'S TEAM", "")]),

 dict(kind="chapter", n=4, text="Balto's Glory"),
 dict(kind="narr", text="The last leg, fifty-five miles, was run by musher Gunnar Kaasen, with a lead dog named Balto.",
      vis=[("PHOTO", "kaasen_balto", None, "Gunnar Kaasen with Balto · Brown Brothers (public domain)")]),
 dict(kind="narr", text="Before dawn on February second, 1925, they pulled into Nome with the serum. The town was saved.",
      vis=[("PHOTO", "balto1925", None, "Balto, 1925 · public domain"), (WK, 56.2, WKC, CWK, 61.9)], place="NOME · FEBRUARY 2, 1925"),
 dict(kind="narr", text="Newspapers across the world told the story. And because Balto ran the final stretch, Balto got the fame.",
      vis=[(WK, 68.2, WKC, CWK, 69.9), ("PHOTO", "kaasen_seattle", None, "Kaasen and Balto, Seattle, 1925 · MOHAI (public domain)")]),
 dict(kind="narr", text="Before the year was out, a bronze statue of Balto stood in New York's Central Park. It's still there today.",
      vis=[("PHOTO", "balto_statue", None, "Balto statue, Central Park · Photo: Jim.henderson (public domain)")]),
 dict(kind="narr", text="Balto lived out his life in Cleveland. Today, he's on display at the Cleveland Museum of Natural History.",
      vis=[(WK, 78.2, WKC, CWK, 86.9)]),

 dict(kind="chapter", n=5, text="The Real Hero"),
 dict(kind="narr", text="Seppala never forgot who had carried them through the worst of it. To him, Togo was the best dog he ever had.",
      vis=[(AF, 62.2, None, CAF, 76.9)]),
 dict(kind="narr", text="Togo died in 1929, at sixteen years old. Today, he's preserved at the Iditarod headquarters in Wasilla, Alaska.",
      vis=[(SM, 32.2, SMC, CSM, 38.9)]),
 dict(kind="narr", text="Every year, the Iditarod sled dog race honors the old trails of Alaska, and the dogs who ran them.",
      vis=[(SM, 8.2, SMC, CSM, 15.9), (SM, 24.2, SMC, CSM, 29.9)]),
 dict(kind="narr", text="In 2011, Time magazine named Togo the most heroic animal of all time. And in 2019, his story finally reached the movies.",
      vis=[("STAT", "#1", "MOST HEROIC ANIMAL OF ALL TIME · TIME", "")]),
 dict(kind="narr", text="Balto finished the race. But it was Togo who carried it. Through the ice, the dark, and the cold... an old dog who never quit.",
      vis=[(AF, 156.0, None, CAF, 156.05)][:0] + [(SM, 94.2, SMC, CSM, 103.9)]),

 dict(kind="narr", text="If Togo's story touched your heart, subscribe for more true stories of incredible dogs.",
      vis=[("CTA", 0, None, "")], cta=True),
 dict(kind="narr", text="And tell us in the comments: Togo or Balto, who's your hero?",
      vis=[("CTA", 1, None, "")], cta=True),
]
