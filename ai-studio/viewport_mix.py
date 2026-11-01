"""Put a video inside a screenshot of Blender's 3D viewport (the "made in Blender" look).

  python viewport_mix.py dance.mp4 --ui blender_ui.png
  python viewport_mix.py dance.mp4 --ui blender_ui.png --playhead 120,1000,1700,1840   # moving blue playhead

--ui: a screenshot of Blender with the window made tall (portrait). In the viewport, switch off Overlays -> Floor,
      Axes and Text Info so the viewport is one plain grey; keep the navigation gizmo and toolbar (they stay on top
      of your video, like the real thing). The viewport is found automatically (the plain grey area around the
      centre); give --rect x,y,w,h (screenshot pixels) if it picks the wrong area.
--playhead x0,x1,y0,y1: screenshot pixels of the timeline area; a blue playhead with a frame counter moves across it.
Output: 1080 x 1920 MP4 with the video's sound.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile

import numpy as np
from PIL import Image, ImageDraw

W, H = 1080, 1920


def run(cmd):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if r.returncode:
        sys.exit(f'  !!  ffmpeg failed: {r.stderr[-1500:]}')
    return r.stdout


def probe(path):
    out = json.loads(run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,r_frame_rate:format=duration',
                          '-of', 'json', path]))
    v = next(s for s in out['streams'] if s['codec_type'] == 'video')
    num, den = (int(x) for x in v['r_frame_rate'].split('/'))
    return float(out['format']['duration']), num / max(den, 1), any(s['codec_type'] == 'audio' for s in out['streams'])


def fit_canvas(ui):
    """Scale the screenshot to fill 1080 x 1920 (cropping the sides or top/bottom evenly)."""
    s = max(W / ui.width, H / ui.height)
    ui = ui.resize((round(ui.width * s), round(ui.height * s)), Image.Resampling.LANCZOS)
    x, y = (ui.width - W) // 2, (ui.height - H) // 2
    return ui.crop((x, y, x + W, y + H)), s, x, y


def find_viewport(ui, tol=10):
    """Flood-fill the plain grey around the centre; returns its bounding box and the mask of that grey."""
    rgb = ui.convert('RGB')
    marker = (255, 0, 255)
    probe_img = rgb.copy()
    cx, cy = W // 2, H // 2
    ImageDraw.floodfill(probe_img, (cx, cy), marker, thresh=tol)
    a = np.asarray(probe_img)
    filled = np.all(a == marker, axis=-1)
    ys, xs = np.nonzero(filled)
    if len(xs) < W * H * 0.08:
        sys.exit('  !!  could not find the grey viewport around the centre; pass --rect x,y,w,h')
    ref = np.asarray(rgb)[cy, cx].astype(int)
    # every pixel of the viewport grey counts, also inside the gizmo circles
    grey = np.all(np.abs(np.asarray(rgb).astype(int) - ref) <= tol, axis=-1)
    return (int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)), grey


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('video')
    ap.add_argument('--ui', required=True, help='Blender screenshot (tall window)')
    ap.add_argument('--rect', help='viewport x,y,w,h in screenshot pixels (default: found automatically)')
    ap.add_argument('--playhead', help='timeline x0,x1,y0,y1 in screenshot pixels')
    ap.add_argument('--out', default='viewport_mix.mp4')
    a = ap.parse_args()

    dur, fps, has_audio = probe(a.video)
    ui, scale, ox, oy = fit_canvas(Image.open(a.ui).convert('RGBA'))
    to_canvas = lambda x, y: (round(x * scale - ox), round(y * scale - oy))
    if a.rect:
        x, y, w, h = (float(v) for v in a.rect.split(','))
        (x0, y0), (x1, y1) = to_canvas(x, y), to_canvas(x + w, y + h)
        rect = (x0, y0, x1 - x0, y1 - y0)
        ref = np.asarray(ui.convert('RGB'))[y0 + (y1 - y0) // 2, x0 + (x1 - x0) // 2].astype(int)
        grey = np.all(np.abs(np.asarray(ui.convert('RGB')).astype(int) - ref) <= 10, axis=-1)
    else:
        rect, grey = find_viewport(ui)
    x, y, w, h = rect
    w -= w % 2
    h -= h % 2

    # UI elements inside the viewport (gizmo, toolbar) stay on top of the video
    top = np.asarray(ui).copy()
    inside = np.zeros(grey.shape, bool)
    inside[y:y + h, x:x + w] = True
    top[..., 3] = np.where(inside & ~grey, 255, 0).astype(np.uint8)

    tmp = tempfile.mkdtemp(prefix='viewport_')
    try:
        base_png, top_png = os.path.join(tmp, 'base.png'), os.path.join(tmp, 'top.png')
        ui.convert('RGB').save(base_png)
        Image.fromarray(top).save(top_png)
        graph = [f'[1:v]scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h},setsar=1[vid]',
                 f'[0:v][vid]overlay={x}:{y}:shortest=1[a]', '[a][2:v]overlay=0:0[b]']
        last = 'b'
        extra = []
        if a.playhead:
            px0, px1, py0, py1 = (float(v) for v in a.playhead.split(','))
            (cx0, cy0), (cx1, cy1) = to_canvas(px0, py0), to_canvas(px1, py1)
            ph = Image.new('RGBA', (48, cy1 - cy0), (0, 0, 0, 0))
            pd = ImageDraw.Draw(ph)
            pd.rectangle([23, 0, 25, ph.height], fill=(71, 114, 179, 255))       # Blender's blue playhead
            pd.rounded_rectangle([0, 0, 47, 25], radius=5, fill=(71, 114, 179, 255))
            ph_png = os.path.join(tmp, 'playhead.png')
            ph.save(ph_png)
            extra = ['-loop', '1', '-framerate', f'{fps:.6f}', '-i', ph_png]
            move = f'{cx0}+({cx1}-{cx0})*t/{dur:.3f}-24'
            graph.append(f"[b][3:v]overlay=x='{move}':y={cy0}[p]")
            graph.append(f"[p]drawtext=text='%{{eif\\:n+1\\:d}}':x='{move}+24-tw/2':y={cy0 + 5}:fontsize=17:"
                         "fontcolor=white[c]")
            last = 'c'
        cmd = ['ffmpeg', '-y', '-v', 'error', '-loop', '1', '-framerate', f'{fps:.6f}', '-i', base_png,
               '-i', a.video, '-loop', '1', '-framerate', f'{fps:.6f}', '-i', top_png, *extra,
               '-filter_complex', ';'.join(graph), '-map', f'[{last}]']
        if has_audio:
            cmd += ['-map', '1:a', '-c:a', 'aac', '-b:a', '192k']
        cmd += ['-t', f'{dur:.3f}', '-r', f'{fps:.6f}', '-c:v', 'libx264', '-crf', '17', '-preset', 'medium',
                '-pix_fmt', 'yuv420p', '-movflags', '+faststart', a.out]
        run(cmd)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f'  OK  {a.out}  (viewport {w}x{h} at {x},{y}; {dur:.1f} s)')


if __name__ == '__main__':
    main()
