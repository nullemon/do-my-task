"""
GRAVITY SYNCED TO MUSIC  -  planet-sims #05
============================================
A cosy living room (sofa, table, sideboard, books, cups, balls, cushions,
records, plants, a speaker ... ~40 rigid bodies).  The script analyses a song
and drives the rigid-body gravity with it:

    quiet passages  ->  gravity flips slightly UP (Pluto strength, 0.62 m/s^2)
                        and everything drifts off the floor
    loud passages   ->  normal Earth gravity (9.81)
    every strong beat -> a short spike to JUPITER (24.79) and on the biggest
                        drop(s) to the SUN (274.0): everything slams down.

The song is added as a sound strip in the Video Sequencer, so playback and
renders (MP4 + AAC) include the music.  A HUD shows the gravity level live,
e.g. "PLUTO 0.62 m/s²  FLOATING" / "JUPITER 24.79 m/s²  BEAT!".

How to use
----------
* Blender >= 4.2: open the Scripting tab, open this file, set AUDIO_PATH, press Run.
  Press play (with audio sync) in the timeline - the physics is baked.
* Headless:  blender -b -P gravity_music_sync.py -- --render  [--audio song.wav]
             blender -b -P gravity_music_sync.py -- --preview (few low-res Cycles stills)
* No AUDIO_PATH?  A ~20 s demo track (pad, riser, drop, kicks) is generated next
  to the script as  gms_demo_track.wav  and used.
* MP3: Blender can usually decode it itself (audaspace).  If not, convert:
      ffmpeg -i song.mp3 -ac 2 -ar 44100 song.wav
"""

# =============================================================================
# CONFIG
# =============================================================================
AUDIO_PATH = ""            # "" -> generate demo track. WAV best; MP3/FLAC/OGG via Blender's decoder
AUDIO_OFFSET_S = 0.0       # start analysing/playing the song this many seconds in
SECONDS = 20.0             # clip length (clamped to song length)
FPS = 30
RESOLUTION = (1080, 1920)  # vertical 9:16
ENGINE = "EEVEE"           # "EEVEE" or "CYCLES" for the final render
CYCLES_SAMPLES = 96
EEVEE_SAMPLES = 64
RENDER = False             # True = render the full clip after building (same as --render)
PREVIEW = False            # True = render low-res Cycles stills (same as --preview)
OUTPUT_DIR = "//renders/gravity_music_sync/"   # relative to the .blend (or the script dir if unsaved)
OUTPUT_AS_MP4 = True       # MP4 (H.264 + AAC music) if FFmpeg is available, else PNG frames

# Planet levels the HUD can name (m/s^2).  Real values.
PLANETS = {
    "PLUTO": 0.62, "MOON": 1.62, "MERCURY": 3.70, "MARS": 3.71, "URANUS": 8.69,
    "VENUS": 8.87, "EARTH": 9.81, "SATURN": 10.44, "NEPTUNE": 11.15,
    "JUPITER": 24.79, "SUN": 274.0,
}
HUD_PLANETS = ["PLUTO", "MOON", "MARS", "EARTH", "JUPITER", "SUN"]  # which ones the HUD snaps to

# --- gravity mapping --------------------------------------------------------
QUIET_PLANET = "PLUTO"     # quiet  -> this strength, pointing UP (objects drift up)
LOUD_PLANET = "EARTH"      # loud   -> this strength, pointing down
BEAT_PLANET = "JUPITER"    # normal beat hit
DROP_PLANET = "SUN"        # strongest hits (beat drops)
DROP_STRENGTH = 0.80       # hits with bass punch >= this fraction of the max ...
DROP_AFTER_GAP_S = 1.5     # ... that also follow >= this many seconds without hits are "drops"
QUIET_LEVEL = 0.30         # normalised loudness below this = fully quiet (float)
LOUD_LEVEL = 0.80          # normalised loudness above this = fully loud (Earth)
DYNAMIC_RANGE_DB = 24.0    # loudness scale: 'fully quiet' = this many dB below the loudest parts
FLOAT_PERIOD_S = 6.0       # quiet gravity breathes: up for ~1/4 of this, then a gentle sink ...
FLOAT_SINK = 0.35          # ... at this fraction of the quiet strength, then up again
BEAT_HOLD_FRAMES = 7       # frames gravity stays at BEAT_PLANET after a hit
DROP_HOLD_FRAMES = 4       # frames gravity stays at DROP_PLANET after a drop
SETTLE_FRAMES = 3          # frames of Earth gravity after a hit before easing back

# --- beat detection ---------------------------------------------------------
MIN_BEAT_GAP_S = 0.30      # minimum time between two detected hits
ONSET_SENSITIVITY = 2.0    # higher = fewer hits (threshold = local mean + k * std)
MIN_ONSET_FRACTION = 0.25  # ignore onsets weaker than this fraction of the strongest
LOW_BAND_HZ = 180.0        # kick band (weighted extra in the onset function)

# --- physics ----------------------------------------------------------------
SUBSTEPS = 30              # rigid body substeps per frame (Sun gravity needs many)
SOLVER_ITERATIONS = 30
LINEAR_DAMPING = 0.45      # keeps the float gentle (terminal drift ~1 m/s)
ANGULAR_DAMPING = 0.35
TURBULENCE = 1.2           # gentle swirling during quiet parts (0 = off)
CAMERA_SHAKE = 0.035       # metres of shake on drops (0 = off)
PUSH_IN = 0.9              # metres the camera dollies in over the clip
SEED = 7

SCENE_NAME = "05_GravitySync"
PREFIX = "GMS_"

# =============================================================================
import bpy, bmesh, math, os, sys, random, wave, struct, time
import numpy as np
from mathutils import Vector, Euler, Matrix

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if "--render" in ARGS:
    RENDER = True
if "--preview" in ARGS:
    PREVIEW = True
if "--audio" in ARGS:
    AUDIO_PATH = ARGS[ARGS.index("--audio") + 1]
if "--seconds" in ARGS:
    SECONDS = float(ARGS[ARGS.index("--seconds") + 1])
if "--engine" in ARGS:
    ENGINE = ARGS[ARGS.index("--engine") + 1].upper()


def script_dir():
    if bpy.data.filepath:
        return os.path.dirname(bpy.path.abspath(bpy.data.filepath))
    f = globals().get("__file__", "")
    if f and os.path.isfile(f):
        return os.path.dirname(os.path.abspath(f))
    for t in bpy.data.texts:  # run from the Text Editor
        if t.filepath and os.path.basename(t.filepath) == "gravity_music_sync.py":
            return os.path.dirname(bpy.path.abspath(t.filepath))
    return os.getcwd()


def out_dir():
    p = OUTPUT_DIR
    if p.startswith("//"):
        p = os.path.join(script_dir(), p[2:])
    return os.path.abspath(p)


