# Judy: case settings
DOG = "Judy"
HOOK_TITLE = "The Only Dog Ever Made a Prisoner of War"
HEADER_TITLE = "PRISONER OF WAR 81A"
HEADER_SUB = "JUDY · SUMATRA 1942–1945"
TITLE_BIG = "Judy"
TITLE_SMALL = "PRISONER OF WAR 81A"
HOOK = [(0.0, 3.3, [("ONLY ONE DOG", "w"), ("WAS EVER A", "w"), ("PRISONER OF WAR", "r")]),
        (3.3, 7.0, [("HER NUMBER:", "w"), ("81A", "y")])]
PRON = {"Judy": "/dʒˈuːdi/", "Yangtze": "/jˈæŋtsi/", "Gnat": "/nˈæt/", "Sumatra": "/suːmˈɑːtɹə/", "Medan": "/mˈeɪdɑːn/",
        "Singkep": "/sˈɪŋkɛp/", "Padang": "/pˈɑːdɑːŋ/", "Harugiku Maru": "/hˌɑːɹuːɡˈiːkuː mˈɑːɹuː/", "Pekanbaru": "/pˌeɪkənbˈɑːɹuː/",
        "Dickin": "/dˈɪkɪn/", "PDSA": "/pˌiː dˌiː ˌɛs ˈeɪ/", "Tanganyika": "/tˌæŋɡənjˈiːkə/", "81A": "/ˈeɪti wˈʌn ˈeɪ/", "Shanghai": "/ʃæŋhˈaɪ/"}
SPEED = 0.93
DEFAULT_BG = "judy_on_deck"
MAPFILE = "map_judy.json"
HILITE = ("Indonesia", "Malaysia", "China")
TIMELINE = [("1936", "BORN"), ("1942", "SHIPWRECK"), ("1942", "81A"), ("1945", "FREE"), ("1946", "MEDAL")]
CTA_Q = "Would YOUR dog stay by your side through anything?"
THUMB = dict(photo="judy_on_deck", crop=None, face=(0.6, 0.55), lines=["PRISONER", "OF WAR", "81A"], yellow={2},
             sub="THE ONLY DOG EVER REGISTERED", c1=(100, 25, 25), c2=(30, 8, 8), sepia=True)
