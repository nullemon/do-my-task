import sys, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
SP="/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad"
T=SP+"/series/03-you-are-not-sitting-still/tex"; OUT=SP+"/thumb03"
W,H=2400,1350
rng=np.random.default_rng(7)
ld=lambda n: np.asarray(Image.open(f"{T}/{n}"),np.float32)/255
base=ld("room_base.png"); m=ld("room_win.png")[...,None]; rim=ld("room_rim.png"); hz=ld("horizon.png")

# --- window sky: warp-speed star streaks converging on a vanishing point + galactic glow
vx,vy=1700,560
yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
sky=np.zeros((H,W,3),np.float32)
dx,dy=xx-vx,yy-vy; r=np.hypot(dx,dy)+1
# deep blue gradient
sky+=np.array([0.02,0.04,0.10])+np.array([0.05,0.10,0.25])*np.exp(-r/900)[...,None]
# galactic core glow (warm) + band
sky+=np.array([1.0,0.75,0.45])*(0.75*np.exp(-(r/85)**2)+0.22*np.exp(-r/260))[...,None]
band=np.exp(-((dy*np.cos(-0.35)-dx*np.sin(-0.35))/90)**2)*np.exp(-r/900)
sky+=np.array([0.55,0.6,0.9])*0.5*band[...,None]
img=Image.fromarray((np.clip(sky,0,1)*255).astype(np.uint8))
d=ImageDraw.Draw(img,"RGBA")
for _ in range(1400):
    a=rng.uniform(0,2*np.pi); r0=rng.uniform(30,900)**1.0
    L=r0*rng.uniform(0.25,0.7)
    x0,y0=vx+np.cos(a)*r0,vy+np.sin(a)*r0
    x1,y1=vx+np.cos(a)*(r0+L),vy+np.sin(a)*(r0+L)
    c=[(200,220,255),(255,240,220),(170,200,255)][int(rng.integers(3))]
    w=1 if r0<300 else int(rng.integers(1,4))
    al=int(min(255,60+r0/4))
    d.line([(x0,y0),(x1,y1)],fill=c+(al,),width=w)
sky=np.asarray(img.filter(ImageFilter.GaussianBlur(1.2)),np.float32)/255
sky=np.clip(sky+np.asarray(img,np.float32)/255*0.6,0,1)
sky=sky*(1-hz[...,3:])+hz[...,:3]*hz[...,3:]

# --- room: lift exposure, cool tint, strong window light spill + rim
room=base*1.25+np.array([0.0,0.01,0.03])
spill=np.exp(-(((xx-1700)/1100)**2+((yy-650)/700)**2))[...,None]*np.array([0.06,0.10,0.22])
o=room*(1-m)+sky*m+(rim*5.0+spill)*(1-m)
# vignette
v=1-0.55*np.clip(((xx-W/2)/(W*0.7))**2+((yy-H/2)/(H*0.75))**2,0,1)
o=np.clip(o*v[...,None],0,1)
im=Image.fromarray((o*255).astype(np.uint8))
# glow bloom
bl=im.filter(ImageFilter.GaussianBlur(40)); im=Image.blend(im,Image.fromarray(np.clip(np.asarray(im,np.int16)+np.asarray(bl,np.int16)//2,0,255).astype(np.uint8)),1.0)

# crop to 16:9 framing that puts figure left-centre, keep 2400x1350 then text
d=ImageDraw.Draw(im)
def font(sz,w="Black"):
    for p in [f"/usr/share/fonts/opentype/inter/InterDisplay-{w}.otf",f"/usr/share/fonts/opentype/inter/Inter-{w}.otf","/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"]:
        try: return ImageFont.truetype(p,sz)
        except OSError: pass
def text(xy,s,f,fill,stroke=14):
    d.text(xy,s,font=f,fill=fill,stroke_width=stroke,stroke_fill=(0,0,0))
variant=sys.argv[1] if len(sys.argv)>1 else "a"
if variant=="a":
    text((90,70),"1,300,000",font(250),(255,214,40))
    text((100,320),"KM/H",font(170),(255,214,40))
    text((100,1110),"...and you feel nothing.",font(110,"Bold"),(255,255,255),10)
else:
    text((90,70),"YOU ARE NOT",font(175),(255,255,255))
    text((90,255),"SITTING STILL",font(175),(255,214,40))
    f=font(110,"Black"); s="1,300,000 KM/H"
    bb=d.textbbox((0,0),s,font=f); pw,ph=bb[2]-bb[0],bb[3]-bb[1]
    d.rounded_rectangle((90,1100,90+pw+80,1100+ph+70),30,fill=(225,30,30))
    d.text((130,1100+35-bb[1]),s,font=f,fill=(255,255,255))
im.resize((1280,720),Image.LANCZOS).save(f"{OUT}/thumb_{variant}.png")
im.resize((1280,720),Image.LANCZOS).convert("RGB").save(f"{OUT}/thumb_{variant}.jpg",quality=92)
print("ok",variant)
