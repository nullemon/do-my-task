"""
06 - Saturn at the Moon's distance  (50 s cinematic, vertical 1080x1920 @ 30 fps)
==================================================================================
Title: "What if Saturn replaced the Moon? (you'd feel nothing... at first)"

Single self-contained Blender script (Blender 4.2 - 5.x). Everything procedural.

Run:
  Blender GUI : Scripting tab -> open this file -> Run Script (builds scene + prints verification)
  Headless    : blender -b -P script.py -- --render            (full-quality animation)
                blender -b -P script.py -- --preview           (half-res fast animation)
                blender -b -P script.py -- --frames 1,200,600  (stills only)
                blender -b -P script.py -- --verify-only       (build + verify, no render)
  Extra args  : --engine eevee|cycles  --out /path/to/folder  --samples N  --res-pct N
"""

# =============================================================================
# CONFIG
# =============================================================================
CONFIG = {
    "fps": 30,
    "duration_s": 50.0,
    "resolution": (1080, 1920),
    "engine": "EEVEE",            # "EEVEE" (default) or "CYCLES"
    "PREVIEW": False,             # --preview : 50 % res, low samples
    "RENDER": False,              # --render  : full animation render
    "preview_res_pct": 50,
    "eevee_samples": {"preview": 16, "final": 64},
    "cycles_samples": {"preview": 16, "final": 128},
    "output_dir": None,           # None -> ./render_06 next to the script (or cwd)
    "output_format": "MP4",       # "MP4" (falls back to PNG sequence) or "PNG"
    # --- real astronomy (km, kg, SI) ---
    "moon_distance_km": 384_400.0,
    "saturn_eq_radius_km": 60_268.0,
    "saturn_polar_radius_km": 54_364.0,
    "ring_A_outer_km": 136_780.0,
    "ring_C_inner_km": 74_658.0,
    "saturn_mass_kg": 5.683e26,
    "moon_mass_kg": 7.342e22,
    "earth_mass_kg": 5.972e24,
    "earth_radius_km": 6_371.0,
    "saturn_density": 687.0,      # kg/m^3
    "earth_density": 5_514.0,     # kg/m^3
    "moon_radius_km": 1_737.4,
    "G": 6.674e-11,
    "g": 9.81,
    # --- scene scale: 384,400 km is represented by this many scene metres ---
    "scene_distance_m": 6000.0,
    # --- camera ---
    "h_fov_deg": 50.0,            # horizontal field of view (portrait frame)
    "cam_pitch_deg": 10.0,
    "eye_height_m": 4.5,          # standing on a dune / lifeguard tower
    # --- Saturn placement (final pose, as seen from the beach) ---
    "saturn_azimuth_deg": 1.0,    # + = right of view centre
    "saturn_elevation_deg": 22.0,
    "ring_opening_deg": 21.0,     # how far we look onto the ring plane
    "ring_roll_deg": -17.0,       # image-plane tilt of the rings
    # --- beach / tide ---
    "beach_slope": 0.03,          # 3 % slope: 10 m sea drop -> ~333 m retreat
    "tide_drop_m": 10.0,
    "seed": 6,
}

import bpy
import bmesh
import math
import os
import random
import sys
from mathutils import Vector, Matrix, Quaternion, Euler

# =============================================================================
# Args
# =============================================================================
ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def _arg_val(name, default=None):
    if name in ARGV:
        i = ARGV.index(name)
        if i + 1 < len(ARGV):
            return ARGV[i + 1]
    return default


if "--preview" in ARGV:
    CONFIG["PREVIEW"] = True
if "--render" in ARGV:
    CONFIG["RENDER"] = True
if _arg_val("--engine"):
    CONFIG["engine"] = _arg_val("--engine").upper()
if _arg_val("--out"):
    CONFIG["output_dir"] = _arg_val("--out")
FRAMES_ARG = _arg_val("--frames")
SAMPLES_ARG = _arg_val("--samples")
RESPCT_ARG = _arg_val("--res-pct")
VERIFY_ONLY = "--verify-only" in ARGV

FPS = CONFIG["fps"]
NFRAMES = int(round(CONFIG["duration_s"] * FPS))
RNG = random.Random(CONFIG["seed"])


def F(t):
    """seconds -> frame number (frame 1 == t 0)."""
    return 1 + int(round(t * FPS))


def smooth(a, b, x):
    if b == a:
        return 1.0 if x >= b else 0.0
    u = max(0.0, min(1.0, (x - a) / (b - a)))
    return u * u * (3 - 2 * u)


# =============================================================================
# Scale
# =============================================================================
D_M = CONFIG["scene_distance_m"]
KM2M = D_M / CONFIG["moon_distance_km"]           # scene metres per real km (Saturn system)
SAT_R = CONFIG["saturn_eq_radius_km"] * KM2M
SAT_FLAT = CONFIG["saturn_polar_radius_km"] / CONFIG["saturn_eq_radius_km"]
RING_OUT = CONFIG["ring_A_outer_km"] * KM2M
RING_IN = 74_000.0 * KM2M


def ring_km(x):
    return x / CONFIG["ring_A_outer_km"]          # normalised ring radius


SLOPE = CONFIG["beach_slope"]


def sand_z(y):
    return -SLOPE * y


# =============================================================================
# Utilities (version-safe)
# =============================================================================
def clean_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.lights,
                 bpy.data.cameras, bpy.data.node_groups):
        for b in list(coll):
            if b.users == 0:
                coll.remove(b)


def link(obj, parent=None):
    bpy.context.scene.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


def new_empty(name, loc=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None)
    e.location = loc
    return link(e, parent)


def mesh_obj(name, verts, faces, parent=None, smooth_shade=False):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    if smooth_shade:
        for p in me.polygons:
            p.use_smooth = True
    return link(bpy.data.objects.new(name, me), parent)


def no_ray_vis(obj):
    """Overlay objects: invisible to shadows / reflections."""
    for a in ("visible_shadow", "visible_diffuse", "visible_glossy",
              "visible_transmission", "visible_volume_scatter"):
        if hasattr(obj, a):
            setattr(obj, a, False)


def set_blend(mat, blended=True):
    if hasattr(mat, "surface_render_method"):          # 4.2+
        mat.surface_render_method = "BLENDED" if blended else "DITHERED"
    elif hasattr(mat, "blend_method"):
        mat.blend_method = "BLEND" if blended else "HASHED"
    if hasattr(mat, "use_backface_culling"):
        mat.use_backface_culling = False


def new_mat(name):
    m = bpy.data.materials.new(name)
    if hasattr(m, "use_nodes") and not m.use_nodes:
        try:
            m.use_nodes = True
        except Exception:
            pass
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    return m, nt


def N(nt, kind, **props):
    n = nt.nodes.new(kind)
    for k, v in props.items():
        setattr(n, k, v)
    return n


def sock(sockets, key):
    """Find socket by identifier first, then name (handles duplicate names on Mix nodes)."""
    if isinstance(key, int):
        return sockets[key]
    for s in sockets:
        if s.identifier == key:
            return s
    for s in sockets:
        if s.name == key and s.enabled:
            return s
    return sockets[key]


def L(nt, a, ao, b, bi):
    nt.links.new(sock(a.outputs, ao), sock(b.inputs, bi))


def setin(node, key, val):
    sock(node.inputs, key).default_value = val


def math_node(nt, op, a=None, b=None, clamp=False):
    n = N(nt, "ShaderNodeMath", operation=op)
    n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n


def vmath(nt, op, a=None, b=None):
    n = N(nt, "ShaderNodeVectorMath", operation=op)
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (tuple, list, Vector)):
            n.inputs[i].default_value = tuple(v)
        else:
            nt.links.new(v, n.inputs[i])
    return n


def vout(n):
    return sock(n.outputs, "Vector")


def fout(n):
    return n.outputs[0] if n.bl_idname == "ShaderNodeMath" else sock(n.outputs, "Value")


def mix_rgb(nt, fac, a, b):
    n = N(nt, "ShaderNodeMix")
    n.data_type = "RGBA"
    for key, v in (("Factor_Float", fac), ("A_Color", a), ("B_Color", b)):
        s = sock(n.inputs, key)
        if isinstance(v, (int, float)):
            s.default_value = v
        elif isinstance(v, (tuple, list)):
            s.default_value = tuple(v) if len(v) == 4 else tuple(v) + (1.0,)
        else:
            nt.links.new(v, s)
    return n, sock(n.outputs, "Result_Color")


def ramp(nt, stops, interp="LINEAR"):
    r = N(nt, "ShaderNodeValToRGB")
    cr = r.color_ramp
    cr.interpolation = interp
    while len(cr.elements) > 1:
        cr.elements.remove(cr.elements[-1])
    cr.elements[0].position = stops[0][0]
    cr.elements[0].color = tuple(stops[0][1]) + ((1.0,) if len(stops[0][1]) == 3 else ())
    for pos, col in stops[1:]:
        e = cr.elements.new(pos)
        e.color = tuple(col) + ((1.0,) if len(col) == 3 else ())
    return r


def key_val(node_socket, frame, value):
    node_socket.default_value = value
    node_socket.keyframe_insert("default_value", frame=frame)


def emission_mat(name, color, strength=1.0, alpha=1.0, blended=True):
    """Unlit material with keyable alpha -> returns (mat, alpha_socket)."""
    m, nt = new_mat(name)
    out = N(nt, "ShaderNodeOutputMaterial")
    em = N(nt, "ShaderNodeEmission")
    setin(em, "Color", tuple(color) + (1.0,))
    setin(em, "Strength", strength)
    tr = N(nt, "ShaderNodeBsdfTransparent")
    mx = N(nt, "ShaderNodeMixShader")
    val = N(nt, "ShaderNodeValue")
    val.outputs[0].default_value = alpha
    L(nt, val, 0, mx, 0)
    L(nt, tr, 0, mx, 1)
    L(nt, em, 0, mx, 2)
    L(nt, mx, 0, out, "Surface")
    set_blend(m, blended)
    return m, val.outputs[0], em


def apply_mat(obj, mat):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


# =============================================================================
# Scene / render setup
# =============================================================================
def eevee_id():
    items = bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys()
    return "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in items else "BLENDER_EEVEE"


