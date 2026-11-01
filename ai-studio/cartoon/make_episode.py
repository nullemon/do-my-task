"""Assemble a finished vertical episode from an episode folder.

  python make_episode.py episodes/ep01                      # 80s cartoon look, full-screen 1080x1920
  python make_episode.py episodes/ep01 --look 80s-anime --frame tv
  python make_episode.py episodes/ep01 --look clean         # no retro treatment (stickman, Rusty, ...)

The folder holds episode.json (written by story_to_episode.py or by hand) and whatever you have made so far:
  shot01.png / shot01.mp4 ...   a picture (gets a camera pan in code) or an animated clip, per shot
  voice/shot01.wav ...          dialogue or narration for that shot (any audio format), or narration.* for all
  music.*                       background music (looped/trimmed to fit, ducked under voices)
  sfx/shot01.wav ...            a sound effect that starts with that shot
Missing shots become labelled placeholder cards, so you can preview the cut at any time.
Writes final.mp4 and cover.jpg into the folder.
"""
import argparse, glob, json, math, os, shutil, subprocess, sys, textwrap

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_TITLE = os.path.join(HERE, 'fonts', 'Righteous-Regular.ttf')
FONT_TEXT = os.path.join(HERE, 'fonts', 'LuckiestGuy-Regular.ttf')
W, H = 1080, 1920
OUT_FPS = 24
VIDEO_EXT = ('.mp4', '.mov', '.webm', '.mkv', '.gif', '.m4v')
IMAGE_EXT = ('.png', '.jpg', '.jpeg', '.webp')
AUDIO_EXT = ('.wav', '.mp3', '.m4a', '.aac', '.flac', '.ogg', '.opus', '.mp4', '.webm')

# fps: frames per second of the drawn motion (12 = "on twos", like hand-drawn TV animation)
LOOKS = {
    '80s-cartoon': dict(fps=12, filters=(
        'eq=saturation=0.9:contrast=1.05:gamma=1.02,colorbalance=rm=0.04:bm=-0.04,'
        "curves=all='0/0.05 1/0.95',noise=alls=7:allf=t,vignette=PI/5")),
    '80s-anime': dict(fps=12, filters=(
        "eq=saturation=0.85:contrast=1.02,curves=all='0/0.07 1/0.94',gblur=sigma=0.5,"
        'rgbashift=rh=2:bh=-2,noise=alls=6:allf=t,vignette=PI/5')),
    'clean': dict(fps=24, filters=''),
}
WEAVE = 'crop=iw-8:ih-8:4+2*sin(n*1.7)+1.5*sin(n*0.43):4+2*cos(n*1.1)+1.5*sin(n*0.29)'  # film gate weave


def run(cmd):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if r.returncode:
        sys.exit(f'  !!  ffmpeg failed:\n{" ".join(cmd)}\n{r.stderr[-2500:]}')
    return r.stdout


def duration(path):
    try:
        return float(run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path]).strip())
    except ValueError:
        return 0.0


def find(folder, stem, exts):
    for e in exts:
        for p in (os.path.join(folder, stem + e), os.path.join(folder, stem + e.upper())):
            if os.path.isfile(p):
                return p
    return None


def font(path, size):
    return ImageFont.truetype(path, size)


