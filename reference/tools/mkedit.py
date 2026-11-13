"""mkedit.py DIR spec.json : writes DIR/edit.py. Shots reference (clip, sheet_index) with 12-frame sheets -> time."""
import sys, json, subprocess
d = sys.argv[1]; spec = json.load(open(sys.argv[2]))
L = lambda c: float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f"{d}/cl/{c}.mp4"]))
def T(c, k, n=12): return round(L(c) / n * (k + 0.5), 1)
out = ["CLIPS = {"] + [f'    "{c}": ({tuple(v[0])}, "{v[1]}"),' for c, v in spec["clips"].items()] + ["}", 'G = ("gfx",)', "SHOTS = {"]
for i, shots in spec["shots"].items():
    parts = []
    for s in shots:
        if s[1] == "G": parts.append(f"({s[0]}, G)")
        else: parts.append(f'({s[0]}, ("clip", "{s[1]}", {T(s[1], s[2]) if len(s) < 4 else s[3]}))')
    out.append(f"    {i}: [{', '.join(parts)}],")
out += ["}", "INTERLUDES = " + repr({int(k): tuple(v) for k, v in spec.get("inter", {}).items()}), "BG = ["]
for a, b, c, t in spec["bg"]: out.append(f'    (range({a}, {b}), "{c}", {t}),')
out += ["]", "def bg_for(i):", "    for r, c, t in BG:", "        if i in r: return c, t", "    return None, 0"]
open(f"{d}/edit.py", "w").write("\n".join(out) + "\n")
