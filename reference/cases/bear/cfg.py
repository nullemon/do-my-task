B = "/home/claude/footage/05_bear_koala/05_bear_koala/"
import glob
def V(i): return glob.glob(B + f"youtube/*/{i}.mp4")[0]
SRC = {"BBC": V("2L3isEfGpC8"), "PBS": V("zW62kHpVLQ0"), "IFAW": V("ztAbAtlU_p0"), "USC": V("zQMrGkTyjtY"),
       "TYS": V("V-ksURlRZTY"), "TODAY": V("ZXMXmswrtOg")}
PHOTOS = {
 "himawari": B + "photos_commons/" + [p for p in __import__("os").listdir(B + "photos_commons") if "himawari" in p][0],
 "koolie": B + "photos_commons/koolie-blue_merle_jpg.jpg",
 "koala": B + "photos_commons/koala_climbing_tree_jpg.jpg",
 "night": B + "photos_commons/" + [p for p in __import__("os").listdir(B + "photos_commons") if "nighttime" in p][0],
}
HEADER = "BEAR · THE KOALA DETECTIVE"
HOOK_V = ("NOBODY WANTED HIM…", "THEN AUSTRALIA BURNED", "HE FOUND 100+ KOALAS")
HOOK_H = ("NOBODY WANTED HIM… THEN AUSTRALIA BURNED. ", "HE FOUND 100+ KOALAS")
TITLE_BIG = "Bear"
TITLE_SMALL = "THE KOALA DETECTIVE"
STILL = ("PBS", 22.0)
MAPFILE = "bmap.json"
PIN = ("NorthernRivers", "NORTHERN RIVERS, NSW", "THE BLACK SUMMER · 2019–2020")
PIN_EXTRA = [("Sydney", "Sydney"), ("Melbourne", "Melbourne")]
HILITE = ("Australia",)
CTA_Q = "Should Bear get a medal? Tell us below!"
