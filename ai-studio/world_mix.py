""""1 dance, many worlds": cut between several motion-transfer versions of the SAME driving clip.

Every version follows the same clip, so they stay in sync and the moves flow straight across each cut.

  python world_mix.py --audio dance16.mp4 --every 4 v1.mp4 v2.mp4 v3.mp4 v4.mp4
  python world_mix.py --audio dance16.mp4 --every 3 --original dance16.mp4 v1.mp4 v2.mp4   # starts with the real clip

--every: seconds per world (match the beat: 60 / bpm x beats, e.g. 120 bpm, 8 beats = 4 s).
--audio: the clip whose sound to use (normally your driving clip). Output: tall 1080 x 1920 MP4.
"""
import argparse, os, shutil, subprocess, sys, tempfile


def run(cmd):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if r.returncode:
        sys.exit(f'  !!  ffmpeg failed: {r.stderr[-1500:]}')
    return r.stdout


def duration(p):
    return float(run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]).strip())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('versions', nargs='+', help='motion-transfer results of the same clip, in the order to show')
    ap.add_argument('--every', type=float, default=4.0, help='seconds per version before the next cut')
    ap.add_argument('--original', help='the real driving clip, shown first (a "real vs. animated" opener)')
    ap.add_argument('--audio', help='take the sound from this file (default: the first version)')
    ap.add_argument('--size', default='1080x1920')
    ap.add_argument('--fps', type=int, default=24)
    ap.add_argument('--out', default='world_mix.mp4')
    a = ap.parse_args()

    W, H = (int(v) for v in a.size.split('x'))
    order = ([a.original] if a.original else []) + a.versions
    for p in order:
        if not os.path.isfile(p):
            sys.exit(f'  !!  not found: {p}')
    total = min(duration(p) for p in order)
    tmp = tempfile.mkdtemp(prefix='worldmix_')
    try:
        parts, t, k = [], 0.0, 0
        while t < total - 0.05:
            d = min(a.every, total - t)
            src = order[k % len(order)]
            part = os.path.join(tmp, f'{k:03d}.mp4')
            run(['ffmpeg', '-y', '-v', 'error', '-i', src, '-ss', f'{t:.3f}', '-t', f'{d:.3f}', '-an', '-vf',
                 f'scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},fps={a.fps}',
                 '-c:v', 'libx264', '-crf', '16', '-preset', 'fast', '-pix_fmt', 'yuv420p', part])
            parts.append(part)
            print(f'  ..  {t:5.1f}-{t + d:5.1f}s  {os.path.basename(src)}')
            t += d
            k += 1
        lst = os.path.join(tmp, 'list.txt')
        open(lst, 'w').writelines(f"file '{p}'\n" for p in parts)
        video = os.path.join(tmp, 'video.mp4')
        run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', video])
        audio_src = a.audio or a.versions[0]
        has_audio = bool(run(['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=index',
                              '-of', 'csv=p=0', audio_src]).strip())
        cmd = ['ffmpeg', '-y', '-v', 'error', '-i', video]
        if has_audio:
            cmd += ['-i', audio_src, '-map', '0:v', '-map', '1:a', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11',
                    '-c:a', 'aac', '-b:a', '192k']
        cmd += ['-t', f'{total:.3f}', '-c:v', 'copy', '-movflags', '+faststart', a.out]
        run(cmd)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f'  OK  {a.out}  ({total:.1f} s, {len(parts)} cuts, {"with" if has_audio else "no"} sound)')


if __name__ == '__main__':
    main()
