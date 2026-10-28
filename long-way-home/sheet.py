# Tile rendered stills into contact sheets for review: python3 sheet.py out/stills out/sheet 3 2
import sys, glob, os
from PIL import Image, ImageDraw

src, dst = sys.argv[1], sys.argv[2]
cols, rows = int(sys.argv[3]), int(sys.argv[4])
files = sorted(glob.glob(os.path.join(src, '*.png')))
tw, th = 360, 640
per = cols * rows
for p in range(0, len(files), per):
    sheet = Image.new('RGB', (cols * tw, rows * th), 'black')
    d = ImageDraw.Draw(sheet)
    for i, f in enumerate(files[p:p + per]):
        im = Image.open(f).convert('RGB').resize((tw, th), Image.LANCZOS)
        x, y = (i % cols) * tw, (i // cols) * th
        sheet.paste(im, (x, y))
        d.text((x + 6, y + 6), os.path.basename(f)[2:-4], fill=(255, 255, 0))
    sheet.save(f'{dst}_{p // per}.jpg', quality=88)
    print(f'{dst}_{p // per}.jpg')
