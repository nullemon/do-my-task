"""
OMINOUS #6 - ONE HOUR
=====================
A small craft hovers above a spinning black hole. Two clocks: HERE ticks
normally; HOME runs faster and faster as the dilation factor climbs to ~61,000
(1 hour here ~ 7 years at home).

Fully procedural Blender script (no downloads):
  * The black hole is ray-traced in numpy (null geodesics of a Schwarzschild
    metric, u'' = -u + 3Mu^2) into two "lens maps" (disc hit radius / azimuth /
    Doppler factor, and escaped sky direction / impact parameter).
  * Those maps drive an emission-only shader on a single plane: turbulent
    rotating accretion disc (Keplerian shear), Doppler beaming, thin photon
    ring and a warped, slowly streaming starfield. Very cheap in Cycles.
  * Craft = a few primitives lit by one sun lamp. Text = Blender text objects
    parented to the camera. All animation is evaluated per frame in Python.

Run headless:
    blender -b -P script.py -- --render
    blender -b -P script.py -- --stills 0,120,300,560      (test frames)
    blender -b -P script.py -- --render --start 0 --end 623
Blender-as-module:
    python -c "import sys; p='script.py'; sys.argv=['blender','--','--render']; exec(compile(open(p).read(),p,'exec'))"
"""

# ---------------------------------------------------------------- CONFIG ----
CONFIG = dict(
    fps=24,
    duration_s=26.0,                 # 624 frames
    resolution=(1080, 1920),
    resolution_percentage=53,        # -> 572x1018 (final render ~576x1024)
    engine="CYCLES",
    device="CPU",
    samples=5,
    denoise=False,                   # emission-only scene: AA samples suffice
    max_bounces=2,
    output_dir="/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/ominous/06/frames",
    cache_dir="/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/ominous/06/cache",
    # lens map
    map_res=(1440, 2880),            # width x height (1:2)
    map_half=(18.0, 36.0),           # half extents in units of M (GM/c^2)
    disc_r_in=3.4, disc_r_out=15.5,  # in M
    disc_tilt=0.15,                  # rad: camera elevation above the disc plane
    disc_roll=-0.13,                 # rad: roll of the disc in the image
    sky_fov=0.034,                   # undeflected view-direction slope per M
    # fonts (system fonts if present; Blender's built-in font otherwise)
    font_thin="/usr/share/fonts/opentype/inter/Inter-Light.otf",
    font_big="/usr/share/fonts/opentype/inter/Inter-ExtraLight.otf",
    font_mono="/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Light.ttf",
    final_factor=61000.0,
)

import sys, os, math, time
import numpy as np
import bpy

FPS = CONFIG["fps"]
NFRAMES = int(round(CONFIG["duration_s"] * FPS))
BC = 3.0 * math.sqrt(3.0)          # critical impact parameter (photon ring), M=1


# ------------------------------------------------------------ utilities ----
def clamp01(x):
    return max(0.0, min(1.0, x))


def smooth(a, b, x):
    t = clamp01((x - a) / (b - a)) if b != a else float(x >= b)
    return t * t * (3 - 2 * t)


def smoother(a, b, x):
    t = clamp01((x - a) / (b - a))
    return t * t * t * (t * (t * 6 - 15) + 10)


def window(t, a, b, fade=0.6):
    """1 inside [a,b] with smooth fades."""
    return smooth(a, a + fade, t) * (1.0 - smooth(b - fade, b, t))