# =============================================================================
# DEMO TRACK
# =============================================================================
def make_demo_track(path, sr=44100, dur=20.0):
    """Quiet pad -> single hit -> pad -> riser -> big DROP -> kicks -> pad outro."""
    rng = np.random.default_rng(3)
    n = int(sr * dur)
    t = np.arange(n) / sr
    out = np.zeros(n)

    # warm pad: A minor-ish chord, detuned sines with soft harmonics + slow tremolo
    pad = np.zeros(n)
    for f in (110.0, 130.81, 164.81, 220.0, 261.63):
        for det in (-0.6, 0.6):
            ff = f + det
            pad += np.sin(2 * np.pi * ff * t) + 0.3 * np.sin(4 * np.pi * ff * t + 1.0)
    pad *= 0.012 * (0.85 + 0.15 * np.sin(2 * np.pi * 0.25 * t))
    pad *= np.clip(t / 1.5, 0, 1) * np.clip((dur - t) / 1.0, 0, 1)
    out += pad

    def add(sig, start):
        fade = min(len(sig), int(0.03 * sr))     # no clicks at the tail
        sig = sig.copy()
        sig[-fade:] *= np.linspace(1, 0, fade)
        i = int(start * sr)
        j = min(n, i + len(sig))
        out[i:j] += sig[: j - i]

    def kick(amp=0.9, length=0.45):
        k = np.arange(int(length * sr)) / sr
        freq = 45 + 110 * np.exp(-k * 28)
        ph = 2 * np.pi * np.cumsum(freq) / sr
        click = rng.standard_normal(len(k)) * np.exp(-k * 300) * 0.4
        return amp * (np.sin(ph) * np.exp(-k * 7) + click)

    def crash(amp=0.35, length=1.6):
        k = np.arange(int(length * sr)) / sr
        noise = rng.standard_normal(len(k))
        noise = np.diff(noise, prepend=0)  # brighter
        return amp * noise * np.exp(-k * 2.5)

    def sub(amp=0.5, length=0.9, f=55.0):
        k = np.arange(int(length * sr)) / sr
        return amp * np.sin(2 * np.pi * f * k) * np.exp(-k * 3.5)

    # 4.5 s: first hit (Jupiter)
    add(kick(0.75), 4.5)
    add(crash(0.12, 1.0), 4.5)
    # 8.5 - 11 s: riser (noise + rising tone, getting louder) -> Earth gravity
    rs, re_ = 8.5, 11.0
    i0, i1 = int(rs * sr), int(re_ * sr)
    k = np.arange(i1 - i0) / sr
    prog = k / (re_ - rs)
    noise = rng.standard_normal(len(k))
    noise = np.convolve(noise, np.ones(8) / 8, mode="same")
    tone = np.sin(2 * np.pi * np.cumsum(200 + 900 * prog ** 2) / sr)
    out[i0:i1] += (0.05 * prog ** 2) * (0.6 * noise + 0.4 * tone)   # soft riser: still 'quiet'
    # 11 s: THE DROP (Sun)
    add(kick(1.0, 0.6), 11.0)
    add(sub(0.6, 1.2), 11.0)
    add(crash(0.45, 2.0), 11.0)
    # 12.4 - 16.6 s: half-time kicks every 1.05 s with short sub tails (Jupiter hits)
    for bt in np.arange(12.4, 16.7, 1.05):
        add(kick(0.7), bt)
        add(sub(0.25, 0.4), bt)
    # outro: pad only (float again)

    out /= max(1e-9, np.max(np.abs(out))) / 0.89
    pcm = (np.clip(out, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return path


# =============================================================================
# AUDIO ANALYSIS (numpy only)
# =============================================================================
def load_audio(path):
    """Returns (mono float32 samples, sample rate). WAV via `wave`, else Blender's audaspace."""
    if path.lower().endswith(".wav"):
        try:
            with wave.open(path, "rb") as w:
                ch, sw, sr, nfr = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
                raw = w.readframes(nfr)
            if sw == 1:
                a = (np.frombuffer(raw, np.uint8).astype(np.float32) - 128) / 128
            elif sw == 2:
                a = np.frombuffer(raw, "<i2").astype(np.float32) / 32768
            elif sw == 3:
                b = np.frombuffer(raw, np.uint8).reshape(-1, 3).astype(np.int32)
                v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
                v = np.where(v >= 1 << 23, v - (1 << 24), v)
                a = v.astype(np.float32) / (1 << 23)
            else:
                a = np.frombuffer(raw, "<i4").astype(np.float32) / 2147483648.0
            a = a.reshape(-1, ch).mean(axis=1)
            return a, sr
        except wave.Error:
            pass  # e.g. float WAV -> try audaspace
    import aud
    snd = aud.Sound(path)
    sr = int(snd.specs[0])
    data = np.asarray(snd.data(), dtype=np.float32)
    if data.ndim == 2:
        data = data.mean(axis=1)
    return data, sr


def analyse(path, fps, seconds, offset):
    y, sr = load_audio(path)
    y = y[int(offset * sr):]
    seconds = min(seconds, len(y) / sr)
    y = y[: int(seconds * sr)]
    nframes = int(round(seconds * fps))

    # --- RMS envelope, one value per video frame (fast attack, ~0.12 s release)
    spf = sr / fps
    rms = np.zeros(nframes)
    for f in range(nframes):
        seg = y[int(f * spf): int((f + 1) * spf)]
        rms[f] = np.sqrt(np.mean(seg ** 2)) if len(seg) else 0.0
    db = 20 * np.log10(rms + 1e-6)
    env = np.copy(db)
    rel = math.exp(-1.0 / (0.12 * fps))
    for f in range(1, nframes):
        env[f] = db[f] if db[f] > env[f - 1] else rel * env[f - 1] + (1 - rel) * db[f]
    hi = np.percentile(env, 97)
    lo = max(np.percentile(env, 5), hi - DYNAMIC_RANGE_DB)
    loud = np.clip((env - lo) / max(1e-6, hi - lo), 0, 1)

    # --- onset strength: log-spectral flux, kick band weighted x3
    nfft, hop = 2048, 512
    win = np.hanning(nfft)
    pad = np.concatenate([np.zeros(nfft // 2), y, np.zeros(nfft)])
    nh = (len(pad) - nfft) // hop
    idx = np.arange(nfft)[None, :] + hop * np.arange(nh)[:, None]
    mag = np.abs(np.fft.rfft(pad[idx] * win, axis=1))
    logm = np.log1p(1000 * mag)
    freqs = np.fft.rfftfreq(nfft, 1 / sr)
    w = np.where(freqs < LOW_BAND_HZ, 3.0, 1.0)
    w[freqs > 8000] = 0.3
    flux = np.concatenate([[0], (np.maximum(0, np.diff(logm, axis=0)) * w).sum(axis=1)])
    flux /= max(1e-9, flux.max())
    tt = np.arange(nh) * hop / sr
    # adaptive threshold
    L = max(1, int(1.0 * sr / hop))
    kern = np.ones(2 * L + 1) / (2 * L + 1)
    loc_mean = np.convolve(flux, kern, mode="same")
    loc_sq = np.convolve(flux ** 2, kern, mode="same")
    loc_std = np.sqrt(np.maximum(0, loc_sq - loc_mean ** 2))
    thr = np.maximum(loc_mean + ONSET_SENSITIVITY * loc_std, MIN_ONSET_FRACTION)
    G = max(1, int(MIN_BEAT_GAP_S * sr / hop))
    cand = [i for i in range(1, nh - 1)
            if flux[i] >= thr[i] and flux[i] == flux[max(0, i - G): i + G + 1].max()]
    # hit strength = linear low-band energy in the 120 ms after the onset (the "punch")
    lowband = (mag[:, freqs < LOW_BAND_HZ] ** 2).sum(axis=1)
    A = max(1, int(0.12 * sr / hop))
    beats = []
    for i in cand:
        if beats and tt[i] - beats[-1][0] < MIN_BEAT_GAP_S:
            continue
        beats.append((float(tt[i]), float(lowband[i: i + A].mean())))
    smax = max([s for _, s in beats], default=1.0)
    beats = [(bt, s / smax) for bt, s in beats]
    return dict(sr=sr, seconds=seconds, nframes=nframes, loud=loud, env_db=env, beats=beats)


def gravity_curve(an, fps):
    """Signed vertical gravity per frame (m/s^2, + = up) and the reason/state."""
    n = an["nframes"]
    up = PLANETS[QUIET_PLANET]
    down = PLANETS[LOUD_PLANET]
    loud = an["loud"]
    x = np.clip((loud - QUIET_LEVEL) / max(1e-6, LOUD_LEVEL - QUIET_LEVEL), 0, 1)
    x = x * x * (3 - 2 * x)  # smoothstep
    # "breathing" float: each quiet stretch starts with an upward pull, then gently
    # reverses so objects hover mid-room instead of sticking to the ceiling
    qt = np.zeros(n)
    for f in range(1, n):
        qt[f] = qt[f - 1] + 1.0 / fps if x[f] < 0.5 else 0.0
    up_eff = up * np.clip(1.6 * np.cos(2 * np.pi * qt / FLOAT_PERIOD_S), -FLOAT_SINK, 1)
    base = up_eff + (-down - up_eff) * x
    g = base.copy()
    hits = []
    prev_t = -1e9
    for bt, s in an["beats"]:
        f0 = int(round(bt * fps))
        if f0 >= n:
            continue
        drop = s >= DROP_STRENGTH and bt - prev_t >= DROP_AFTER_GAP_S
        prev_t = bt
        hold = DROP_HOLD_FRAMES if drop else BEAT_HOLD_FRAMES
        gh = -PLANETS[DROP_PLANET if drop else BEAT_PLANET]
        hits.append((f0, drop, s))
        for k in range(hold):
            if f0 + k < n:
                g[f0 + k] = min(g[f0 + k], gh)
        for k in range(SETTLE_FRAMES):  # Earth briefly, then ease back to the music
            f = f0 + hold + k
            if f < n:
                g[f] = min(g[f], -down)
        for k in range(6):
            f = f0 + hold + SETTLE_FRAMES + k
            if f < n:
                a = (k + 1) / 7.0
                g[f] = min(g[f], -down * (1 - a) + base[f] * a)
    return g, hits


def nearest_planet(gabs):
    best = None
    for name in HUD_PLANETS:
        v = PLANETS[name]
        d = abs(math.log(max(gabs, 0.05)) - math.log(v))
        if best is None or d < best[0]:
            best = (d, name)
    return best[1]


# =============================================================================
# SCENE HELPERS
# =============================================================================
def clear_previous():
    sc = bpy.data.scenes.get(SCENE_NAME)
    if sc:
        for o in list(sc.objects):
            bpy.data.objects.remove(o, do_unlink=True)
        if len(bpy.data.scenes) == 1:
            sc.name = "tmp_old"
            new = bpy.data.scenes.new("Scene")
            win = getattr(bpy.context, "window", None)
            if win:
                win.scene = new
        bpy.data.scenes.remove(sc)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.curves, bpy.data.lights,
                 bpy.data.cameras, bpy.data.collections, bpy.data.worlds, bpy.data.sounds):
        for d in list(coll):
            if d.name.startswith(PREFIX) and d.users == 0:
                coll.remove(d)


SC = None
COLL = None


def link(o):
    COLL.objects.link(o)
    return o


def new_obj(name, mesh):
    return link(bpy.data.objects.new(PREFIX + name, mesh))


def mat(name, color, rough=0.5, metal=0.0, sheen=0.0, coat=0.0, emit=None, emit_strength=0.0,
        tex=None):
    m = bpy.data.materials.get(PREFIX + name)
    if m:
        return m
    m = bpy.data.materials.new(PREFIX + name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes.get("Principled BSDF")
    def setin(key, val):
        for k in (key if isinstance(key, tuple) else (key,)):
            if k in p.inputs:
                p.inputs[k].default_value = val
                return
    setin("Base Color", (*color, 1))
    setin("Roughness", rough)
    setin("Metallic", metal)
    setin(("Sheen Weight", "Sheen"), sheen)
    setin(("Coat Weight", "Clearcoat"), coat)
    if emit is not None:
        setin(("Emission Color", "Emission"), (*emit, 1))
        setin("Emission Strength", emit_strength)
    m.diffuse_color = (*color, 1)
    if tex:
        tex(nt, p)
    return m


def tex_wood(nt, p):
    """Plank floor: brick texture (long planks) + wave grain."""
    N = nt.nodes
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0, 1.0, 1.0)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    br = N.new("ShaderNodeTexBrick")
    br.inputs["Color1"].default_value = (0.24, 0.11, 0.045, 1)
    br.inputs["Color2"].default_value = (0.34, 0.17, 0.07, 1)
    br.inputs["Mortar"].default_value = (0.05, 0.025, 0.01, 1)
    br.inputs["Scale"].default_value = 1.0
    br.inputs["Mortar Size"].default_value = 0.006
    br.inputs["Brick Width"].default_value = 1.4
    br.inputs["Row Height"].default_value = 0.18
    nt.links.new(mp.outputs["Vector"], br.inputs["Vector"])
    wv = N.new("ShaderNodeTexWave")
    wv.inputs["Scale"].default_value = 3.0
    wv.inputs["Distortion"].default_value = 8.0
    wv.inputs["Detail"].default_value = 4.0
    nt.links.new(mp.outputs["Vector"], wv.inputs["Vector"])
    mix = N.new("ShaderNodeMixRGB")
    mix.blend_type = "MULTIPLY"
    mix.inputs["Fac"].default_value = 0.35
    nt.links.new(br.outputs["Color"], mix.inputs["Color1"])
    nt.links.new(wv.outputs["Color"], mix.inputs["Color2"])
    nt.links.new(mix.outputs["Color"], p.inputs["Base Color"])
    p.inputs["Roughness"].default_value = 0.38


def tex_plaster(nt, p):
    N = nt.nodes
    nz = N.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 40.0
    bump = N.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.05
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])


def tex_rug(nt, p):
    N = nt.nodes
    tc = N.new("ShaderNodeTexCoord")
    wv = N.new("ShaderNodeTexWave")
    wv.wave_type = "RINGS"
    wv.inputs["Scale"].default_value = 2.2
    wv.inputs["Distortion"].default_value = 1.5
    nt.links.new(tc.outputs["Object"], wv.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.55, 0.12, 0.08, 1)
    ramp.color_ramp.elements[1].color = (0.85, 0.62, 0.38, 1)
    nt.links.new(wv.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], p.inputs["Base Color"])


def finalize(bm, name, mats, smooth=False):
    me = bpy.data.meshes.new(PREFIX + name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    if smooth:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    return me


def bm_box(bm, size, center=(0, 0, 0), mi=0):
    r = bmesh.ops.create_cube(bm, size=1.0)
    vs = r["verts"]
    bmesh.ops.scale(bm, vec=size, verts=vs)
    bmesh.ops.translate(bm, vec=center, verts=vs)
    for f in {f for v in vs for f in v.link_faces}:
        f.material_index = mi
    return vs


def bm_cyl(bm, r1, r2, depth, center=(0, 0, 0), seg=32, mi=0, cap=True, rot=None):
    r = bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=seg,
                              radius1=r1, radius2=r2, depth=depth)
    vs = r["verts"]
    if rot:
        bmesh.ops.rotate(bm, verts=vs, cent=(0, 0, 0), matrix=Euler(rot).to_matrix())
    bmesh.ops.translate(bm, vec=center, verts=vs)
    for f in {f for v in vs for f in v.link_faces}:
        f.material_index = mi
        f.smooth = len(f.verts) == 4
    return vs


def bm_sphere(bm, radius, center=(0, 0, 0), scale=(1, 1, 1), mi=0, rot=None, sub=3):
    r = bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=radius)
    vs = r["verts"]
    bmesh.ops.scale(bm, vec=scale, verts=vs)
    if rot:
        bmesh.ops.rotate(bm, verts=vs, cent=(0, 0, 0), matrix=Euler(rot).to_matrix())
    bmesh.ops.translate(bm, vec=center, verts=vs)
    for f in {f for v in vs for f in v.link_faces}:
        f.material_index = mi
        f.smooth = True
    return vs


