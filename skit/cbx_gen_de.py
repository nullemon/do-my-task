"""German performances via Chatterbox multilingual, same character reference voices."""
import torch, torchaudio as ta
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
SP = "/tmp/claude-0/-home-user-do-my-task/2bcae0ac-8e61-53db-a931-9dcf67a790bf/scratchpad"
m = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
LINES = [  # no all-caps; emphasis via punctuation + exaggeration
    ("kakashi",  "kakashi", "Ooh, nett! Die haben ein neues Hauptquartier gebaut!", 1.0, 0.35),
    ("sasuke1",  "sasuke",  "Moment... war das gestern nicht blau?",                0.6, 0.45),
    ("sasuke2",  "sasuke",  "Okay... wer macht das ständig?!",                      1.5, 0.25),
    ("kakashi2", "kakashi", "Hmmm? Was denn?",                                      1.0, 0.3),
    ("naruto",   "naruto",  "Orange sieht viel besser aus! Oder?!",                 1.1, 0.3),
    ("obito",    "obito",   "Hehe... denselben Turm an vier verschiedene Dörfer verkauft.", 0.75, 0.4),
]
for seed in [7, 21, 42]:
    torch.manual_seed(seed)
    for f, who, text, ex, cfg in LINES:
        wav = m.generate(text, language_id="de", audio_prompt_path=f"{SP}/cbx_out/ref_{who}.wav", exaggeration=ex, cfg_weight=cfg)
        ta.save(f"{SP}/cbx_de/{f}_s{seed}.wav", wav, m.sr)
        print(f, seed, round(wav.shape[-1] / m.sr, 2), flush=True)
