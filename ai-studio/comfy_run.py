"""Run a ComfyUI workflow headlessly through its local API (standard library only).

The workflow must be in API format: in ComfyUI open the template, then Workflow -> Export (API).

  python comfy_run.py --workflow workflows/wan_animate2.json --list
  python comfy_run.py --workflow workflows/wan_animate2.json \
      --upload 57.image=inputs/rusty.png --upload 63.file=inputs/dog_walk.mp4 \
      --set "6.text=a golden retriever walking in the rain, cinematic" --random-seed --out outputs/

With the portable build, run it with ComfyUI's own Python:
  C:\\AI\\ComfyUI_windows_portable\\python_embeded\\python.exe ai-studio\\comfy_run.py ...
"""
import argparse, json, mimetypes, os, random, sys, time, urllib.parse, urllib.request, uuid


def call(server, path, data=None, headers=None, raw=False):
    req = urllib.request.Request(server + path, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=120) as r:
        body = r.read()
    return body if raw else json.loads(body)


def upload(server, path):
    boundary = uuid.uuid4().hex
    name = os.path.basename(path)
    ctype = mimetypes.guess_type(name)[0] or 'application/octet-stream'
    with open(path, 'rb') as f:
        payload = f.read()
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\n'
            f'Content-Type: {ctype}\r\n\r\n').encode() + payload + \
           f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n--{boundary}--\r\n'.encode()
    res = call(server, '/upload/image', body, {'Content-Type': f'multipart/form-data; boundary={boundary}'})
    return res['name'] if not res.get('subfolder') else f"{res['subfolder']}/{res['name']}"


def parse_value(v):
    try:
        return json.loads(v)
    except ValueError:
        return v


def run_job(server, workflow, sets=None, uploads=None, random_seed=False, out='outputs', timeout=3600, log=print):
    """Queue one API-format workflow on a ComfyUI server, wait for it, download its outputs.
    workflow: path or dict. sets: {"NODE.input": value}. uploads: {"NODE.input": "local/file"}."""
    wf = json.load(open(workflow, encoding='utf-8')) if isinstance(workflow, str) else json.loads(json.dumps(workflow))
    if 'nodes' in wf:
        raise ValueError('UI-format workflow: in ComfyUI use Workflow -> Export (API) and pass that file.')
    for key, path in (uploads or {}).items():
        nid, inp = key.split('.', 1)
        wf[nid]['inputs'][inp] = upload(server, path)
    for key, val in (sets or {}).items():
        nid, inp = key.split('.', 1)
        wf[nid]['inputs'][inp] = val
    if random_seed:
        for node in wf.values():
            for k in ('seed', 'noise_seed'):
                if k in node['inputs'] and not isinstance(node['inputs'][k], list):
                    node['inputs'][k] = random.randint(0, 2**48)
    pid = call(server, '/prompt', json.dumps({'prompt': wf, 'client_id': uuid.uuid4().hex}).encode(),
               {'Content-Type': 'application/json'})['prompt_id']
    log(f'queued {pid} on {server}')
    t0 = time.time()
    while True:
        hist = call(server, f'/history/{pid}')
        if pid in hist:
            break
        if time.time() - t0 > timeout:
            raise TimeoutError(f'{pid} timed out after {timeout}s')
        time.sleep(2)
    entry = hist[pid]
    status = entry.get('status', {})
    if status.get('status_str') == 'error':
        raise RuntimeError('ComfyUI reported an error: ' + json.dumps(status.get('messages', []))[:2000])
    os.makedirs(out, exist_ok=True)
    saved = []
    for node_out in entry.get('outputs', {}).values():
        for files in node_out.values():
            if not isinstance(files, list):
                continue
            for f in files:
                if isinstance(f, dict) and 'filename' in f and f.get('type') == 'output':
                    q = urllib.parse.urlencode({'filename': f['filename'], 'subfolder': f.get('subfolder', ''), 'type': 'output'})
                    dest = os.path.join(out, f['filename'])
                    with open(dest, 'wb') as fh:
                        fh.write(call(server, '/view?' + q, raw=True))
                    saved.append(dest)
    log(f'done {pid} in {time.time() - t0:.0f}s')
    return saved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--server', default='http://127.0.0.1:8188')
    ap.add_argument('--workflow', required=True)
    ap.add_argument('--set', action='append', default=[], help='NODE.input=value (JSON or text)')
    ap.add_argument('--upload', action='append', default=[], help='NODE.input=local/file (image or video)')
    ap.add_argument('--random-seed', action='store_true')
    ap.add_argument('--out', default='outputs')
    ap.add_argument('--list', action='store_true', help='print node ids and inputs, then exit')
    ap.add_argument('--timeout', type=int, default=3600)
    a = ap.parse_args()

    if a.list:
        wf = json.load(open(a.workflow, encoding='utf-8'))
        if 'nodes' in wf:
            sys.exit('This is a UI-format workflow. In ComfyUI use Workflow -> Export (API) and pass that file.')
        for nid, node in sorted(wf.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 0):
            simple = {k: v for k, v in node['inputs'].items() if not isinstance(v, list)}
            print(f"{nid:>5}  {node['class_type']:32s} {json.dumps(simple)[:150]}")
        return
    sets = dict((k, parse_value(v)) for k, v in (item.split('=', 1) for item in a.set))
    uploads = dict(item.split('=', 1) for item in a.upload)
    try:
        saved = run_job(a.server, a.workflow, sets, uploads, a.random_seed, a.out, a.timeout)
    except (ValueError, RuntimeError, TimeoutError) as e:
        sys.exit(str(e))
    for s in saved:
        print('  ', s)


if __name__ == '__main__':
    main()
