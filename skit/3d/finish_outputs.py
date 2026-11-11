"""Post-render step (plain python3 + Pillow): contact sheets, sprite manifest, naruto turntable MP4."""
import os, json, glob, subprocess
from PIL import Image, ImageDraw

OUT = "/home/user/do-my-task/skit/3d"
NAMES = ["naruto", "kakashi", "sasuke", "obito"]
LABS = ["front", "three_quarter_front_left", "side_left", "back", "three_quarter_back", "side_right"]

for n in NAMES:
    d = f"{OUT}/previews/{n}"
    ims = [Image.open(f"{d}/{n}_{l}.png").convert("RGB") for l in LABS]
    w, h = ims[0].size; tw, th = w // 2, h // 2
    cs = Image.new("RGB", (tw * 3, th * 2), (255, 255, 255)); dr = ImageDraw.Draw(cs)
    for i, (im, l) in enumerate(zip(ims, LABS)):
        x, y = (i % 3) * tw, (i // 3) * th
        cs.paste(im.resize((tw, th), Image.LANCZOS), (x, y)); dr.text((x + 12, y + 12), l, fill=(20, 20, 20))
    cs.save(f"{OUT}/{n}_contact_sheet.png")
    # copy the five requested angles for naruto at top level too
manifest = {"frame_width": 900, "frame_height": 1100, "feet_row": 1040, "pixels_per_metre": 450,
            "camera": "orthographic, identical for all characters/frames; ground plane z=0 at feet_row",
            "yaw_convention": "0=facing camera, 90=facing screen-left, 180=back, 270=facing screen-right",
            "characters": {}}
for n in NAMES:
    frames = json.load(open(f"{OUT}/sprites/{n}/frames.json"))
    manifest["characters"][n] = {"dir": f"sprites/{n}", "frames": frames}
json.dump(manifest, open(f"{OUT}/sprites/manifest.json", "w"), indent=1)

tt = f"{OUT}/turntable_frames/naruto"
if os.path.isdir(tt):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "30", "-i", f"{tt}/f_%03d.png",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart",
                    f"{OUT}/naruto_turntable.mp4"], check=True)
print("ok")