def bm_torus(bm, R, r, center=(0, 0, 0), rot=(0, 0, 0), seg=16, rseg=8, mi=0):
    rows = []
    M = Euler(rot).to_matrix()
    for i in range(seg):
        a = 2 * math.pi * i / seg
        row = []
        for j in range(rseg):
            b = 2 * math.pi * j / rseg
            p = Vector(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a),
                        r * math.sin(b)))
            row.append(bm.verts.new(M @ p + Vector(center)))
        rows.append(row)
    for i in range(seg):
        for j in range(rseg):
            f = bm.faces.new((rows[i][j], rows[(i + 1) % seg][j], rows[(i + 1) % seg][(j + 1) % rseg],
                              rows[i][(j + 1) % rseg]))
            f.material_index = mi
            f.smooth = True


def bevel(o, w=0.01, seg=2):
    m = o.modifiers.new("Bevel", "BEVEL")
    m.width = w
    m.segments = seg
    m.limit_method = "ANGLE"
    return m


ACTIVE = []


def rigid(o, kind="ACTIVE", shape="CONVEX_HULL", mass=1.0, friction=0.6, bounce=0.15,
          margin=0.004):
    vl = SC.view_layers[0]
    with bpy.context.temp_override(scene=SC, view_layer=vl, object=o, active_object=o,
                                   selected_objects=[o], selected_editable_objects=[o]):
        bpy.ops.rigidbody.object_add(type=kind)
    rb = o.rigid_body
    rb.collision_shape = shape
    rb.friction = friction
    rb.restitution = bounce
    rb.use_margin = True
    rb.collision_margin = margin
    if kind == "ACTIVE":
        rb.mass = mass
        rb.linear_damping = LINEAR_DAMPING
        rb.angular_damping = ANGULAR_DAMPING
        rb.use_deactivation = False
        ACTIVE.append(o)
    return o


