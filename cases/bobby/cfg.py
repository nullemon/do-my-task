# Greyfriars Bobby: case settings
DOG = "Greyfriars Bobby"
HOOK_TITLE = "14 Years at a Grave or Did He"
HEADER_TITLE = "14 YEARS AT A GRAVE?"
HEADER_SUB = "BOBBY · EDINBURGH 1858–1872"
TITLE_BIG = "Greyfriars Bobby"
TITLE_SMALL = "THE TRUTH BEHIND THE LEGEND"
HOOK = [(0.0, 3.3, [("HE GUARDED", "w"), ("A GRAVE", "w"), ("14 YEARS", "y")]),
        (3.3, 7.0, [("...OR", "w"), ("DID HE?", "r")])]
PRON = {"Edinburgh": "/ˈɛdɪnbɹə/", "Greyfriars": "/ɡɹˈeɪfɹaɪɚz/", "Kirkyard": "/kˈɜːkjɑːɹd/", "kirkyard": "/kˈɜːkjɑːɹd/",
        "Provost": "/pɹˈɑːvəst/", "Traill": "/tɹˈeɪl/", "Traill's": "/tɹˈeɪlz/", "Burdett-Coutts": "/bɚdˈɛt kˈuːts/",
        "Bondeson": "/bˈɑːndəsən/", "Brodie": "/bɹˈoʊdi/", "Skye": "/skˈaɪ/", "Auld": "/ˈɔːld/"}
SPEED = 0.93
DEFAULT_BG = "bobby_photo_ngs"
MAPFILE = "map_scotland.json"
HILITE = ("United Kingdom",)
TIMELINE = [("1858", "THE LEGEND"), ("1867", "LICENCE"), ("1872", "DIES"), ("1873", "STATUE"), ("2011", "THE DEBATE")]
CTA_Q = "Was Bobby loyal, or a lovable stray with a great story? What do YOU think?"
THUMB = dict(photo="bobby_photo_ngs", crop=None, face=(0.5, 0.45), lines=["14 YEARS", "AT A GRAVE?"], yellow={0},
             sub="THE TRUTH ABOUT GREYFRIARS BOBBY", c1=(40, 70, 60), c2=(10, 25, 20), sepia=True)