# ======================================================= LENS RAY TRACER ====
def build_lens_maps():
    """Returns two float32 RGBA arrays (H, W, 4), row 0 = bottom (Blender order).
       map1 = (disc r, cos psi, sin psi, g)     g = redshift/Doppler factor
       map2 = (sky dir x, y, z, impact parameter b)"""
    W, H = CONFIG["map_res"]
    xr, yr = CONFIG["map_half"]
    r_in, r_out = CONFIG["disc_r_in"], CONFIG["disc_r_out"]
    os.makedirs(CONFIG["cache_dir"], exist_ok=True)
    key = "lens_%dx%d_%g_%g_%g_%g_%g_%g_%g_v3.npz" % (W, H, xr, yr, r_in, r_out,
                                                       CONFIG["disc_tilt"], CONFIG["disc_roll"], CONFIG["sky_fov"])
    path = os.path.join(CONFIG["cache_dir"], key)
    if os.path.exists(path):
        d = np.load(path)
        return d["m1"], d["m2"]

    t0 = time.time()
    # ---- 1. orbit table u(phi; b) for photons coming from infinity -------
    bmax = math.hypot(xr, yr) * 1.02
    near = BC + np.concatenate([-np.geomspace(1e-7, 1.5, 700), np.geomspace(1e-7, 1.5, 700)])
    bgrid = np.unique(np.concatenate([np.linspace(0.02, bmax, 2600), near]))
    bgrid = bgrid[(bgrid > 0.01) & (bgrid < bmax + 1)]
    NB = len(bgrid)
    dphi = 0.0025
    phimax = 3.5 * math.pi
    NP = int(phimax / dphi) + 2
    u = np.zeros(NB)
    w = 1.0 / bgrid
    U = np.empty((NP, NB), np.float32)
    Wt = np.empty((NP, NB), np.float32)
    cap = np.zeros(NB, bool)
    esc = np.zeros(NB, bool)
    phi_end = np.full(NB, np.nan)

    def f(u_, w_):
        return w_, -u_ + 3.0 * u_ * u_

    for i in range(NP):
        Uc = np.where(cap, 10.0, np.where(esc, -1.0, u))
        U[i] = Uc
        Wt[i] = np.where(cap | esc, 0.0, w)
        k1u, k1w = f(u, w)
        k2u, k2w = f(u + 0.5 * dphi * k1u, w + 0.5 * dphi * k1w)
        k3u, k3w = f(u + 0.5 * dphi * k2u, w + 0.5 * dphi * k2w)
        k4u, k4w = f(u + dphi * k3u, w + dphi * k3w)
        un = u + dphi / 6 * (k1u + 2 * k2u + 2 * k3u + k4u)
        wn = w + dphi / 6 * (k1w + 2 * k2w + 2 * k3w + k4w)
        newesc = (~esc) & (~cap) & (un < 0) & (i > 2)
        frac = u / np.maximum(u - un, 1e-12)
        phi_end[newesc] = (i + frac[newesc]) * dphi
        esc |= newesc
        cap |= (~esc) & (un > 0.5)
        un = np.minimum(un, 0.6)
        u, w = un, wn
    # rays still orbiting at phimax: treat as captured (they are ~0 measure)
    print("[lens] orbit table %d b x %d phi in %.1fs" % (NB, NP, time.time() - t0))

    # ---- 2. per pixel ------------------------------------------------------
    eps, rho = CONFIG["disc_tilt"], CONFIG["disc_roll"]
    n = np.array([-math.sin(rho) * math.cos(eps), math.cos(rho) * math.cos(eps), math.sin(eps)])
    z = np.array([0.0, 0.0, 1.0])
    d1 = z - z.dot(n) * n
    d1 /= np.linalg.norm(d1)
    d2 = np.cross(n, d1)
    bidx = np.arange(NB, dtype=np.float64)
    s_fov = CONFIG["sky_fov"]

    m1 = np.zeros((H, W, 4), np.float32)
    m2 = np.zeros((H, W, 4), np.float32)
    xs = (np.arange(W) + 0.5) / W * 2 * xr - xr
    CH = 96
    for j0 in range(0, H, CH):
        j1 = min(H, j0 + CH)
        ys = -yr + (np.arange(j0, j1) + 0.5) / H * 2 * yr
        X, Y = np.meshgrid(xs, ys)
        b = np.maximum(np.hypot(X, Y), 0.011)
        ex, ey = X / b, Y / b
        en = ex * n[0] + ey * n[1]
        phi0 = np.mod(np.arctan2(-n[2], en), math.pi)
        phi0 = np.where(phi0 < 1e-6, math.pi, phi0)
        bi = np.interp(b, bgrid, bidx)
        bnear = np.clip(np.round(bi).astype(int), 0, NB - 1)
        pe = phi_end[bnear]
        escaped = ~np.isnan(pe)
        b0 = np.clip(np.floor(bi).astype(int), 0, NB - 2)
        tb = bi - b0

        hit = np.zeros(b.shape, bool)
        R = np.zeros(b.shape)
        PH = np.zeros(b.shape)
        WW = np.zeros(b.shape)
        for k in range(4):
            phk = phi0 + k * math.pi
            ok = phk < (phimax - 0.01)
            ok &= np.where(escaped, phk < np.nan_to_num(pe, nan=0.0), True)
            fi = np.clip(phk / dphi, 0, NP - 2.0001)
            p0 = np.floor(fi).astype(int)
            tp = fi - p0
            uu = ((U[p0, b0] * (1 - tp) + U[p0 + 1, b0] * tp) * (1 - tb)
                  + (U[p0, b0 + 1] * (1 - tp) + U[p0 + 1, b0 + 1] * tp) * tb)
            ww = ((Wt[p0, b0] * (1 - tp) + Wt[p0 + 1, b0] * tp) * (1 - tb)
                  + (Wt[p0, b0 + 1] * (1 - tp) + Wt[p0 + 1, b0 + 1] * tp) * tb)
            ok &= (uu > 1.0 / r_out) & (uu < 1.0 / r_in) & (uu < 0.55)
            new = ok & ~hit
            R[new] = 1.0 / uu[new]
            PH[new] = phk[new]
            WW[new] = ww[new]
            hit |= new

        # disc point and photon direction
        c, s = np.cos(PH), np.sin(PH)
        px, py, pz = s * ex, s * ey, c                       # unit position dir
        qx, qy, qz = c * ex, c * ey, -s                      # d/dphi of it
        dr = -WW * R * R
        tx, ty, tz = dr * px + R * qx, dr * py + R * qy, dr * pz + R * qz
        tn = np.sqrt(tx * tx + ty * ty + tz * tz) + 1e-12
        kx, ky, kz = -tx / tn, -ty / tn, -tz / tn          # photon travel dir (towards camera)
        vx = n[1] * pz - n[2] * py                          # v = n x p
        vy = n[2] * px - n[0] * pz
        vz = n[0] * py - n[1] * px
        cosv = kx * vx + ky * vy + kz * vz
        Rs = np.maximum(R, 2.2)
        beta = np.minimum(1.0 / np.sqrt(Rs - 2.0), 0.78)
        gam = 1.0 / np.sqrt(1 - beta * beta)
        g = np.sqrt(np.maximum(1 - 2.0 / Rs, 0.0)) / (gam * (1 - beta * cosv))
        cpsi = px * d1[0] + py * d1[1] + pz * d1[2]
        spsi = px * d2[0] + py * d2[1] + pz * d2[2]

        sl = m1[j0:j1]
        sl[..., 0] = np.where(hit, R, 0.0)
        sl[..., 1] = np.where(hit, cpsi, 0.0)
        sl[..., 2] = np.where(hit, spsi, 0.0)
        sl[..., 3] = np.where(hit, g, 0.0)

        # escaped sky direction
        pe0 = np.nan_to_num(pe, nan=math.pi)
        dx = np.sin(pe0) * ex + s_fov * X
        dy = np.sin(pe0) * ey + s_fov * Y
        dz = np.cos(pe0)
        dn = np.sqrt(dx * dx + dy * dy + dz * dz)
        sky = escaped & ~hit
        s2 = m2[j0:j1]
        s2[..., 0] = np.where(sky, dx / dn, 0.0)
        s2[..., 1] = np.where(sky, dy / dn, 0.0)
        s2[..., 2] = np.where(sky, dz / dn, 0.0)
        s2[..., 3] = b
    np.savez(path, m1=m1, m2=m2)
    print("[lens] maps %dx%d in %.1fs" % (W, H, time.time() - t0))
    return m1, m2


