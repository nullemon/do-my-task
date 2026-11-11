"""Expressive re-performance of the skit lines with Chatterbox, using each character's synthetic reference voice."""
import sys, torch, torchaudio as ta
from chatterbox.tts import ChatterboxTTS

OUT = "/tmp/claude-0/-home-user-do-my-task/2bcae0ac-8e61-53db-a931-9dcf67a790bf/scratchpad/cbx_out"
torch.manual_seed(int(sys.argv[1]) if len(sys.argv) > 1 else 7)
tag = sys.argv[2] if len(sys.argv) > 2 else "t1"
m = ChatterboxTTS.from_pretrained(device="cpu")

# (file, character, text, exaggeration = emotion strength, cfg_weight = pacing/adherence)
LINES = [
    ("kakashi",  "kakashi", "Oh, nice. They built a new HQ.",                          0.45, 0.5),
    ("sasuke1",  "sasuke",  "Wait... wasn't this blue yesterday?",                     0.6,  0.45),
    ("sasuke2",  "sasuke",  "Okay. WHO keeps doing this?!",                             1.0,  0.3),
    ("kakashi2", "kakashi", "Hmmm? Doing what?",                                        0.55, 0.45),
    ("naruto",   "naruto",  "Orange looks WAY better! Right?!",                         1.1,  0.3),
    ("obito",    "obito",   "Heh heh heh... Sold the same tower... to four different villages.", 0.75, 0.4),
]
only = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else None
for f, who, text, ex, cfg in LINES:
    if only and f not in only: continue
    wav = m.generate(text, audio_prompt_path=f"{OUT}/ref_{who}.wav", exaggeration=ex, cfg_weight=cfg)
    ta.save(f"{OUT}/{f}_{tag}.wav", wav, m.sr)
    print(f, tag, round(wav.shape[-1] / m.sr, 2), flush=True)