def setup_render(scene):
    r = scene.render
    r.resolution_x, r.resolution_y = CONFIG["resolution"]
    pct = 100
    if CONFIG["PREVIEW"]:
        pct = CONFIG["preview_res_pct"]
    if RESPCT_ARG:
        pct = int(RESPCT_ARG)
    r.resolution_percentage = pct
    r.fps = FPS
    scene.frame_start = 1
    scene.frame_end = NFRAMES
    q = "preview" if CONFIG["PREVIEW"] else "final"
    if CONFIG["engine"].startswith("CYC"):
        r.engine = "CYCLES"
        cy = scene.cycles
        cy.samples = int(SAMPLES_ARG) if SAMPLES_ARG else CONFIG["cycles_samples"][q]
        cy.use_denoising = True
        cy.transparent_max_bounces = 32
        cy.max_bounces = 4
        try:
            cy.device = "CPU"
        except Exception:
            pass
    else:
        r.engine = eevee_id()
        ee = scene.eevee
        s = int(SAMPLES_ARG) if SAMPLES_ARG else CONFIG["eevee_samples"][q]
        if hasattr(ee, "taa_render_samples"):
            ee.taa_render_samples = s
        for a, v in (("use_raytracing", True), ("use_shadows", True),
                     ("use_gtao", True), ("use_ssr", True)):
            if hasattr(ee, a):
                try:
                    setattr(ee, a, v)
                except Exception:
                    pass
    vs = scene.view_settings
    try:
        vs.view_transform = "AgX"
    except Exception:
        vs.view_transform = "Filmic"
    for look in ("AgX - Medium High Contrast", "Medium High Contrast", "None"):
        try:
            vs.look = look
            break
        except Exception:
            pass
    vs.exposure = 0.0
    out_dir = CONFIG["output_dir"]
    if not out_dir:
        try:
            base = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            base = os.getcwd()
        out_dir = os.path.join(base, "render_06")
    CONFIG["output_dir"] = out_dir
    if (FRAMES_ARG or CONFIG["RENDER"] or CONFIG["PREVIEW"]) and not VERIFY_ONLY:
        os.makedirs(out_dir, exist_ok=True)
    return out_dir


def set_video_output(scene, out_dir):
    r = scene.render
    if CONFIG["output_format"] == "MP4":
        try:
            ims = r.image_settings
            if hasattr(ims, "media_type"):
                ims.media_type = "VIDEO"         # Blender 5.x
            ims.file_format = "FFMPEG"
            r.ffmpeg.format = "MPEG4"
            r.ffmpeg.codec = "H264"
            r.ffmpeg.constant_rate_factor = "HIGH"
            r.filepath = os.path.join(out_dir, "saturn_moon_distance.mp4")
            return
        except Exception as ex:
            print("[06] MP4 output unavailable (%s) -> PNG sequence" % ex)
    ims = r.image_settings
    if hasattr(ims, "media_type"):
        try:
            ims.media_type = "IMAGE"
        except Exception:
            pass
    ims.file_format = "PNG"
    r.filepath = os.path.join(out_dir, "frame_")


# =============================================================================
# World: golden-hour sky -> night with stars
# =============================================================================
SUN_EL0 = 5.5          # deg at t=0
SUN_EL1 = -7.0         # deg at night
SUN_AZ_VEC = Vector((-0.30, -1.0, 0.0)).normalized()   # sun sits behind the camera, a bit left


def build_world(scene):
    w = bpy.data.worlds.new("SkyWorld")
    scene.world = w
    if hasattr(w, "use_nodes"):
        try:
            if not w.use_nodes:
                w.use_nodes = True
        except Exception:
            pass
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = N(nt, "ShaderNodeOutputWorld")
    tc = N(nt, "ShaderNodeTexCoord")

    # --- day sky ---------------------------------------------------------
    sky_ok = False
    day_bg = N(nt, "ShaderNodeBackground")
    sky = None
    try:
        sky = N(nt, "ShaderNodeTexSky")
        types = sky.bl_rna.properties["sky_type"].enum_items.keys()
        for t in ("NISHITA", "MULTIPLE_SCATTERING", "SINGLE_SCATTERING"):
            if t in types:
                sky.sky_type = t
                sky_ok = True
                break
        if sky_ok:
            sky.sun_disc = False
            sky.altitude = 10.0
            sky.air_density = 1.2
            sky.aerosol_density = 2.5 if hasattr(sky, "aerosol_density") else 1.0
            # sun_rotation: Blender's sky puts the sun at angle `rotation` measured
            # from +Y towards -X ... we search numerically below for robustness.
            az = math.atan2(SUN_AZ_VEC.x, SUN_AZ_VEC.y)
            sky.sun_rotation = _sky_rotation_for_azimuth(sky, az)
            for t, el in ((0.0, SUN_EL0), (6.0, 2.5), (10.0, -1.0), (14.0, SUN_EL1)):
                sky.sun_elevation = math.radians(el)
                sky.keyframe_insert("sun_elevation", frame=F(t))
            L(nt, sky, "Color", day_bg, "Color")
    except Exception as ex:
        print("[06] Sky texture unavailable (%s) -> gradient sky" % ex)
        sky_ok = False
    if not sky_ok:
        if sky is not None:
            nt.nodes.remove(sky)
        sep = N(nt, "ShaderNodeSeparateXYZ")
        L(nt, tc, "Generated", sep, 0)
        gr = ramp(nt, [(0.0, (1.0, 0.55, 0.30)), (0.12, (0.85, 0.55, 0.55)),
                       (0.45, (0.25, 0.40, 0.75)), (1.0, (0.10, 0.20, 0.55))])
        L(nt, sep, "Z", gr, "Fac")
        L(nt, gr, "Color", day_bg, "Color")
    day_strength = sock(day_bg.inputs, "Strength")
    for t, v in ((0.0, 0.14 if sky_ok else 1.0), (8.0, 0.16 if sky_ok else 0.6),
                 (14.0, 0.05 if sky_ok else 0.1)):
        key_val(day_strength, F(t), v)

    # --- night sky with stars ------------------------------------------
    sep = N(nt, "ShaderNodeSeparateXYZ")
    L(nt, tc, "Generated", sep, 0)
    grad = ramp(nt, [(0.0, (0.020, 0.035, 0.075)), (0.25, (0.006, 0.012, 0.035)),
                     (1.0, (0.002, 0.004, 0.014))])
    L(nt, sep, "Z", grad, "Fac")
    vor = N(nt, "ShaderNodeTexVoronoi")
    setin(vor, "Scale", 260.0)
    L(nt, tc, "Generated", vor, "Vector")
    star = math_node(nt, "LESS_THAN", sock(vor.outputs, "Distance"), 0.035)
    rnd = N(nt, "ShaderNodeSeparateColor")
    L(nt, vor, "Color", rnd, 0)
    starb = math_node(nt, "POWER", rnd.outputs[0], 6.0)
    sm = math_node(nt, "MULTIPLY", fout(star), fout(starb))
    above = math_node(nt, "GREATER_THAN", sep.outputs[2], 0.02)
    sm2 = math_node(nt, "MULTIPLY", fout(sm), fout(above))
    sm3 = math_node(nt, "MULTIPLY", fout(sm2), 6.0)
    add = N(nt, "ShaderNodeMix")
    add.data_type = "RGBA"
    add.blend_type = "ADD"
    nt.links.new(fout(sm3), sock(add.inputs, "Factor_Float"))
    nt.links.new(grad.outputs["Color"], sock(add.inputs, "A_Color"))
    sock(add.inputs, "B_Color").default_value = (1.0, 0.97, 0.9, 1.0)
    night_bg = N(nt, "ShaderNodeBackground")
    nt.links.new(sock(add.outputs, "Result_Color"), sock(night_bg.inputs, "Color"))
    setin(night_bg, "Strength", 1.0)

    mix = N(nt, "ShaderNodeMixShader")
    L(nt, day_bg, 0, mix, 1)
    L(nt, night_bg, 0, mix, 2)
    fac = mix.inputs[0]
    for t, v in ((0.0, 0.0), (8.0, 0.0), (16.0, 1.0)):
        key_val(fac, F(t), v)
    L(nt, mix, 0, out, "Surface")
    return sky_ok


def _sky_rotation_for_azimuth(sky, az):
    """Blender sky: sun_rotation 0 puts the sun towards -Y (verified for Nishita
    and its 5.x successors by rendering); rotation increases counter-clockwise."""
    # azimuth here measured as atan2(x, y) (0 = +Y, positive towards +X)
    # sun at +Y corresponds to rotation pi; we want direction SUN_AZ_VEC.
    return (math.pi - az) % (2 * math.pi) if SKY_ROT_MODE == 0 else az


SKY_ROT_MODE = 1


# =============================================================================
# Camera rig + overlays
# =============================================================================
W_HALF = math.tan(math.radians(CONFIG["h_fov_deg"] / 2))       # half-width at 1 m
ASPECT = CONFIG["resolution"][1] / CONFIG["resolution"][0]
H_HALF = W_HALF * ASPECT


def cam_base_y(t):
    # slow push-in during the first 20 s, a few more metres later
    return -22.0 + 5.0 * smooth(0.0, 20.0, t) + 2.5 * smooth(36.0, 48.0, t)


def build_camera(scene):
    rig = new_empty("CamRig")
    rig.rotation_euler = (math.radians(90 + CONFIG["cam_pitch_deg"]), 0, 0)
    for i in range(0, NFRAMES + 1, 6):
        t = i / FPS
        y = cam_base_y(t)
        rig.location = (0.0, y, sand_z(y) + CONFIG["eye_height_m"])
        rig.keyframe_insert("location", frame=1 + i)
    cd = bpy.data.cameras.new("Cam")
    cd.sensor_fit = "HORIZONTAL"
    cd.sensor_width = 36.0
    cd.lens = 18.0 / W_HALF
    cd.clip_start = 0.1
    cd.clip_end = 60000.0
    cam = link(bpy.data.objects.new("Camera", cd), rig)
    scene.camera = cam

    # --- shake during wave impact + tremors (keyframed; deterministic) -----
    rng = random.Random(99)

    def env(t):
        e = 0.0
        e = max(e, 0.6 * smooth(33.4, 34.2, t) * (1 - smooth(34.4, 35.2, t)))
        e = max(e, smooth(35.0, 36.0, t) * (1 - smooth(43.5, 45.0, t)) *
                (0.65 + 0.35 * math.sin(t * 2.3) ** 2))
        return e
    cam.location = (0, 0, 0)
    cam.rotation_euler = (0, 0, 0)
    cam.keyframe_insert("location", frame=1)
    cam.keyframe_insert("rotation_euler", frame=1)
    for f in range(F(33.0), F(45.5), 2):
        e = env((f - 1) / FPS)
        cam.location = (rng.uniform(-1, 1) * 0.06 * e, rng.uniform(-1, 1) * 0.05 * e, 0.0)
        cam.rotation_euler = (rng.uniform(-1, 1) * math.radians(0.9) * e,
                              rng.uniform(-1, 1) * math.radians(0.9) * e,
                              rng.uniform(-1, 1) * math.radians(0.6) * e)
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
    cam.location = (0, 0, 0)
    cam.rotation_euler = (0, 0, 0)
    cam.keyframe_insert("location", frame=F(45.6))
    cam.keyframe_insert("rotation_euler", frame=F(45.6))
    return rig, cam