def make_image(name, arr):
    H, W = arr.shape[:2]
    img = bpy.data.images.get(name)
    if img:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, W, H, alpha=True, float_buffer=True)
    try:
        img.colorspace_settings.name = "Non-Color"
    except Exception:
        pass
    img.pixels.foreach_set(arr.astype(np.float32).ravel())
    img.pack()
    return img


# ===================================================== NODE HELPERS =========
class NB:
    def __init__(self, mat):
        mat.use_nodes = True
        self.nt = mat.node_tree
        self.nt.nodes.clear()
        self.x = 0

    def node(self, typ, **props):
        nd = self.nt.nodes.new(typ)
        nd.location = (self.x, 0)
        self.x += 40
        for k, v in props.items():
            setattr(nd, k, v)
        return nd

    def link(self, out, inp):
        self.nt.links.new(out, inp)

    def feed(self, sock, v):
        if isinstance(v, (int, float)):
            sock.default_value = v
        elif isinstance(v, (tuple, list)):
            sock.default_value = v
        else:
            self.link(v, sock)

    def math(self, op, a, b=0.0, clamp=False):
        nd = self.node("ShaderNodeMath", operation=op, use_clamp=clamp)
        self.feed(nd.inputs[0], a)
        self.feed(nd.inputs[1], b)
        return nd.outputs[0]

    def add(self, a, b): return self.math("ADD", a, b)
    def mul(self, a, b): return self.math("MULTIPLY", a, b)
    def sub(self, a, b): return self.math("SUBTRACT", a, b)

    def maprange(self, v, a, b, c=0.0, d=1.0, interp="SMOOTHSTEP"):
        nd = self.node("ShaderNodeMapRange", interpolation_type=interp, clamp=True)
        self.feed(nd.inputs["Value"], v)
        nd.inputs["From Min"].default_value = a
        nd.inputs["From Max"].default_value = b
        nd.inputs["To Min"].default_value = c
        nd.inputs["To Max"].default_value = d
        return nd.outputs["Result"]

    def combine(self, x, y, z):
        nd = self.node("ShaderNodeCombineXYZ")
        self.feed(nd.inputs[0], x)
        self.feed(nd.inputs[1], y)
        self.feed(nd.inputs[2], z)
        return nd.outputs[0]

    def value(self, name, v=0.0):
        nd = self.node("ShaderNodeValue")
        nd.name = name
        nd.label = name
        nd.outputs[0].default_value = v
        return nd.outputs[0]

    def mixrgb(self, fac, a, b, blend="MIX"):
        nd = self.node("ShaderNodeMix", data_type="RGBA", blend_type=blend)
        self.feed(nd.inputs["Factor"], fac)
        self.feed(nd.inputs[6], a)
        self.feed(nd.inputs[7], b)
        return nd.outputs[2]

    def scale_vec(self, vec, s):
        nd = self.node("ShaderNodeVectorMath", operation="SCALE")
        self.feed(nd.inputs[0], vec)
        self.feed(nd.inputs["Scale"], s)
        return nd.outputs[0]


# ===================================================== SCENE BUILD ==========
def setup_scene():
    sc = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    sc.render.engine = "CYCLES"
    try:
        sc.cycles.device = CONFIG["device"]
        sc.cycles.samples = CONFIG["samples"]
        sc.cycles.use_denoising = CONFIG["denoise"]
        sc.cycles.max_bounces = CONFIG["max_bounces"]
        sc.cycles.diffuse_bounces = 1
        sc.cycles.glossy_bounces = 1
        sc.cycles.transmission_bounces = 2
        sc.cycles.transparent_max_bounces = 8
        sc.cycles.use_adaptive_sampling = False
        sc.cycles.pixel_filter_type = "BLACKMAN_HARRIS"
        sc.cycles.filter_width = 1.4
        sc.cycles.caustics_reflective = False
        sc.cycles.caustics_refractive = False
    except Exception as e:
        print("cycles settings:", e)
    sc.render.resolution_x, sc.render.resolution_y = CONFIG["resolution"]
    sc.render.resolution_percentage = CONFIG["resolution_percentage"]
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 0, NFRAMES - 1
    ims = sc.render.image_settings
    if hasattr(ims, "media_type"):          # Blender 5.x
        try:
            ims.media_type = "IMAGE"
        except Exception:
            pass
    ims.file_format = "PNG"
    ims.color_mode = "RGB"
    ims.color_depth = "8"
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        try:
            sc.view_settings.view_transform = "Filmic"
        except Exception:
            pass
    sc.view_settings.exposure = 0.0
    # black world
    world = bpy.data.worlds.new("void") if not sc.world else sc.world
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0, 0, 0, 1)
        bg.inputs[1].default_value = 0.0
    return sc


def hide_from_rays(ob):
    for attr in ("visible_diffuse", "visible_glossy", "visible_transmission",
                 "visible_volume_scatter", "visible_shadow"):
        if hasattr(ob, attr):
            setattr(ob, attr, False)


