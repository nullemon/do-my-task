import numpy as np, wave
SR=44100; D=12.5; N=int(SR*D); t=np.arange(N)/SR
rng=np.random.default_rng(7)
L=np.zeros(N); R=np.zeros(N)
def env(a,b,att=.02,rel=.05):
    e=np.clip((t-a)/att,0,1)*np.clip((b-t)/rel,0,1); return e
def lp(x,k):  # simple one-pole lowpass
    y=np.empty_like(x); acc=0.
    kk=np.broadcast_to(np.asarray(k,float),x.shape)
    for i in range(len(x)): acc+= kk[i]*(x[i]-acc); y[i]=acc
    return y
def add(sig,a=0,pan=0.):
    i=int(a*SR); sig=sig[:N-i]; L[i:i+len(sig)]+=sig*(1-pan)*.5*2**.5*.8; R[i:i+len(sig)]+=sig*(1+pan)*.5*2**.5*.8
def blip(f,dur,vol=.25):
    tt=np.arange(int(dur*SR))/SR; e=np.minimum(1,tt/.005)*np.exp(-tt*18)
    return (np.sign(np.sin(2*np.pi*f*tt))*.4+np.sin(2*np.pi*f*tt))*e*vol
# hot ambience: low drone + cicada buzz
brown=np.cumsum(rng.standard_normal(N)); brown-=lp(brown,.001); brown/=np.abs(brown).max()
amb=brown*.10 + .03*np.sin(2*np.pi*55*t)*(1+.3*np.sin(2*np.pi*.3*t))
cic=rng.standard_normal(N)*(.5+.5*np.sign(np.sin(2*np.pi*38*t)))*(.5+.5*np.sin(2*np.pi*.7*t))
cic=cic-lp(cic,.6); amb+=cic*.035
fade=np.clip(t/.4,0,1)*np.clip((D-t)/.45,0,1)
duck=1-.7*((t>9.45)&(t<10.6))
amb*=fade*duck
L+=amb; R+=amb
# egg crack at 2.0
tt=np.arange(int(.12*SR))/SR
crack=rng.standard_normal(len(tt))*np.exp(-tt*60); crack=crack-lp(crack,.3)
add(crack*.7,2.0,.1); add(crack*.5,2.04,.1)
# splat at 2.32
tt=np.arange(int(.15*SR))/SR
add(lp(rng.standard_normal(len(tt)),.15)*np.exp(-tt*30)*1.2,2.32,.1)
# sizzle 2.35 -> end
sz=rng.standard_normal(N); sz=sz-lp(sz,.35)
crk=(rng.random(N)<.004)*rng.standard_normal(N)*3
sz=(sz*(.7+.3*np.sin(2*np.pi*7*t+rng.random()))+crk)
lvl=np.clip((t-2.35)/.15,0,1)*(.10+.05*np.clip((t-3)/6,0,1))
lvl=np.where(t>=10.6,.2,lvl)*duck*fade
add((sz*lvl)[:],0,.15)
# whoosh + AC hum while bubble moves in/out
def bx(x):
    if x<4.6: return 1000
    if x<6.7: p=(x-4.6)/2.1; return 1000+(478-1000)*(1-(1-p)**3)
    if x<9.45: return 478
    p=min(1,(x-9.45)/1.1); return 478+(-330-478)*p**3
pos=np.array([bx(x) for x in t[::100]]); pos=np.interp(t,t[::100],pos)
vis=np.clip(1-np.abs(pos-360)/700,0,1)
hum=(np.sin(2*np.pi*120*t)+.5*np.sin(2*np.pi*240*t)+.3*np.sin(2*np.pi*360*t))*.04
air=rng.standard_normal(N); air=lp(air,.08)*.5
bub=(hum+air*.25)*vis
pan=np.clip((pos-360)/400,-1,1)
L+=bub*(1-pan)*.6; R+=bub*(1+pan)*.6
for a,b in [(4.6,6.7),(9.45,10.55)]:
    tt=np.arange(int((b-a)*SR))/SR; w=lp(rng.standard_normal(len(tt)),.05+.1*np.sin(np.pi*tt/(b-a)))*np.sin(np.pi*tt/(b-a))**2
    add(w*1.0,a,0)
# arrival chime 6.6
for k,f in enumerate([1318,1760,2093]):
    tt=np.arange(int(.6*SR))/SR; add(np.sin(2*np.pi*f*tt)*np.exp(-tt*6)*.10,6.55+k*.07,.4)
# slurp 6.8
tt=np.arange(int(.4*SR))/SR; s=lp(rng.standard_normal(len(tt)),.2)*(.5+.5*np.sin(2*np.pi*14*tt))*np.sin(np.pi*tt/.4)
add(s*.6,6.8,.3)
# mumble speech blips
def mumble(a,b,base,pan,step=.085):
    x=a; i=0
    while x<b:
        f=base*(1+.25*np.sin(i*2.3)+.1*rng.standard_normal()); add(blip(f,.07,.18),x,pan); x+=step*(1+.3*rng.random()); i+=1
mumble(2.95,4.5,420,-.3)      # guy
mumble(7.4,9.1,260,.35,.095)  # neighbour (deeper)
mumble(10.9,12.0,330,-.3,.11) # sad guy
# punch-in: whoosh + crickets
tt=np.arange(int(.18*SR))/SR; add(lp(rng.standard_normal(len(tt)),.3)*np.exp(-tt*20)*1.2,9.42,0)
for k in range(4):
    for j in range(3):
        tt=np.arange(int(.05*SR))/SR; add(np.sin(2*np.pi*4400*tt)*np.sin(np.pi*tt/.05)*.07,9.6+k*.25+j*.06,.5)
# sad trombone-ish at 11.2
for k,f in enumerate([392,370,349,330]):
    d=.28 if k<3 else .8
    tt=np.arange(int(d*SR))/SR; ff=f*(1+.02*np.sin(2*np.pi*5*tt)*(k==3))
    ph=2*np.pi*np.cumsum(ff)/SR; w=(np.sin(ph)+.5*np.sin(2*ph)+.3*np.sin(3*ph))*np.minimum(1,tt/.03)*np.minimum(1,(d-tt)/.08)
    add(w*.07,11.25+k*.3,0)
st=np.stack([L,R],1); st/=max(1,np.abs(st).max()/0.9)
with wave.open('audio.wav','wb') as w:
    w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR);w.writeframes((st*32767).astype('<i2').tobytes())
print('done')
