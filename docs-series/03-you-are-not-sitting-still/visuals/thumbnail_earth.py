import sys, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
SP="/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad"
G=SP+"/dl_globe/package/example"; OUT=SP+"/thumb03"
W,H=2560,1440
rng=np.random.default_rng(11)
def tex(p,mode="RGB"): return np.asarray(Image.open(p).convert(mode),np.float32)/255
day=tex(G+"/img/earth-blue-marble.jpg")**1.0
night=tex(G+"/img/earth-night.jpg")
water=tex(G+"/img/earth-water.png","L")
cloud=np.asarray(Image.open(G+"/clouds/clouds.png").convert("RGBA"),np.float32)[...,3]/255
def samp(t,lat,lon):
    h,w=t.shape[:2]
    x=((lon/(2*np.pi)+0.5)%1.0)*(w-1); y=(0.5-lat/np.pi)*(h-1)
    x0=np.floor(x).astype(int); y0=np.clip(np.floor(y).astype(int),0,h-2); fx=x-x0; fy=y-y0
    x1=(x0+1)%w
    if t.ndim==3: fx=fx[...,None]; fy=fy[...,None]
    a=t[y0,x0]*(1-fx)+t[y0,x1]*fx; b=t[y0+1,x0]*(1-fx)+t[y0+1,x1]*fx
    return a*(1-fy)+b*fy
def norm(v): return v/np.linalg.norm(v)

# ---------- background: Milky Way sky + horizontal speed streaks
sky=Image.open(G+"/img/night-sky.png").convert("RGB")
sky=sky.crop((1200,500,1200+2400,500+1350)).resize((W,H),Image.LANCZOS)
bg=np.asarray(sky,np.float32)/255
bg=np.clip((bg.mean(2,keepdims=True)-0.05)*1.6,0,1)*np.array([0.8,0.9,1.15])
# streaks: blur bright stars along motion direction (Earth moving right -> streaks trail left)
bright=np.clip(bg-0.25,0,1)*2.5
st=Image.fromarray((np.clip(bright,0,1)*255).astype(np.uint8))
k=np.zeros((1,121),np.float32); k[0,:]=np.linspace(1,0,121)**1.5
from numpy.lib.stride_tricks import sliding_window_view
def hblur(a,L=160):
    out=np.zeros_like(a); w=np.linspace(1,0,L)**1.6; w/=w.sum()
    for i in range(0,L,2):
        out+=np.roll(a,-i,axis=1)*w[i]*2   # trail extends to the left of each star
    return out
bg=bg*0.35+hblur(bright)*1.2
yy0,xx0=np.mgrid[0:H,0:W].astype(np.float32)
bg+=np.array([0.02,0.035,0.09])+np.array([0.05,0.08,0.20])*np.exp(-(((xx0-W*0.75)/(W*0.6))**2+((yy0-H*0.55)/(H*0.7))**2))[...,None]
# extra synthetic streak stars
img=Image.new("RGB",(W,H)); d=ImageDraw.Draw(img)
for _ in range(500):
    x=rng.uniform(-200,W); y=rng.uniform(0,H); L=rng.uniform(60,420); b=rng.uniform(60,255)
    for j in range(6):
        t=j/6; d.line([(x-L*t,y),(x-L*(t+1/6),y)],fill=(int(b*(1-t)*0.85),int(b*(1-t)*0.92),int(b*(1-t))),width=2 if b>200 else 1)
bg+=np.asarray(img.filter(ImageFilter.GaussianBlur(0.8)),np.float32)/255*0.6

yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
# Sun glow upper-left, off-frame
sx,sy=-250,-180
rs=np.hypot(xx-sx,yy-sy)
bg+=np.array([1.0,0.9,0.75])[None,None]*(np.exp(-rs/380)*1.2+np.exp(-rs/1100)*0.18)[...,None]

# ---------- Earth (analytic sphere)
cx,cy,R=W*0.765,H*0.56,H*0.47
u=(xx-cx)/R; v=-(yy-cy)/R; rr=u*u+v*v; inside=rr<1
z=np.sqrt(np.clip(1-rr,0,1))
N=np.stack([u,v,z],-1)
L=norm(np.array([-0.82,0.38,0.42]))
ndl=N@L
tilt=np.radians(-20); lon0=np.radians(25)
ct,stt=np.cos(tilt),np.sin(tilt)
nx=u*ct-v*stt; ny=u*stt+v*ct; nz=z
# small x-axis tip so we look a bit from above
ta=np.radians(18); ny2=ny*np.cos(ta)+nz*np.sin(ta); nz2=-ny*np.sin(ta)+nz*np.cos(ta)
lat=np.arcsin(np.clip(ny2,-1,1)); lon=np.arctan2(nx,nz2)+lon0
m=inside
lat_m,lon_m=lat[m],lon[m]
dcol=samp(day,lat_m,lon_m); ncol=samp(night,lat_m,lon_m); wat=samp(water,lat_m,lon_m); cl=samp(cloud,lat_m,lon_m-0.15)
d_=ndl[m]; lit=np.clip(d_,0,1)
term=np.clip((d_+0.08)/0.25,0,1)  # soft terminator
dcol=dcol**1.1*1.15
surf=dcol*(lit**0.8*term)[:,None]
# warm terminator band
surf+=np.array([0.35,0.12,0.02])*(np.exp(-((d_-0.03)/0.07)**2)*0.25)[:,None]*dcol.mean(1,keepdims=True)*3
# ocean glint
V=np.array([0,0,1.0]); Hh=norm(L+V); ndh=np.clip(N[m]@Hh,0,1)
surf+=np.array([1.0,0.9,0.75])*(wat*ndh**120*1.2+wat*ndh**12*0.08)[:,None]*term[:,None]
# clouds
cl=np.clip(cl*0.95,0,1)
surf=surf*(1-cl[:,None]*0.9)+(cl*(lit**0.9*term))[:,None]*np.array([1.0,1.0,1.02])
# night lights
dark=np.clip((-d_+0.02)/0.18,0,1)
lights=np.clip(ncol.mean(1)-0.06,0,1)*1.8
surf+=np.array([1.0,0.72,0.35])*(lights*dark*(1-cl*0.7))[:,None]*1.3
# atmosphere inner rim
zz=z[m]; fres=(1-zz)**2.5
surf+=np.array([0.30,0.55,1.0])*(fres*np.clip(d_+0.25,0,1)*1.4)[:,None]
earth=np.zeros((H,W,3),np.float32); earth[m]=surf
# outer halo
r=np.sqrt(rr); dirl=np.clip(((u*L[0]+v*L[1])/np.maximum(r,1e-3))*0.6+0.55,0,1)
halo=np.where(~inside,np.exp(-(r-1)*R/26)*0.9+np.exp(-(r-1)*R/110)*0.25,0)*dirl
alpha=np.clip((1-r)*R/1.5,0,1)  # antialias edge
# ---------- motion trail: helix ribbon behind Earth (to the left)
tr=np.zeros((H,W),np.float32)
img=Image.new("L",(W,H)); d=ImageDraw.Draw(img)
pts=[]
for i in range(900):
    t=i/899
    x=cx-R*0.6-t*1900
    y=cy+np.sin(t*9.0)*R*0.22*(1-t*0.6)+t*-120
    pts.append((x,y,t))