def build_blackhole_plane(m1, m2):
    xr, yr = CONFIG["map_half"]
    r_in, r_out = CONFIG["disc_r_in"], CONFIG["disc_r_out"]
    img1 = make_image("lens_disc", m1)
    img2 = make_image("lens_sky", m2)
    mesh = bpy.data.meshes.new("bh_plane")
    verts = [(-xr, -yr, 0), (xr, -yr, 0), (xr, yr, 0), (-xr, yr, 0)]
    mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
    uvl = mesh.uv_layers.new(name="UVMap")
    for li, uv in zip(range(4), [(0, 0), (1, 0), (1, 1), (0, 1)]):
        uvl.data[li].uv = uv
    ob = bpy.data.objects.new("BlackHole", mesh)
    bpy.context.scene.collection.objects.link(ob)
    hide_from_rays(ob)

    mat = bpy.data.materials.new("bh_mat")
    ob.data.materials.append(mat)
    try:
        mat.emission_sampling = "NONE"
    except Exception:
        try:
            mat.cycles.emission_sampling = "NONE"
        except Exception:
            pass
    B = NB(mat)
    T = B.value("TIME", 0.0)          # seconds of disc time
    SKYROT = B.value("SKYROT", 0.0)   # radians
    MASTER = B.value("MASTER", 1.0)

    uvn = B.node("ShaderNodeTexCoord")
    t1 = B.node("ShaderNodeTexImage", image=img1, interpolation="Closest", extension="CLIP")
    t2 = B.node("ShaderNodeTexImage", image=img2, interpolation="Linear", extension="CLIP")
    B.link(uvn.outputs["UV"], t1.inputs[0])
    B.link(uvn.outputs["UV"], t2.inputs[0])
    sep1 = B.node("ShaderNodeSeparateColor")
    B.link(t1.outputs["Color"], sep1.inputs[0])
    r, c, s = sep1.outputs[0], sep1.outputs[1], sep1.outputs[2]
    g = t1.outputs["Alpha"]
    bimp = t2.outputs["Alpha"]

    # --- disc --------------------------------------------------------------
    rs = B.math("MAXIMUM", r, 1.0)
    omega = B.math("POWER", rs, -1.5)                    # Keplerian angular speed
    ang = B.mul(B.mul(omega, T), 2.6)
    ca, sa = B.math("COSINE", ang), B.math("SINE", ang)
    c2 = B.add(B.mul(c, ca), B.mul(s, sa))
    s2 = B.sub(B.mul(s, ca), B.mul(c, sa))
    # big turbulent clumps (sheared along the orbit)
    v1 = B.combine(B.mul(r, 0.55), B.mul(c2, 1.3), B.mul(s2, 1.3))
    n1 = B.node("ShaderNodeTexNoise", noise_dimensions="4D")
    B.link(v1, n1.inputs["Vector"])
    B.feed(n1.inputs["W"], B.mul(T, 0.05))
    n1.inputs["Scale"].default_value = 1.7
    n1.inputs["Detail"].default_value = 3.0
    n1.inputs["Roughness"].default_value = 0.62
    # fine filaments
    v2 = B.combine(B.mul(r, 2.6), B.mul(c2, 1.1), B.mul(s2, 1.1))
    n2 = B.node("ShaderNodeTexNoise", noise_dimensions="4D")
    B.link(v2, n2.inputs["Vector"])
    B.feed(n2.inputs["W"], B.mul(T, 0.03))
    n2.inputs["Scale"].default_value = 2.3
    n2.inputs["Detail"].default_value = 2.0
    n2.inputs["Roughness"].default_value = 0.5
    clump = B.maprange(n1.outputs["Fac"], 0.32, 0.72, 0.15, 1.0)
    fil = B.maprange(n2.outputs["Fac"], 0.3, 0.7, 0.35, 1.0)
    dens = B.mul(clump, fil)
    # radial profile
    prof = B.math("POWER", B.math("DIVIDE", r_in, rs), 1.9)
    edge_in = B.maprange(r, r_in, r_in + 0.9, 0.0, 1.0)
    edge_out = B.maprange(r, r_out - 6.0, r_out, 1.0, 0.0)
    prof = B.mul(B.mul(prof, edge_in), edge_out)
    beam = B.math("POWER", B.math("MAXIMUM", g, 0.0), 3.2)   # Doppler beaming g^3
    I = B.mul(B.mul(prof, dens), beam)
    # colour: temperature-like ramp, shifted by g
    hue_in = B.mul(B.math("POWER", I, 0.5), 1.2)
    ramp = B.node("ShaderNodeValToRGB")
    B.link(hue_in, ramp.inputs[0])
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, (0.05, 0.012, 0.002, 1)
    els[1].position, els[1].color = 1.0, (1.0, 0.93, 0.80, 1)
    e = els.new(0.22); e.color = (0.42, 0.13, 0.025, 1)
    e = els.new(0.50); e.color = (1.0, 0.50, 0.12, 1)
    e = els.new(0.75); e.color = (1.0, 0.76, 0.40, 1)
    disc_col = B.scale_vec(ramp.outputs["Color"], B.mul(I, 9.0))

    # --- photon ring (thin) + faint halo ------------------------------------
    db = B.sub(bimp, BC + 0.03)
    ring = B.math("EXPONENT", B.mul(B.math("POWER", B.math("ABSOLUTE", db), 2.0), -1.0 / (0.07 ** 2)))
    halo = B.math("EXPONENT", B.mul(B.math("POWER", B.math("ABSOLUTE", db), 2.0), -1.0 / (0.9 ** 2)))
    nohit = B.math("LESS_THAN", r, 0.5)
    outside = B.maprange(db, -0.05, 0.05, 0.0, 1.0)
    ringv = B.mul(B.add(B.mul(ring, 0.9), B.mul(B.mul(halo, outside), 0.03)), nohit)
    ring_col = B.scale_vec((1.0, 0.72, 0.38), ringv)

    # --- stars (lensed) -----------------------------------------------------
    sky = B.combine(0, 0, 0)
    sepd = B.node("ShaderNodeSeparateColor")
    B.link(t2.outputs["Color"], sepd.inputs[0])
    dirv = B.combine(sepd.outputs[0], sepd.outputs[1], sepd.outputs[2])
    dlen = B.node("ShaderNodeVectorMath", operation="LENGTH")
    B.link(dirv, dlen.inputs[0])
    skymask = B.maprange(dlen.outputs["Value"], 0.5, 0.9, 0.0, 1.0)
    rot = B.node("ShaderNodeVectorRotate", rotation_type="Y_AXIS")
    B.link(dirv, rot.inputs["Vector"])
    B.link(SKYROT, rot.inputs["Angle"])
    rot2 = B.node("ShaderNodeVectorRotate", rotation_type="X_AXIS")
    B.link(rot.outputs[0], rot2.inputs["Vector"])
    B.feed(rot2.inputs["Angle"], B.mul(SKYROT, 0.4))
    dv = rot2.outputs[0]
    vor = B.node("ShaderNodeTexVoronoi", voronoi_dimensions="3D", feature="F1")
    B.link(dv, vor.inputs["Vector"])
    vor.inputs["Scale"].default_value = 70.0
    vsep = B.node("ShaderNodeSeparateColor")
    B.link(vor.outputs["Color"], vsep.inputs[0])
    present = B.maprange(vsep.outputs[0], 0.55, 0.60, 0.0, 1.0)
    bright = B.math("POWER", vsep.outputs[1], 4.0)
    core = B.maprange(vor.outputs["Distance"], 0.0, 0.075, 1.0, 0.0)
    star = B.mul(B.mul(B.mul(present, core), B.add(B.mul(bright, 3.0), 0.12)), skymask)
    # second, denser layer of faint stars
    vor2 = B.node("ShaderNodeTexVoronoi", voronoi_dimensions="3D", feature="F1")
    B.link(dv, vor2.inputs["Vector"])
    vor2.inputs["Scale"].default_value = 180.0
    v2sep = B.node("ShaderNodeSeparateColor")
    B.link(vor2.outputs["Color"], v2sep.inputs[0])
    core2 = B.maprange(vor2.outputs["Distance"], 0.0, 0.11, 1.0, 0.0)
    pres2 = B.maprange(v2sep.outputs[0], 0.62, 0.66, 0.0, 1.0)
    star2 = B.mul(B.mul(B.mul(core2, pres2), B.mul(v2sep.outputs[2], 0.35)), skymask)
    # faint dusty haze band
    nh = B.node("ShaderNodeTexNoise", noise_dimensions="3D")
    B.link(dv, nh.inputs["Vector"])
    nh.inputs["Scale"].default_value = 2.5
    nh.inputs["Detail"].default_value = 5.0
    haze = B.mul(B.maprange(nh.outputs["Fac"], 0.45, 0.8, 0.0, 1.0), B.mul(skymask, 0.009))
    starv = B.add(B.add(star, star2), haze)
    star_col = B.scale_vec((0.86, 0.88, 0.95), starv)

    add1 = B.node("ShaderNodeVectorMath", operation="ADD")
    B.link(disc_col, add1.inputs[0]); B.link(ring_col, add1.inputs[1])
    add2 = B.node("ShaderNodeVectorMath", operation="ADD")
    B.link(add1.outputs[0], add2.inputs[0]); B.link(star_col, add2.inputs[1])
    em = B.node("ShaderNodeEmission")
    B.link(add2.outputs[0], em.inputs["Color"])
    B.link(MASTER, em.inputs["Strength"])
    out = B.node("ShaderNodeOutputMaterial")
    B.link(em.outputs[0], out.inputs["Surface"])
    return ob, mat


