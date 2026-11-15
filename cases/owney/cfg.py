# Owney: case settings
DOG = "Owney"
HOOK_TITLE = "The Dog Who Traveled the World by Mail"
HEADER_TITLE = "HE TRAVELED BY MAIL"
HEADER_SUB = "OWNEY · USA 1888–1897"
TITLE_BIG = "Owney"
TITLE_SMALL = "THE POSTAL DOG"
HOOK = [(0.0, 3.3, [("NO TICKET.", "w"), ("JUST A MUTT.", "w")]),
        (3.3, 7.0, [("HE SAILED", "w"), ("AROUND THE", "w"), ("WORLD", "y")])]
PRON = {"Owney": "/ˈoʊni/", "Owney's": "/ˈoʊniz/", "Albany": "/ˈɔːlbəni/", "Tacoma": "/təkˈoʊmə/", "Toledo": "/təlˈiːdoʊ/",
        "Wanamaker": "/wˈɑːnəmˌeɪkɚ/", "Algiers": "/ældʒˈɪɹz/", "Azores": "/ˈeɪzɔːɹz/", "Smithsonian": "/smɪθsˈoʊniən/"}
SPEED = 0.93
DEFAULT_BG = "owney_portrait"
MAPFILE = "map_world.json"
HILITE = ()
TIMELINE = [("1888", "ALBANY"), ("1895", "WORLD TRIP"), ("1897", "TOLEDO"), ("1911", "SMITHSONIAN"), ("2011", "STAMP")]
CTA_Q = "Where would YOUR dog travel if they could go anywhere?"
THUMB = dict(photo="owney_portrait", crop=(140, 420, 1180, 1500), face=(0.45, 0.35), lines=["AROUND", "THE WORLD", "BY MAIL"], yellow={2},
             sub="140,000+ MILES BY MAIL TRAIN", c1=(30, 60, 120), c2=(10, 20, 50), sepia=True)