# =============================================================================
# BUILD THE ROOM
# =============================================================================
RX, RY_BACK, RY_FRONT, RZ = 2.1, 2.0, -1.15, 3.3   # room half-width, back wall y, front limit, height


def build_room():
    floor_m = mat("Floor", (0.5, 0.3, 0.15), 0.4, tex=tex_wood)
    wall_m = mat("Wall", (0.62, 0.47, 0.34), 0.9, tex=tex_plaster)
    accent_m = mat("AccentWall", (0.30, 0.085, 0.045), 0.85, tex=tex_plaster)
    ceil_m = mat("Ceiling", (0.7, 0.6, 0.5), 0.9)
    trim_m = mat("Trim", (0.95, 0.92, 0.86), 0.5)

    def slab(name, size, center, m, collide=True, visible=True):
        bm = bmesh.new()
        bm_box(bm, size)           # origin at the box centre: BOX collision shapes are origin-centred
        o = new_obj(name, finalize(bm, name, [m]))
        o.location = center
        if not visible:
            o.hide_render = True
            o.display_type = "WIRE"
            o.visible_camera = False
        if collide:
            rigid(o, "PASSIVE", "BOX", friction=0.7, bounce=0.1, margin=0.01)
        return o

    slab("Floor", (2 * RX + 4, RY_BACK - RY_FRONT + 6, 0.4), (0, (RY_BACK + RY_FRONT) / 2 - 2.5, -0.2),
         floor_m)
    slab("BackWall", (2 * RX + 0.6, 0.3, RZ + 0.4), (0, RY_BACK + 0.15, RZ / 2), accent_m)
    slab("WallL", (0.3, RY_BACK - RY_FRONT + 3, RZ + 0.4), (-RX - 0.15, RY_BACK - (RY_BACK - RY_FRONT + 3) / 2, RZ / 2), wall_m)
    slab("WallR", (0.3, RY_BACK - RY_FRONT + 3, RZ + 0.4), (RX + 0.15, RY_BACK - (RY_BACK - RY_FRONT + 3) / 2, RZ / 2), wall_m)
    slab("Ceiling", (2 * RX + 0.6, RY_BACK - RY_FRONT + 3, 0.3), (0, RY_BACK - (RY_BACK - RY_FRONT + 3) / 2, RZ + 0.15), ceil_m)
    # invisible glass wall between camera and room keeps everything inside
    slab("FrontGlass", (2 * RX, 0.2, RZ), (0, RY_FRONT - 0.1, RZ / 2), wall_m, visible=False)
    # skirting boards
    slab("SkirtB", (2 * RX, 0.03, 0.12), (0, RY_BACK - 0.015, 0.06), trim_m, collide=False)
    slab("SkirtL", (0.03, RY_BACK - RY_FRONT + 3, 0.12), (-RX + 0.015, RY_BACK - (RY_BACK - RY_FRONT + 3) / 2, 0.06), trim_m, collide=False)
    slab("SkirtR", (0.03, RY_BACK - RY_FRONT + 3, 0.12), (RX - 0.015, RY_BACK - (RY_BACK - RY_FRONT + 3) / 2, 0.06), trim_m, collide=False)

    # window on the right wall with warm sunset glow
    glow = mat("WindowGlow", (1, 0.6, 0.3), emit=(1.0, 0.62, 0.32), emit_strength=6.0)
    frame_m = mat("WindowFrame", (0.95, 0.92, 0.86), 0.4)
    bm = bmesh.new()
    bm_box(bm, (0.02, 1.3, 1.5), (RX - 0.01, 0.2, 1.75), 0)
    o = new_obj("Window", finalize(bm, "Window", [glow]))
    o.visible_shadow = False
    bm = bmesh.new()
    for cy, cz, sy, sz in ((0.2, 2.53, 1.42, 0.07), (0.2, 0.97, 1.42, 0.07), (-0.49, 1.75, 0.07, 1.6),
                           (0.89, 1.75, 0.07, 1.6), (0.2, 1.75, 0.05, 1.5), (0.2, 1.75, 1.3, 0.05)):
        bm_box(bm, (0.06, sy, sz), (RX - 0.03, cy, cz))
    new_obj("WindowFrame", finalize(bm, "WindowFrame", [frame_m]))

    # framed poster on back wall
    poster_m = mat("Poster", (0.9, 0.55, 0.2), 0.6, emit=(0.95, 0.5, 0.15), emit_strength=0.15)
    bm = bmesh.new()
    bm_box(bm, (0.9, 0.04, 1.1), (-0.9, RY_BACK - 0.02, 2.05), 0)
    bm_box(bm, (0.78, 0.05, 0.98), (-0.9, RY_BACK - 0.03, 2.05), 1)
    bm_sphere(bm, 0.22, (-0.9, RY_BACK - 0.06, 2.15), (1, 0.1, 1), 2, sub=3)
    o = new_obj("Poster", finalize(bm, "Poster", [mat("PosterFrame", (0.1, 0.07, 0.05), 0.4), poster_m,
                                                  mat("PosterSun", (1, 0.85, 0.5), emit=(1, 0.8, 0.4), emit_strength=1.5)]))

    # rug (visual only)
    bm = bmesh.new()
    bm_cyl(bm, 1.25, 1.25, 0.01, (0.15, 0.1, 0.005), seg=64)
    o = new_obj("Rug", finalize(bm, "Rug", [mat("Rug", (0.7, 0.3, 0.2), 0.95, sheen=0.5, tex=tex_rug)]))
    o.scale = (1.0, 0.7, 1.0)

    # pendant lamp (visual)
    bm = bmesh.new()
    bm_cyl(bm, 0.006, 0.006, 0.9, (0.3, 0.3, RZ - 0.45), seg=8, mi=0)
    bm_cyl(bm, 0.28, 0.08, 0.25, (0.3, 0.3, RZ - 0.95), seg=48, mi=1, cap=False)
    bm_sphere(bm, 0.07, (0.3, 0.3, RZ - 1.02), mi=2, sub=2)
    o = new_obj("Pendant", finalize(bm, "Pendant", [mat("Cord", (0.05, 0.05, 0.05), 0.5),
                                                     mat("Brass", (0.85, 0.6, 0.3), 0.25, metal=1.0),
                                                     mat("Bulb", (1, 0.8, 0.5), emit=(1, 0.75, 0.45), emit_strength=25)]))
    o.modifiers.new("Solid", "SOLIDIFY").thickness = 0.006