def wrap(text, fnt, max_w, draw):
    words, lines, cur = text.split(), [], ''
    for w_ in words:
        test = (cur + ' ' + w_).strip()
        if draw.textlength(test, font=fnt) <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def text_layer(path, text, fnt_path, size, y, fill, stroke, max_w=900, anchor_bottom=False):
    """Full-canvas transparent PNG with centred, outlined text (top at y, or bottom at y)."""
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fnt = font(fnt_path, size)
    lines = wrap(text, fnt, max_w, d)
    lh = int(size * 1.12)
    total = lh * len(lines)
    top = y - total if anchor_bottom else y
    sw = max(3, size // 9)
    for i, line in enumerate(lines):
        tw = d.textlength(line, font=fnt)
        x, yy = (W - tw) / 2, top + i * lh
        d.text((x + 5, yy + 6), line, font=fnt, fill=(0, 0, 0, 150), stroke_width=sw, stroke_fill=(0, 0, 0, 150))
        d.text((x, yy), line, font=fnt, fill=fill, stroke_width=sw, stroke_fill=stroke)
    img.save(path)


def ease(t):
    return t * t * (3 - 2 * t)


def cover_box(iw, ih, pw, ph):
    """Largest box of the picture's aspect ratio inside the image, centred."""
    if iw / ih > pw / ph:
        bw, bh = ih * pw / ph, ih
    else:
        bw, bh = iw, iw * ph / pw
    return (iw - bw) / 2, (ih - bh) / 2, bw, bh


def pan_frames(img, pw, ph, n, move):
    """Camera move over a still picture, done in code (no AI wobble)."""
    iw, ih = img.size
    bx, by, bw, bh = cover_box(iw, ih, pw, ph)
    for i in range(n):
        t = ease(i / max(1, n - 1))
        if move in ('left', 'right', 'up', 'down'):
            z = 1.18
            cw, ch = bw / z, bh / z
            if move in ('left', 'right'):
                span = (iw - cw) if iw - cw > bw - cw else (bw - cw)
                x0 = (iw - cw) / 2 - span / 2
                x = x0 + span * (t if move == 'right' else 1 - t)
                y = by + (bh - ch) / 2
            else:
                span = (ih - ch) if ih - ch > bh - ch else (bh - ch)
                y0 = (ih - ch) / 2 - span / 2
                y = y0 + span * (t if move == 'down' else 1 - t)
                x = bx + (bw - cw) / 2
        else:  # in / out / still (gentle push-in)
            z0, z1 = {'in': (1.0, 1.14), 'out': (1.14, 1.0)}.get(move, (1.0, 1.05))
            z = z0 + (z1 - z0) * t
            cw, ch = bw / z, bh / z
            x, y = bx + (bw - cw) / 2, by + (bh - ch) / 2
        yield img.transform((pw, ph), Image.Transform.EXTENT, (x, y, x + cw, y + ch), Image.Resampling.BICUBIC)


def placeholder(pw, ph, shot):
    img = Image.new('RGB', (pw, ph), (38, 30, 46))
    d = ImageDraw.Draw(img)
    big = font(FONT_TITLE, int(pw * 0.14))
    small = font(FONT_TEXT, int(pw * 0.04))
    label = f'SHOT {shot["id"]:02d}'
    d.text(((pw - d.textlength(label, font=big)) / 2, ph * 0.22), label, font=big, fill=(255, 210, 63))
    hint = f'{shot.get("kind", "")} - missing'.upper()
    hy = ph * 0.22 + pw * 0.18
    d.text(((pw - d.textlength(hint, font=small)) / 2, hy), hint, font=small, fill=(230, 220, 240))
    body = font(FONT_TEXT, int(pw * 0.03))
    for i, line in enumerate(textwrap.wrap(shot.get('image_prompt', '')[:260], 42)[:7]):
        d.text((pw * 0.08, hy + pw * 0.09 + i * pw * 0.045), line.upper(), font=body, fill=(170, 160, 185))
    return img


def make_shot_clip(src, shot, out, pw, ph, secs, look):
    fps = look['fps']
    vf = [f'fps={fps}']
    if look['filters']:
        vf += [look['filters'], WEAVE, f'scale={pw}:{ph}']
    vf = ','.join(vf)
    enc = ['-c:v', 'libx264', '-crf', '14', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-an']
    if src and src.lower().endswith(VIDEO_EXT):
        run(['ffmpeg', '-y', '-v', 'error', '-i', src, '-vf',
             f'scale={pw}:{ph}:force_original_aspect_ratio=increase:flags=lanczos,crop={pw}:{ph},'
             f'tpad=stop_mode=clone:stop_duration={secs},{vf}', '-t', f'{secs:.3f}', *enc, out])
        return
    n = max(1, round(secs * fps))
    if src:
        img = Image.open(src).convert('RGB')
        frames = pan_frames(img, pw, ph, n, shot.get('move') or ('in' if shot.get('kind') == 'still' else 'right'))
    else:
        still = placeholder(pw, ph, shot)
        frames = (still for _ in range(n))
    p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{pw}x{ph}',
                          '-r', str(fps), '-i', '-', '-vf', vf, '-r', str(fps), *enc, out], stdin=subprocess.PIPE)
    for f in frames:
        p.stdin.write(f.tobytes())
    p.stdin.close()
    if p.wait():
        sys.exit(f'  !!  could not encode shot {shot["id"]}')