def principled(name, col, rough=0.5, metal=0.0, emit=None, emit_strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    p = mat.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = col
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if emit is not None:
        key = "Emission Color" if "Emission Color" in p.inputs else "Emission"
        p.inputs[key].default_value = emit
        p.inputs["Emission Strength"].default_value = emit_strength
    return mat


def add_prim(kind, name, loc, scale, rot=(0, 0, 0), mat=None, parent=None, **kw):
    if kind == "cube":
        bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot, **kw)
    elif kind == "cyl":
        bpy.ops.mesh.primitive_cylinder_add(location=loc, rotation=rot, **kw)
    elif kind == "torus":
        bpy.ops.mesh.primitive_torus_add(location=loc, rotation=rot, **kw)
    elif kind == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(location=loc, rotation=rot, **kw)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = scale
    if mat:
        ob.data.materials.append(mat)
    if parent:
        ob.parent = parent
    for p in ob.data.polygons:
        p.use_smooth = kind in ("cyl", "torus", "sphere")
    return ob


def build_ship():
    """Original small craft: slim hull, crew ring, two outrigger pods,
    a forward lamp (faces the camera) and a dim drive glow aft (towards the hole)."""
    root = bpy.data.objects.new("Ship", None)
    bpy.context.scene.collection.objects.link(root)
    hull_m = principled("hull", (0.10, 0.095, 0.09, 1), rough=0.55, metal=0.35)
    lamp_m = principled("lamp", (0, 0, 0, 1), emit=(1.0, 0.95, 0.88, 1), emit_strength=12.0)
    win_m = principled("win", (0, 0, 0, 1), emit=(1.0, 0.72, 0.38, 1), emit_strength=4.0)
    drive_m = principled("drive", (0, 0, 0, 1), emit=(1.0, 0.6, 0.25, 1), emit_strength=6.0)
    # ship long axis = local Y; +Y = nose
    add_prim("cyl", "hull", (0, 0, 0), (0.07, 0.07, 0.42), rot=(math.pi / 2, 0, 0),
             mat=hull_m, parent=root, vertices=16)
    add_prim("cyl", "nose", (0, 0.47, 0), (0.05, 0.05, 0.06), rot=(math.pi / 2, 0, 0),
             mat=hull_m, parent=root, vertices=16)
    add_prim("torus", "ring", (0, 0.05, 0), (1, 1, 1), rot=(math.pi / 2, 0, 0), mat=hull_m,
             parent=root, major_radius=0.24, minor_radius=0.022, major_segments=40, minor_segments=8)
    for sx in (-1, 1):
        add_prim("cube", "strut", (sx * 0.15, 0.05, 0), (0.18, 0.02, 0.02), mat=hull_m, parent=root)
        add_prim("cyl", "pod", (sx * 0.34, -0.12, 0), (0.035, 0.035, 0.2), rot=(math.pi / 2, 0, 0),
                 mat=hull_m, parent=root, vertices=12)
        add_prim("cube", "pylon", (sx * 0.2, -0.12, 0), (0.28, 0.12, 0.012), mat=hull_m, parent=root)
        add_prim("cube", "podwin", (sx * 0.34, -0.12, 0.034), (0.008, 0.25, 0.006), mat=win_m, parent=root)
    add_prim("cube", "winstrip", (0, 0.12, 0.069), (0.012, 0.42, 0.006), mat=win_m, parent=root)
    lamp = add_prim("sphere", "lamp", (0, 0.535, 0), (0.013, 0.013, 0.013), mat=lamp_m, parent=root,
                    segments=12, ring_count=8)
    add_prim("cyl", "drive", (0, -0.43, 0), (0.055, 0.055, 0.01), rot=(math.pi / 2, 0, 0),
             mat=drive_m, parent=root, vertices=16)
    # soft glow sprite for the lamp (camera-facing quad, radial falloff)
    gm = bpy.data.materials.new("lampglow")
    try:
        gm.blend_method = "BLEND"
    except Exception:
        pass
    B = NB(gm)
    STR = B.value("GLOW", 1.0)
    tc = B.node("ShaderNodeTexCoord")
    grad = B.node("ShaderNodeTexGradient", gradient_type="SPHERICAL")
    mp = B.node("ShaderNodeMapping")
    mp.inputs["Location"].default_value = (0.0, 0.0, 0.0)
    B.link(tc.outputs["Object"], mp.inputs[0])
    B.link(mp.outputs[0], grad.inputs[0])
    gpow = B.math("POWER", grad.outputs["Fac"], 4.0)
    alpha = B.mul(gpow, STR)
    em = B.node("ShaderNodeEmission")
    em.inputs["Color"].default_value = (1.0, 0.9, 0.75, 1)
    em.inputs["Strength"].default_value = 1.0
    tr = B.node("ShaderNodeBsdfTransparent")
    mix = B.node("ShaderNodeMixShader")
    B.link(B.math("MINIMUM", alpha, 1.0), mix.inputs[0])
    B.link(tr.outputs[0], mix.inputs[1])
    B.link(em.outputs[0], mix.inputs[2])
    addsh = B.node("ShaderNodeAddShader")       # additive glow
    B.link(tr.outputs[0], addsh.inputs[0])
    em2 = B.node("ShaderNodeEmission")
    em2.inputs["Color"].default_value = (1.0, 0.88, 0.7, 1)
    B.link(B.mul(alpha, 1.2), em2.inputs["Strength"])
    B.link(em2.outputs[0], addsh.inputs[1])
    out = B.node("ShaderNodeOutputMaterial")
    B.link(addsh.outputs[0], out.inputs["Surface"])
    mesh = bpy.data.meshes.new("glowquad")
    a = 1.0
    mesh.from_pydata([(-a, -a, 0), (a, -a, 0), (a, a, 0), (-a, a, 0)], [], [(0, 1, 2, 3)])
    glow = bpy.data.objects.new("lampglow", mesh)
    bpy.context.scene.collection.objects.link(glow)
    glow.data.materials.append(gm)
    hide_from_rays(glow)
    return root, lamp, glow, lamp_m, gm