def build_furniture():
    teal = mat("Velvet", (0.05, 0.25, 0.27), 0.8, sheen=0.8)
    wood_dark = mat("WoodDark", (0.22, 0.12, 0.06), 0.45, coat=0.3)
    wood_light = mat("WoodLight", (0.6, 0.4, 0.22), 0.4, coat=0.2)
    brass = mat("Brass", (0.85, 0.6, 0.3), 0.25, metal=1.0)

    # sofa (passive) against the left half of the back wall
    bm = bmesh.new()
    sx, sy = -0.65, RY_BACK - 0.5
    bm_box(bm, (2.1, 0.85, 0.28), (sx, sy, 0.24))           # base
    bm_box(bm, (1.9, 0.75, 0.16), (sx, sy + 0.02, 0.46))    # seat cushion
    bm_box(bm, (2.1, 0.22, 0.6), (sx, sy + 0.32, 0.65))     # back
    bm_box(bm, (0.2, 0.85, 0.32), (sx - 1.0, sy, 0.53))     # arms
    bm_box(bm, (0.2, 0.85, 0.32), (sx + 1.0, sy, 0.53))
    for dx in (-0.95, 0.95):
        for dy in (-0.33, 0.33):
            bm_cyl(bm, 0.025, 0.018, 0.1, (sx + dx, sy + dy, 0.05), seg=12, mi=1)
    o = new_obj("Sofa", finalize(bm, "Sofa", [teal, brass]))
    bevel(o, 0.04, 3)
    rigid(o, "PASSIVE", "MESH", friction=0.9, bounce=0.05)

    # sideboard on the right of the back wall (passive)
    bm = bmesh.new()
    bx, by = 1.35, RY_BACK - 0.25
    bm_box(bm, (1.3, 0.45, 0.55), (bx, by, 0.4))
    for dx in (-0.55, 0.55):
        for dy in (-0.17, 0.17):
            bm_cyl(bm, 0.02, 0.015, 0.13, (bx + dx, by + dy, 0.065), seg=12, mi=1)
    bm_box(bm, (0.6, 0.01, 0.4), (bx - 0.31, by - 0.226, 0.4), 2)
    bm_box(bm, (0.6, 0.01, 0.4), (bx + 0.31, by - 0.226, 0.4), 2)
    o = new_obj("Sideboard", finalize(bm, "Sideboard", [wood_dark, brass, wood_light]))
    bevel(o, 0.012, 2)
    rigid(o, "PASSIVE", "MESH", friction=0.7)

    # coffee table (ACTIVE: even the table floats)
    bm = bmesh.new()
    tz = 0.0
    bm_cyl(bm, 0.5, 0.5, 0.05, (0, 0, 0.42), seg=48)
    for a in range(3):
        ang = a * 2 * math.pi / 3 + 0.3
        bm_cyl(bm, 0.025, 0.02, 0.4, (0.33 * math.cos(ang), 0.33 * math.sin(ang), 0.2), seg=12, mi=1)
    me = finalize(bm, "Table", [wood_light, wood_dark])
    o = new_obj("CoffeeTable", me)
    o.location = (0.15, 0.1, 0.0)
    rigid(o, mass=12, shape="CONVEX_HULL", friction=0.8, bounce=0.1)

    # ottoman pouf (active)
    bm = bmesh.new()
    bm_cyl(bm, 0.26, 0.26, 0.36, (0, 0, 0), seg=40)
    o = new_obj("Pouf", finalize(bm, "Pouf", [mat("Mustard", (0.85, 0.55, 0.12), 0.85, sheen=0.7)]))
    bevel(o, 0.05, 3)
    o.location = (-1.35, -0.6, 0.182)
    rigid(o, mass=4, shape="CYLINDER", friction=0.9, bounce=0.2)

    # standing lamp (passive) in the left corner
    bm = bmesh.new()
    lx, ly = -1.8, RY_BACK - 0.3
    bm_cyl(bm, 0.18, 0.18, 0.03, (lx, ly, 0.015), seg=32, mi=0)
    bm_cyl(bm, 0.015, 0.015, 1.5, (lx, ly, 0.78), seg=12, mi=0)
    bm_cyl(bm, 0.24, 0.17, 0.32, (lx, ly, 1.65), seg=40, mi=1, cap=False)
    o = new_obj("FloorLamp", finalize(bm, "FloorLamp",
                [brass, mat("Shade", (1, 0.85, 0.65), 0.7, emit=(1, 0.7, 0.4), emit_strength=3.0)]))
    o.modifiers.new("Solid", "SOLIDIFY").thickness = 0.005
    rigid(o, "PASSIVE", "MESH")