def rounded_rect(name, w, h, r, parent, loc, mat, segs=6):
    r = min(r, w / 2, h / 2)
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90),
                       (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for i in range(segs + 1):
            a = math.radians(a0 + 90 * i / segs)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a), 0))
    o = mesh_obj(name, pts, [list(range(len(pts)))], parent)
    o.location = loc
    apply_mat(o, mat)
    no_ray_vis(o)
    return o


class Overlay:
    """A group of camera-parented text/plate pieces sharing one fade schedule."""

    def __init__(self, name):
        self.name = name
        self.alpha_sockets = []     # (socket, base_alpha)
        self.objects = []

    def fade(self, t_in, t_out, fade_in=0.35, fade_out=0.35):
        for s, base in self.alpha_sockets:
            if t_in <= 0.0:
                key_val(s, 1, base)
            else:
                key_val(s, 1, 0.0)
                key_val(s, F(t_in), 0.0)
                key_val(s, F(t_in + fade_in), base)
            if t_out is not None:
                key_val(s, F(t_out - fade_out), base)
                key_val(s, F(t_out), 0.0)


OV_Z = -1.0


def add_text(ov, cam, body, size, x, y, color=(1, 1, 1), plate=True, plate_alpha=0.74,
             pad=(0.035, 0.022), z=OV_Z, bold=0.0, align="CENTER", strength=1.6):
    cu = bpy.data.curves.new(ov.name + "_txt", type="FONT")
    cu.body = body
    cu.size = size
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.space_line = 1.05
    if bold:
        cu.offset = bold
    tob = link(bpy.data.objects.new(ov.name + "_txt", cu), cam)
    tob.location = (x, y, z + 0.002)
    tm, ta, _ = emission_mat(ov.name + "_txtmat", color, strength)
    apply_mat(tob, tm)
    no_ray_vis(tob)
    ov.alpha_sockets.append((ta, 1.0))
    ov.objects.append(tob)
    if plate:
        bpy.context.view_layer.update()
        dw, dh = tob.dimensions.x, tob.dimensions.y
        if dw < 1e-4:  # fallback estimate
            lines = body.split("\n")
            dw = max(len(l) for l in lines) * size * 0.55
            dh = len(lines) * size * 1.2
        pm, pa, _ = emission_mat(ov.name + "_platemat", (0.0, 0.0, 0.0), 0.0)
        cx = x if align == "CENTER" else x + dw / 2
        p = rounded_rect(ov.name + "_plate", dw + 2 * pad[0], dh + 2 * pad[1], 0.022, cam,
                         (cx, y, z), pm)
        ov.alpha_sockets.append((pa, plate_alpha))
        ov.objects.append(p)
    return tob


def build_overlays(cam):
    ovs = []
    xh, yh = W_HALF, H_HALF

    # Top label (top third), stays all video until the cut
    top = Overlay("TopLabel")
    add_text(top, cam, "SATURN", 0.105, 0.0, yh * 0.80, color=(1.0, 0.86, 0.55), bold=0.0018,
             plate_alpha=0.70)
    add_text(top, cam, "at the Moon's distance  |  384,400 km", 0.038, 0.0, yh * 0.80 - 0.105,
             color=(1, 1, 1), plate_alpha=0.70)
    top.fade(0.0, 49.0, fade_out=0.04)
    ovs.append(top)

    def cap(name, body, t0, t1, y=-yh * 0.42, size=0.062, color=(1, 1, 1), **kw):
        o = Overlay(name)
        add_text(o, cam, body, size, 0.0, y, color=color, **kw)
        o.fade(t0, t1, **{k: v for k, v in kw.items() if k in ()})
        ovs.append(o)
        return o

    c = Overlay("Hook")
    add_text(c, cam, "What if Saturn\nreplaced the Moon?", 0.082, 0.0, -yh * 0.38, bold=0.0012)
    c.fade(0.0, 3.2)
    ovs.append(c)

    cap("Dist", "Distance: 384,400 km", 3.6, 11.8, y=-yh * 0.34, size=0.066,
        color=(1.0, 0.9, 0.6))
    cap("Ang", "17.8° wide, rings 39°\n= 34 full Moons across", 6.5, 11.8,
        y=-yh * 0.50, size=0.05)
    cap("Feel", "You'd feel… nothing.", 12.6, 19.6, y=-yh * 0.36, size=0.074, bold=0.0012)
    cap("Feel2", "(weight change < 0.1%)", 14.0, 19.6, y=-yh * 0.50, size=0.05,
        color=(0.75, 0.9, 1.0))
    cap("Tide", "Tides ~7,700× stronger", 20.4, 27.6, y=-yh * 0.36, size=0.066,
        color=(1.0, 0.9, 0.6))
    cap("Tide2", "The sea pulls back\nhundreds of metres…", 22.0, 27.6, y=-yh * 0.52,
        size=0.052)
    cap("Back", "…then it comes back.", 28.4, 33.8, y=-yh * 0.42, size=0.072, bold=0.0012)
    cap("Quake", "Earthquakes. Volcanoes.", 35.6, 44.6, y=-yh * 0.22, size=0.068,
        color=(1.0, 0.75, 0.5))
    cap("Safe", "And this was the\nSAFE distance.", 45.0, 49.0, y=-yh * 0.30, size=0.074,
        bold=0.0012)
    fin = cap("Torn", "At 73,000 km,\nEarth gets torn apart…", 46.6, None, y=-yh * 0.55,
              size=0.06, color=(1.0, 0.55, 0.45), z=OV_Z + 0.004)

    # --- Moon-orbit insert (picture-in-picture diagram) -----------------
    ins = Overlay("Insert")
    cx, cy = xh * 0.0, -yh * 0.62
    R = 0.115
    z0 = OV_Z + 0.001
    pm, pa, _ = emission_mat("Insert_platemat", (0.0, 0.01, 0.03), 0.0)
    plate = rounded_rect("Insert_plate", 2 * R + 0.20, 2 * R + 0.20, 0.03, cam, (cx, cy, z0 - 0.001), pm)
    ins.alpha_sockets.append((pa, 0.72))
    ins.objects.append(plate)

    def disc(name, r, col, loc, strength=1.5, n=40):
        verts = [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n), 0)
                 for i in range(n)]
        o = mesh_obj(name, verts, [list(range(n))], cam)
        o.location = loc
        m, a, _ = emission_mat(name + "_m", col, strength)
        apply_mat(o, m)
        no_ray_vis(o)
        ins.alpha_sockets.append((a, 1.0))
        ins.objects.append(o)
        return o
    disc("InsEarth", 0.024, (0.2, 0.5, 1.0), (cx, cy, z0 + 0.0004))
    # dashed original orbit
    for i in range(36):
        a0 = 2 * math.pi * i / 36
        a1 = a0 + 2 * math.pi / 72
        rr0, rr1 = R - 0.002, R + 0.002
        v = [(rr0 * math.cos(a0), rr0 * math.sin(a0), 0), (rr1 * math.cos(a0), rr1 * math.sin(a0), 0),
             (rr1 * math.cos(a1), rr1 * math.sin(a1), 0), (rr0 * math.cos(a1), rr0 * math.sin(a1), 0)]
        o = mesh_obj("InsDash%02d" % i, v, [(0, 1, 2, 3)], cam)
        o.location = (cx, cy, z0 + 0.0002)
        m = bpy.data.materials.get("InsDash_m")
        if m is None:
            m, a, _ = emission_mat("InsDash_m", (0.6, 0.65, 0.75), 1.0)
            ins.alpha_sockets.append((a, 0.8))
        apply_mat(o, m)
        no_ray_vis(o)
    # Saturn on the orbit (where the Moon used to be)
    sat_ang = math.radians(20)
    disc("InsSaturn", 0.028, (0.95, 0.8, 0.5),
         (cx + R * math.cos(sat_ang), cy + R * math.sin(sat_ang), z0 + 0.0006))
    ring_v = []
    n = 40
    for i in range(n):
        a = 2 * math.pi * i / n
        ring_v.append((0.055 * math.cos(a), 0.012 * math.sin(a), 0))
    for i in range(n):
        a = 2 * math.pi * i / n
        ring_v.append((0.045 * math.cos(a), 0.008 * math.sin(a), 0))
    faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    ro = mesh_obj("InsRing", ring_v, faces, cam)
    ro.location = (cx + R * math.cos(sat_ang), cy + R * math.sin(sat_ang), z0 + 0.0007)
    ro.rotation_euler = (0, 0, math.radians(-20))
    rm, ra, _ = emission_mat("InsRing_m", (0.85, 0.75, 0.55), 1.2)
    apply_mat(ro, rm)
    no_ray_vis(ro)
    ins.alpha_sockets.append((ra, 1.0))
    # the Moon dot, flung off course
    moon = disc("InsMoon", 0.013, (0.85, 0.85, 0.85), (cx, cy, z0 + 0.0008), strength=2.0)
    t0, t1 = 38.0, 45.0
    for f in range(F(t0) - 3, F(t1) + 1, 2):
        t = (f - 1) / FPS
        u = max(0.0, (t - t0) / (t1 - t0))
        ang = math.radians(200) + u * math.radians(250)
        rr = R * (1.0 + 0.55 * u * u + 0.10 * math.sin(u * 14) * u)
        moon.location = (cx + rr * math.cos(ang), cy + rr * math.sin(ang), z0 + 0.0008)
        moon.keyframe_insert("location", frame=f)
    add_text(ins, cam, "The Moon is flung\noff course", 0.036, cx, cy - R - 0.055, plate=False,
             z=z0 + 0.001, color=(0.85, 0.9, 1.0))
    add_text(ins, cam, "EARTH", 0.022, cx, cy - 0.045, plate=False, z=z0 + 0.001,
             color=(0.5, 0.75, 1.0))
    ins.fade(38.0, 44.8)
    ovs.append(ins)

    # Wave-impact white flash
    fl = Overlay("Flash")
    fm, fa, _ = emission_mat("Flash_m", (0.85, 0.93, 1.0), 1.4)
    p = rounded_rect("Flash_plate", 4 * xh, 4 * yh, 0.0, cam, (0, 0, OV_Z - 0.008), fm)
    fl.alpha_sockets.append((fa, 1.0))
    s = fa
    key_val(s, 1, 0.0)
    key_val(s, F(34.05), 0.0)
    key_val(s, F(34.25), 1.0)
    key_val(s, F(34.7), 0.95)
    key_val(s, F(35.6), 0.0)
    ovs.append(fl)

    # Final cut to black (hard cut at 49.0 s; last caption stays on black)
    bk = Overlay("Black")
    bm, ba, _ = emission_mat("Black_m", (0, 0, 0), 0.0)
    rounded_rect("Black_plate", 4 * xh, 4 * yh, 0.0, cam, (0, 0, OV_Z - 0.006), bm)
    key_val(ba, 1, 0.0)
    key_val(ba, F(49.0) - 1, 0.0)
    key_val(ba, F(49.0), 1.0)
    ovs.append(bk)
    return ovs


