B = "/home/claude/footage/06_togo_serum_run/06_togo_serum_run/"
import glob
def V(i): return glob.glob(B + f"youtube/*/{i}.mp4")[0]
SRC = {"AFA": V("nQuEM73i6_M"), "WKYC": V("iJLXoArcvTs"), "SMI": V("2rE6UQNZXP0"), "WKY2": V("7-ZYI2PYcbM")}
P = B + "photos_commons/"
PHOTOS = {
 "seppala_dogs": P + "leonhard_seppala_with_dogs_jpg.jpg",
 "seppala_kneel": P + [p for p in __import__("os").listdir(P) if p.startswith("leonhard_seppala_kneeling")][0],
 "seppala_win": P + [p for p in __import__("os").listdir(P) if p.startswith("leonhard_seppala_winner")][0],
 "kaasen_balto": P + "gunnar_kaasen_with_balto_jpg.jpg",
 "balto1925": P + "balto_1925_jpg.jpg",
 "balto_fund": P + "balto_saved_nome_fund_appeal_jpg.jpg",
 "nome1": P + "street_scene_in_nome_alaska_showing_the_behring_saloon_circa_1910_al_c.jpg",
 "nome2": P + [p for p in __import__("os").listdir(P) if "celebration_on_front_street_nome" in p][0],
 "balto_statue": P + "balto_bright_jeh_jpg.jpg",
 "balto_museum": P + "balto_cmnh_visitor_hall_display_jpg.jpg",
 "kaasen_seattle": P + [p for p in __import__("os").listdir(P) if p.startswith("gunnar_kaasen_and_dog_balto_seattle")][0],
}
HEADER = "TOGO · THE FORGOTTEN HERO"
HOOK_V = ("A TOWN WAS DYING…", "THE CURE WAS 674 MILES AWAY", "A 12-YEAR-OLD DOG RAN")
HOOK_H = ("A TOWN WAS DYING. THE CURE WAS 674 MILES AWAY… ", "A 12-YEAR-OLD DOG RAN")
TITLE_BIG = "Togo"
TITLE_SMALL = "THE FORGOTTEN HERO"
STILL = ("AFA", 60.0)
MAPFILE = "akmap.json"
HILITE = ("United States of America",)
RELAY = ["Nenana", "Tanana", "Nulato", "Kaltag", "Unalakleet", "Shaktoolik", "Golovin", "Nome"]
TOWNS = [("Nenana", "NENANA", "r"), ("Nulato", "NULATO", "t"), ("Shaktoolik", "SHAKTOOLIK", "r"), ("Golovin", "GOLOVIN", "t"), ("Nome", "NOME", "b"), ("Unalakleet", "UNALAKLEET", "b")]
ROUTES = {
 "relay": dict(pts=["Nenana", "Tanana", "Nulato", "Kaltag", "Unalakleet", "Shaktoolik", "Golovin", "Nome"], color=(200, 200, 210), label="THE SERUM RUN · 674 MILES", miles=674),
 "togo_out": dict(pts=["Nome", "Golovin", "NortonSound", "Shaktoolik"], color=(255, 205, 80), label="TOGO'S RUN · OUT FROM NOME", miles=170),
 "togo_back": dict(pts=["Shaktoolik", "NortonSound", "Golovin"], color=(255, 120, 60), label="BACK ACROSS THE ICE · WITH THE SERUM", miles=91),
}
CTA_Q = "Togo or Balto: who's YOUR hero?"
