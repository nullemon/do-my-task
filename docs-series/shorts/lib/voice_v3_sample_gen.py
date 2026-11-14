import numpy as np, soundfile as sf, sys
from kokoro_onnx import Kokoro
k=Kokoro("/home/user/tts-models/kokoro-v1.0.onnx","/home/user/tts-models/voices-v1.0.bin")
O=sys.argv[1]; SR=24000
def sil(s): return np.zeros(int(SR*s),np.float32)
def build(lines, voice, speed):
    out=[]
    for txt,p in lines:
        a,_=k.create(txt,voice=voice,speed=speed,lang="en-us"); out+= [a, sil(p)]
    return np.concatenate(out)
OLD=[("What if black holes replaced our Sun? One Sun of mass, six kilometers wide. Same orbit, but dark forever. Sagittarius A star, four million Suns. Its shadow spans twenty-four degrees. TON 618, up to sixty-six billion Suns. It would swallow our solar system.",0.5)]
NEW=[("Imagine our Sun...",0.5),("replaced by a black hole.",1.0),
("First, one with exactly the same mass.",0.45),("Just six kilometers wide.",0.6),
("Earth keeps orbiting...",0.4),("but the light is gone.",0.35),("Forever.",1.1),
("Now... Sagittarius A star.",0.45),("Four million Suns.",0.5),("Its shadow would cover a quarter of the sky.",1.1),
("And TON 618.",0.5),("Sixty-six billion Suns.",0.5),("Its edge... is bigger than our entire solar system.",1.2),
("Suddenly...",0.45),("the Sun seems kind.",1.0)]
sf.write(f"{O}/A.wav",build(OLD,"am_michael",0.92),SR)
sf.write(f"{O}/B.wav",build(NEW,"am_michael",0.86),SR)
st=0.7*k.get_voice_style("am_michael")+0.3*k.get_voice_style("am_onyx")
sf.write(f"{O}/C.wav",build(NEW,st,0.86),SR)
print("ok")