# =============================================================================
# Saturn system
# =============================================================================
def ring_opacity_group():
    g = bpy.data.node_groups.new("RingOpacity", "ShaderNodeTree")
    g.interface.new_socket("R", in_out="INPUT", socket_type="NodeSocketFloat")
    g.interface.new_socket("Opacity", in_out="OUTPUT", socket_type="NodeSocketFloat")
    gi = g.nodes.new("NodeGroupInput")
    go = g.nodes.new("NodeGroupOutput")
    # radial structure (real ring boundaries, km)
    st = [(0.0, 0.0), (ring_km(74_658), 0.13), (ring_km(84_000), 0.20), (ring_km(92_000), 0.80),
          (ring_km(99_000), 0.95), (ring_km(104_000), 0.86), (ring_km(110_000), 0.95),
          (ring_km(117_580), 0.03), (ring_km(122_170), 0.62), (ring_km(128_000), 0.70),
          (ring_km(133_200), 0.12), (ring_km(134_000), 0.58), (ring_km(136_780), 0.0)]
    r = ramp(g, [(p, (v, v, v)) for p, v in st], interp="CONSTANT")
    L(g, gi, 0, r, "Fac")
    # fine ringlets
    nz = g.nodes.new("ShaderNodeTexNoise")
    if hasattr(nz, "noise_dimensions"):
        nz.noise_dimensions = "1D"
    setin(nz, "Scale", 90.0)
    setin(nz, "Detail", 6.0)
    g.links.new(gi.outputs[0], sock(nz.inputs, "W"))
    mod = math_node(g, "MULTIPLY_ADD", sock(nz.outputs, "Fac"), 0.5)
    mod.inputs[2].default_value = 0.72
    mul = math_node(g, "MULTIPLY", r.outputs["Color"], fout(mod))
    clampn = math_node(g, "MINIMUM", fout(mul), 1.0)
    L(g, clampn, 0, go, 0)
    return g


def saturn_materials(L_local):
    grp = ring_opacity_group()
    Lv = tuple(L_local)

    # ---------- planet ----------
    m, nt = new_mat("SaturnMat")
    out = N(nt, "ShaderNodeOutputMaterial")
    tc = N(nt, "ShaderNodeTexCoord")
    P = sock(tc.outputs, "Object")
    # oblate normal
    nscale = vmath(nt, "MULTIPLY", P, (1.0, 1.0, 1.0 / (SAT_FLAT * SAT_FLAT)))
    Nn = vmath(nt, "NORMALIZE", vout(nscale))
    dl = vmath(nt, "DOT_PRODUCT", vout(Nn), Lv)
    lit = N(nt, "ShaderNodeMapRange")
    L(nt, dl, "Value", lit, "Value")
    setin(lit, "From Min", -0.06)
    setin(lit, "From Max", 1.0)
    lit.clamp = True
    litp = math_node(nt, "POWER", lit.outputs[0], 0.75)
    # ring shadow: Q = P + t L, t = -Pz/Lz
    sp = N(nt, "ShaderNodeSeparateXYZ")
    nt.links.new(P, sp.inputs[0])
    tt = math_node(nt, "DIVIDE", sp.outputs[2], -Lv[2] if abs(Lv[2]) > 1e-6 else -1e-6)
    tpos = math_node(nt, "GREATER_THAN", fout(tt), 0.0)
    tL = vmath(nt, "SCALE", Lv)
    nt.links.new(fout(tt), sock(tL.inputs, "Scale"))
    Q = vmath(nt, "ADD", P, vout(tL))
    qlen = vmath(nt, "LENGTH", vout(Q))
    qn = math_node(nt, "DIVIDE", sock(qlen.outputs, "Value"), RING_OUT)
    gnode = N(nt, "ShaderNodeGroup")
    gnode.node_tree = grp
    nt.links.new(fout(qn), gnode.inputs[0])
    shd = math_node(nt, "MULTIPLY", gnode.outputs[0], fout(tpos))
    shf = math_node(nt, "MULTIPLY_ADD", fout(shd), -0.85)
    shf.inputs[2].default_value = 1.0
    light = math_node(nt, "MULTIPLY", fout(litp), fout(shf))
    light2 = math_node(nt, "ADD", fout(light), 0.015)          # faint earthshine on night side
    # bands
    spn = N(nt, "ShaderNodeSeparateXYZ")
    L(nt, Nn, "Vector", spn, 0)
    nz = N(nt, "ShaderNodeTexNoise")
    setin(nz, "Scale", 1.6)
    setin(nz, "Detail", 8.0)
    setin(nz, "Roughness", 0.55)
    nmap = vmath(nt, "MULTIPLY", vout(Nn), (1.0, 1.0, 9.0))     # streak along longitude
    L(nt, nmap, "Vector", nz, "Vector")
    turb = math_node(nt, "MULTIPLY_ADD", sock(nz.outputs, "Fac"), 0.05)
    turb.inputs[2].default_value = -0.025
    lat = math_node(nt, "ADD", spn.outputs[2], fout(turb))
    latm = math_node(nt, "MULTIPLY_ADD", fout(lat), 0.5)
    latm.inputs[2].default_value = 0.5
    bands = ramp(nt, [
        (0.00, (0.42, 0.45, 0.48)), (0.07, (0.50, 0.50, 0.46)), (0.16, (0.62, 0.55, 0.42)),
        (0.24, (0.78, 0.66, 0.46)), (0.30, (0.66, 0.52, 0.34)), (0.36, (0.86, 0.75, 0.55)),
        (0.42, (0.72, 0.58, 0.38)), (0.47, (0.93, 0.84, 0.64)), (0.53, (0.95, 0.87, 0.68)),
        (0.58, (0.74, 0.60, 0.40)), (0.63, (0.88, 0.78, 0.58)), (0.70, (0.70, 0.57, 0.38)),
        (0.77, (0.82, 0.71, 0.52)), (0.85, (0.62, 0.56, 0.45)), (0.93, (0.52, 0.53, 0.52)),
        (1.00, (0.45, 0.48, 0.52))])
    nt.links.new(fout(latm), bands.inputs["Fac"])
    # limb darkening
    lw = N(nt, "ShaderNodeLayerWeight")
    setin(lw, "Blend", 0.5)
    limb = math_node(nt, "POWER", sock(lw.outputs, "Facing"), 2.5)
    limbf = math_node(nt, "MULTIPLY_ADD", fout(limb), -0.45)
    limbf.inputs[2].default_value = 1.0
    lit_all = math_node(nt, "MULTIPLY", fout(light2), fout(limbf))
    # horizon reddening / brightness (keyed)
    bright = N(nt, "ShaderNodeValue", label="Bright")
    red = N(nt, "ShaderNodeValue", label="Redden")
    _, tinted = mix_rgb(nt, red.outputs[0], bands.outputs["Color"], (1.0, 0.45, 0.2))
    em = N(nt, "ShaderNodeEmission")
    nt.links.new(tinted, sock(em.inputs, "Color"))
    st = math_node(nt, "MULTIPLY", fout(lit_all), bright.outputs[0])
    st2 = math_node(nt, "MULTIPLY", fout(st), 1.25)
    nt.links.new(fout(st2), sock(em.inputs, "Strength"))
    L(nt, em, 0, out, "Surface")
    sat_mat = m
    sat_keys = (bright.outputs[0], red.outputs[0])

    # ---------- rings ----------
    m, nt = new_mat("RingMat")
    out = N(nt, "ShaderNodeOutputMaterial")
    tc = N(nt, "ShaderNodeTexCoord")
    P = sock(tc.outputs, "Object")
    ln = vmath(nt, "LENGTH", P)
    rn = math_node(nt, "DIVIDE", sock(ln.outputs, "Value"), RING_OUT)
    gnode = N(nt, "ShaderNodeGroup")
    gnode.node_tree = grp
    nt.links.new(fout(rn), gnode.inputs[0])
    col = ramp(nt, [(ring_km(74_000), (0.45, 0.42, 0.38)), (ring_km(92_000), (0.70, 0.62, 0.50)),
                    (ring_km(105_000), (0.93, 0.85, 0.70)), (ring_km(117_000), (0.88, 0.80, 0.64)),
                    (ring_km(122_500), (0.74, 0.68, 0.58)), (ring_km(136_780), (0.66, 0.62, 0.55))])
    nt.links.new(fout(rn), col.inputs["Fac"])
    # planet shadow on the rings
    dpl = vmath(nt, "DOT_PRODUCT", P, Lv)
    behind = math_node(nt, "LESS_THAN", sock(dpl.outputs, "Value"), 0.0)
    cr = vmath(nt, "CROSS_PRODUCT", P, Lv)
    crl = vmath(nt, "LENGTH", vout(cr))
    inside = math_node(nt, "LESS_THAN", sock(crl.outputs, "Value"), SAT_R)
    shadow = math_node(nt, "MULTIPLY", fout(behind), fout(inside))
    shf = math_node(nt, "MULTIPLY_ADD", fout(shadow), -0.92)
    shf.inputs[2].default_value = 1.0
    bright2 = N(nt, "ShaderNodeValue", label="Bright")
    red2 = N(nt, "ShaderNodeValue", label="Redden")
    _, tinted = mix_rgb(nt, red2.outputs[0], col.outputs["Color"], (1.0, 0.45, 0.2))
    st = math_node(nt, "MULTIPLY", fout(shf), bright2.outputs[0])
    st2 = math_node(nt, "MULTIPLY", fout(st), 1.3)
    em = N(nt, "ShaderNodeEmission")
    nt.links.new(tinted, sock(em.inputs, "Color"))
    nt.links.new(fout(st2), sock(em.inputs, "Strength"))
    tr = N(nt, "ShaderNodeBsdfTransparent")
    mx = N(nt, "ShaderNodeMixShader")
    nt.links.new(gnode.outputs[0], mx.inputs[0])
    L(nt, tr, 0, mx, 1)
    L(nt, em, 0, mx, 2)
    L(nt, mx, 0, out, "Surface")
    set_blend(m, blended=False)
    ring_mat = m
    ring_keys = (bright2.outputs[0], red2.outputs[0])
    return sat_mat, ring_mat, sat_keys, ring_keys


