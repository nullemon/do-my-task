# Patron: case settings
DOG = "Patron"
HOOK_TITLE = "The Tiny Dog Ukraine Gave a Medal"
HEADER_TITLE = "4 KILOS OF COURAGE"
HEADER_SUB = "PATRON · UKRAINE 2022"
TITLE_BIG = "Patron"
TITLE_SMALL = "THE TINY DOG WITH A MEDAL"
HOOK = [(0.0, 3.2, [("HE WEIGHS", "w"), ("4 KILOS", "y")]),
        (3.2, 6.8, [("A PRESIDENT", "w"), ("GAVE HIM", "w"), ("A MEDAL", "y")])]
PRON = {"Patron": "/pɑtɹˈɔn/", "Mykhailo": "/mihˈaɪloʊ/", "Iliev": "/ˈɪljɛf/", "Ilievs": "/ˈɪljɛfs/",
        "Chernihiv": "/tʃɚnˈiːhɪv/", "Kyiv": "/kˈiːɪv/", "Volodymyr": "/vˌɑːloʊdˈɪmɪɹ/", "Zelensky": "/zəlˈɛnski/",
        "Trudeau": "/tɹuːdˈoʊ/", "Okhmatdyt": "/ˌɑːkmɑːtdˈɪt/", "AmbassaDOG": "/æmbˈæsədˌɔɡ/", "UNICEF": "/jˈuːnɪsˌɛf/",
        "101": "/wˈʌn ˈoʊ wˈʌn/"}
SPEED = 0.93
DEFAULT_BG = "patron_portrait_2022"
MAPFILE = "map_ukraine.json"
HILITE = ("Ukraine",)
TIMELINE = [("2019", "BORN"), ("2022", "THE MEDAL"), ("2022", "THE STAMP"), ("2023", "300+"), ("2026", "PUPPIES")]
CTA_Q = "What is YOUR dog's secret talent?"
THUMB = dict(photo="patron_portrait_2022", crop=None, face=(0.5, 0.35), lines=["4 KILOS", "OF COURAGE"], yellow={0},
             sub="300+ EXPLOSIVES FOUND", c1=(20, 70, 150), c2=(10, 30, 70), sepia=False)