def build_props(rng):
    book_cols = [(0.6, 0.1, 0.08), (0.08, 0.2, 0.4), (0.85, 0.65, 0.2), (0.15, 0.35, 0.2),
                 (0.9, 0.85, 0.75), (0.45, 0.15, 0.35), (0.9, 0.4, 0.15), (0.12, 0.12, 0.12)]
    page_m = mat("Pages", (0.95, 0.92, 0.82), 0.8)

    def book(name, loc, rot, w, d, h, ci):
        bm = bmesh.new()
        bm_box(bm, (w, d, h), (0, 0, 0), 0)
        bm_box(bm, (w * 0.96, d * 0.97, h * 0.86), (0.01 * w, 0, 0), 1)   # page block peeks out
        o = new_obj(name, finalize(bm, name, [mat("Book%d" % ci, book_cols[ci], 0.55), page_m]))
        o.location = loc
        o.rotation_euler = rot
        bevel(o, 0.004, 1)
        rigid(o, mass=0.6, shape="BOX", friction=0.7, bounce=0.1)

    # upright books on the sideboard
    x = 0.85
    for i in range(7):
        h = rng.uniform(0.2, 0.28)
        d = rng.uniform(0.03, 0.05)
        book("BookUp%d" % i, (x, RY_BACK - 0.27, 0.675 + h / 2 + 0.002), (0, 0, math.pi / 2),
             rng.uniform(0.14, 0.18), d, h, i % 8)
        x += d + 0.006
    # stack on the coffee table
    z = 0.445
    for i in range(4):
        th = rng.uniform(0.025, 0.045)
        book("BookStack%d" % i, (0.0, 0.25, z + th / 2 + 0.002), (0, 0, rng.uniform(-0.3, 0.3)),
             rng.uniform(0.18, 0.24), rng.uniform(0.14, 0.17), th, (i + 3) % 8)
        z += th + 0.003
    # books on the floor
    for i in range(3):
        book("BookFloor%d" % i, (rng.uniform(-1.6, 1.6), rng.uniform(-0.95, -0.55), 0.03 + 0.04 * i),
             (0, 0, rng.uniform(0, 3)), 0.2, 0.15, 0.035, (i + 5) % 8)

    # cups / mugs
    cup_cols = [(0.95, 0.94, 0.9), (0.9, 0.5, 0.4), (0.4, 0.6, 0.65), (0.95, 0.8, 0.3), (0.2, 0.2, 0.22)]
    for i, (px, py, pz) in enumerate([(0.25, -0.1, 0.447), (0.35, 0.1, 0.447), (-0.2, -0.05, 0.447),
                                      (1.7, RY_BACK - 0.25, 0.677), (-0.25, 0.25, 0.447)]):
        bm = bmesh.new()
        bm_cyl(bm, 0.042, 0.047, 0.1, (0, 0, 0.05), seg=24, mi=0)
        bm_torus(bm, 0.03, 0.009, (0.052, 0, 0.05), rot=(math.pi / 2, 0, 0), mi=0)
        bm_cyl(bm, 0.039, 0.039, 0.004, (0, 0, 0.085), seg=24, mi=1)   # coffee surface
        name = "Cup%d" % i
        o = new_obj(name, finalize(bm, name, [mat("Ceramic%d" % i, cup_cols[i], 0.15, coat=0.6),
                                              mat("Coffee", (0.12, 0.05, 0.02), 0.1)]))
        o.location = (px, py, pz)
        o.rotation_euler = (0, 0, rng.uniform(0, 6.28))
        rigid(o, mass=0.3, shape="CONVEX_HULL", friction=0.5, bounce=0.2)

    # balls
    ball_cols = [(0.9, 0.2, 0.15), (0.95, 0.75, 0.15), (0.15, 0.45, 0.85), (0.95, 0.95, 0.95),
                 (0.2, 0.7, 0.4), (0.95, 0.45, 0.6), (0.98, 0.5, 0.1)]
    for i, c in enumerate(ball_cols):
        r = rng.uniform(0.07, 0.13)
        bm = bmesh.new()
        bm_sphere(bm, r, sub=3)
        name = "Ball%d" % i
        o = new_obj(name, finalize(bm, name, [mat("Ball%d" % i, c, 0.25, coat=0.8)], smooth=True))
        o.location = (rng.uniform(-1.8, 1.8), rng.uniform(-0.95, 0.9), r + 0.002)
        if abs(o.location.x - 0.15) < 0.65 and abs(o.location.y - 0.1) < 0.65:
            o.location.x += 1.3 if o.location.x > 0.15 else -1.3
        rigid(o, mass=0.4, shape="SPHERE", friction=0.5, bounce=0.6, margin=0.002)

    # cushions on the sofa
    cush_cols = [(0.95, 0.55, 0.35), (0.85, 0.65, 0.2), (0.6, 0.7, 0.55), (0.9, 0.85, 0.75)]
    for i, c in enumerate(cush_cols):
        bm = bmesh.new()
        bm_box(bm, (0.4, 0.17, 0.4))
        name = "Cushion%d" % i
        me = finalize(bm, name, [mat("Cushion%d" % i, c, 0.9, sheen=0.9)])
        o = new_obj(name, me)
        bevel(o, 0.07, 3)
        o.location = (-1.35 + i * 0.45, RY_BACK - 0.36, 0.79)
        o.rotation_euler = (-0.25, rng.uniform(-0.15, 0.15), rng.uniform(-0.1, 0.1))
        sd = o.modifiers.new("Sub", "SUBSURF")
        sd.levels = 1
        sd.render_levels = 2
        o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))
        rigid(o, mass=0.5, shape="BOX", friction=0.9, bounce=0.05)

    # vinyl records
    vinyl = mat("Vinyl", (0.02, 0.02, 0.025), 0.2, coat=0.5)
    for i, lc in enumerate([(0.9, 0.2, 0.2), (0.95, 0.8, 0.2), (0.2, 0.6, 0.8)]):
        bm = bmesh.new()
        bm_cyl(bm, 0.15, 0.15, 0.006, (0, 0, 0), seg=48, mi=0)
        bm_cyl(bm, 0.05, 0.05, 0.007, (0, 0, 0), seg=32, mi=1)
        name = "Record%d" % i
        o = new_obj(name, finalize(bm, name, [vinyl, mat("Label%d" % i, lc, 0.5)]))
        o.location = (-0.5 + 0.12 * i, -0.75 + 0.05 * i, 0.004 + 0.008 * i)
        o.rotation_euler = (0, 0, i * 0.7)
        rigid(o, mass=0.18, shape="CYLINDER", friction=0.5, bounce=0.1)

    # speaker (music!) on the sideboard
    bm = bmesh.new()
    bm_box(bm, (0.24, 0.22, 0.36), (0, 0, 0), 0)
    bm_cyl(bm, 0.08, 0.08, 0.01, (0, -0.112, -0.06), seg=32, mi=1, rot=(math.pi / 2, 0, 0))
    bm_cyl(bm, 0.035, 0.035, 0.01, (0, -0.112, 0.1), seg=24, mi=1, rot=(math.pi / 2, 0, 0))
    o = new_obj("Speaker", finalize(bm, "Speaker", [mat("WoodDark", (0.22, 0.12, 0.06)),
                                                     mat("Grille", (0.03, 0.03, 0.03), 0.7)]))
    o.location = (1.85, RY_BACK - 0.27, 0.677 + 0.18)
    bevel(o, 0.01, 2)
    rigid(o, mass=3.0, shape="BOX", friction=0.7, bounce=0.05)

    # plants
    pot_m = mat("Terracotta", (0.7, 0.32, 0.18), 0.8)
    leaf_m = mat("Leaf", (0.12, 0.38, 0.12), 0.5, sheen=0.2)
    soil_m = mat("Soil", (0.1, 0.06, 0.03), 1.0)
    for i, (px, py, pz, s) in enumerate([(1.75, -0.2, 0.0, 1.0), (1.05, RY_BACK - 0.25, 0.677, 0.55)]):
        bm = bmesh.new()
        bm_cyl(bm, 0.11 * s, 0.15 * s, 0.26 * s, (0, 0, 0.13 * s), seg=32, mi=0)
        bm_cyl(bm, 0.135 * s, 0.135 * s, 0.01, (0, 0, 0.255 * s), seg=32, mi=2)
        prng = random.Random(i + 11)
        for k in range(9):
            a = k * 2.4
            tilt = prng.uniform(0.35, 0.9)
            L = prng.uniform(0.18, 0.3) * s
            c = Vector((math.cos(a) * L * 0.55 * math.sin(tilt), math.sin(a) * L * 0.55 * math.sin(tilt),
                        0.26 * s + L * 0.6 * math.cos(tilt) + 0.04 * s))
            bm_sphere(bm, 1.0, c, (L * 0.5, L * 0.18, 0.012 * s + 0.01), mi=1,
                      rot=(0, -tilt + math.pi / 2, a), sub=2)
        name = "Plant%d" % i
        o = new_obj(name, finalize(bm, name, [pot_m, leaf_m, soil_m]))
        o.location = (px, py, pz + 0.002)
        rigid(o, mass=2.5 * s, shape="CONVEX_HULL", friction=0.8, bounce=0.1)


def build_lights():
    w = bpy.data.worlds.new(PREFIX + "World")
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.02, 0.013, 0.008, 1)
    bg.inputs[1].default_value = 1.0
    SC.world = w

    def light(name, kind, loc, rot, energy, color, size=1.0, spot=None):
        ld = bpy.data.lights.new(PREFIX + name, kind)
        ld.energy = energy
        ld.color = color
        if kind == "AREA":
            ld.shape = "RECTANGLE"
            ld.size = size
            ld.size_y = size * 1.1
        else:
            ld.shadow_soft_size = size
        if spot:
            ld.spot_size = spot
            ld.spot_blend = 0.6
        o = link(bpy.data.objects.new(PREFIX + name, ld))
        o.location = loc
        o.rotation_euler = rot
        return o

    # sunset through the window (right wall)
    light("WindowSun", "AREA", (RX + 0.4, 0.2, 1.8), (0, -math.radians(90), 0), 900, (1.0, 0.62, 0.35), 1.4)
    # pendant
    light("PendantBulb", "POINT", (0.3, 0.3, RZ - 1.1), (0, 0, 0), 160, (1.0, 0.72, 0.45), 0.08)
    # floor lamp
    light("LampBulb", "POINT", (-1.8, RY_BACK - 0.3, 1.6), (0, 0, 0), 90, (1.0, 0.7, 0.4), 0.1)
    # soft fill from the camera side
    light("Fill", "AREA", (0, -3.2, 2.6), (math.radians(60), 0, 0), 70, (1.0, 0.82, 0.65), 3.0)


def build_camera(nframes):
    rig = link(bpy.data.objects.new(PREFIX + "CamRig", None))
    cd = bpy.data.cameras.new(PREFIX + "Camera")
    cd.lens = 20
    cd.sensor_fit = "AUTO"
    cd.clip_start = 0.05
    cam = link(bpy.data.objects.new(PREFIX + "Camera", cd))
    cam.parent = rig
    SC.camera = cam
    start = Vector((0.0, -3.55, 1.25))
    target = Vector((0.0, 0.8, 1.45))
    d = (target - start).normalized()
    rig.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    rig.location = start
    rig.keyframe_insert("location", frame=1)
    rig.location = start + d * PUSH_IN
    rig.keyframe_insert("location", frame=nframes)
    set_interp(rig, "BEZIER")
    return rig, cam, cd


