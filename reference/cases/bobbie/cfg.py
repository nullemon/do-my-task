# Bobbie used an early version of the pipeline where these lived in timeline.py/render.py;
# this cfg.py is the same settings in the later shared format.
B = "/home/claude/footage/01_bobbie_wonder_dog/01_bobbie_wonder_dog/"
SRC = {
 "WISH": B + "youtube/m04_silverton_pet_parade_bobbie/q7FxHFXLhIY.mp4",       # WISH-TV copy of KOIN 6 report (no station bug)
 "COTW": B + "youtube/m02_call_of_the_west_1924_bobbie_oregon_hist/eeYe990biYI.mp4",  # Call of the West (1924), Oregon Historical Society
 "KGWS": B + "youtube/m06_silverton_oregon_downtown/5qYvfB-ObQk.mp4",
}
PHOTOS = {
 "sanborn": B + "photos_commons/sanborn_fire_insurance_map_from_wolcott_white_county_indiana_1909_plat.jpg",
 "statue": B + "photos_openverse/bobbie_the_wonder_dog_silverto_bobbie_the_wonder_dog_statue_in_the_fc7e838c.jpg",
 "street": B + "photos_commons/silverton_oregon_october_2020_-_50_jpg.jpg",
}
HEADER = "BOBBIE · THE WONDER DOG"
HOOK_V = ("LOST 2,551 MILES", "FROM HOME…", "HE WALKED BACK")
HOOK_H = ("LOST 2,551 MILES FROM HOME… ", "HE WALKED BACK")
TITLE_BIG = "Bobbie"
TITLE_SMALL = "THE WONDER DOG"
STILL = ("COTW", 455.0)
MAPFILE = "usmap.json"
HILITE = ("Oregon", "Indiana")
CTA_Q = "What's the most loyal thing YOUR dog has ever done?"
# Map routes (MAP_OUT / MAP_HOME) used points Silverton, Boise, SaltLake, Cheyenne, Omaha, DesMoines, Wolcott, ContinentalDivide