def build_text_rig(cam):
    fonts = {}
    for k in ("font_thin", "font_big", "font_mono"):
        p = CONFIG[k]
        try:
            fonts[k] = bpy.data.fonts.load(p, check_existing=True) if os.path.exists(p) else None
        except Exception:
            fonts[k] = None

    texts = {}

    def T(name, body, x, y, size, font="font_thin", align="CENTER", spacing=1.25, col=(0.92, 0.9, 0.85)):
        cu = bpy.data.curves.new(name, type="FONT")
        cu.body = body
        if fonts.get(font):
            cu.font = fonts[font]
        cu.size = size
        cu.align_x = align
        cu.align_y = "CENTER"
        cu.space_character = spacing
        ob = bpy.data.objects.new(name, cu)
        bpy.context.scene.collection.objects.link(ob)
        ob.parent = cam
        ob.location = (x, y, -1.0)
        hide_from_rays(ob)
        mat = bpy.data.materials.new("m_" + name)
        B = NB(mat)
        A = B.value("ALPHA", 1.0)
        em = B.node("ShaderNodeEmission")
        em.inputs["Color"].default_value = (*col, 1)
        em.inputs["Strength"].default_value = 1.35
        tr = B.node("ShaderNodeBsdfTransparent")
        mix = B.node("ShaderNodeMixShader")
        B.link(A, mix.inputs[0])
        B.link(tr.outputs[0], mix.inputs[1])
        B.link(em.outputs[0], mix.inputs[2])
        out = B.node("ShaderNodeOutputMaterial")
        B.link(mix.outputs[0], out.inputs["Surface"])
        cu.materials.append(mat)
        texts[name] = (ob, mat)
        return ob

    GOLD = (1.0, 0.74, 0.38)
    # hook
    T("hook1", "ONE HOUR HERE", 0, -0.215, 0.050, "font_big", spacing=1.35)
    T("hook2", "COSTS SEVEN YEARS BACK HOME", 0, -0.275, 0.0215, "font_thin", spacing=1.5)
    # beats
    T("beat1", "THE DEEPER YOU SINK", 0, -0.225, 0.0225, spacing=1.5)
    T("beat2", "THE SLOWER YOUR TIME RUNS", 0, -0.225, 0.0225, spacing=1.5)
    T("beat3", "NEAR A SPINNING BLACK HOLE", 0, -0.225, 0.0225, spacing=1.5)
    # clocks
    T("lbl_here", "HERE", -0.215, -0.300, 0.0185, align="LEFT", spacing=1.6)
    T("lbl_home", "HOME", -0.215, -0.355, 0.0185, align="LEFT", spacing=1.6, col=GOLD)
    T("val_here", "00:00:00.00", 0.215, -0.300, 0.030, "font_mono", align="RIGHT", spacing=1.05)
    T("val_home", "000d 00:00:00", 0.215, -0.355, 0.030, "font_mono", align="RIGHT", spacing=1.05, col=GOLD)
    T("factor", "TIME RUNS  ×1", 0, -0.405, 0.0165, "font_thin", spacing=1.6, col=(0.7, 0.68, 0.64))
    # final
    T("end1", "1 HOUR HERE", 0, -0.215, 0.044, "font_big", spacing=1.35)
    T("end2", "7 YEARS AT HOME", 0, -0.275, 0.044, "font_big", spacing=1.35, col=GOLD)
    return texts