def build_saturn(cam_pivot):
    # final-pose direction from the camera
    az = math.radians(CONFIG["saturn_azimuth_deg"])
    el = math.radians(CONFIG["saturn_elevation_deg"])
    v = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
    centre = cam_pivot + v * D_M
    # ring orientation: start from "image up", open the rings towards the camera, roll
    up = Vector((0, 0, 1))
    n0 = (up - v * up.dot(v)).normalized()
    B = math.radians(CONFIG["ring_opening_deg"])
    n = (n0 * math.cos(B) - v * math.sin(B)).normalized()
    n = Matrix.Rotation(math.radians(CONFIG["ring_roll_deg"]), 3, v) @ n
    x = v.cross(n).normalized()
    y = n.cross(x).normalized()
    R0 = Matrix((x, y, n)).transposed()                # columns = local axes
    M0 = Matrix.Translation(centre) @ R0.to_4x4()

    to_sun = Vector((SUN_AZ_VEC.x, SUN_AZ_VEC.y, math.tan(math.radians(SUN_EL0)))).normalized()
    L_local = (R0.transposed() @ to_sun).normalized()

    sat_mat, ring_mat, sat_keys, ring_keys = saturn_materials(L_local)

    system = new_empty("SaturnSystem")
    system.rotation_mode = "QUATERNION"
    # planet: oblate UV sphere built in local coords (radius in scene metres)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=128, v_segments=64, radius=SAT_R)
    for vv in bm.verts:
        vv.co.z *= SAT_FLAT
    me = bpy.data.meshes.new("Saturn")
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    planet = link(bpy.data.objects.new("Saturn", me), system)
    apply_mat(planet, sat_mat)
    # ring annulus (z = 0 in local space)
    seg = 512
    verts, faces = [], []
    radii = [RING_IN, RING_IN + (RING_OUT - RING_IN) * 0.5, RING_OUT]
    for r in radii:
        for i in range(seg):
            a = 2 * math.pi * i / seg
            verts.append((r * math.cos(a), r * math.sin(a), 0.0))
    for k in range(len(radii) - 1):
        for i in range(seg):
            j = (i + 1) % seg
            faces.append((k * seg + i, k * seg + j, (k + 1) * seg + j, (k + 1) * seg + i))
    rings = mesh_obj("Rings", verts, faces, system)
    apply_mat(rings, ring_mat)
    for o in (planet, rings):
        if hasattr(o, "visible_shadow"):
            o.visible_shadow = False
    # rise animation: rigid rotation about a tilted "celestial pole" through the camera
    pole = Vector((-math.cos(math.radians(32)), 0.0, math.sin(math.radians(32)))).normalized()

    def pose(theta_deg):
        Rr = Matrix.Rotation(math.radians(theta_deg), 4, pole)
        return Matrix.Translation(cam_pivot) @ Rr @ Matrix.Translation(-cam_pivot) @ M0

    # sample ring rim to find when the topmost ring point sits just under the horizon
    rim = [Vector((RING_OUT * math.cos(a), RING_OUT * math.sin(a), 0))
           for a in [2 * math.pi * i / 180 for i in range(180)]]

    def top_elev(theta):
        M = pose(theta)
        best = -90
        for p in rim + [Vector((0, 0, SAT_R * SAT_FLAT)), Vector((0, 0, -SAT_R * SAT_FLAT))]:
            w = M @ p - cam_pivot
            best = max(best, math.degrees(math.asin(w.z / w.length)))
        return best
    lo, hi = 0.0, 90.0
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if top_elev(mid) > -0.4:
            lo = mid
        else:
            hi = mid
    theta_start = hi

    def theta_at(t):
        if t <= 3.0:
            return theta_start
        if t <= 12.0:
            u = (t - 3.0) / 9.0
            e = 1 - (1 - u) ** 2.2               # ease-out
            return theta_start * (1 - e)
        return -(t - 12.0) * 0.06                # keeps creeping upward
    for f in range(1, NFRAMES + 2, 3):
        t = (f - 1) / FPS
        M = pose(theta_at(t))
        loc, rot, _ = M.decompose()
        system.location = loc
        system.rotation_quaternion = rot
        system.keyframe_insert("location", frame=f)
        system.keyframe_insert("rotation_quaternion", frame=f)

    # horizon extinction keys
    for sock_b, sock_r in (sat_keys, ring_keys):
        for t, b, r in ((0.0, 0.25, 0.75), (4.0, 0.30, 0.7), (7.0, 0.55, 0.45),
                        (10.0, 0.85, 0.18), (13.0, 1.0, 0.05), (16.0, 1.0, 0.02)):
            key_val(sock_b, F(t), b)
            key_val(sock_r, F(t), r)
    return system, planet, rings, v, theta_start, theta_at, pose


# =============================================================================
# Beach, sea, boats, palms, volcano
# =============================================================================
def sand_material():
    m, nt = new_mat("SandMat")
    out = N(nt, "ShaderNodeOutputMaterial")
    bs = N(nt, "ShaderNodeBsdfPrincipled")
    geo = N(nt, "ShaderNodeNewGeometry")
    sp = N(nt, "ShaderNodeSeparateXYZ")
    L(nt, geo, "Position", sp, 0)
    wet = N(nt, "ShaderNodeMapRange")
    nt.links.new(sp.outputs[2], sock(wet.inputs, "Value"))
    setin(wet, "From Min", 0.25)
    setin(wet, "From Max", -0.35)
    wet.clamp = True
    nz = N(nt, "ShaderNodeTexNoise")
    setin(nz, "Scale", 0.08)
    setin(nz, "Detail", 6.0)
    L(nt, geo, "Position", nz, "Vector")
    dry = ramp(nt, [(0.35, (0.80, 0.66, 0.46)), (0.65, (0.88, 0.76, 0.56))])
    L(nt, nz, "Fac", dry, "Fac")
    wetc = ramp(nt, [(0.35, (0.20, 0.17, 0.12)), (0.55, (0.30, 0.25, 0.16)),
                     (0.70, (0.17, 0.20, 0.12))])
    L(nt, nz, "Fac", wetc, "Fac")
    _, col = mix_rgb(nt, wet.outputs[0], dry.outputs["Color"], wetc.outputs["Color"])
    nt.links.new(col, sock(bs.inputs, "Base Color"))
    rough = math_node(nt, "MULTIPLY_ADD", wet.outputs[0], -0.6)
    rough.inputs[2].default_value = 0.95
    nt.links.new(fout(rough), sock(bs.inputs, "Roughness"))
    # ripples
    wv = N(nt, "ShaderNodeTexWave")
    setin(wv, "Scale", 0.9)
    setin(wv, "Distortion", 6.0)
    setin(wv, "Detail", 3.0)
    L(nt, geo, "Position", wv, "Vector")
    bump = N(nt, "ShaderNodeBump")
    setin(bump, "Strength", 0.35)
    L(nt, wv, "Fac", bump, "Height")
    L(nt, bump, "Normal", bs, "Normal")
    L(nt, bs, 0, out, "Surface")
    return m


def water_material(name="WaterMat", foam=True):
    m, nt = new_mat(name)
    out = N(nt, "ShaderNodeOutputMaterial")
    bs = N(nt, "ShaderNodeBsdfPrincipled")
    setin(bs, "Roughness", 0.06)
    base = (0.015, 0.06, 0.075, 1.0)
    if foam:
        at = N(nt, "ShaderNodeAttribute")
        at.attribute_name = "foam"
        fm = N(nt, "ShaderNodeMapRange")
        L(nt, at, "Fac", fm, "Value")
        setin(fm, "From Min", 0.25)
        setin(fm, "From Max", 0.9)
        fm.clamp = True
        _, col = mix_rgb(nt, fm.outputs[0], base, (0.75, 0.8, 0.82))
        nt.links.new(col, sock(bs.inputs, "Base Color"))
    else:
        setin(bs, "Base Color", base)
    L(nt, bs, 0, out, "Surface")
    return m


def wave_material():
    m, nt = new_mat("WaveWallMat")
    out = N(nt, "ShaderNodeOutputMaterial")
    bs = N(nt, "ShaderNodeBsdfPrincipled")
    setin(bs, "Roughness", 0.12)
    tc = N(nt, "ShaderNodeTexCoord")
    sp = N(nt, "ShaderNodeSeparateXYZ")
    L(nt, tc, "Object", sp, 0)
    nz = N(nt, "ShaderNodeTexNoise")
    setin(nz, "Scale", 0.15)
    setin(nz, "Detail", 8.0)
    L(nt, tc, "Object", nz, "Vector")
    hz = math_node(nt, "MULTIPLY_ADD", sock(nz.outputs, "Fac"), 6.0)
    nt.links.new(sp.outputs[2], hz.inputs[2])
    fm = N(nt, "ShaderNodeMapRange")
    nt.links.new(fout(hz), sock(fm.inputs, "Value"))
    setin(fm, "From Min", 22.0)
    setin(fm, "From Max", 31.0)
    fm.clamp = True
    _, col = mix_rgb(nt, fm.outputs[0], (0.02, 0.08, 0.10), (0.85, 0.9, 0.92))
    nt.links.new(col, sock(bs.inputs, "Base Color"))
    em = math_node(nt, "MULTIPLY", fm.outputs[0], 0.8)
    nt.links.new(col, sock(bs.inputs, "Emission Color"))
    nt.links.new(fout(em), sock(bs.inputs, "Emission Strength"))
    L(nt, bs, 0, out, "Surface")
    return m


def sea_level(t):
    d = CONFIG["tide_drop_m"]
    if t < 20.0:
        return 0.0
    if t < 34.2:
        return -d * smooth(20.0, 27.0, t) + 1.5 * smooth(30.0, 34.2, t)
    return 0.6 * math.exp(-(t - 34.2) / 3.0)          # surge settles


