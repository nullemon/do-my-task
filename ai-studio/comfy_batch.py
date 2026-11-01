"""Spread many ComfyUI jobs across several ComfyUI servers at once (one server per GPU).

  python comfy_batch.py --jobs jobs.json --auto          # finds servers on 127.0.0.1:8188..8197
  python comfy_batch.py --jobs jobs.json --servers https://<podId>-8188.proxy.runpod.net,https://<podId>-8189.proxy.runpod.net

jobs.json is a list of jobs:
  [{"name": "rusty_walk_1",
    "workflow": "workflows/video_wan_animate2.json",
    "set": {"6.text": "an old golden retriever walking in the rain"},
    "upload": {"57.image": "inputs/rusty.png", "63.file": "inputs/dog_walk.mp4"},
    "random_seed": true,
    "out": "outputs/rusty_walk_1"}]

Each server takes the next waiting job as soon as it finishes the previous one, so 4 GPUs finish
a queue about 4x sooner for the same total GPU-hours.
"""
import argparse, json, os, queue, sys, threading, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comfy_run import run_job  # noqa: E402


def alive(server):
    try:
        with urllib.request.urlopen(server + '/system_stats', timeout=5):
            return True
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--jobs', required=True)
    ap.add_argument('--servers', default='', help='comma-separated server URLs')
    ap.add_argument('--auto', action='store_true', help='use every ComfyUI found on 127.0.0.1:8188-8197')
    ap.add_argument('--timeout', type=int, default=7200, help='seconds per job')
    a = ap.parse_args()

    servers = [s.strip().rstrip('/') for s in a.servers.split(',') if s.strip()]
    if a.auto:
        servers += [f'http://127.0.0.1:{p}' for p in range(8188, 8198) if alive(f'http://127.0.0.1:{p}')]
    servers = [s for s in dict.fromkeys(servers) if alive(s)]
    if not servers:
        sys.exit('No ComfyUI server answered. Start them first (runpod/start.sh or start-comfyui.ps1).')

    jobs = json.load(open(a.jobs, encoding='utf-8'))
    base = os.path.dirname(os.path.abspath(a.jobs))
    rel = lambda p: p if os.path.isabs(p) else os.path.join(base, p)
    work = queue.Queue()
    for i, job in enumerate(jobs):
        job.setdefault('name', f'job{i + 1}')
        work.put(job)
    print(f'{len(jobs)} jobs on {len(servers)} server(s): {", ".join(servers)}')

    results, lock = [], threading.Lock()

    def worker(server):
        while True:
            try:
                job = work.get_nowait()
            except queue.Empty:
                return
            t0 = time.time()
            say = lambda m: print(f'[{job["name"]}] {m}', flush=True)
            try:
                saved = run_job(server, rel(job['workflow']), job.get('set'),
                                {k: rel(v) for k, v in job.get('upload', {}).items()},
                                job.get('random_seed', False), rel(job.get('out', f'outputs/{job["name"]}')),
                                a.timeout, say)
                row = {'name': job['name'], 'server': server, 'ok': True, 'seconds': round(time.time() - t0), 'files': saved}
            except Exception as e:  # keep the other jobs going
                row = {'name': job['name'], 'server': server, 'ok': False, 'seconds': round(time.time() - t0), 'error': str(e)[:500]}
                say(f'FAILED: {row["error"]}')
            with lock:
                results.append(row)

    t0 = time.time()
    threads = [threading.Thread(target=worker, args=(s,)) for s in servers]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f'\nFinished in {time.time() - t0:.0f}s')
    for r in sorted(results, key=lambda r: r['name']):
        status = f"{len(r['files'])} file(s)" if r['ok'] else 'FAILED'
        print(f"  {r['name']:30s} {r['seconds']:>6}s  {status}")
    out = os.path.join(base, 'batch_results.json')
    json.dump(results, open(out, 'w'), indent=2)
    print('details:', out)
    sys.exit(0 if all(r['ok'] for r in results) else 1)


if __name__ == '__main__':
    main()
