import sys, torch, torchaudio as ta
from chatterbox.tts import ChatterboxTTS
OUT = "/tmp/claude-0/-home-user-do-my-task/2bcae0ac-8e61-53db-a931-9dcf67a790bf/scratchpad/cbx_out"
m = ChatterboxTTS.from_pretrained(device="cpu")
# no ALL-CAPS anywhere (caps get spelled out as letters); emphasis comes from punctuation + exaggeration
LINES = [
    ("sasuke2",  "sasuke",  "Okay... who keeps doing this?!",      1.5, 0.25),
    ("kakashi",  "kakashi", "Ooh, nice! They built a new HQ!",     1.0, 0.35),
    ("kakashi2", "kakashi", "Hmmm?! Doing what?!",                 1.0, 0.3),
]
for seed in [3, 11, 29, 57]:
    torch.manual_seed(seed)
    for f, who, text, ex, cfg in LINES:
        wav = m.generate(text, audio_prompt_path=f"{OUT}/ref_{who}.wav", exaggeration=ex, cfg_weight=cfg)
        ta.save(f"{OUT}/{f}_d{seed}.wav", wav, m.sr)
        print(f, seed, round(wav.shape[-1] / m.sr, 2), flush=True)