def build_beach(scene):
    sand_m = sand_material()
    # sand / seabed grid (denser near the camera)
    nx, ny = 160, 170
    xs = [-520 + 1040 * i / (nx - 1) for i in range(nx)]
    ys = [-140 + 1700 * (j / (ny - 1)) ** 1.8 for j in range(ny)]
    nzr = random.Random(3)
    verts = []
    for y in ys:
        for x in xs:
            z = sand_z(y) + 0.12 * math.sin(x * 0.11 + y * 0.05) + 0.08 * math.sin(x * 0.03 - y * 0.13)
            if y > 1250:
                z -= (y - 1250) * 0.1
            verts.append((x, y, z))
    faces = [(j * nx + i, j * nx + i + 1, (j + 1) * nx + i + 1, (j + 1) * nx + i)
             for j in range(ny - 1) for i in range(nx - 1)]
    sand = mesh_obj("Sand", verts, faces, smooth_shade=True)
    apply_mat(sand, sand_m)

    # seabed rocks & weed (revealed at low tide)
    rock_m, nt = new_mat("RockMat")
    o = N(nt, "ShaderNodeOutputMaterial")
    b = N(nt, "ShaderNodeBsdfPrincipled")
    setin(b, "Base Color", (0.09, 0.09, 0.08, 1))
    setin(b, "Roughness", 0.35)
    L(nt, b, 0, o, "Surface")
    for i in range(70):
        y = nzr.uniform(25, 340)
        x = nzr.uniform(-150, 150) + (y - 20) * 0.1
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
        for vv in bm.verts:
            vv.co += Vector((nzr.uniform(-.25, .25), nzr.uniform(-.25, .25), nzr.uniform(-.2, .2)))
        me = bpy.data.meshes.new("Rock")
        bm.to_mesh(me)
        bm.free()
        r = link(bpy.data.objects.new("Rock%02d" % i, me))
        s = nzr.uniform(0.4, 2.6)
        r.scale = (s * nzr.uniform(0.8, 1.6), s, s * 0.45)
        r.location = (x, y, sand_z(y) - 0.15 * s)
        r.rotation_euler = (0, 0, nzr.uniform(0, 6.28))
        apply_mat(r, rock_m)

    # sea: parent empty carries the sea level (tide)
    sea = new_empty("SeaLevel")
    for f in range(1, NFRAMES + 2, 3):
        sea.location = (0, 0, sea_level((f - 1) / FPS))
        sea.keyframe_insert("location", frame=f)
    wm = water_material()
    have_ocean = bool(getattr(bpy.app.build_options, "mod_oceansim", True))
    near = None
    me = bpy.data.meshes.new("OceanNear")
    near = link(bpy.data.objects.new("OceanNear", me), sea)
    near.location = (-700, -120, 0)
    ok = False
    if have_ocean:
        try:
            md = near.modifiers.new("Ocean", "OCEAN")
            md.geometry_mode = "GENERATE"
            md.size = 1.0
            md.spatial_size = 100
            md.repeat_x = 14
            md.repeat_y = 14
            md.resolution = 7
            if hasattr(md, "viewport_resolution"):
                md.viewport_resolution = 7
            md.wave_scale = 0.55
            md.choppiness = 1.1
            md.wind_velocity = 9.0
            md.wave_alignment = 0.3
            md.wave_direction = math.radians(-90)
            md.depth = 200
            md.use_normals = True
            md.use_foam = True
            md.foam_layer_name = "foam"
            md.foam_coverage = 0.25
            md.random_seed = 6
            fc = near.driver_add('modifiers["Ocean"].time')
            fc.driver.type = "SCRIPTED"
            fc.driver.expression = "frame/%d" % FPS
            ok = True
        except Exception as ex:
            print("[06] Ocean modifier failed (%s) -> displaced grid fallback" % ex)
            near.modifiers.clear()
    if not ok:
        # fallback: subdivided grid + animated clouds displacement
        verts, faces = [], []
        n = 140
        for j in range(n):
            for i in range(n):
                verts.append((1400 * i / (n - 1), 1400 * (j / (n - 1)) ** 1.5, 0))
        faces = [(j * n + i, j * n + i + 1, (j + 1) * n + i + 1, (j + 1) * n + i)
                 for j in range(n - 1) for i in range(n - 1)]
        me.from_pydata(verts, [], faces)
        tex = bpy.data.textures.new("WaveTex", "CLOUDS")
        tex.noise_scale = 6.0
        drv = new_empty("WaveTexMover")
        for t in (0, 50):
            drv.location = (t * 1.5, t * 0.8, t * 0.3)
            drv.keyframe_insert("location", frame=F(t))
        d = near.modifiers.new("Displace", "DISPLACE")
        d.texture = tex
        d.texture_coords = "OBJECT"
        d.texture_coords_object = drv
        d.strength = 0.8
        wm = water_material(foam=False)
    for p in near.data.polygons:
        p.use_smooth = True
    apply_mat(near, wm)
    # far flat sea out to (and past) the horizon
    S = 45000
    far = mesh_obj("OceanFar", [(-S, -S, 0), (S, -S, 0), (S, S, 0), (-S, S, 0)], [(0, 1, 2, 3)], sea)
    far.location = (0, 0, -0.45)
    apply_mat(far, water_material("FarWaterMat", foam=False))

    # returning wave wall
    prof = [(120, 0.0), (60, 9.0), (22, 22.5), (6, 30.7), (-4, 33.0), (-12, 30.0), (-14, 24.0),
            (-9, 18.7), (-1.5, 12.0), (3.0, 4.5), (6.0, -3.0)]
    nxw = 220
    verts, faces = [], []
    for i in range(nxw):
        x = -3000 + 6000 * i / (nxw - 1)
        wob = 1.0 + 0.12 * math.sin(x * 0.004) + 0.06 * math.sin(x * 0.017)
        for (py, pz) in prof:
            verts.append((x, py * wob, pz * wob))
    m = len(prof)
    for i in range(nxw - 1):
        for k in range(m - 1):
            faces.append((i * m + k, (i + 1) * m + k, (i + 1) * m + k + 1, i * m + k + 1))
    wave = mesh_obj("WaveWall", verts, faces, smooth_shade=True)
    apply_mat(wave, wave_material())
    wave.scale = (1, 1, 0.01)
    wave.location = (0, 6000, -60)
    wave.keyframe_insert("location", frame=1)
    wave.keyframe_insert("scale", frame=1)
    for f in range(F(28.4), F(34.3) + 1, 3):
        t = (f - 1) / FPS
        u = (t - 28.4) / (34.25 - 28.4)
        u = max(0.0, min(1.0, u))
        y = 2600 - (2600 - 22) * (u ** 1.6)
        sc = 0.30 + 0.70 * smooth(0.0, 1.0, u)
        wave.location = (0, y, sea_level(t) - 0.5)
        wave.scale = (1, 1 + u * 0.6, sc)
        wave.keyframe_insert("location", frame=f)
        wave.keyframe_insert("scale", frame=f)
    wave.location = (0, 6000, -60)
    wave.scale = (1, 1, 0.01)
    wave.keyframe_insert("location", frame=F(34.35))
    wave.keyframe_insert("scale", frame=F(34.35))
    return sand, sea, near, far, wave


def build_boats():
    hull_m, nt = new_mat("HullMat")
    o = N(nt, "ShaderNodeOutputMaterial")
    b = N(nt, "ShaderNodeBsdfPrincipled")
    setin(b, "Base Color", (0.85, 0.83, 0.78, 1))
    setin(b, "Roughness", 0.4)
    L(nt, b, 0, o, "Surface")
    stripe_m, nt = new_mat("StripeMat")
    o = N(nt, "ShaderNodeOutputMaterial")
    b = N(nt, "ShaderNodeBsdfPrincipled")
    setin(b, "Base Color", (0.55, 0.06, 0.04, 1))
    L(nt, b, 0, o, "Surface")
    boats = []
    specs = [(-22.0, 62.0, 7.5, 25), (30.0, 118.0, 10.0, -35), (-70.0, 170.0, 8.0, 70)]
    for k, (bx, by, length, yaw) in enumerate(specs):
        beam, depth = length * 0.32, length * 0.16
        stations = 14
        verts, faces = [], []
        prof = [(-1.0, 1.0), (-0.92, 0.35), (-0.55, 0.0), (0.0, -0.08), (0.55, 0.0), (0.92, 0.35),
                (1.0, 1.0)]
        for s in range(stations):
            u = s / (stations - 1)
            yy = -length / 2 + length * u
            wfac = (1 - (2 * u - 1) ** 2) ** 0.45 if u > 0.5 else (1 - (2 * u - 1) ** 4) ** 0.35
            wfac = max(wfac, 0.03)
            for px, pz in prof:
                verts.append((px * beam / 2 * wfac, yy, (pz - 0.25) * depth + (0.25 * depth * max(0, u - 0.7))))
        m = len(prof)
        for s in range(stations - 1):
            for i in range(m - 1):
                faces.append((s * m + i, s * m + i + 1, (s + 1) * m + i + 1, (s + 1) * m + i))
        faces.append(tuple(s * m + 0 for s in range(stations)) + tuple(s * m + m - 1 for s in reversed(range(stations))))
        faces.append(tuple(range(m)))
        faces.append(tuple((stations - 1) * m + i for i in reversed(range(m))))
        boat = mesh_obj("Boat%d" % k, verts, faces, smooth_shade=False)
        apply_mat(boat, hull_m)
        # cabin + mast
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        me = bpy.data.meshes.new("Cabin")
        bm.to_mesh(me)
        bm.free()
        cab = link(bpy.data.objects.new("Cabin%d" % k, me), boat)
        cab.scale = (beam * 0.5, length * 0.25, depth * 0.8)
        cab.location = (0, -length * 0.12, depth * 0.95)
        apply_mat(cab, stripe_m if k == 1 else hull_m)
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.09, radius2=0.05, depth=length * 0.9)
        me = bpy.data.meshes.new("Mast")
        bm.to_mesh(me)
        bm.free()
        mast = link(bpy.data.objects.new("Mast%d" % k, me), boat)
        mast.location = (0, length * 0.1, depth * 0.75 + length * 0.45)
        apply_mat(mast, hull_m)
        boat.rotation_mode = "XYZ"
        rng = random.Random(10 + k)
        grounded_z = sand_z(by) + depth * 0.15
        for f in range(1, NFRAMES + 2, 3):
            t = (f - 1) / FPS
            sl = sea_level(t)
            float_z = sl + 0.12 * math.sin(t * 1.3 + k) - depth * 0.05
            if t >= 34.25:   # thrown towards the beach by the wave
                xx, yy = bx * 0.7 + 6 * k, by * 0.35 - 6
                ground = sand_z(yy) + depth * 0.15
            else:
                xx, yy = bx, by
                ground = grounded_z
            z = max(float_z, ground)
            g = 1.0 if ground > float_z else 0.0
            roll = 0.04 * math.sin(t * 1.1 + k) * (1 - g) + g * math.radians(14 if k != 1 else -11)
            pitch = 0.03 * math.sin(t * 0.9 + 2 * k) * (1 - g) + g * math.radians(3)
            yaw_r = math.radians(yaw) + (math.radians(55) if t >= 34.25 else 0.0)
            boat.location = (xx, yy, z)
            boat.rotation_euler = (pitch, roll, yaw_r)
            boat.keyframe_insert("location", frame=f)
            boat.keyframe_insert("rotation_euler", frame=f)
        boats.append(boat)
    return boats


def palm_materials():
    tm, nt = new_mat("TrunkMat")
    o = N(nt, "ShaderNodeOutputMaterial")
    b = N(nt, "ShaderNodeBsdfPrincipled")
    wv = N(nt, "ShaderNodeTexWave")
    setin(wv, "Scale", 4.0)
    wv.bands_direction = "Z" if hasattr(wv, "bands_direction") else wv.bands_direction
    tc = N(nt, "ShaderNodeTexCoord")
    L(nt, tc, "Object", wv, "Vector")
    r = ramp(nt, [(0.3, (0.16, 0.11, 0.07)), (0.8, (0.32, 0.24, 0.15))])
    L(nt, wv, "Fac", r, "Fac")
    L(nt, r, "Color", b, "Base Color")
    setin(b, "Roughness", 0.9)
    L(nt, b, 0, o, "Surface")
    lm, nt = new_mat("FrondMat")
    o = N(nt, "ShaderNodeOutputMaterial")
    b = N(nt, "ShaderNodeBsdfPrincipled")
    setin(b, "Base Color", (0.06, 0.16, 0.04, 1))
    setin(b, "Roughness", 0.55)
    L(nt, b, 0, o, "Surface")
    return tm, lm


