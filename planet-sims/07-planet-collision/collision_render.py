"""
collision_render.py - final "NASA look" renderer for planet-collision caches.

Reads a particle cache written by collision_sim.py (meta.json + frame_00000.npz ...)
and renders it as glowing molten material: volumetric SPH-kernel bulk (Points to
Volume, split into temperature bands with a blackbody-like colour ramp), a faint
hot "heat haze" volume, tiny emissive sparkle/debris points, compositor bloom +
fog glow, a sparse faint starfield, an auto-framing slow camera and thin captions.

Run in Blender (Scripting tab, press Run) or headless:
    blender -b -P collision_render.py -- --cache /path/to/cache/theia --preset theia --render
    blender -b -P collision_render.py -- --cache ... --preview          # few tiny Cycles stills
Options after "--":
    --cache DIR  --preset NAME  --render  --preview  --engine CYCLES|EEVEE
    --frames START END  --res W H  --samples N  --out DIR  --stills f1,f2,..
Works with Blender 4.2 LTS ... 5.x.
"""

import bpy
import json
import math
import os
import sys
import time

import numpy as np

# ----------------------------------------------------------------------------- CONFIG
CONFIG = dict(
    PRESET="theia",              # theia | moon_hits_earth | mars_vs_earth | earth_into_jupiter | two_earths | speed_series
    CACHE_DIR="",                # "" -> <script dir>/cache/<PRESET>
    OUTPUT_DIR="",               # "" -> <script dir>/renders/07-planet-collision/<PRESET>/
    RENDER=False,                # render the whole animation when the script runs
    PREVIEW=False,               # tiny fast Cycles stills (approach/contact/arms/re-collapse)
    ENGINE="EEVEE",              # EEVEE (fast) | CYCLES (best volumes, slower)
    RESOLUTION=(1080, 1920),
    FPS=30,
    SAMPLES_EEVEE=64,
    SAMPLES_CYCLES=96,
    DENOISE=True,
    # time mapping: each cache frame becomes INTERP_STEPS output frames (Catmull-Rom between them)
    INTERP_STEPS=2,
    CACHE_FRAME_START=0,
    CACHE_FRAME_END=-1,          # -1 = last cache frame
    # look
    TEMP_BANDS=(0.0, 0.25, 0.42, 0.58, 0.72, 0.86, 1.01),   # temperature band edges (temp is 0..1)
    TEMP_GAMMA=1.0,              # >1 = cooler overall, <1 = hotter
    RADIUS_FACTOR=1.4, 
    MAX_RADIUS_H=2.0,            # cap volume radius at this * bulk h, so sparse ejecta stay thin filaments          # Points-to-Volume radius = h * this
    VOXEL_FACTOR=0.42,           # voxel size = median(h of bulk) * this (smaller = sharper, slower)
    MAX_VOXEL_SIZE=0.08,         # Earth radii
    MIN_VOXEL_SIZE=0.006,
    VOLUME_STEP_RATE=1.0,        # Cycles: >1 = faster, coarser volume ray marching
    SMOOTH_ITER=2,               # Blender 5.x only: grid blur passes on the density (0 = off)
    VOLUME_DENSITY=26.0,         # optical density of the molten bulk (higher = more solid surface)
    EMISSION=1.0,                # overall glow strength of the bulk
    EMISSION_FLOOR=0.45,
    EMISSION_HOT=0.8,            # extra glow of the hottest material (too high -> clipped white)         # glow of the coolest material (molten bodies self-luminous)
    ALBEDO=(0.55, 0.22, 0.07),    # scattering colour (lit by the sun lamp -> day/night shading)
    HAZE=True, HAZE_TEMP=0.55, HAZE_RADIUS=3.2, HAZE_DENSITY=0.10, HAZE_EMISSION=5.0,
    SPARKLE=True,                # tiny emissive points for every particle (grain + debris)
    SPARKLE_RADIUS=0.22,         # * h
    SPARKLE_MAX_RADIUS=0.012,    # Earth radii
    SPARKLE_EMISSION=3.0,
    DEBRIS_H=2.2,                # particles with h > this * bulk h are sparse debris: drawn as glowing dots, not volume
    DEBRIS_RADIUS=0.30,          # debris dot radius (* bulk h)
    SUN_STRENGTH=3.0, SUN_DIR=(-0.55, 0.35, 0.45),
    COMPOSITOR_CPU=False,        # force CPU compositing (always on in background mode)
    GLARE=True, BLOOM_SIZE=0.6, FOG_GLOW_MIX=0.35, GLARE_THRESHOLD=0.8,
    VIEW_TRANSFORM="Standard",   # Standard keeps the saturated NASA orange; AgX/Filmic wash hot areas to pink-white
    VIEW_LOOK="None",   # falls back to plain AgX / Filmic if missing
    EXPOSURE=0.0,
    STARS=900, STAR_BRIGHTNESS=0.6,
    # camera
    LENS_MM=50,
    CAM_ELEVATION=22.0,          # degrees above the collision plane
    CAM_AZIMUTH=-80.0,           # degrees, start
    CAM_ORBIT=18.0,              # degrees of slow orbit over the whole video
    CAM_ROLL=0.0,                # 90 puts the orbital plane vertical in the 9:16 frame
    CAM_FIT_PERCENTILE=99.5,     # fraction of particles kept in frame
    CAM_MARGIN=1.25,
    CAM_MIN_EXTENT=1.6,          # Earth radii (half height of the view at least)
    CAM_SMOOTH_S=1.5,            # gaussian smoothing of auto-framing (seconds)
    CAM_PUSH=0.10,               # slow push-in over the video (fraction of distance)
    DOF=False, F_STOP=4.0,       # scene is ~10 units across, so DOF is subtle; it also softens captions
    MOTION_BLUR=False, SHUTTER=0.5,
    # text
    FONT_PATH="",                # optional .ttf/.otf (e.g. a light sans); "" = Blender default
    CAPTION_SIZE=0.042,          # fraction of frame height
    SHOW_CLOCK=True,
    SHOW_CREDIT=True,
    FADE_S=0.4,
)