for i in range(len(pts)-1):
    x0,y0,t=pts[i]; x1,y1,_=pts[i+1]
    w=int(max(2,40*(1-t)**1.3)); c=int(255*(1-t)**1.6)
    d.line([(x0,y0),(x1,y1)],fill=c,width=w)
tr=np.asarray(img.filter(ImageFilter.GaussianBlur(14)),np.float32)/255
tr2=np.asarray(img.filter(ImageFilter.GaussianBlur(60)),np.float32)/255
trail=np.array([0.35,0.75,1.0])*tr[...,None]*0.9+np.array([0.45,0.4,1.0])*tr2[...,None]*0.9
comp=bg+trail*0.0
comp+=np.array([0.35,0.6,1.0])*halo[...,None]
comp=comp*(1-alpha[...,None])+earth*alpha[...,None]
# bloom
im=Image.fromarray((np.clip(comp,0,1)*255).astype(np.uint8))
bl=np.asarray(im.filter(ImageFilter.GaussianBlur(30)),np.float32)/255
comp=1-(1-np.clip(comp,0,1))*(1-np.clip(bl-0.35,0,1)*0.6)
# vignette + grade
vig=1-0.5*np.clip(((xx-W*0.55)/(W*0.75))**2+((yy-H*0.5)/(H*0.8))**2,0,1)
comp=np.clip(comp*vig[...,None],0,1)
comp=comp**0.95
base=Image.fromarray((comp*255).astype(np.uint8))
base.save(OUT+"/earth_base.png")

# ---------- text
def font(sz,w="Black"):
    for p in [f"/usr/share/fonts/opentype/inter/InterDisplay-{w}.otf",f"/usr/share/fonts/opentype/inter/Inter-{w}.otf"]:
        try: return ImageFont.truetype(p,sz)
        except OSError: pass
def layer_text(im,items):
    sh=Image.new("L",im.size,0); ds=ImageDraw.Draw(sh)
    for (xy,s,f,col) in items: ds.text((xy[0]+8,xy[1]+12),s,font=f,fill=255,stroke_width=10,stroke_fill=255)
    sh=sh.filter(ImageFilter.GaussianBlur(18))
    im=Image.composite(Image.new("RGB",im.size,(0,0,0)),im,sh.point(lambda p:int(p*0.85)))
    d=ImageDraw.Draw(im)
    for (xy,s,f,col) in items: d.text(xy,s,font=f,fill=col,stroke_width=5,stroke_fill=(10,10,20))
    return im
Y=(255,206,0)
v=sys.argv[1] if len(sys.argv)>1 else "c"
if v=="c":
    im=layer_text(base.copy(),[((110,120),"YOU'RE MOVING",font(150),(255,255,255)),
                               ((100,290),"1,300,000",font(270),Y),
                               ((110,580),"KM/H",font(210),Y)])
    d=ImageDraw.Draw(im); f=font(84,"Bold"); s="RIGHT NOW."
    bb=d.textbbox((0,0),s,font=f)
    d.rounded_rectangle((110,860,110+bb[2]+70,860+bb[3]+50),24,fill=(230,30,40))
    d.text((145,860+25-bb[1]+bb[1]//2),s,font=f,fill=(255,255,255))
else:
    im=layer_text(base.copy(),[((110,110),"YOU ARE",font(170),(255,255,255)),
                               ((110,300),"NOT SITTING",font(170),(255,255,255)),
                               ((110,490),"STILL",font(270),Y)])
    d=ImageDraw.Draw(im); f=font(92,"Black"); s="1,300,000 KM/H"
    bb=d.textbbox((0,0),s,font=f)
    d.rounded_rectangle((110,1150,110+bb[2]+80,1150+bb[3]+56),26,fill=(230,30,40))
    d.text((150,1150+28),s,font=f,fill=(255,255,255))
im=im.resize((1280,720),Image.LANCZOS)
im.save(f"{OUT}/thumb_{v}.png"); im.save(f"{OUT}/thumb_{v}.jpg",quality=93)
print("ok",v)
