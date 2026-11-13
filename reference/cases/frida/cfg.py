B = "/home/claude/footage/04_frida_navy/04_frida_navy/"
import glob
def V(i): return glob.glob(B + f"youtube/*/{i}.mp4")[0]
SRC = {"SEMAR": V("DwpU0HpY7Ig"), "CBBC": V("RktzPa_EcoM"), "CBS": V("3PBj18Z_Bos"), "NYT": V("cB5tzCrD6ww"),
       "RET": V("x2TBD0LxKZ4"), "STATUE": V("FkwWybDL5ZE"), "MIL": V("XEQkkiLzsvk")}
PHOTOS = {
 "frida": B + "photos_commons/frida_perra_de_rescate_de_la_marina_jpg.jpg",
 "mural": B + "photos_commons/mural_of_frida_the_dog_in_mexico_city_jpg.jpg",
 "quake1": B + "photos_commons/terremoto_de_puebla_de_2017_-_ciudad_de_m_xico_-_16_jpg.jpg",
 "quake2": B + "photos_commons/ciudad_de_m_xico_-_terremoto_puebla_2017_3_jpg.jpg",
 "rebsamen": B + "photos_commons/colegio_enrique_r_bsamen_01_jpg.jpg",
}
HEADER = "FRIDA · THE NAVY RESCUE DOG"
HOOK_V = ("SHE WORE GOGGLES", "AND LITTLE BOOTS…", "AND SAVED 12 LIVES")
HOOK_H = ("SHE WORE GOGGLES AND LITTLE BOOTS… ", "AND SAVED 12 LIVES")
TITLE_BIG = "Frida"
TITLE_SMALL = "THE NAVY RESCUE DOG"
STILL = ("SEMAR", 29.0)
MAPFILE = "mxmap.json"
PIN = ("MexicoCity", "MEXICO CITY", "SEPTEMBER 19, 2017 · 1:14 PM")
PIN_EXTRA = [("Puebla", "Puebla"), ("Guadalajara", "Guadalajara"), ("Monterrey", "Monterrey")]
HILITE = ("Mexico",)
CTA_Q = "Which hero dog should we cover next?"