PRESETS = {
    "theia": dict(
        title="",
        captions=[(0.3, "4.5 billion years ago, a Mars-sized world"),
                  (3.5, "slammed into the young Earth"),
                  (7.0, "Molten debris is flung into space"),
                  (11.0, "and some of it becomes the Moon")]),
    "moon_hits_earth": dict(
        title="",
        captions=[(0.3, "What if the Moon crashed into Earth?"),
                  (4.0, "Impact at 2.4 km/s"),
                  (8.0, "Both worlds melt within hours")]),
    "mars_vs_earth": dict(
        title="",
        captions=[(0.3, "Mars vs Earth"),
                  (4.0, "A head-on collision"),
                  (8.0, "Mars doesn't survive")]),
    "earth_into_jupiter": dict(
        title="",
        captions=[(0.3, "What if Earth fell into Jupiter?"),
                  (4.0, "Jupiter is 318 times heavier"),
                  (8.0, "Earth is swallowed whole")]),
    "two_earths": dict(
        title="",
        captions=[(0.3, "Two Earths collide"),
                  (4.0, "Equal mass, glancing blow"),
                  (8.0, "They merge into one molten world")]),
    "speed_series": dict(
        title="",
        captions=[(0.3, "Same collision, different speeds"),
                  (4.0, "Slow: they merge"),
                  (8.0, "Fast: they shatter")]),
}

# colour ramp used for the bands: temperature (0..1) -> emission colour (blackbody-like)
RAMP = [(0.00, (0.70, 0.130, 0.020)),
        (0.25, (1.00, 0.260, 0.040)),
        (0.45, (1.00, 0.380, 0.070)),
        (0.62, (1.00, 0.490, 0.110)),
        (0.78, (1.00, 0.620, 0.220)),
        (0.92, (1.00, 0.760, 0.420)),
        (1.00, (1.00, 0.860, 0.620))]

PFX = "PC_"
SCENE_NAME = "07_Collision"
STATE = {}


# ----------------------------------------------------------------------------- utils
def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    c = CONFIG
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--render": c["RENDER"] = True
        elif a == "--preview": c["PREVIEW"] = True
        elif a == "--cache": c["CACHE_DIR"] = argv[i + 1]; i += 1
        elif a == "--preset": c["PRESET"] = argv[i + 1]; i += 1
        elif a == "--engine": c["ENGINE"] = argv[i + 1].upper(); i += 1
        elif a == "--out": c["OUTPUT_DIR"] = argv[i + 1]; i += 1
        elif a == "--samples": c["SAMPLES_CYCLES"] = c["SAMPLES_EEVEE"] = int(argv[i + 1]); i += 1
        elif a == "--res": c["RESOLUTION"] = (int(argv[i + 1]), int(argv[i + 2])); c["_RESSET"] = True; i += 2
        elif a == "--frames": c["_FRAMES"] = (int(argv[i + 1]), int(argv[i + 2])); i += 2
        elif a == "--stills": c["_STILLS"] = [int(x) for x in argv[i + 1].split(",")]; i += 1
        elif a == "--set":  # --set KEY=VALUE (python literal)
            k, v = argv[i + 1].split("=", 1); c[k] = eval(v); i += 1
        i += 1


def script_dir():
    try:
        p = bpy.path.abspath("//")
        if p:
            return p
    except Exception:
        pass
    return os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()


def ramp(t):
    t = float(np.clip(t, 0, 1))
    for (a, ca), (b, cb) in zip(RAMP[:-1], RAMP[1:]):
        if t <= b:
            f = (t - a) / max(b - a, 1e-6)
            return tuple(ca[k] * (1 - f) + cb[k] * f for k in range(3))
    return RAMP[-1][1]


def set_in(node, name, value, prop=None, prop_value=None):
    """Set a node option that is a socket in 5.x and a property in 4.x."""
    if name in node.inputs:
        try:
            node.inputs[name].default_value = value
            return
        except Exception:
            pass
    if prop and hasattr(node, prop):
        try:
            setattr(node, prop, prop_value if prop_value is not None else value)
        except Exception as e:
            print("warn: cannot set", prop, e)


def engine_id(want):
    items = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    if want.upper().startswith("EEVEE"):
        for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
            if e in items:
                return e
    return "CYCLES"


# ----------------------------------------------------------------------------- cache
class Cache:
    def __init__(self, d):
        self.dir = d
        self.meta = json.load(open(os.path.join(d, "meta.json")))
        self.files = sorted(f for f in os.listdir(d) if f.startswith("frame_") and f.endswith(".npz"))
        if not self.files:
            raise RuntimeError("no frame_*.npz in " + d)
        self.n = int(np.load(os.path.join(d, self.files[0]))["pos"].shape[0])
        self._lru = {}

    def __len__(self):
        return len(self.files)

    def get(self, i):
        i = int(np.clip(i, 0, len(self.files) - 1))
        if i not in self._lru:
            z = np.load(os.path.join(self.dir, self.files[i]))
            d = dict(pos=z["pos"].astype(np.float32),
                     temp=z["temp"].astype(np.float32) if "temp" in z else np.zeros(self.n, np.float32),
                     h=z["h"].astype(np.float32) if "h" in z else np.full(self.n, 0.05, np.float32),
                     mat=z["mat"].astype(np.int32) if "mat" in z else np.zeros(self.n, np.int32),
                     t=float(z["t"]) if "t" in z else None)
            if "absorbed" in z:            # e.g. swallowed by Jupiter: hide from every layer
                d["temp"] = np.where(z["absorbed"].astype(bool), -1.0, d["temp"]).astype(np.float32)
            if len(self._lru) > 6:
                self._lru.pop(next(iter(self._lru)))
            self._lru[i] = d
        return self._lru[i]

    def sample(self, x):
        """Catmull-Rom interpolation at fractional cache index x."""
        i0 = int(math.floor(x))
        f = x - i0
        a, b = self.get(i0), self.get(i0 + 1)
        if f < 1e-4 or i0 + 1 >= len(self.files):
            return a
        p0, p3 = self.get(i0 - 1)["pos"], self.get(i0 + 2)["pos"]
        p1, p2 = a["pos"], b["pos"]
        f2, f3 = f * f, f * f * f
        pos = 0.5 * ((2 * p1) + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f2 + (-p0 + 3 * p1 - 3 * p2 + p3) * f3)
        out = dict(pos=pos.astype(np.float32),
                   temp=a["temp"] * (1 - f) + b["temp"] * f,
                   h=a["h"] * (1 - f) + b["h"] * f, mat=a["mat"],
                   t=None if a["t"] is None or b["t"] is None else a["t"] * (1 - f) + b["t"] * f)
        return out

    def hours(self, x, d):
        tu = float(self.meta.get("time_unit_hours", 1.0))
        if d.get("t") is not None:
            return d["t"] * tu
        for k in ("frame_dt_hours", "hours_per_frame"):
            if k in self.meta:
                return x * float(self.meta[k])
        if "frame_dt" in self.meta:
            return x * float(self.meta["frame_dt"]) * tu
        return x * tu