def build_palm(name, base, height, lean, yaw, tm, lm, rng):
    # trunk curve
    cu = bpy.data.curves.new(name + "_trunk", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.2 * height / 9
    cu.bevel_resolution = 3
    sp = cu.splines.new("POLY")
    n = 12
    sp.points.add(n - 1)
    lx, ly = math.cos(yaw) * lean, math.sin(yaw) * lean
    pts = []
    for i in range(n):
        u = i / (n - 1)
        p = Vector((lx * u ** 1.8, ly * u ** 1.8, height * u))
        pts.append(p)
        sp.points[i].co = (p.x, p.y, p.z, 1.0)
        sp.points[i].radius = 1.35 - 0.6 * u
    trunk = link(bpy.data.objects.new(name, cu))
    trunk.location = base
    cu.materials.append(tm)
    crown = pts[-1]
    # fronds
    nf = 11
    for k in range(nf):
        ang = 2 * math.pi * k / nf + rng.uniform(-0.2, 0.2)
        length = height * rng.uniform(0.42, 0.55)
        droop = rng.uniform(0.55, 0.95)
        rise = rng.uniform(0.15, 0.45)
        segs = 16
        verts, faces = [], []
        for s in range(segs + 1):
            u = s / segs
            w = length * 0.13 * math.sin(math.pi * min(1, u * 1.05)) ** 0.7
            jag = 1.0 if s % 2 == 0 else 0.55
            w *= jag
            along = Vector((math.cos(ang), math.sin(ang), 0))
            side = Vector((-math.sin(ang), math.cos(ang), 0))
            c = along * (u * length) + Vector((0, 0, rise * length * u - droop * length * u * u))
            verts.append(c + side * w + Vector((0, 0, -w * 0.35)))
            verts.append(c + Vector((0, 0, 0.02)))
            verts.append(c - side * w + Vector((0, 0, -w * 0.35)))
        for s in range(segs):
            a = s * 3
            faces.append((a, a + 3, a + 4, a + 1))
            faces.append((a + 1, a + 4, a + 5, a + 2))
        fr = mesh_obj("%s_frond%d" % (name, k), verts, faces, trunk, smooth_shade=True)
        fr.location = crown
        apply_mat(fr, lm)
    # coconuts
    for k in range(4):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=0.16 * height / 9)
        me = bpy.data.meshes.new("Coco")
        bm.to_mesh(me)
        bm.free()
        c = link(bpy.data.objects.new(name + "_coco%d" % k, me), trunk)
        a = k * 1.7
        c.location = crown + Vector((0.25 * math.cos(a), 0.25 * math.sin(a), -0.25))
        apply_mat(c, tm)
    return trunk


def build_palms():
    tm, lm = palm_materials()
    rng = random.Random(21)
    palms = []
    # foreground framing palms
    palms.append(build_palm("PalmL", (-10.0, -8.0, sand_z(-8.0) - 0.2), 9.0, 2.6,
                            math.radians(-5), tm, lm, rng))
    palms.append(build_palm("PalmR", (12.5, 6.0, sand_z(6.0) - 0.2), 9.0, 2.6,
                            math.radians(160), tm, lm, rng))
    # headland on the left with a row of palms
    for i in range(9):
        x = -95 - i * 22 + rng.uniform(-5, 5)
        y = 25 + i * 18 + rng.uniform(-5, 5)
        palms.append(build_palm("PalmFar%d" % i, (x, y, sand_z(y) + 1.0), rng.uniform(8, 13),
                                rng.uniform(0.5, 3), rng.uniform(0, 6.28), tm, lm, rng))
    # low land on the left
    land_m, nt = new_mat("LandMat")
    o = N(nt, "ShaderNodeOutputMaterial")
    b = N(nt, "ShaderNodeBsdfPrincipled")
    setin(b, "Base Color", (0.05, 0.09, 0.04, 1))
    setin(b, "Roughness", 0.9)
    L(nt, b, 0, o, "Surface")
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=1.0)
    me = bpy.data.meshes.new("Headland")
    bm.to_mesh(me)
    bm.free()
    hl = link(bpy.data.objects.new("Headland", me))
    hl.scale = (260, 650, 9)
    hl.location = (-380, 520, -2.0)
    hl.rotation_euler = (0, 0, math.radians(-30))
    apply_mat(hl, land_m)
    return palms


def build_volcano():
    vm, nt = new_mat("VolcanoMat")
    o = N(nt, "ShaderNodeOutputMaterial")
    b = N(nt, "ShaderNodeBsdfPrincipled")
    setin(b, "Base Color", (0.035, 0.03, 0.03, 1))
    setin(b, "Roughness", 0.95)
    geo = N(nt, "ShaderNodeNewGeometry")
    sp = N(nt, "ShaderNodeSeparateXYZ")
    L(nt, geo, "Position", sp, 0)
    nz = N(nt, "ShaderNodeTexNoise")
    setin(nz, "Scale", 0.02)
    setin(nz, "Detail", 6.0)
    L(nt, geo, "Position", nz, "Vector")
    # lava near the top + streaks
    hm = N(nt, "ShaderNodeMapRange")
    nt.links.new(sp.outputs[2], sock(hm.inputs, "Value"))
    setin(hm, "From Min", 240.0)
    setin(hm, "From Max", 330.0)
    hm.clamp = True
    st = math_node(nt, "GREATER_THAN", sock(nz.outputs, "Fac"), 0.58)
    lava = math_node(nt, "MAXIMUM", hm.outputs[0], fout(math_node(nt, "MULTIPLY", fout(st), 0.6)))
    glow = N(nt, "ShaderNodeValue", label="Glow")
    es = math_node(nt, "MULTIPLY", fout(lava), glow.outputs[0])
    setin(b, "Emission Color", (1.0, 0.28, 0.05, 1))
    nt.links.new(fout(es), sock(b.inputs, "Emission Strength"))
    L(nt, b, 0, o, "Surface")
    # cone mesh
    verts, faces = [], []
    rings_n, seg = 14, 64
    H, Rb, Rt = 340.0, 1300.0, 70.0
    vr = random.Random(5)
    for j in range(rings_n):
        u = j / (rings_n - 1)
        r = Rb * (1 - u) ** 1.6 + Rt * u
        z = H * u
        for i in range(seg):
            a = 2 * math.pi * i / seg
            rr = r * (1 + 0.06 * vr.uniform(-1, 1))
            verts.append((rr * math.cos(a), rr * math.sin(a), z if j < rings_n - 1 else z - 25))
    for j in range(rings_n - 1):
        for i in range(seg):
            k = (i + 1) % seg
            faces.append((j * seg + i, j * seg + k, (j + 1) * seg + k, (j + 1) * seg + i))
    faces.append(tuple((rings_n - 1) * seg + i for i in range(seg)))
    vol = mesh_obj("Volcano", verts, faces, smooth_shade=True)
    vol.location = (-1500, 5200, -5)
    apply_mat(vol, vm)
    gs = glow.outputs[0]
    key_val(gs, 1, 0.0)
    key_val(gs, F(35.5), 0.0)
    key_val(gs, F(38.0), 18.0)
    key_val(gs, F(41.0), 30.0)
    key_val(gs, F(49.0), 26.0)
    # fake glow billboard above the crater
    gm, nt = new_mat("VolcanoGlowMat")
    o = N(nt, "ShaderNodeOutputMaterial")
    tc = N(nt, "ShaderNodeTexCoord")
    gr = N(nt, "ShaderNodeTexGradient")
    gr.gradient_type = "SPHERICAL"
    L(nt, tc, "Object", gr, "Vector")
    gpow = math_node(nt, "POWER", sock(gr.outputs, "Fac"), 2.2)
    gglow = N(nt, "ShaderNodeValue", label="GlowAlpha")
    ga = math_node(nt, "MULTIPLY", fout(gpow), gglow.outputs[0])
    em = N(nt, "ShaderNodeEmission")
    setin(em, "Color", (1.0, 0.35, 0.08, 1))
    setin(em, "Strength", 4.0)
    tr = N(nt, "ShaderNodeBsdfTransparent")
    mx = N(nt, "ShaderNodeMixShader")
    nt.links.new(fout(ga), mx.inputs[0])
    L(nt, tr, 0, mx, 1)
    L(nt, em, 0, mx, 2)
    L(nt, mx, 0, o, "Surface")
    set_blend(gm, True)
    bb = mesh_obj("VolcanoGlow", [(-1, 0, -1), (1, 0, -1), (1, 0, 1), (-1, 0, 1)], [(0, 1, 2, 3)])
    bb.scale = (420, 1, 330)
    bb.location = (-1500, 5150, 330)
    apply_mat(bb, gm)
    no_ray_vis(bb)
    a = gglow.outputs[0]
    key_val(a, 1, 0.0)
    key_val(a, F(35.5), 0.0)
    key_val(a, F(39.0), 0.75)
    key_val(a, F(42.0), 0.9)
    key_val(a, F(49.0), 0.85)
    return vol


def build_lights(saturn_dir):
    # golden-hour sun behind the camera
    sd = bpy.data.lights.new("SunEarth", "SUN")
    sd.color = (1.0, 0.62, 0.36)
    sd.angle = math.radians(1.5)
    sun = link(bpy.data.objects.new("SunEarth", sd))
    to_sun = Vector((SUN_AZ_VEC.x, SUN_AZ_VEC.y, math.tan(math.radians(SUN_EL0)))).normalized()
    sun.rotation_mode = "QUATERNION"
    sun.rotation_quaternion = (-to_sun).to_track_quat("-Z", "Y")
    for t, e in ((0.0, 3.2), (6.0, 2.2), (10.0, 0.4), (12.0, 0.0)):
        sd.energy = e
        sd.keyframe_insert("energy", frame=F(t))
    # Saturn-shine (sunlit rings + planet light the beach at night)
    ld = bpy.data.lights.new("SaturnShine", "SUN")
    ld.color = (1.0, 0.9, 0.74)
    ld.angle = math.radians(25)
    sl = link(bpy.data.objects.new("SaturnShine", ld))
    sl.rotation_mode = "QUATERNION"
    sl.rotation_quaternion = (-saturn_dir).to_track_quat("-Z", "Y")
    for t, e in ((0.0, 0.0), (7.0, 0.0), (14.0, 0.9), (50.0, 0.9)):
        ld.energy = e
        ld.keyframe_insert("energy", frame=F(t))
    # volcano point light (far)
    pd = bpy.data.lights.new("VolcanoLight", "POINT")
    pd.color = (1.0, 0.35, 0.1)
    pd.shadow_soft_size = 50
    pl = link(bpy.data.objects.new("VolcanoLight", pd))
    pl.location = (-1500, 5200, 450)
    for t, e in ((0.0, 0.0), (35.5, 0.0), (39.0, 3.0e8), (49.0, 2.6e8)):
        pd.energy = e
        pd.keyframe_insert("energy", frame=F(t))
    return sun, sl


