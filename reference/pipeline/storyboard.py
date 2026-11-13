import json, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0,"."); from cfg import SRC, PHOTOS
tl = json.load(open("timeline.json"))
F = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13)
def grab(src, t):
    out = subprocess.run(["ffmpeg","-loglevel","error","-ss",str(max(0,t)),"-i",src,"-frames:v","1","-vf","scale=160:90:force_original_aspect_ratio=decrease,pad=160:90:(ow-iw)/2:(oh-ih)/2","-f","rawvideo","-pix_fmt","rgb24","-"],capture_output=True).stdout
    return Image.frombytes("RGB",(160,90),out) if len(out)==160*90*3 else Image.new("RGB",(160,90),"red")
used = {}
tiles=[]
for i,s in enumerate(tl["spans"]):
    v=s["vis"]; d=s["t1"]-s["t0"]
    tile=Image.new("RGB",(484,112),(30,30,30)); dr=ImageDraw.Draw(tile)
    if v[0] in SRC:
        end = min(v[1]+d, v[4]) if len(v)>4 else v[1]+d
        for k,f in enumerate([0.05,0.5,0.95]): tile.paste(grab(SRC[v[0]], v[1]+(end-v[1])*f),(2+k*161,20))
        rng=(v[1],end); used.setdefault(v[0],[]).append((rng,i))
        if len(v)>4 and v[1]+d > v[4]+0.05: dr.text((300,3),f"hold {v[1]+d-v[4]:.1f}s",fill="orange",font=F)
    elif v[0]=="PHOTO":
        im=Image.open(PHOTOS[v[1]]).convert("RGB"); im.thumbnail((160,90)); tile.paste(im,(2,20))
    dr.text((3,3),f"#{i} {s['t0']:.1f}s {v[0]} @{v[1]} ({d:.1f}s)",fill="yellow",font=F)
    tiles.append(tile)
cols=4; rows=(len(tiles)+cols-1)//cols
S=Image.new("RGB",(cols*484,rows*112))
for i,t in enumerate(tiles): S.paste(t,((i%cols)*484,(i//cols)*112))
S.save("sheets/storyboard.jpg",quality=88)
# overlap check
for src,lst in used.items():
    lst.sort()
    for (a,i),(b,j) in zip(lst,lst[1:]):
        if b[0] < a[1]-0.05: print(f"OVERLAP {src}: span#{i} {a[0]:.1f}-{a[1]:.1f}  vs span#{j} {b[0]:.1f}-{b[1]:.1f}")