def iter_fcurves(idblock):
    ad = idblock.animation_data
    if not ad or not ad.action:
        return []
    act = ad.action
    if hasattr(act, "fcurves") and not hasattr(act, "layers"):
        return list(act.fcurves)
    out = []
    try:  # layered actions (4.4+ / 5.x)
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    out += list(bag.fcurves)
    except Exception:
        pass
    if not out and hasattr(act, "fcurves"):
        out = list(act.fcurves)
    return out


def set_interp(idblock, mode):
    for fc in iter_fcurves(idblock):
        for k in fc.keyframe_points:
            k.interpolation = mode


def build_hud(cam, cd, states):
    """One text object per gravity state; visibility keyed per frame."""
    font_m = mat("HudText", (1, 1, 1), emit=(1.0, 0.97, 0.9), emit_strength=2.5)
    hot_m = mat("HudHot", (1, 0.5, 0.2), emit=(1.0, 0.45, 0.12), emit_strength=4.0)
    cool_m = mat("HudCool", (0.6, 0.85, 1), emit=(0.55, 0.85, 1.0), emit_strength=3.0)
    shadow_m = mat("HudShadow", (0, 0, 0), 1.0, emit=(0, 0, 0), emit_strength=0.0)
    for m in (font_m, hot_m, cool_m, shadow_m):
        p = m.node_tree.nodes.get("Principled BSDF")
        p.inputs["Base Color"].default_value = (0, 0, 0, 1)
    D = 1.0
    H = 36.0 / cd.lens * D          # visible height at distance D (sensor fit on height)
    W = H * RESOLUTION[0] / RESOLUTION[1]

    def text(name, body, y, size, m, parent=cam):
        objs = []
        for sh, mm in ((1, shadow_m), (0, m)):
            cu = bpy.data.curves.new(PREFIX + name + ("_sh" if sh else ""), "FONT")
            cu.body = body
            cu.align_x = "CENTER"
            cu.align_y = "CENTER"
            cu.size = size
            cu.extrude = 0.0
            cu.materials.append(mm)
            o = link(bpy.data.objects.new(PREFIX + name + ("_sh" if sh else ""), cu))
            o.parent = parent
            o.location = (size * 0.06 * sh, y - size * 0.06 * sh, -D - 0.001 * sh)
            o.visible_shadow = False
            objs.append(o)
        return objs

    text("Hook", "WHEN THE BEAT DROPS...", 0.40 * H, W * 0.075, font_m)
    hud = {}
    for key in states:
        planet, mode = key
        g = PLANETS[planet]
        sub = {"up": "FLOATING", "down": "DRIFTING" if g < 1 else "", "hit": "BEAT!", "drop": "BEAT DROP!"}[mode]
        m = cool_m if mode == "up" else (hot_m if mode in ("hit", "drop") else font_m)
        objs = text("HUD_%s_%s" % (planet, mode), "%s %s m/s²" % (planet, ("%.2f" % g) if g < 100 else "%.1f" % g),
                    0.31 * H, W * 0.085, m)
        if sub:
            objs += text("HUDsub_%s_%s" % (planet, mode), sub, 0.25 * H, W * 0.06, m)
        hud[key] = objs
    return hud


def key_hud(hud, state_per_frame):
    n = len(state_per_frame)
    prev = None
    for f in range(n):
        s = state_per_frame[f]
        if s == prev:
            continue
        for key, objs in hud.items():
            for o in objs:
                o.hide_render = key != s
                o.hide_viewport = key != s
                o.keyframe_insert("hide_render", frame=f + 1)
                o.keyframe_insert("hide_viewport", frame=f + 1)
        prev = s
    for objs in hud.values():
        for o in objs:
            set_interp(o, "CONSTANT")


def add_sound(path, offset):
    se = SC.sequence_editor or SC.sequence_editor_create()
    strips = se.strips if hasattr(se, "strips") else se.sequences
    for s in list(strips):
        strips.remove(s)
    st = strips.new_sound(PREFIX + "Music", path, 1, 1)
    if offset > 0:
        try:
            st.frame_offset_start = int(round(offset * FPS))
            st.frame_start = 1 - int(round(offset * FPS))
        except Exception:
            pass
    SC.sync_mode = "AUDIO_SYNC"
    return st


def setup_render(engine, nframes, preview=False):
    r = SC.render
    r.fps = FPS
    r.resolution_x, r.resolution_y = RESOLUTION
    r.resolution_percentage = 100
    engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    if engine == "CYCLES" or preview:
        r.engine = "CYCLES"
        SC.cycles.samples = 16 if preview else CYCLES_SAMPLES
        SC.cycles.device = "CPU"
        SC.cycles.max_bounces = 4 if preview else 8
        try:
            SC.cycles.use_denoising = True
        except Exception:
            pass
    else:
        r.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in engines else "BLENDER_EEVEE_NEXT"
        ee = SC.eevee
        if hasattr(ee, "taa_render_samples"):
            ee.taa_render_samples = EEVEE_SAMPLES
        for attr, val in (("use_raytracing", True), ("use_shadows", True), ("use_gtao", True),
                          ("use_bloom", True)):
            if hasattr(ee, attr):
                setattr(ee, attr, val)
    try:
        SC.view_settings.view_transform = "AgX"
        SC.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        try:
            SC.view_settings.look = "Medium High Contrast"
        except Exception:
            pass