# ----------------------------------------------------------------------------- scene
def clean():
    col = bpy.data.collections.get(PFX + "Collision")
    if col:
        for o in list(col.all_objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(col)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.node_groups, bpy.data.cameras,
                 bpy.data.lights, bpy.data.curves, bpy.data.volumes, bpy.data.pointclouds):
        for d in list(coll):
            if d.name.startswith(PFX) and d.users == 0:
                coll.remove(d)
    for h in list(bpy.app.handlers.frame_change_pre):
        if getattr(h, "__name__", "") == "pc_frame_change":
            bpy.app.handlers.frame_change_pre.remove(h)


def new_obj(name, data, col):
    o = bpy.data.objects.new(PFX + name, data)
    col.objects.link(o)
    return o


def no_secondary(o):
    for a in ("visible_shadow", "visible_diffuse", "visible_glossy", "visible_transmission", "visible_volume_scatter"):
        if hasattr(o, a):
            setattr(o, a, False)


def gn_group(name, build):
    ng = bpy.data.node_groups.new(PFX + name, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    gi = ng.nodes.new("NodeGroupInput")
    go = ng.nodes.new("NodeGroupOutput")
    build(ng, gi, go)
    return ng


def add_socket(ng, name, typ, default=None):
    s = ng.interface.new_socket(name, in_out="INPUT", socket_type=typ)
    if default is not None:
        s.default_value = default
    return s


def set_mod_input(mod, ng, name, value):
    for item in ng.interface.items_tree:
        if getattr(item, "in_out", None) == "INPUT" and item.name == name:
            if hasattr(mod, "properties") and hasattr(mod.properties, "inputs"):   # 5.2+
                getattr(mod.properties.inputs, item.identifier).value = value
            else:                                                                  # 4.2 .. 5.1
                mod[item.identifier] = value
            return
    raise KeyError(name)


def build_volume_group():
    def b(ng, gi, go):
        add_socket(ng, "TMin", "NodeSocketFloat", 0.0)
        add_socket(ng, "TMax", "NodeSocketFloat", 1.0)
        add_socket(ng, "RadiusFactor", "NodeSocketFloat", 1.0)
        add_socket(ng, "MaxRadius", "NodeSocketFloat", 1.0)
        add_socket(ng, "MaxH", "NodeSocketFloat", 100.0)
        add_socket(ng, "VoxelSize", "NodeSocketFloat", 0.03)
        add_socket(ng, "Density", "NodeSocketFloat", 1.0)
        add_socket(ng, "Material", "NodeSocketMaterial")
        N = ng.nodes
        L = ng.links
        temp = N.new("GeometryNodeInputNamedAttribute"); temp.data_type = "FLOAT"; temp.inputs["Name"].default_value = "temp"
        hh = N.new("GeometryNodeInputNamedAttribute"); hh.data_type = "FLOAT"; hh.inputs["Name"].default_value = "h"
        ge = N.new("FunctionNodeCompare"); ge.data_type = "FLOAT"; ge.operation = "GREATER_EQUAL"
        lt = N.new("FunctionNodeCompare"); lt.data_type = "FLOAT"; lt.operation = "LESS_THAN"
        L.new(temp.outputs["Attribute"], ge.inputs[0]); L.new(gi.outputs["TMin"], ge.inputs[1])
        L.new(temp.outputs["Attribute"], lt.inputs[0]); L.new(gi.outputs["TMax"], lt.inputs[1])
        band0 = N.new("FunctionNodeBooleanMath"); band0.operation = "AND"
        L.new(ge.outputs[0], band0.inputs[0]); L.new(lt.outputs[0], band0.inputs[1])
        dense = N.new("FunctionNodeCompare"); dense.data_type = "FLOAT"; dense.operation = "LESS_THAN"
        L.new(hh.outputs["Attribute"], dense.inputs[0]); L.new(gi.outputs["MaxH"], dense.inputs[1])
        band = N.new("FunctionNodeBooleanMath"); band.operation = "AND"
        L.new(band0.outputs[0], band.inputs[0]); L.new(dense.outputs[0], band.inputs[1])
        sep = N.new("GeometryNodeSeparateGeometry"); sep.domain = "POINT"
        L.new(gi.outputs["Geometry"], sep.inputs["Geometry"]); L.new(band.outputs[0], sep.inputs["Selection"])
        rad = N.new("ShaderNodeMath"); rad.operation = "MULTIPLY"
        L.new(hh.outputs["Attribute"], rad.inputs[0]); L.new(gi.outputs["RadiusFactor"], rad.inputs[1])
        radc = N.new("ShaderNodeMath"); radc.operation = "MINIMUM"
        L.new(rad.outputs[0], radc.inputs[0]); L.new(gi.outputs["MaxRadius"], radc.inputs[1])
        ptv = N.new("GeometryNodePointsToVolume")
        set_in(ptv, "Resolution Mode", "Size", "resolution_mode", "VOXEL_SIZE")
        L.new(sep.outputs["Selection"], ptv.inputs["Points"])
        L.new(radc.outputs[0], ptv.inputs["Radius"])
        L.new(gi.outputs["VoxelSize"], ptv.inputs["Voxel Size"])
        L.new(gi.outputs["Density"], ptv.inputs["Density"])
        vol_out = ptv.outputs[0]
        it = int(CONFIG["SMOOTH_ITER"])
        if it > 0 and hasattr(bpy.types, "GeometryNodeGridMean"):
            # Blender 5.x: blur the density grid -> smooth molten surface instead of a union of spheres
            gg = N.new("GeometryNodeGetNamedGrid"); gg.data_type = "FLOAT"
            gg.inputs["Name"].default_value = "density"
            dil = N.new("GeometryNodeGridDilateAndErode"); dil.data_type = "FLOAT"
            dil.inputs["Steps"].default_value = it + 1
            mean = N.new("GeometryNodeGridMean"); mean.data_type = "FLOAT"
            mean.inputs["Width"].default_value = 1
            mean.inputs["Iterations"].default_value = it
            st = N.new("GeometryNodeStoreNamedGrid"); st.data_type = "FLOAT"
            st.inputs["Name"].default_value = "density"
            L.new(ptv.outputs[0], gg.inputs["Volume"])
            L.new(gg.outputs["Grid"], dil.inputs["Grid"]); L.new(dil.outputs["Grid"], mean.inputs["Grid"])
            L.new(gg.outputs["Volume"], st.inputs["Volume"]); L.new(mean.outputs["Grid"], st.inputs["Grid"])
            vol_out = st.outputs[0]
        sm = N.new("GeometryNodeSetMaterial")
        L.new(vol_out, sm.inputs["Geometry"]); L.new(gi.outputs["Material"], sm.inputs["Material"])
        L.new(sm.outputs[0], go.inputs["Geometry"])
    return gn_group("BandVolume", b)


def build_points_group():
    def b(ng, gi, go):
        add_socket(ng, "RadiusFactor", "NodeSocketFloat", 0.2)
        add_socket(ng, "MaxRadius", "NodeSocketFloat", 0.01)
        add_socket(ng, "DebrisH", "NodeSocketFloat", 0.12)
        add_socket(ng, "DebrisRadius", "NodeSocketFloat", 0.02)
        add_socket(ng, "Material", "NodeSocketMaterial")
        N, L = ng.nodes, ng.links
        hh = N.new("GeometryNodeInputNamedAttribute"); hh.data_type = "FLOAT"; hh.inputs["Name"].default_value = "h"
        rad = N.new("ShaderNodeMath"); rad.operation = "MULTIPLY"
        L.new(hh.outputs["Attribute"], rad.inputs[0]); L.new(gi.outputs["RadiusFactor"], rad.inputs[1])
        radc = N.new("ShaderNodeMath"); radc.operation = "MINIMUM"
        L.new(rad.outputs[0], radc.inputs[0]); L.new(gi.outputs["MaxRadius"], radc.inputs[1])
        isdeb = N.new("FunctionNodeCompare"); isdeb.data_type = "FLOAT"; isdeb.operation = "GREATER_THAN"
        L.new(hh.outputs["Attribute"], isdeb.inputs[0]); L.new(gi.outputs["DebrisH"], isdeb.inputs[1])
        sw = N.new("GeometryNodeSwitch"); sw.input_type = "FLOAT"
        L.new(isdeb.outputs[0], sw.inputs[0]); L.new(radc.outputs[0], sw.inputs[1]); L.new(gi.outputs["DebrisRadius"], sw.inputs[2])
        tt = N.new("GeometryNodeInputNamedAttribute"); tt.data_type = "FLOAT"; tt.inputs["Name"].default_value = "temp"
        vis = N.new("FunctionNodeCompare"); vis.data_type = "FLOAT"; vis.operation = "GREATER_EQUAL"
        L.new(tt.outputs["Attribute"], vis.inputs[0]); vis.inputs[1].default_value = 0.0
        m2p = N.new("GeometryNodeMeshToPoints")
        L.new(gi.outputs["Geometry"], m2p.inputs["Mesh"]); L.new(sw.outputs[0], m2p.inputs["Radius"])
        L.new(vis.outputs[0], m2p.inputs["Selection"])
        sm = N.new("GeometryNodeSetMaterial")
        L.new(m2p.outputs[0], sm.inputs["Geometry"]); L.new(gi.outputs["Material"], sm.inputs["Material"])
        L.new(sm.outputs[0], go.inputs["Geometry"])
    return gn_group("Sparkle", b)


def mat_volume(name, emis_col, emis_strength, density_scale, albedo, absorb_col=None):
    m = bpy.data.materials.new(PFX + name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    pv = nt.nodes.new("ShaderNodeVolumePrincipled")
    pv.inputs["Color"].default_value = (*albedo, 1)
    pv.inputs["Density"].default_value = density_scale
    if absorb_col is not None and "Absorption Color" in pv.inputs:
        pv.inputs["Absorption Color"].default_value = (*absorb_col, 1)
    pv.inputs["Emission Color"].default_value = (*emis_col, 1)
    # Principled Volume emission is NOT scaled by density -> multiply by the density grid ourselves
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "density"
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = emis_strength * max(density_scale, 1e-3)   # radiance of a thick region ~ emission/extinction
    nt.links.new(at.outputs["Fac"], mul.inputs[0])
    nt.links.new(mul.outputs[0], pv.inputs["Emission Strength"])
    if "Anisotropy" in pv.inputs:
        pv.inputs["Anisotropy"].default_value = 0.2
    nt.links.new(pv.outputs[0], out.inputs["Volume"])
    return m


def mat_points(name, strength):
    m = bpy.data.materials.new(PFX + name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "temp"
    cr = nt.nodes.new("ShaderNodeValToRGB")
    el = cr.color_ramp.elements
    el[0].position, el[0].color = 0.0, (*ramp(0.25), 1)
    el[1].position, el[1].color = 1.0, (*ramp(1.0), 1)
    for p in (0.45, 0.62, 0.8):
        e = el.new(p); e.color = (*ramp(p), 1)
    # strength ~ temp^2
    pw = nt.nodes.new("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = 2.0
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = strength
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(at.outputs["Fac"], cr.inputs[0])
    nt.links.new(at.outputs["Fac"], pw.inputs[0]); nt.links.new(pw.outputs[0], mul.inputs[0])
    nt.links.new(cr.outputs[0], em.inputs["Color"]); nt.links.new(mul.outputs[0], em.inputs["Strength"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def mat_text(name):
    m = bpy.data.materials.new(PFX + name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = 1.0
    em.inputs["Color"].default_value = (0.92, 0.92, 0.92, 1)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mx = nt.nodes.new("ShaderNodeMixShader"); mx.name = "fade"
    mx.inputs[0].default_value = 1.0
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    if hasattr(m, "blend_method"):
        try:
            m.blend_method = "BLEND"
        except Exception:
            pass
    if hasattr(m, "surface_render_method"):
        try:
            m.surface_render_method = "BLENDED"
        except Exception:
            pass
    return m


def make_text(name, body, col, parent, size, y, align="CENTER"):
    cu = bpy.data.curves.new(PFX + name, "FONT")
    cu.body = body
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.size = size
    if CONFIG["FONT_PATH"] and os.path.exists(CONFIG["FONT_PATH"]):
        try:
            cu.font = bpy.data.fonts.load(CONFIG["FONT_PATH"], check_existing=True)
        except Exception as e:
            print("font load failed", e)
    o = new_obj(name, cu, col)
    o.parent = parent
    o.location = (0, y, 0)
    no_secondary(o)
    m = mat_text(name)
    cu.materials.append(m)
    return o, m


def setup_world(scene):
    w = bpy.data.worlds.get(PFX + "World") or bpy.data.worlds.new(PFX + "World")
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0, 0, 0, 1)
        bg.inputs["Strength"].default_value = 0.0
    scene.world = w


def setup_compositor(scene):
    c = CONFIG
    if hasattr(scene, "compositing_node_group"):          # 5.x
        ng = bpy.data.node_groups.get(PFX + "Comp") or bpy.data.node_groups.new(PFX + "Comp", "CompositorNodeTree")
        ng.nodes.clear()
        if not any(i.in_out == "OUTPUT" for i in ng.interface.items_tree if hasattr(i, "in_out")):
            ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        out = ng.nodes.new("NodeGroupOutput")
        scene.compositing_node_group = ng
    else:                                                 # 4.x
        scene.use_nodes = True
        ng = scene.node_tree
        ng.nodes.clear()
        out = ng.nodes.new("CompositorNodeComposite")
    if hasattr(scene.render, "use_compositing"):
        scene.render.use_compositing = True
    if hasattr(scene.render, "compositor_device") and (bpy.app.background or CONFIG["COMPOSITOR_CPU"]):
        scene.render.compositor_device = "CPU"     # GPU compositor needs an OpenGL context
    rl = ng.nodes.new("CompositorNodeRLayers")
    img = rl.outputs["Image"]
    if c["GLARE"]:
        bl = ng.nodes.new("CompositorNodeGlare")
        set_in(bl, "Type", "Bloom", "glare_type", "BLOOM")
        set_in(bl, "Quality", "High", "quality", "HIGH")
        set_in(bl, "Threshold", c["GLARE_THRESHOLD"], "threshold")
        set_in(bl, "Size", c["BLOOM_SIZE"], "size", 8)
        set_in(bl, "Strength", 0.8, "mix", -0.2)
        ng.links.new(img, bl.inputs["Image"])
        img = bl.outputs[0]
        fg = ng.nodes.new("CompositorNodeGlare")
        set_in(fg, "Type", "Fog Glow", "glare_type", "FOG_GLOW")
        set_in(fg, "Quality", "High", "quality", "HIGH")
        set_in(fg, "Threshold", 0.25, "threshold")
        set_in(fg, "Size", 0.9, "size", 9)
        set_in(fg, "Strength", c["FOG_GLOW_MIX"], "mix", c["FOG_GLOW_MIX"] * 2 - 1)
        ng.links.new(img, fg.inputs["Image"])
        img = fg.outputs[0]
    ng.links.new(img, out.inputs[0])


def setup_render(scene, preview):
    c = CONFIG
    r = scene.render
    r.engine = engine_id("CYCLES" if preview else c["ENGINE"])
    r.resolution_x, r.resolution_y = c["RESOLUTION"]
    r.resolution_percentage = 100
    r.fps = c["FPS"]
    r.film_transparent = False
    r.use_motion_blur = bool(c["MOTION_BLUR"])
    if hasattr(r, "motion_blur_shutter"):
        r.motion_blur_shutter = c["SHUTTER"]
    if hasattr(r, "use_lock_interface"):
        r.use_lock_interface = True
    r.image_settings.file_format = "PNG"
    vs = scene.view_settings
    for vt in (c["VIEW_TRANSFORM"], "AgX", "Filmic"):
        try:
            vs.view_transform = vt
            break
        except Exception:
            pass
    for lk in (c["VIEW_LOOK"], c["VIEW_LOOK"].replace("AgX - ", ""), "None"):
        try:
            vs.look = lk
            break
        except Exception:
            pass
    vs.exposure = c["EXPOSURE"]
    cy = scene.cycles
    cy.samples = c["SAMPLES_CYCLES"]
    cy.use_denoising = c["DENOISE"]
    cy.max_bounces = 4
    cy.volume_bounces = 0
    cy.transparent_max_bounces = 16
    if hasattr(cy, "volume_step_rate"):
        cy.volume_step_rate = c["VOLUME_STEP_RATE"]
    if hasattr(cy, "volume_preview_step_rate"):
        cy.volume_preview_step_rate = 2.0
    if hasattr(cy, "use_adaptive_sampling"):
        cy.use_adaptive_sampling = True
    try:
        cy.device = "CPU"
    except Exception:
        pass
    ee = scene.eevee
    for k, v in (("taa_render_samples", c["SAMPLES_EEVEE"]), ("volumetric_tile_size", "2"),
                 ("volumetric_samples", 128), ("volumetric_sample_distribution", 0.9),
                 ("use_volumetric_shadows", True), ("volumetric_shadow_samples", 32),
                 ("volumetric_ray_depth", 8), ("use_bloom", False), ("use_gtao", False)):
        if hasattr(ee, k):
            try:
                setattr(ee, k, v)
            except Exception:
                pass


def make_stars(col):
    rng = np.random.default_rng(7)
    n = CONFIG["STARS"]
    v = rng.normal(size=(n, 3))
    v /= np.linalg.norm(v, axis=1)[:, None]
    v *= 400.0
    me = bpy.data.meshes.new(PFX + "Stars")
    me.vertices.add(n)
    me.vertices.foreach_set("co", v.astype(np.float32).ravel())
    b = (rng.random(n) ** 6) * CONFIG["STAR_BRIGHTNESS"] + 0.02
    a = me.attributes.new("temp", "FLOAT", "POINT")   # reuse 'temp' slot as brightness
    a.data.foreach_set("value", b.astype(np.float32))
    o = new_obj("Stars", me, col)
    ng = bpy.data.node_groups.new(PFX + "StarPts", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    gi, go = ng.nodes.new("NodeGroupInput"), ng.nodes.new("NodeGroupOutput")
    m2p = ng.nodes.new("GeometryNodeMeshToPoints"); m2p.inputs["Radius"].default_value = 0.35
    sm = ng.nodes.new("GeometryNodeSetMaterial")
    m = bpy.data.materials.new(PFX + "StarMat"); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
    at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "temp"
    em.inputs["Color"].default_value = (0.9, 0.92, 1.0, 1)
    nt.links.new(at.outputs["Fac"], em.inputs["Strength"]); nt.links.new(em.outputs[0], out.inputs["Surface"])
    sm.inputs["Material"].default_value = m
    ng.links.new(gi.outputs[0], m2p.inputs["Mesh"]); ng.links.new(m2p.outputs[0], sm.inputs["Geometry"])
    ng.links.new(sm.outputs[0], go.inputs[0])
    mod = o.modifiers.new("Stars", "NODES"); mod.node_group = ng
    no_secondary(o)
    return o


# ----------------------------------------------------------------------------- camera
def camera_track(cache, frames, scene, cam):
    """Pre-compute a smoothed auto-framing camera path and keyframe it."""
    c = CONFIG
    nf = len(frames)
    rng = np.random.default_rng(3)
    sub = rng.choice(cache.n, size=min(cache.n, 40000), replace=False)
    sw, sh = scene.render.resolution_x, scene.render.resolution_y
    sensor = 36.0
    cam.data.sensor_fit = "VERTICAL"
    cam.data.sensor_height = sensor
    tan_v = (sensor / 2) / c["LENS_MM"]
    tan_h = tan_v * sw / sh
    cen = np.zeros((nf, 3)); dist = np.zeros(nf); bases = []
    stats_by_cache = {}
    for k, (f, x) in enumerate(frames):
        prog = k / max(nf - 1, 1)
        az = math.radians(c["CAM_AZIMUTH"] + c["CAM_ORBIT"] * prog)
        el = math.radians(c["CAM_ELEVATION"])
        fwd = -np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])  # camera looks along fwd
        right = np.cross(fwd, [0, 0, 1.0]); right /= np.linalg.norm(right)
        up = np.cross(right, fwd)
        rl = math.radians(c["CAM_ROLL"])
        right, up = right * math.cos(rl) + up * math.sin(rl), -right * math.sin(rl) + up * math.cos(rl)
        bases.append((fwd, right, up))
        ci = int(round(x))
        if ci not in stats_by_cache:
            p = cache.get(ci)["pos"][sub].astype(np.float64)
            stats_by_cache[ci] = p
        p = stats_by_cache[ci]
        m = np.median(p, axis=0)
        hs = cache.get(ci)["h"][sub]
        dense = hs < np.percentile(hs, 30) * c["DEBRIS_H"]      # ignore sparse debris when framing
        if dense.sum() > 50:
            p = p[dense]
        q = p - m
        ex = np.percentile(np.abs(q @ right), c["CAM_FIT_PERCENTILE"])
        ey = np.percentile(np.abs(q @ up), c["CAM_FIT_PERCENTILE"])
        ex, ey = max(ex, c["CAM_MIN_EXTENT"] * sw / sh), max(ey, c["CAM_MIN_EXTENT"])
        cen[k] = m
        dist[k] = c["CAM_MARGIN"] * max(ex / tan_h, ey / tan_v)
    # gaussian smoothing (edge-padded)
    sig = max(c["CAM_SMOOTH_S"] * c["FPS"], 1e-3)
    rad = int(3 * sig)
    ker = np.exp(-0.5 * (np.arange(-rad, rad + 1) / sig) ** 2); ker /= ker.sum()

    def sm(a):
        pad = np.pad(a, [(rad, rad)] + [(0, 0)] * (a.ndim - 1), mode="edge")
        if a.ndim == 1:
            return np.convolve(pad, ker, mode="valid")
        return np.stack([np.convolve(pad[:, j], ker, mode="valid") for j in range(a.shape[1])], 1)
    w = int(sig)
    dist = np.array([dist[max(0, k - w):k + w + 1].max() for k in range(nf)])
    cen, dist = sm(cen), sm(dist)
    # never zoom in faster than a slow drift: use running max-ish blend for comfort
    dist *= (1 - c["CAM_PUSH"] * np.linspace(0, 1, nf))
    import mathutils
    prev = None
    track = []
    for k, (f, x) in enumerate(frames):
        fwd, right, up = bases[k]
        loc = cen[k] - fwd * (dist[k] + 1.5)
        mat = mathutils.Matrix(((right[0], up[0], -fwd[0]), (right[1], up[1], -fwd[1]), (right[2], up[2], -fwd[2])))
        e = mat.to_euler("XYZ", prev) if prev is not None else mat.to_euler("XYZ")
        prev = e
        cam.location = loc
        cam.rotation_euler = e
        cam.data.dof.focus_distance = float(dist[k] + 1.5)
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
        cam.data.dof.keyframe_insert("focus_distance", frame=f)
        track.append(float(dist[k] + 1.5))
    STATE["focus"] = dict(zip([f for f, _ in frames], track))


# ----------------------------------------------------------------------------- per frame
def fmt_hours(h):
    if h < 1:
        return "T + %d min" % round(h * 60)
    if h < 48:
        return "T + %.1f h" % h
    return "T + %.1f days" % (h / 24)


def pc_frame_change(scene, depsgraph=None):
    st = STATE
    if "cache" not in st:
        return
    f = scene.frame_current + scene.frame_subframe
    c = CONFIG
    x = st["cache_start"] + (f - scene.frame_start) / c["INTERP_STEPS"]
    x = float(np.clip(x, st["cache_start"], st["cache_end"]))
    d = st["cache"].sample(x)
    me = st["mesh"]
    if len(me.vertices) != len(d["pos"]):
        return
    me.vertices.foreach_set("co", d["pos"].ravel())
    t = np.where(d["temp"] < 0, -1.0, np.clip(d["temp"], 0, 1) ** c["TEMP_GAMMA"])
    me.attributes["temp"].data.foreach_set("value", t.astype(np.float32))
    me.attributes["h"].data.foreach_set("value", d["h"].astype(np.float32))
    me.update()
    rig = st.get("rig")
    if rig is not None:
        fd = st["focus"].get(int(round(f)), None) or bpy.data.objects[PFX + "Camera"].data.dof.focus_distance
        rig.location = (0, 0, -fd * 0.5)
        rig.scale = (fd * 0.5,) * 3
    clock = st.get("clock")
    if clock is not None:
        clock.data.body = fmt_hours(st["cache"].hours(x, d))


pc_frame_change.__name__ = "pc_frame_change"


# ----------------------------------------------------------------------------- build
def find_cache():
    c = CONFIG
    if c["CACHE_DIR"]:
        return c["CACHE_DIR"]
    base = script_dir()
    for p in (os.path.join(base, "cache", c["PRESET"]), os.path.join(base, "cache", c["PRESET"] + "_test"),
              os.path.join(base, "cache")):
        if os.path.exists(os.path.join(p, "meta.json")):
            return p
    raise RuntimeError("No cache found - pass --cache DIR or set CONFIG['CACHE_DIR']")


def build(preview=False):
    c = CONFIG
    clean()
    scene = bpy.data.scenes.get(SCENE_NAME) or bpy.data.scenes.new(SCENE_NAME)
    try:
        if bpy.context.window is not None:
            bpy.context.window.scene = scene
    except Exception:
        pass
    cache = Cache(find_cache())
    print("cache:", cache.dir, cache.n, "particles,", len(cache), "frames")
    cs = c["CACHE_FRAME_START"]
    ce = len(cache) - 1 if c["CACHE_FRAME_END"] < 0 else min(c["CACHE_FRAME_END"], len(cache) - 1)
    nout = (ce - cs) * c["INTERP_STEPS"] + 1
    scene.frame_start, scene.frame_end = 1, nout
    if "_FRAMES" in c:
        scene.frame_start, scene.frame_end = c["_FRAMES"]
    frames = [(1 + k, cs + k / c["INTERP_STEPS"]) for k in range(nout)]
    STATE.update(cache=cache, cache_start=cs, cache_end=ce)

    setup_render(scene, preview)
    setup_world(scene)
    col = bpy.data.collections.new(PFX + "Collision")
    scene.collection.children.link(col)

    # particle mesh (shared by every layer object)
    d0 = cache.get(cs)
    me = bpy.data.meshes.new(PFX + "Particles")
    me.vertices.add(cache.n)
    me.vertices.foreach_set("co", d0["pos"].ravel())
    for nm in ("temp", "h"):
        me.attributes.new(nm, "FLOAT", "POINT")
    me.attributes["temp"].data.foreach_set("value", np.clip(d0["temp"], 0, 1).astype(np.float32))
    me.attributes["h"].data.foreach_set("value", d0["h"])
    STATE["mesh"] = me
    src = new_obj("Particles", me, col)
    src.hide_render = True
    src.hide_viewport = False
    src.display_type = "BOUNDS"

    # voxel size tied to smoothing length of the dense bulk
    hb = np.percentile(d0["h"], 30)
    vox = float(np.clip(hb * c["VOXEL_FACTOR"], c["MIN_VOXEL_SIZE"], c["MAX_VOXEL_SIZE"]))
    print("median h %.4f  bulk h %.4f  -> voxel %.4f" % (np.median(d0["h"]), hb, vox))
    STATE["voxel"] = vox

    vg = build_volume_group()
    edges = c["TEMP_BANDS"]
    for b in range(len(edges) - 1):
        t0, t1 = edges[b], edges[b + 1]
        tm = min(1.0, 0.5 * (t0 + t1))
        col_e = ramp(tm)
        strength = c["EMISSION"] * (c["EMISSION_FLOOR"] + c["EMISSION_HOT"] * tm ** 1.6)
        m = mat_volume("Band%d" % b, col_e, strength, c["VOLUME_DENSITY"], c["ALBEDO"])
        o = new_obj("Band%d" % b, me, col)
        mod = o.modifiers.new("Volume", "NODES"); mod.node_group = vg
        set_mod_input(mod, vg, "TMin", float(t0)); set_mod_input(mod, vg, "TMax", float(t1))
        set_mod_input(mod, vg, "RadiusFactor", float(c["RADIUS_FACTOR"]))
        set_mod_input(mod, vg, "MaxRadius", float(hb * c["MAX_RADIUS_H"]))
        set_mod_input(mod, vg, "MaxH", float(hb * c["DEBRIS_H"]))
        set_mod_input(mod, vg, "VoxelSize", vox)
        set_mod_input(mod, vg, "Density", 1.0)
        set_mod_input(mod, vg, "Material", m)
    if c["HAZE"]:
        m = mat_volume("Haze", ramp(0.7), c["HAZE_EMISSION"], c["HAZE_DENSITY"], (0.0, 0.0, 0.0), absorb_col=(0, 0, 0))
        o = new_obj("Haze", me, col)
        mod = o.modifiers.new("Haze", "NODES"); mod.node_group = vg
        set_mod_input(mod, vg, "TMin", float(c["HAZE_TEMP"])); set_mod_input(mod, vg, "TMax", 2.0)
        set_mod_input(mod, vg, "RadiusFactor", float(c["HAZE_RADIUS"]))
        set_mod_input(mod, vg, "MaxRadius", float(hb * c["MAX_RADIUS_H"] * 2.5))
        set_mod_input(mod, vg, "VoxelSize", float(np.clip(vox * 3, 0.02, 0.15)))
        set_mod_input(mod, vg, "Density", 1.0)
        set_mod_input(mod, vg, "Material", m)
        no_secondary(o)
    if c["SPARKLE"]:
        pg = build_points_group()
        m = mat_points("Sparkle", c["SPARKLE_EMISSION"])
        o = new_obj("Sparkle", me, col)
        mod = o.modifiers.new("Sparkle", "NODES"); mod.node_group = pg
        set_mod_input(mod, pg, "RadiusFactor", float(c["SPARKLE_RADIUS"]))
        set_mod_input(mod, pg, "MaxRadius", float(c["SPARKLE_MAX_RADIUS"]))
        set_mod_input(mod, pg, "DebrisH", float(hb * c["DEBRIS_H"]))
        set_mod_input(mod, pg, "DebrisRadius", float(hb * c["DEBRIS_RADIUS"]))
        set_mod_input(mod, pg, "Material", m)
        no_secondary(o)

    # light: sun gives the day/night shading seen in the reference
    ld = bpy.data.lights.new(PFX + "Sun", "SUN")
    ld.energy = c["SUN_STRENGTH"]
    if hasattr(ld, "angle"):
        ld.angle = math.radians(2)
    sun = new_obj("Sun", ld, col)
    import mathutils
    sun.rotation_euler = mathutils.Vector(c["SUN_DIR"]).to_track_quat("Z", "Y").to_euler()

    if c["STARS"]:
        make_stars(col)

    # camera
    cd = bpy.data.cameras.new(PFX + "Camera")
    cd.lens = c["LENS_MM"]
    cd.clip_start, cd.clip_end = 0.05, 2000
    cd.dof.use_dof = bool(c["DOF"])
    cd.dof.aperture_fstop = c["F_STOP"]
    cam = new_obj("Camera", cd, col)
    scene.camera = cam
    camera_track(cache, frames, scene, cam)

    # text rig: an empty in front of the camera at half the focus distance
    rig = new_obj("TextRig", None, col)
    rig.parent = cam
    STATE["rig"] = rig
    res = c["RESOLUTION"]
    half_h = (36.0 / 2) / c["LENS_MM"]      # half frame height at distance 1 (rig scale 1)
    half_w = half_h * res[0] / res[1]
    pre = PRESETS.get(c["PRESET"], PRESETS["theia"])
    fps = c["FPS"]
    caps = list(c.get("CAPTIONS") or pre["captions"])
    size = c["CAPTION_SIZE"] * 2 * half_h
    dur = (scene.frame_end - scene.frame_start + 1) / fps
    span = caps[-1][0] + 3.0 if caps else 1
    k = dur / span if (caps and span > dur) else 1.0     # squeeze caption times into a short cache
    for i, (ts, txt) in enumerate(caps):
        te = caps[i + 1][0] * k if i + 1 < len(caps) else dur + 10
        f0 = scene.frame_start + ts * k * fps
        f1 = scene.frame_start + te * fps
        o, m = make_text("Cap%d" % i, wrap(txt, 30), col, rig, size, -half_h * 0.70)
        fade_keys(m, f0, f1, min(c["FADE_S"] * fps, (f1 - f0) / 3))
    if pre.get("title"):
        o, m = make_text("Title", wrap(pre["title"], 22), col, rig, size * 1.6, half_h * 0.62)
    if c["SHOW_CLOCK"]:
        o, m = make_text("Clock", "T + 0.0 h", col, rig, size * 0.62, half_h * 0.88)
        STATE["clock"] = o
    if c["SHOW_CREDIT"]:
        make_text("Credit", "Simulated with {:,} particles".format(cache.n), col, rig, size * 0.5, -half_h * 0.90)

    bpy.app.handlers.frame_change_pre.append(pc_frame_change)
    setup_compositor(scene)
    scene.frame_set(scene.frame_start)
    return scene


def wrap(txt, n):
    words, lines, cur = txt.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > n and cur:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    lines.append(cur)
    return "\n".join(lines)


def fade_keys(m, f0, f1, fl):
    mx = m.node_tree.nodes["fade"].inputs[0]
    keys = [(min(0, f0 - 1), 0.0), (f0, 0.0), (f0 + fl, 1.0), (f1 - fl, 1.0), (f1, 0.0)]
    for f, v in keys:
        mx.default_value = v
        mx.keyframe_insert("default_value", frame=f)
    ad = m.node_tree.animation_data
    if ad and ad.action:
        for fc in all_fcurves(ad):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"


def all_fcurves(ad):
    """fcurves of an animation_data in 4.x (action.fcurves) and 5.x (layered actions)."""
    act = ad.action
    if hasattr(act, "fcurves") and len(getattr(act, "fcurves", [])):
        return list(act.fcurves)
    out = []
    try:
        for layer in act.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    out.extend(cb.fcurves)
    except Exception:
        pass
    return out


# ----------------------------------------------------------------------------- render
def out_dir():
    c = CONFIG
    d = c["OUTPUT_DIR"] or os.path.join(script_dir(), "renders", "07-planet-collision", c["PRESET"])
    os.makedirs(d, exist_ok=True)
    return d


def render_frames(scene, frames, tag="frame"):
    d = out_dir()
    times = []
    try:
        import resource                     # not on Windows
    except ImportError:
        resource = None

    def cpu_s():
        if resource is None:
            return time.process_time()
        r = resource.getrusage(resource.RUSAGE_SELF)
        return r.ru_utime + r.ru_stime
    cpu = []
    for f in frames:
        t0 = time.time()
        c0 = cpu_s()
        scene.frame_set(f)
        scene.render.filepath = os.path.join(d, "%s_%04d.png" % (tag, f))
        bpy.ops.render.render(write_still=True, scene=scene.name)
        times.append(time.time() - t0)
        cpu.append(cpu_s() - c0)
        print("rendered %s  %.1fs wall  %.0f cpu-s" % (scene.render.filepath, times[-1], cpu[-1]), flush=True)
    if times:
        print("avg %.1fs/frame" % (sum(times) / len(times)))


def main():
    parse_args()
    c = CONFIG
    if c["PREVIEW"]:
        if "_RESSET" not in c:
            c["RESOLUTION"] = (270, 480)
        c["SAMPLES_CYCLES"] = min(c["SAMPLES_CYCLES"], 24)
        c["VOXEL_FACTOR"] = max(c["VOXEL_FACTOR"], 0.6)
        c["STARS"] = min(c["STARS"], 400)
    scene = build(preview=c["PREVIEW"])
    if c["PREVIEW"]:
        n = scene.frame_end
        stills = c.get("_STILLS") or [max(1, int(n * p)) for p in (0.08, 0.25, 0.5, 0.92)]
        render_frames(scene, stills, "preview")
    elif c["RENDER"]:
        render_frames(scene, range(scene.frame_start, scene.frame_end + 1))
    elif c.get("_STILLS"):
        render_frames(scene, c["_STILLS"], "still")


if __name__ == "__main__":
    main()
