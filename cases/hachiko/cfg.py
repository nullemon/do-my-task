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
PRON = {  # /ipa/ = exact phonemes for the voice (captions keep the real spelling)
    "Hachikō": "/hˌɑːtʃiːkˈoʊ/", "Hachi": "/hˈɑːtʃi/", "kō": "/kˈoʊ/", "Ōdate": "/oʊdˈɑːteɪ/", "Akita": "/əkˈiːtə/",
    "Hidesaburō": "/hˌiːdɛsəbˈʊɹoʊ/", "Ueno": "/ˈuːɛnoʊ/", "Shibuya": "/ʃɪbˈuːjə/", "Kikusaburō": "/kˌiːkusəbˈʊɹoʊ/",
    "Kobayashi": "/kˌoʊbəjˈɑːʃi/", "Hirokichi": "/hˌiːɹoʊkˈiːtʃi/", "Saitō": "/sˈaɪtoʊ/", "Asahi": "/əsˈɑːhi/",
    "Shimbun": "/ʃˈɪmbʊn/", "Aoyama": "/ˌɑːoʊjˈɑːmə/", "yakitori": "/jˌækɪtˈɔːɹi/"}
SPEED = 0.93
SRC = {}            # footage key -> file (filled once the fetcher zips arrive)
SRC_CREDIT = {}
DEFAULT_BG = "portrait"
MAPFILE = "map_japan.json"
TIMELINE = [("1923", "BORN"), ("1925", "UENO DIES"), ("1932", "FAMOUS"), ("1934", "STATUE"), ("1935", "")]
CTA_Q = "What's the most loyal thing YOUR dog has ever done?"
THUMB = dict(photo="photo34", crop=None, face=(0.50, 0.24), lines=["HE WAITED", "9 YEARS"], yellow={1},
             sub="FOR A MAN WHO NEVER CAME HOME", c1=(120, 70, 20), c2=(40, 20, 8), sepia=True)