# =============================================================================
# MAIN
# =============================================================================
def main():
    global SC, COLL, AUDIO_PATH
    t0 = time.time()
    rng = random.Random(SEED)
    clear_previous()

    # ---- audio
    if not AUDIO_PATH:
        AUDIO_PATH = os.path.join(script_dir(), "gms_demo_track.wav")
        if not os.path.exists(AUDIO_PATH):
            make_demo_track(AUDIO_PATH)
            print("[gms] generated demo track:", AUDIO_PATH)
    AUDIO_PATH = bpy.path.abspath(AUDIO_PATH)
    an = analyse(AUDIO_PATH, FPS, SECONDS, AUDIO_OFFSET_S)
    n = an["nframes"]
    g, hits = gravity_curve(an, FPS)
    print("[gms] audio %s  %.1fs @ %d Hz  -> %d frames" % (os.path.basename(AUDIO_PATH), an["seconds"], an["sr"], n))
    print("[gms] detected %d hits:" % len(an["beats"]))
    hit_kind = {f0: d for f0, d, _ in hits}
    for bt, s in an["beats"]:
        f0 = int(round(bt * FPS))
        print("       t=%6.2fs  frame %4d  strength %.2f  %s" % (bt, f0 + 1, s,
              DROP_PLANET if hit_kind.get(f0) else BEAT_PLANET))

    # ---- scene
    SC = bpy.data.scenes.new(SCENE_NAME)
    win = getattr(bpy.context, "window", None)
    if win:
        win.scene = SC
    COLL = bpy.data.collections.new(PREFIX + "Room")
    SC.collection.children.link(COLL)
    SC.frame_start, SC.frame_end = 1, n
    SC.render.fps = FPS
    with bpy.context.temp_override(scene=SC, view_layer=SC.view_layers[0]):
        bpy.ops.rigidbody.world_add()
    rbw = SC.rigidbody_world
    if rbw.collection is None:
        rbw.collection = bpy.data.collections.new(PREFIX + "RigidBodies")
    rbw.substeps_per_frame = SUBSTEPS
    rbw.solver_iterations = SOLVER_ITERATIONS
    rbw.point_cache.frame_start = 1
    rbw.point_cache.frame_end = n
    SC.use_gravity = True

    build_room()
    build_furniture()
    build_props(rng)
    build_lights()
    rig, cam, cd = build_camera(n)

    # ---- gravity: scene.gravity keyed every frame (the rigid body solver reads the
    #      evaluated scene gravity each step, so the animation is honoured in the bake)
    for f in range(n):
        SC.gravity = (0.0, 0.0, float(g[f]))
        SC.keyframe_insert("gravity", index=2, frame=f + 1)
    SC.gravity = (0, 0, float(g[0]))
    set_interp(SC, "LINEAR")

    # ---- turbulence: gentle drifting in quiet parts (strength keyed with the music)
    if TURBULENCE > 0:
        tb = link(bpy.data.objects.new(PREFIX + "Turbulence", None))
        tb.location = (0, 0, 1.4)
        tb.empty_display_size = 0.5
        with bpy.context.temp_override(scene=SC, view_layer=SC.view_layers[0], object=tb, active_object=tb):
            bpy.ops.object.forcefield_toggle()
        tb.field.type = "TURBULENCE"
        tb.field.size = 1.2
        tb.field.flow = 0.0
        for f in range(0, n, 3):
            q = max(0.0, g[f]) / PLANETS[QUIET_PLANET]
            tb.field.strength = TURBULENCE * q
            tb.field.keyframe_insert("strength", frame=f + 1)

    # ---- camera shake on drops
    if CAMERA_SHAKE > 0:
        srng = random.Random(5)
        cam.keyframe_insert("location", frame=1)
        for f0, drop, s in hits:
            amp = CAMERA_SHAKE * (1.0 if drop else 0.35)
            cam.location = (0, 0, 0)
            cam.keyframe_insert("location", frame=f0)
            for k in range(1, 10):
                a = amp * math.exp(-k / 3.0)
                cam.location = (srng.uniform(-a, a), srng.uniform(-a, a), 0)
                cam.keyframe_insert("location", frame=f0 + k)
            cam.location = (0, 0, 0)
            cam.keyframe_insert("location", frame=f0 + 10)

    # ---- HUD states
    states = []
    hitframes = {}
    for f0, drop, s in hits:
        hold = DROP_HOLD_FRAMES if drop else BEAT_HOLD_FRAMES
        for k in range(hold + 3):
            hitframes.setdefault(f0 + k, drop)
    for f in range(n):
        if f in hitframes:
            st = (DROP_PLANET, "drop") if hitframes[f] else (BEAT_PLANET, "hit")
        elif g[f] > 0.05:
            st = (QUIET_PLANET, "up")
        else:
            st = (nearest_planet(-g[f]), "down")
        states.append(st)
    hud = build_hud(cam, cd, sorted(set(states)))
    key_hud(hud, states)

    add_sound(AUDIO_PATH, AUDIO_OFFSET_S)
    setup_render(ENGINE, n, preview=PREVIEW)
    SC.frame_set(1)

    # ---- bake
    tb0 = time.time()
    with bpy.context.temp_override(scene=SC, view_layer=SC.view_layers[0], point_cache=rbw.point_cache):
        bpy.ops.ptcache.free_bake_all()
        bpy.ops.ptcache.bake(bake=True)
    print("[gms] baked %d frames, %d active bodies in %.1fs" % (n, len(ACTIVE), time.time() - tb0))

    # ---- verify numerically
    heights = np.zeros(n)
    inside = True
    for f in range(n):
        SC.frame_set(f + 1)
        zs = []
        for o in ACTIVE:
            p = o.matrix_world.translation
            zs.append(p.z)
            if not (-RX - 0.1 < p.x < RX + 0.1 and RY_FRONT - 0.3 < p.y < RY_BACK + 0.1 and -0.1 < p.z < RZ + 0.1):
                inside = False
        heights[f] = float(np.mean(zs))
    print("\n[gms]  time  frame  mean_h(m)  gravity(m/s²)  HUD")
    for f in range(0, n, 6):
        st = states[f]
        print("      %5.2f  %5d   %6.3f     %+8.2f     %s %s" % (f / FPS, f + 1, heights[f], g[f], st[0], st[1]))
    print("\n[gms] per hit: mean height at hit -> +3 / +6 frames")
    for f0, drop, s in hits:
        a = heights[min(n - 1, f0)]
        b = heights[min(n - 1, f0 + 3)]
        c = heights[min(n - 1, f0 + 6)]
        print("      t=%5.2fs %-7s  %.3f -> %.3f -> %.3f  (drop %.0f cm)" % (f0 / FPS, DROP_PLANET if drop else BEAT_PLANET,
              a, b, c, 100 * (a - c)))
    # quiet stretches
    print("\n[gms] quiet (floating) stretches: mean height start -> peak")
    f = 0
    while f < n:
        if states[f][0] == QUIET_PLANET:
            e = f
            while e < n and states[e][0] == QUIET_PLANET:
                e += 1
            if e - f >= 10:
                pk = f + int(np.argmax(heights[f:e]))
                print("      %5.2fs-%5.2fs  %.3f -> %.3f m at %.2fs  (+%.0f cm)" % (
                      f / FPS, e / FPS, heights[f], heights[pk], pk / FPS, 100 * (heights[pk] - heights[f])))
            f = e
        else:
            f += 1
    print("[gms] all objects stayed inside the room:", inside)
    np.save(os.path.join(os.getcwd(), "gms_heights.npy"), np.stack([heights, g])) if PREVIEW else None

    # ---- preview stills / render
    od = out_dir()
    if PREVIEW:
        SC.render.resolution_percentage = 25
        pd = os.path.join(od, "preview")
        os.makedirs(pd, exist_ok=True)
        fq = int(np.argmax(heights[: hits[0][0]] if hits else heights))      # floating before first hit
        drops = [h for h in hits if h[1]] or hits
        picks = [("01_float", fq)]
        if drops:
            fd = drops[0][0]
            picks.append(("02_before_drop", max(0, fd - 1)))
            picks.append(("03_after_drop", min(n - 1, fd + 4)))
        later = [h for h in hits if h[0] > (drops[0][0] if drops else 0) + 20]
        if later:
            picks.append(("04_float_between_kicks", later[0][0] - 1))
        picks.append(("05_outro_float", n - 1))
        SC.render.image_settings.file_format = "PNG"
        for name, f in picks:
            SC.frame_set(f + 1)
            SC.render.filepath = os.path.join(pd, "%s_f%04d.png" % (name, f + 1))
            with bpy.context.temp_override(scene=SC):
                bpy.ops.render.render(write_still=True, scene=SC.name)
            print("[gms] preview", SC.render.filepath, "mean_h %.2f g %+.2f" % (heights[f], g[f]))
    if RENDER:
        setup_render(ENGINE, n)
        rd = os.path.join(od, SCENE_NAME)
        os.makedirs(rd, exist_ok=True)
        fmts = [e.identifier for e in bpy.types.ImageFormatSettings.bl_rna.properties["file_format"].enum_items]
        imf = SC.render.image_settings
        if OUTPUT_AS_MP4 and "FFMPEG" in fmts:
            if hasattr(imf, "media_type"):
                imf.media_type = "VIDEO"
            imf.file_format = "FFMPEG"
            ff = SC.render.ffmpeg
            ff.format = "MPEG4"
            ff.codec = "H264"
            ff.constant_rate_factor = "HIGH"
            ff.audio_codec = "AAC"
            ff.audio_bitrate = 256
            SC.render.filepath = os.path.join(rd, "gravity_music_sync.mp4")
        else:
            imf.file_format = "PNG"
            SC.render.filepath = os.path.join(rd, "frame_####")
        with bpy.context.temp_override(scene=SC):
            bpy.ops.render.render(animation=True, scene=SC.name)
        print("[gms] rendered to", SC.render.filepath)
    print("[gms] done in %.1fs" % (time.time() - t0))


main()