# =============================================================================
# Verification
# =============================================================================
def verify(scene, cam, planet, rings, theta_start, pose):
    C = CONFIG
    print("\n" + "=" * 70)
    print("[06] VERIFICATION - Saturn at the Moon's distance")
    print("=" * 70)
    ok = True

    def check(cond, msg):
        nonlocal ok
        print(("  OK   " if cond else "  FAIL ") + msg)
        ok = ok and cond

    d_km, R_km, Ra_km = C["moon_distance_km"], C["saturn_eq_radius_km"], C["ring_A_outer_km"]
    ang_s_atan = 2 * math.degrees(math.atan(R_km / d_km))
    ang_s_asin = 2 * math.degrees(math.asin(R_km / d_km))
    ang_r = 2 * math.degrees(math.atan(Ra_km / d_km))
    moon_ang = 2 * math.degrees(math.atan(C["moon_radius_km"] / d_km))
    print("  Real numbers: Saturn eq. radius %.0f km, A-ring outer radius %.0f km, distance %.0f km"
          % (R_km, Ra_km, d_km))
    print("  Analytic: Saturn 2*atan(R/d) = %.2f deg (true limb 2*asin(R/d) = %.2f deg), "
          "rings 2*atan(Ra/d) = %.2f deg, Moon = %.3f deg -> Saturn = %.1f Moon widths"
          % (ang_s_atan, ang_s_asin, ang_r, moon_ang, ang_s_atan / moon_ang))
    print("  Scene scale: %.0f km -> %.1f m ; Saturn R = %.2f m ; ring outer R = %.2f m"
          % (d_km, D_M, SAT_R, RING_OUT))

    # --- measure from evaluated scene geometry, as seen from the camera ----
    for t in (12.0, 20.0, 40.0):
        scene.frame_set(F(t))
        dg = bpy.context.evaluated_depsgraph_get()
        camw = cam.matrix_world.translation.copy()
        pe = planet.evaluated_get(dg)
        Mw = pe.matrix_world
        centre = Mw.translation.copy()
        verts = [Mw @ v.co for v in pe.data.vertices]
        dist = (centre - camw).length
        R_meas = max((p - centre).length for p in verts)            # equatorial radius
        view = (centre - camw).normalized()
        # flat-disc convention (what the 17.8 deg figure uses) + true sphere silhouette
        perp = view.cross(Vector((0, 0, 1))).normalized()
        a = (centre + perp * R_meas - camw).normalized()
        b = (centre - perp * R_meas - camw).normalized()
        sat_disc = math.degrees(a.angle(b))
        sat_limb = 2 * math.degrees(math.asin(R_meas / dist))
        re = rings.evaluated_get(dg)
        Mr = re.matrix_world
        rv = [Mr @ v.co for v in re.data.vertices]
        rc = Mr.translation
        outer = [p for p in rv if abs((p - rc).length - RING_OUT) < 1e-3 * RING_OUT]
        best = 0.0
        nO = len(outer)
        for i in range(nO // 2):
            p1, p2 = outer[i], outer[i + nO // 2]
            best = max(best, math.degrees((p1 - camw).angle(p2 - camw)))
        # in-frame check (all ring rim + limb points inside the image)
        from bpy_extras.object_utils import world_to_camera_view
        pts = outer[::8] + [centre + perp * R_meas, centre - perp * R_meas]
        ndc = [world_to_camera_view(scene, cam, p) for p in pts]
        inside = all(0.0 <= q.x <= 1.0 and 0.0 <= q.y <= 1.0 and q.z > 0 for q in ndc)
        print("    ring/limb NDC x %.3f..%.3f  y %.3f..%.3f" % (min(q.x for q in ndc), max(q.x for q in ndc),
              min(q.y for q in ndc), max(q.y for q in ndc)))
        q1 = world_to_camera_view(scene, cam, centre + perp * R_meas)
        q2 = world_to_camera_view(scene, cam, centre - perp * R_meas)
        px = abs(q1.x - q2.x) * C["resolution"][0]
        elev = math.degrees(math.asin((centre - camw).z / dist))
        print("  t=%4.1fs camera->Saturn %.2f m (= %.0f km) | Saturn disc %.2f deg (limb %.2f) | "
              "rings %.2f deg | Saturn %.0f px wide of 1080 | centre elev %.1f deg | in frame: %s"
              % (t, dist, dist / KM2M, sat_disc, sat_limb, best, px, elev, inside))
        if t == 12.0:
            check(abs(sat_disc - 17.8) < 0.15, "Saturn angular diameter %.2f deg ~ 17.8 deg" % sat_disc)
            check(abs(best - 39.2) < 0.4, "Ring angular diameter %.2f deg ~ 39 deg" % best)
            check(inside, "Saturn + full rings fit inside the 50 deg-wide portrait frame")
            h_fov = 2 * math.degrees(math.atan(18.0 / cam.data.lens))
            check(abs(h_fov - C["h_fov_deg"]) < 0.01, "Camera horizontal FOV %.2f deg (lens %.2f mm, 36 mm sensor)"
                  % (h_fov, cam.data.lens))
    # rise: below horizon at 3 s, above at 12 s
    scene.frame_set(F(3.0))
    camw = cam.matrix_world.translation.copy()
    rv = [rings.matrix_world @ v.co for v in rings.data.vertices]
    top3 = max(math.degrees(math.asin((p - camw).z / (p - camw).length)) for p in rv)
    scene.frame_set(F(12.0))
    camw = cam.matrix_world.translation.copy()
    pv = [planet.matrix_world @ v.co for v in list(planet.data.vertices)[::7]]
    low12 = min(math.degrees(math.asin((p - camw).z / (p - camw).length)) for p in pv)
    check(top3 < 0.0, "At 3 s the whole ring system is below the horizon (top %.2f deg)" % top3)
    check(low12 > 0.0, "At 12 s the whole planet is above the horizon (lowest %.2f deg)" % low12)

    # --- physics -------------------------------------------------------------
    G, Ms, Mm, Me = C["G"], C["saturn_mass_kg"], C["moon_mass_kg"], C["earth_mass_kg"]
    R_e = C["earth_radius_km"] * 1e3
    d = d_km * 1e3
    ratio = Ms / Mm
    check(7500 < ratio < 8000, "Mass ratio Saturn/Moon = %.0f (~7,700)" % ratio)
    a_tide = 2 * G * Ms * R_e / d ** 3
    a_tide_moon = 2 * G * Mm * R_e / d ** 3
    frac = a_tide / C["g"]
    check(frac < 1e-3, "Tidal acceleration 2GMR/d^3 = %.5f m/s^2 = %.3f %% of g (< 0.1 %%); "
          "Moon today: %.2e m/s^2" % (a_tide, frac * 100, a_tide_moon))
    # equilibrium tide height (Newtonian, no Love numbers) for context
    h_moon = 1.5 * (Mm / Me) * (R_e / d) ** 3 * R_e
    h_sat = h_moon * ratio
    print("  Equilibrium tide bulge: Moon %.2f m -> Saturn %.0f m (static upper bound; real oceans "
          "respond dynamically - the brief's 'hundreds of m' is what we show)" % (h_moon, h_sat))
    retreat = C["tide_drop_m"] / SLOPE
    check(200 <= retreat <= 600, "On-screen sea drop %.0f m on a %.0f%% beach -> shoreline retreats %.0f m"
          % (C["tide_drop_m"], SLOPE * 100, retreat))
    rs, re_ = C["saturn_density"], C["earth_density"]
    Rs_km = R_km
    roche_fluid = 2.44 * Rs_km * (rs / re_) ** (1 / 3)
    roche_fluid2 = 2.455 * Rs_km * (rs / re_) ** (1 / 3)
    roche_rigid = 1.26 * Rs_km * (rs / re_) ** (1 / 3)
    print("  Roche limit (Earth near Saturn): fluid d = 2.44 R_S (rho_S/rho_E)^(1/3) = %.0f km "
          "(2.455 coefficient: %.0f km); rigid-body 1.26 coefficient: %.0f km"
          % (roche_fluid, roche_fluid2, roche_rigid))
    check(70_000 < roche_fluid < 76_000, "Fluid Roche limit %.0f km ~ 73,000 km (%.1fx closer than the Moon)"
          % (roche_fluid, d_km / roche_fluid))
    check(abs(C["duration_s"] - 50) < 1e-6 and NFRAMES == 1500, "Duration 50 s @ 30 fps = %d frames" % NFRAMES)
    print("  RESULT: %s" % ("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED"))
    print("=" * 70 + "\n")
    scene.frame_set(1)
    assert ok, "[06] verification failed"
    return ok


# =============================================================================
# Main
# =============================================================================
def main():
    clean_scene()
    scene = bpy.context.scene
    out_dir = setup_render(scene)
    build_world(scene)
    rig, cam = build_camera(scene)
    pivot = Vector((0.0, cam_base_y(0.0), sand_z(cam_base_y(0.0)) + CONFIG["eye_height_m"]))
    system, planet, rings, sdir, theta_start, theta_at, pose = build_saturn(pivot)
    build_beach(scene)
    build_boats()
    build_palms()
    build_volcano()
    build_lights(sdir)
    build_overlays(cam)
    scene.frame_set(1)
    verify(scene, cam, planet, rings, theta_start, pose)

    if FRAMES_ARG:
        frames = [int(x) for x in FRAMES_ARG.split(",") if x.strip()]
        ims = scene.render.image_settings
        if hasattr(ims, "media_type"):
            try:
                ims.media_type = "IMAGE"
            except Exception:
                pass
        ims.file_format = "PNG"
        for f in frames:
            scene.frame_set(f)
            scene.render.filepath = os.path.join(out_dir, "frame_%04d.png" % f)
            bpy.ops.render.render(write_still=True)
            print("[06] wrote", scene.render.filepath)
    elif (CONFIG["RENDER"] or CONFIG["PREVIEW"]) and not VERIFY_ONLY:
        set_video_output(scene, out_dir)
        print("[06] rendering %d frames -> %s" % (NFRAMES, scene.render.filepath))
        bpy.ops.render.render(animation=True)
    print("[06] done. engine=%s out=%s" % (scene.render.engine, out_dir))


main()
