# Chips: case settings
DOG = "Chips"
HOOK_TITLE = "The Family Dog Who Charged a Machine Gun"
HEADER_TITLE = "HE CHARGED A MACHINE GUN"
HEADER_SUB = "CHIPS · SICILY 1943"
TITLE_BIG = "Chips"
TITLE_SMALL = "THE FAMILY DOG WHO WENT TO WAR"
HOOK = [(0.0, 3.3, [("A FAMILY DOG", "w"), ("CHARGED A", "w"), ("MACHINE GUN", "r")]),
        (3.3, 7.0, [("THEN THE ARMY", "w"), ("SAID NO", "y")])]
PRON = {"Rowell": "/ɹˈaʊəl/", "Licata": "/lɪkˈɑːtə/", "Pleasantville": "/plˈɛzəntvˌɪl/", "Truscott": "/tɹˈʌskət/", "Dickin": "/dˈɪkɪn/",
        "PDSA": "/pˌiː dˌiː ˌɛs ˈeɪ/", "Casablanca": "/kˌæsəblˈæŋkə/", "Wren": "/ɹˈɛn/", "Wrens": "/ɹˈɛnz/"}
SPEED = 0.93
DEFAULT_BG = "chips_colorized"
MAPFILE = "map_chips.json"
HILITE = ("Italy", "Morocco")
TIMELINE = [("1942", "ENLISTED"), ("1943", "CASABLANCA"), ("1943", "SICILY"), ("1945", "HOME"), ("2018", "MEDAL")]
CTA_Q = "Would YOUR dog be brave or would they hide under the bed?"
THUMB = dict(photo="chips_colorized", crop=None, face=(0.5, 0.35), lines=["HE CHARGED", "A MACHINE", "GUN"], yellow={2},
             sub="THE TRUE STORY OF CHIPS · WWII", c1=(60, 70, 30), c2=(20, 25, 10), sepia=False)
