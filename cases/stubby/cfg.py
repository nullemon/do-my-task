# Stubby: case settings
DOG = "Stubby"
HOOK_TITLE = "The Stray Who Was Smuggled to War"
HEADER_TITLE = "SMUGGLED TO WAR"
HEADER_SUB = "STUBBY · FRANCE 1918"
TITLE_BIG = "Stubby"
TITLE_SMALL = "THE STRAY WHO WENT TO WAR"
HOOK = [(0.0, 3.3, [("PETS WERE", "w"), ("BANNED", "r")]),
        (3.3, 7.0, [("SO HE", "w"), ("SMUGGLED", "w"), ("HIM TO WAR", "y")])]
PRON = {"Stubby": "/stˈʌbi/", "Conroy": "/kˈɑːnɹɔɪ/", "Seicheprey": "/sɛʃpɹˈeɪ/", "Chemin des Dames": "/ʃəmˈæn deɪ dˈɑːm/",
        "Soissons": "/swɑːsˈoʊn/", "Château-Thierry": "/ʃætˌoʊ tʃɛɹˈiː/", "Pershing": "/pˈɝːʃɪŋ/", "Bausum": "/bˈɔːsəm/", "Hoyas": "/hˈɔɪəz/"}
SPEED = 0.93
DEFAULT_BG = "stubby_coat"
MAPFILE = "map_stubby.json"
HILITE = ("France", "United States of America")
TIMELINE = [("1917", "FOUND"), ("1918", "THE FRONT"), ("1919", "HOME"), ("1921", "MEDAL"), ("1926", "")]
CTA_Q = "What would YOUR dog do if you were in danger?"
THUMB = dict(photo="stubby_coat", crop=None, face=(0.5, 0.35), lines=["SMUGGLED", "TO WAR"], yellow={1},
             sub="THE STRAY WHO BECAME A HERO", c1=(90, 70, 30), c2=(30, 20, 5), sepia=True)
