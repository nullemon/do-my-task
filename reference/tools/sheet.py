import sys, subprocess, os
from PIL import Image, ImageDraw
d, code = sys.argv[1], sys.argv[2]; n = int(sys.argv[3]) if len(sys.argv) > 3 else 30
f = f"{d}/cl/{code}.mp4"
L = float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f]).decode())
step = L / n; cols = 6; tw, th = 320, 180
os.makedirs(f"{d}/sheets/tmp", exist_ok=True)
sheet = Image.new("RGB", (cols * tw, ((n + cols - 1) // cols) * th))
for k in range(n):
    t = step * (k + 0.5); p = f"{d}/sheets/tmp/{code}_{k}.jpg"
    subprocess.run(["ffmpeg","-v","error","-y","-ss",f"{t:.2f}","-i",f,"-frames:v","1","-vf",f"scale={tw}:{th}",p])
    if not os.path.exists(p): continue
    im = Image.open(p); dr = ImageDraw.Draw(im); dr.rectangle((0,0,70,16),fill=(0,0,0)); dr.text((3,2),f"{t:.0f}s",fill=(255,255,0))
    sheet.paste(im, ((k % cols) * tw, (k // cols) * th))
sheet.save(f"{d}/sheets/{code}.jpg", quality=80)
