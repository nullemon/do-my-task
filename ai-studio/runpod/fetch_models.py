"""Download model packs from ../models.json into ComfyUI/models with aria2 (parallel, resumable).

  python fetch_models.py --comfy /workspace/ComfyUI --packs image video motion
Set HF_TOKEN if a Hugging Face file needs a login. Safe to re-run: finished files are skipped.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile

here = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--comfy', required=True)
ap.add_argument('--packs', nargs='+', required=True)
ap.add_argument('--dry-run', action='store_true')
a = ap.parse_args()

manifest = json.load(open(os.path.join(here, '..', 'models.json')))
files, need_gb = {}, 0
for p in a.packs:
    if p not in manifest:
        print(f'  !!  unknown pack "{p}" (choose from: {", ".join(manifest)})')
        continue
    need_gb += manifest[p].get('approxGB', 0)
    for m in manifest[p]['models']:
        files.setdefault(os.path.join(a.comfy, 'models', m['dir'], m['name']), m['url'])

done = lambda d: os.path.exists(d) and not os.path.exists(d + '.aria2')
todo = [(d, u) for d, u in files.items() if not done(d)]
free_gb = shutil.disk_usage(os.path.dirname(os.path.abspath(a.comfy))).free / 1e9
print(f'  {len(files)} files in {len(a.packs)} pack(s), {len(files) - len(todo)} already here, '
      f'{len(todo)} to download (packs total about {need_gb} GB, {free_gb:.0f} GB free)')
if todo and free_gb < need_gb * 0.6:
    print('  !!  the volume looks too small for these packs; make it bigger or pass fewer packs')
if not todo or a.dry_run:
    sys.exit(0)

token = os.environ.get('HF_TOKEN')
with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as f:
    for dest, url in todo:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        f.write(f'{url}\n  dir={os.path.dirname(dest)}\n  out={os.path.basename(dest)}\n')
        if token and 'huggingface.co' in url:
            f.write(f'  header=Authorization: Bearer {token}\n')
    listfile = f.name
rc = subprocess.call(['aria2c', '-i', listfile, '-j', '4', '-x', '16', '-s', '16', '-c',
                      '--auto-file-renaming=false', '--allow-overwrite=true', '--file-allocation=none',
                      '--max-tries=10', '--retry-wait=5', '--console-log-level=warn',
                      '--summary-interval=60', '--download-result=hide'])
os.unlink(listfile)
failed = [u for d, u in todo if not done(d)]
if failed:
    print(f'  !!  {len(failed)} download(s) did not finish; run the setup command again to resume:')
    for u in failed:
        print('      ' + u)
    print('      (401/403 means: accept the license on that Hugging Face page and set HF_TOKEN)')
    sys.exit(1)
print('  OK  all model files are here')
