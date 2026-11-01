"""Copy your newest ComfyUI result into an episode folder under the right name.

  python pick.py ep01 3            # newest picture or video  -> ep01/shot03.png / .mp4
  python pick.py ep01 3 --image    # newest picture only (e.g. you made the video but want the still)
  python pick.py ep01 music        # newest audio             -> ep01/music.*
  python pick.py ep01 voice 3      # newest audio             -> ep01/voice/shot03.*
  python pick.py ep01 sfx 3        # newest audio             -> ep01/sfx/shot03.*
  python pick.py ep01 3 --file /workspace/outputs/gpu0/video/ComfyUI_00012_.mp4   # a specific file

Episode folders are looked up as given, then in ./episodes and /workspace/episodes.
Results are searched in /workspace/outputs and ComfyUI's output folder.
"""
import argparse, glob, os, shutil, sys

IMAGES = ('.png', '.jpg', '.jpeg', '.webp')
VIDEOS = ('.mp4', '.mov', '.webm', '.mkv', '.gif')
AUDIO = ('.wav', '.mp3', '.flac', '.m4a', '.ogg', '.opus')
ROOTS = ['/workspace/outputs', '/workspace/ComfyUI/output',
         os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'ComfyUI', 'output')]


def newest(exts):
    files = [p for r in ROOTS if os.path.isdir(r) for p in glob.glob(os.path.join(r, '**', '*'), recursive=True)
             if p.lower().endswith(exts) and os.path.isfile(p)]
    if not files:
        sys.exit(f'  !!  no {"/".join(exts)} files found in {", ".join(r for r in ROOTS if os.path.isdir(r))}')
    return max(files, key=os.path.getmtime)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('episode')
    ap.add_argument('what', help='shot number, or music / voice / sfx')
    ap.add_argument('shot', nargs='?', type=int, help='shot number for voice / sfx')
    ap.add_argument('--file', help='use this file instead of the newest result')
    ap.add_argument('--image', action='store_true', help='for shots: take the newest picture, not video')
    a = ap.parse_args()

    ep = next((c for c in (a.episode, os.path.join('episodes', a.episode), os.path.join('/workspace/episodes', a.episode))
               if os.path.isfile(os.path.join(c, 'episode.json'))), None)
    if not ep:
        sys.exit(f'  !!  no episode.json in {a.episode} (also looked in ./episodes and /workspace/episodes)')
    if a.what.isdigit():
        n, sub, exts = int(a.what), '', IMAGES if a.image else IMAGES + VIDEOS
        stem = f'shot{n:02d}'
    elif a.what == 'music':
        sub, exts, stem = '', AUDIO, 'music'
    elif a.what in ('voice', 'sfx'):
        if a.shot is None:
            sys.exit(f'  !!  which shot? e.g.  python pick.py {a.episode} {a.what} 3')
        sub, exts, stem = a.what, AUDIO, f'shot{a.shot:02d}'
    else:
        sys.exit('  !!  say a shot number, music, voice N or sfx N')
    src = a.file or newest(exts)
    dest_dir = os.path.join(ep, sub)
    os.makedirs(dest_dir, exist_ok=True)
    keep_still = a.what.isdigit() and src.lower().endswith(VIDEOS)   # a shot can have both its picture and video
    for old in glob.glob(os.path.join(dest_dir, stem + '.*')):
        if keep_still and old.lower().endswith(IMAGES):
            continue
        os.remove(old)
    dest = os.path.join(dest_dir, stem + os.path.splitext(src)[1].lower())
    shutil.copy2(src, dest)
    print(f'  OK  {src}  ->  {dest}')


if __name__ == '__main__':
    main()
