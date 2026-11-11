import torch, torchaudio as ta
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
SP = "/tmp/claude-0/-home-user-do-my-task/2bcae0ac-8e61-53db-a931-9dcf67a790bf/scratchpad"
m = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
# cfg_weight=0 -> stops the English reference accent from bleeding into German
LINES = [
    ("naruto",   "naruto",  "Orange sieht viel besser aus! Oder?!",               0.9, 0.4),
    ("obito",    "obito",   "Hehe... den gleichen Turm an vier Dörfer verkauft.", 0.75, 0.4),
    ("kakashi",  "kakashi", "Ooh, nett! Die haben ein neues Hauptquartier gebaut!", 0.9, 0.4),
    ("kakashi2", "kakashi", "Hmm? Was denn?",                                     0.9, 0.4),
]
for seed in [5, 13, 77]:
    torch.manual_seed(seed)
    for f, who, text, ex, cfg in LINES:
        wav = m.generate(text, language_id="de", audio_prompt_path=f"{SP}/cbx_out/ref_de_{who}.wav", exaggeration=ex, cfg_weight=cfg)
        ta.save(f"{SP}/cbx_de/{f}_g{seed}.wav", wav, m.sr)
        print(f, seed, round(wav.shape[-1] / m.sr, 2), flush=True)
