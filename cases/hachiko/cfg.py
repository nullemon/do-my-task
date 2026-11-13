# Hachikō: case settings
DOG = "Hachiko"
HOOK_TITLE = "He Waited 9 Years"                       # used in file names
HEADER_TITLE = "HE WAITED 9 YEARS"
HEADER_SUB = "HACHIKŌ · TOKYO 1925"
TITLE_BIG = "Hachikō"
TITLE_SMALL = "THE DOG WHO WAITED"
# hook overlay beats: (t0, t1, [(line, colour w|y|r)])
HOOK = [(0.0, 3.4, [("HIS OWNER", "w"), ("NEVER", "r"), ("CAME HOME", "w")]),
        (3.4, 7.0, [("HE WAITED", "w"), ("9 YEARS", "y")])]
PRON = {"Hachikō": "Hachikoh", "Hachi": "Hah-chee", "Ōdate": "Oh-dah-teh", "Hidesaburō": "Hee-deh-sah-boo-roh",
        "Ueno": "Oo-eh-noh", "Kikusaburō": "Kee-koo-sah-boo-roh", "Kobayashi": "Koh-bah-yah-shee", "Hirokichi": "Hee-roh-kee-chee",
        "Saitō": "Sigh-toh", "Shibuya": "Shee-boo-yah", "Asahi Shimbun": "Ah-sah-hee Shim-boon", "Aoyama": "Ah-oh-yah-mah",
        "Akita": "Ah-kee-tah", "yakitori": "yah-kee-toh-ree", "Teru Andō": "Teh-roo Ahn-doh", "kō": "koh"}
SPEED = 0.93
SRC = {}            # footage key -> file (filled once the fetcher zips arrive)
SRC_CREDIT = {}
DEFAULT_BG = "portrait"
MAPFILE = "map_japan.json"
TIMELINE = [("1923", "BORN"), ("1925", "UENO DIES"), ("1932", "FAMOUS"), ("1934", "STATUE"), ("1935", "")]
CTA_Q = "What's the most loyal thing YOUR dog has ever done?"
THUMB = dict(photo="photo34", crop=None, face=(0.50, 0.24), lines=["HE WAITED", "9 YEARS"], yellow={1},
             sub="FOR A MAN WHO NEVER CAME HOME", c1=(120, 70, 20), c2=(40, 20, 8), sepia=True)
