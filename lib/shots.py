"""Script building blocks.  A narration segment's `vis` is a list of shots; each shot is a dict made by these helpers.

Media:
  P(key, focus=(0.5,0.45), z=(1.0,1.08), credit=None)       photo from photos/manifest.csv (Ken Burns)
  F(src, t_in, t_out=None, crop=None, credit=None, focus=..)  footage clip (crop = dict(x0,y0,x1,y1) in source pixels)
Layouts (the four reel formats + specials):
  FULL(media, pops=[...], label=None)        format 2: full-screen + pop-ups
  SPLIT(top, bottom, chip1=None, chip2=None)  format 1: split stack (side by side on 16:9)
  BOARD(items=[(media, caption)], notes=[(big, small)])   format 3: journey board
  FREEZE(media, at=1.2, circle=(u,v,r), label="THAT'S HACHIKO", speaker=None)  format 4
  MAP(kind="route"|"pin", ...), STAT(big, small, bg), CHAPTER handled by segments, CTA(k, bg)
Pop-ups (FULL / FREEZE):  t is seconds from shot start, or "@word" = when that word is spoken
  POL(media, caption, t, pos="br")  polaroid      STAMP(text, t)  red date stamp
  CIRCLE(u, v, r, t, label=None)    red circle (+arrow+label), coordinates normalised to the media
  CHIP(text, t)                     label chip      PIN(text, t)   location chip with red dot
"""
def P(key, focus=(0.5, 0.45), z=(1.0, 1.08), credit=None, pan=None, tone=None, crop=None):
    return dict(m="photo", key=key, focus=focus, z=z, credit=credit, pan=pan, tone=tone, crop=crop)
def F(src, t_in, t_out=None, crop=None, credit=None, focus=(0.5, 0.5), z=(1.0, 1.05)):
    return dict(m="video", src=src, t_in=t_in, t_out=t_out, crop=crop, credit=credit, focus=focus, z=z)

def FULL(media, pops=(), label=None, punch=False): return dict(L="full", media=media, pops=list(pops), label=label, punch=punch)
def SPLIT(top, bottom, chip1=None, chip2=None): return dict(L="split", top=top, bottom=bottom, chip1=chip1, chip2=chip2)
def BOARD(items, notes=(), title=None): return dict(L="board", items=list(items), notes=list(notes), title=title)
def FREEZE(media, at=1.0, circle=None, label=None, speaker=None, chip="FREEZE"):
    return dict(L="freeze", media=media, at=at, circle=circle, label=label, speaker=speaker, chip=chip)
def MAP(kind, bg_key=None, **kw): return dict(L="map", kind=kind, **kw)
def STAT(big, small, bg, sub=None): return dict(L="stat", big=big, small=small, bg=bg, sub=sub)
def CTA(k, bg): return dict(L="cta", k=k, bg=bg)

def POL(media, caption, t, pos="br", tilt=None): return dict(p="polaroid", media=media, caption=caption, t=t, pos=pos, tilt=tilt)
def STAMP(text, t, pos="tl"): return dict(p="stamp", text=text, t=t, pos=pos)
def CIRCLE(u, v, r, t, label=None, side="below"): return dict(p="circle", u=u, v=v, r=r, t=t, label=label, side=side)
def CHIP(text, t=0.2, pos="tl", color="yellow"): return dict(p="chip", text=text, t=t, pos=pos, color=color)
def PIN(text, t=0.3): return dict(p="pin", text=text, t=t)