def caption_text(shot):
    if shot.get('caption'):
        return shot['caption']
    if shot.get('dialogue'):
        return ' '.join(f'"{d["line"]}"' for d in shot['dialogue'])
    return shot.get('narration', '')


def build_audio(folder, shots, starts, total, out):
    """Voices + sound effects at their shots, music under them (ducked while someone speaks), -14 LUFS."""
    inputs, graph, voices, effects = [], [], [], []

    def add(path, start, label, extra='', loop=False):
        k = sum(1 for x in inputs if x == '-i')
        inputs.extend((['-stream_loop', '-1'] if loop else []) + ['-i', path])
        graph.append(f'[{k}:a]aresample=48000,aformat=channel_layouts=stereo,{extra}'
                     f'adelay={int(start * 1000)}:all=1[{label}]')

    music = find(folder, 'music', AUDIO_EXT)
    if music:
        fade = max(0.0, total - 1.8)
        add(music, 0.0, 'mus0', f'atrim=0:{total:.3f},volume=0.32,afade=t=out:st={fade:.3f}:d=1.8,', loop=True)
    narration = find(folder, 'narration', AUDIO_EXT)
    if narration:
        add(narration, 0.0, 'nar')
        voices.append('nar')
    for s, t0 in zip(shots, starts):
        v = find(os.path.join(folder, 'voice'), f'shot{s["id"]:02d}', AUDIO_EXT)
        if v:
            add(v, t0, f'v{s["id"]}')
            voices.append(f'v{s["id"]}')
        fx = find(os.path.join(folder, 'sfx'), f'shot{s["id"]:02d}', AUDIO_EXT)
        if fx:
            add(fx, t0, f'fx{s["id"]}', 'volume=0.8,')
            effects.append(f'fx{s["id"]}')
    if not inputs:
        run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-t', f'{total:.3f}',
             '-c:a', 'pcm_s16le', out])
        return False
    mix = []
    if voices:
        graph.append(f'{"".join(f"[{l}]" for l in voices)}amix=inputs={len(voices)}:normalize=0,asplit=2[vox][vkey]')
        mix.append('[vox]')
        if music:
            graph.append('[mus0][vkey]sidechaincompress=threshold=0.04:ratio=8:attack=20:release=400[mus]')
        else:
            graph.append('[vkey]anullsink')
    elif music:
        graph.append('[mus0]anull[mus]')
    if music:
        mix.append('[mus]')
    mix += [f'[{l}]' for l in effects]
    graph.append(f'{"".join(mix)}amix=inputs={len(mix)}:normalize=0,apad,atrim=0:{total:.3f},'
                 'loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]')
    run(['ffmpeg', '-y', '-v', 'error', *inputs, '-filter_complex', ';'.join(graph), '-map', '[aout]',
         '-c:a', 'pcm_s16le', out])
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('folder')
    ap.add_argument('--look', choices=sorted(LOOKS), default=None, help='default: from episode.json, else 80s-cartoon')
    ap.add_argument('--frame', choices=['full', 'tv'], default='full',
                    help='full = picture fills the tall screen; tv = 4:3 "old TV" picture with title above, captions below')
    ap.add_argument('--out', default='final.mp4')
    a = ap.parse_args()

    folder = next((os.path.abspath(c) for c in (a.folder, os.path.join('episodes', a.folder),
                                                  os.path.join('/workspace/episodes', a.folder))
                   if os.path.isfile(os.path.join(c, 'episode.json'))), None)
    if not folder:
        sys.exit(f'  !!  no episode.json in {a.folder} (also looked in ./episodes and /workspace/episodes)')
    ep = json.load(open(os.path.join(folder, 'episode.json'), encoding='utf-8'))
    look_name = a.look or ep.get('look') or '80s-cartoon'
    look = LOOKS[look_name]
    pw, ph = (W, H) if a.frame == 'full' else (W, 810)
    work = os.path.join(folder, '_work')
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)

    shots, starts, clips, t = ep['shots'], [], [], 0.0
    have = missing = 0
    for s in shots:
        secs = float(s.get('seconds') or 4)
        v = find(os.path.join(folder, 'voice'), f'shot{s["id"]:02d}', AUDIO_EXT)
        if v:
            secs = max(secs, duration(v) + 0.35)          # never cut a line off
        src = find(folder, f'shot{s["id"]:02d}', VIDEO_EXT + IMAGE_EXT)
        have += bool(src)
        missing += not src
        clip = os.path.join(work, f'shot{s["id"]:02d}.mp4')
        make_shot_clip(src, s, clip, pw, ph, secs, look)
        starts.append(t)
        s['_secs'] = secs
        t += secs
        clips.append(clip)
        print(f'  ..  shot {s["id"]:02d}  {secs:4.1f}s  {os.path.basename(src) if src else "(placeholder)"}')
    total = t

    with open(os.path.join(work, 'clips.txt'), 'w') as f:
        f.writelines(f"file '{c}'\n" for c in clips)
    picture = os.path.join(work, 'picture.mp4')
    run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', os.path.join(work, 'clips.txt'),
         '-c', 'copy', picture])

    # Text: title on the opening shot, then each shot's caption (readable with the sound off)
    if a.frame == 'full':
        title_y, cap_y, cap_size = 230, 1480, 72
    else:
        title_y, cap_y, cap_size = 150, 1680, 64
    layers = []
    title = ep.get('title', '')
    if title:
        p = os.path.join(work, 'title.png')
        text_layer(p, title.upper(), FONT_TITLE, 104, title_y, (255, 210, 63), (43, 27, 23), max_w=960)
        layers.append((p, 0.15, min(3.2, shots[0]['_secs'] - 0.1)))
    for s, t0 in zip(shots, starts):
        txt = caption_text(s)
        if not txt:
            continue
        p = os.path.join(work, f'cap{s["id"]:02d}.png')
        text_layer(p, txt.upper(), FONT_TEXT, cap_size, cap_y, (255, 255, 255), (20, 16, 24), anchor_bottom=True)
        layers.append((p, t0 + 0.12, t0 + s['_secs'] - 0.08))

    inputs = ['-i', picture]
    for p, _, _ in layers:
        inputs += ['-loop', '1', '-t', f'{total:.3f}', '-i', p]
    base = f'[0:v]fps={OUT_FPS}'
    if a.frame == 'tv':
        base += f',pad={W}:{H}:0:{(H - ph) // 2 - 40}:color=0x140f12'
    graph = [base + '[v0]']
    for i, (_, t0, t1) in enumerate(layers, 1):
        graph.append(f"[v{i - 1}][{i}:v]overlay=0:0:enable='between(t,{t0:.3f},{t1:.3f})'[v{i}]")
    audio = os.path.join(work, 'audio.wav')
    has_audio = build_audio(folder, shots, starts, total, audio)
    inputs += ['-i', audio]
    out = os.path.join(folder, a.out)
    run(['ffmpeg', '-y', '-v', 'error', *inputs, '-filter_complex', ';'.join(graph), '-map', f'[v{len(layers)}]',
         '-map', f'{len(layers) + 1}:a', '-t', f'{total:.3f}', '-c:v', 'libx264', '-crf', '18', '-preset', 'medium',
         '-pix_fmt', 'yuv420p', '-r', str(OUT_FPS), '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out])
    run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{min(1.0, total / 2):.2f}', '-i', out, '-frames:v', '1', '-q:v', '2',
         os.path.join(folder, 'cover.jpg')])
    print(f'  OK  {out}  ({total:.1f} s, {look_name}, {a.frame} frame, {have} shots ready, {missing} placeholders, '
          f'{"with" if has_audio else "no"} sound)')


if __name__ == '__main__':
    main()
