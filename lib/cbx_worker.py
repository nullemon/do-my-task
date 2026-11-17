"""Runs inside the Chatterbox environment.  python cbx_worker.py jobs.json
jobs.json: {"exaggeration":0.6,"cfg":0.45,"seed":7,"jobs":[{"text":..., "out":...}, ...]}  -> writes 24 kHz wavs"""
import json, sys, os, torch, torchaudio
torch.set_num_threads(os.cpu_count() or 4)
from chatterbox.tts import ChatterboxTTS
spec = json.load(open(sys.argv[1]))
dev = "cuda" if torch.cuda.is_available() else "cpu"
m = ChatterboxTTS.from_pretrained(device=dev)
ref = spec.get("voice_ref")
for j in spec["jobs"]:
    if os.path.exists(j["out"]) and not spec.get("force"): continue
    torch.manual_seed(spec.get("seed", 7))
    kw = dict(exaggeration=spec.get("exaggeration", 0.6), cfg_weight=spec.get("cfg", 0.45))
    if ref: kw["audio_prompt_path"] = ref
    wav = m.generate(j["text"], **kw)
    torchaudio.save(j["out"], wav, m.sr); print("done", os.path.basename(j["out"]), flush=True)
