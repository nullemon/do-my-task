"""python3 stt.py file.mp4 [t0] [t1] [win]  -> prints '[start] text' per window (whisper small.en)"""
import sys, subprocess, numpy as np, sherpa_onnx, os
B = os.path.dirname(os.path.abspath(__file__)) + "/stt/sherpa-onnx-whisper-small.en/"
rec = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=B + "small.en-encoder.int8.onnx", decoder=B + "small.en-decoder.int8.onnx", tokens=B + "small.en-tokens.txt", num_threads=4)
f = sys.argv[1]; t0 = float(sys.argv[2]) if len(sys.argv) > 2 else 0; t1 = float(sys.argv[3]) if len(sys.argv) > 3 else 1e9; win = float(sys.argv[4]) if len(sys.argv) > 4 else 10
args = ["ffmpeg", "-v", "error", "-ss", str(t0)] + (["-t", str(t1 - t0)] if t1 < 1e8 else []) + ["-i", f, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"]
a = np.frombuffer(subprocess.run(args, capture_output=True).stdout, np.float32)
n = int(win * 16000)
for k in range(0, len(a), n):
    s = rec.create_stream(); s.accept_waveform(16000, a[k:k + n]); rec.decode_stream(s)
    print(f"[{t0 + k / 16000:.0f}] {s.result.text.strip()}", flush=True)