# ===================================================== TIMELINE =============
T_CLOCK0 = 3.6        # clocks start
T_RAMP = (4.2, 19.0)  # dilation factor ramp 1 -> 61,000 (log)


def factor_at(t):
    s = smoother(T_RAMP[0], T_RAMP[1], t)
    return math.exp(math.log(CONFIG["final_factor"]) * s)


def home_seconds_table():
    """HOME proper time = integral of factor d(HERE time), sampled per frame
    with fine substeps so the clock is exact for every frame."""
    tab = np.zeros(NFRAMES)
    acc, sub = 0.0, 32
    for f in range(1, NFRAMES):
        for k in range(sub):
            t = (f - 1 + (k + 0.5) / sub) / FPS
            if t >= T_CLOCK0:
                acc += factor_at(t) / (FPS * sub)
        tab[f] = acc
    return tab


def fmt_here(sec):
    sec = max(0.0, sec)
    h = int(sec // 3600); m = int(sec % 3600 // 60); s = sec % 60
    return "%02d:%02d:%05.2f" % (h, m, s)


def fmt_home(sec):
    sec = max(0.0, sec)
    d = int(sec // 86400); rem = sec - d * 86400
    h = int(rem // 3600); m = int(rem % 3600 // 60); s = int(rem % 60)
    return "%03dd %02d:%02d:%02d" % (d, h, m, s)


def fmt_factor(fx):
    if fx < 10:
        return "×%.2f" % fx
    if fx < 1000:
        return "×%d" % int(round(fx))
    return "×{:,}".format(int(round(fx / 10.0) * 10))


class Rig:
    pass


def apply_frame(rig, f):
    t = f / FPS
    sc = bpy.context.scene
    sc.frame_set(f)
    # ---------------- camera: slow descent / push-in ------------------------
    s = smoother(0.0, 24.5, t) * 0.85 + 0.15 * (t / 26.0)
    width = 34.0 * (1 - s) + 16.0 * s
    L = width * 50.0 / 36.0
    Hh = width * 16.0 / 9.0
    cam = rig.cam
    yoff = -0.11 * Hh                                       # hole sits above centre
    sway = 0.15 * math.sin(t * 0.37) * (width / 34)
    cam.location = (sway, yoff + 0.08 * math.sin(t * 0.29) * (width / 34), L)
    cam.rotation_euler = (0.0, 0.0, math.radians(-2.0 + 3.2 * smooth(0, 26, t) + 0.4 * math.sin(t * 0.21)))

    # ---------------- black hole shader ---------------------------------------
    nodes = rig.bh_mat.node_tree.nodes
    nodes["TIME"].outputs[0].default_value = 3.0 + t * 1.0
    nodes["SKYROT"].outputs[0].default_value = 0.0 + 0.010 * t + 0.02 * smooth(0, 26, t)
    nodes["MASTER"].outputs[0].default_value = 1.0

    # ---------------- ship --------------------------------------------------
    # ship lives in camera space: below-left of the hole, sinking towards it
    dist = 4.7 + 2.0 * smooth(4.0, 25.0, t)
    sx = -0.25 + 0.09 * smooth(3, 25, t)
    sy = -0.02 + 0.07 * smooth(3, 25, t)
    bob = 0.015 * math.sin(t * 1.3)
    # place in world: camera-local (sx*dist, sy*dist + bob, -dist)
    mw = cam.matrix_world.copy()
    from mathutils import Vector, Euler, Matrix
    sc.view_layers[0].update()
    mw = cam.matrix_world.copy()
    loc = mw @ Vector((sx * dist, sy * dist + bob, -dist))
    rig.ship.location = loc
    # nose (+Y local) points towards the camera, tilted; at the end it turns away
    turn = smoother(20.6, 24.2, t)
    yaw = math.radians(48 + 4 * math.sin(t * 0.5)) + math.pi * turn * 0.85
    pitch = math.radians(-52 + 12 * turn)
    rig.ship.rotation_euler = Euler((pitch, 0.0, yaw), "ZXY")
    rig.ship.rotation_euler.rotate(Euler((0, 0, math.radians(-2 + 3.2 * smooth(0, 26, t))), "XYZ"))
    sc.view_layers[0].update()
    # lamp facing factor
    lw = rig.lamp.matrix_world.translation
    nose = rig.ship.matrix_world.to_3x3() @ Vector((0, 1, 0))
    tocam = (mw.translation - lw).normalized()
    facing = max(0.0, nose.normalized().dot(tocam))
    blink = 0.75 + 0.25 * (1.0 if (t % 2.2) < 0.12 else 0.0)
    life = 1.0 - smooth(22.6, 24.0, t)
    gl = (0.25 + 0.75 * facing ** 2) * blink * life
    rig.glow.location = lw + tocam * 0.05
    rig.glow.rotation_euler = mw.to_euler()
    gsize = 0.06 * dist / 4.7
    rig.glow.scale = (gsize, gsize, gsize)
    rig.glow_mat.node_tree.nodes["GLOW"].outputs[0].default_value = gl * 0.35
    p = rig.lamp_mat.node_tree.nodes.get("Principled BSDF")
    p.inputs["Emission Strength"].default_value = 12.0 * gl + 0.1

    # ---------------- text --------------------------------------------------
    A = {}
    A["hook1"] = 1.0 - smooth(3.0, 3.7, t)
    A["hook2"] = 1.0 - smooth(3.0, 3.7, t)
    A["beat1"] = window(t, 6.4, 10.4, 0.7)
    A["beat2"] = window(t, 11.2, 15.4, 0.7)
    A["beat3"] = window(t, 16.2, 21.2, 0.7)
    clk = smooth(T_CLOCK0, T_CLOCK0 + 0.8, t) * (1.0 - smooth(21.9, 22.7, t))
    for k in ("lbl_here", "lbl_home", "val_here", "val_home", "factor"):
        A[k] = clk
    A["end1"] = smooth(22.7, 23.5, t)
    A["end2"] = smooth(23.4, 24.3, t)
    here = t - T_CLOCK0
    rig.texts["val_here"][0].data.body = fmt_here(here)
    rig.texts["val_home"][0].data.body = fmt_home(rig.home[f])
    rig.texts["factor"][0].data.body = "TIME AT HOME RUNS  " + fmt_factor(factor_at(t)) + "  FASTER"
    for k, (ob, mat) in rig.texts.items():
        a = A.get(k, 0.0)
        mat.node_tree.nodes["ALPHA"].outputs[0].default_value = a
        ob.hide_render = a < 0.004


def build_all():
    sc = setup_scene()
    m1, m2 = build_lens_maps()
    rig = Rig()
    rig.bh, rig.bh_mat = build_blackhole_plane(m1, m2)
    cd = bpy.data.cameras.new("cam")
    cd.lens = 50.0
    cd.sensor_fit = "HORIZONTAL"
    cd.sensor_width = 36.0
    cd.clip_start = 0.05
    cd.clip_end = 500.0
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    rig.cam = cam
    rig.ship, rig.lamp, rig.glow, rig.lamp_mat, rig.glow_mat = build_ship()
    # one sun: gold back-light from the disc, plus a whisper of cool fill
    sd = bpy.data.lights.new("disc_light", "SUN")
    sd.energy = 7.0
    sd.color = (1.0, 0.7, 0.4)
    sd.angle = math.radians(12)
    sun = bpy.data.objects.new("disc_light", sd)
    sc.collection.objects.link(sun)
    from mathutils import Vector
    sun.rotation_euler = Vector((0.55, -0.45, 0.70)).normalized().to_track_quat('-Z', 'Y').to_euler()  # from behind/upper-left
    fd = bpy.data.lights.new("fill", "SUN")
    fd.energy = 0.05
    fd.color = (0.7, 0.75, 0.9)
    fill = bpy.data.objects.new("fill", fd)
    sc.collection.objects.link(fill)
    fill.rotation_euler = (math.radians(20), 0, 0)
    rig.texts = build_text_rig(cam)
    rig.home = home_seconds_table()
    return rig


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = dict(render=False, stills=None, start=0, end=NFRAMES - 1, out=CONFIG["output_dir"], overwrite=False)
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--render":
            opts["render"] = True
        elif a == "--stills":
            opts["stills"] = [int(v) for v in argv[i + 1].split(",")]; i += 1
        elif a == "--start":
            opts["start"] = int(argv[i + 1]); i += 1
        elif a == "--end":
            opts["end"] = int(argv[i + 1]); i += 1
        elif a == "--out":
            opts["out"] = argv[i + 1]; i += 1
        elif a == "--overwrite":
            opts["overwrite"] = True
        i += 1
    return opts


def main():
    opts = parse_args()
    rig = build_all()
    frames = opts["stills"] if opts["stills"] is not None else (
        list(range(opts["start"], opts["end"] + 1)) if opts["render"] else [])
    os.makedirs(opts["out"], exist_ok=True)
    sc = bpy.context.scene
    print("[home clock] final HOME elapsed: %.0f s (%.2f days)" % (rig.home[-1], rig.home[-1] / 86400))
    for f in frames:
        path = os.path.join(opts["out"], "f_%04d.png" % f)
        if os.path.exists(path) and not opts["overwrite"]:
            continue
        t0 = time.time()
        apply_frame(rig, f)
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print("[frame %d] %.2fs" % (f, time.time() - t0), flush=True)


main()
