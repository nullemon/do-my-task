"""Procedural star clusters seen from INSIDE (population synthesis + spatial model) -> SCR/cl_<key>.npz + SCR/stats.json.

For each cluster: N stars with masses from a Kroupa (2001) IMF, absolute V magnitudes / temperatures from a main-sequence
table (solar or metal-poor), post-main-sequence stars (RGB / HB / AGB) for the old populations from the fuel-consumption
theorem, real named bright members injected for the Pleiades and the Hyades, positions from a Plummer sphere (open and
globular clusters) or a broken power law (the Milky Way's nuclear star cluster). The Sun-observer sits at R_OBS from the
centre. Every star gets V = M_V + 5 log10(d / 10 pc) (no extinction). Stars with V < V_KEEP are kept as points (unit
vectors in an equatorial-like frame, V, Teff); fainter stars are summed into an equirectangular map of integrated light.
Usage: /home/user/ttsenv/bin/python clusters.py [key ...]"""
import os, sys, json, math
import numpy as np

SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/B2-star-clusters"
LY = 3.26156                                   # ly per pc
V_SIRIUS = -1.46
V_KEEP = 7.0
MW, MH = 1024, 512                             # integrated-light map (RA 0..360, Dec +90..-90)
CHUNK = 2_000_000

# ------------------------------------------------------------------------------------------- main sequence tables
# solar metallicity dwarfs (after Pecaut & Mamajek 2013): mass, M_V, Teff
MS_SOLAR = np.array([
    (0.08, 19.0, 2500), (0.10, 16.4, 2850), (0.15, 14.5, 3050), (0.20, 13.0, 3200), (0.30, 11.6, 3400),
    (0.40, 10.6, 3550), (0.50, 9.6, 3750), (0.60, 8.6, 3950), (0.70, 7.3, 4450), (0.80, 6.3, 4950),
    (0.90, 5.6, 5300), (1.00, 4.8, 5770), (1.20, 3.8, 6300), (1.40, 3.0, 6700), (1.60, 2.5, 7200),
    (1.90, 1.9, 8100), (2.30, 1.1, 9700), (2.75, 0.4, 10500), (3.20, -0.1, 11500), (4.20, -0.9, 14500),
    (5.40, -1.6, 17000), (7.0, -2.2, 20500)])
# metal-poor ([Fe/H] ~ -1.6) old main sequence, turnoff ~0.80 Msun at M_V ~ +3.9 (globular-cluster isochrones)
MS_POOR = np.array([
    (0.08, 16.5, 2900), (0.10, 14.0, 3150), (0.20, 11.8, 3450), (0.30, 10.3, 3650), (0.40, 9.0, 3950),
    (0.50, 7.8, 4500), (0.60, 6.6, 5200), (0.70, 5.3, 5800), (0.75, 4.6, 6150), (0.80, 3.9, 6400)])


def ms_lookup(tab, m):
    lm = np.log10(tab[:, 0])
    return np.interp(np.log10(m), lm, tab[:, 1]), np.interp(np.log10(m), lm, tab[:, 2])


def kroupa(n, mlo, mhi, rng):
    """Kroupa (2001): dN/dm ~ m^-1.3 (m < 0.5), m^-2.3 above"""
    g = np.logspace(math.log10(mlo), math.log10(mhi), 4000)
    pdf = np.where(g < 0.5, g ** -1.3, 0.5 * g ** -2.3)
    cdf = np.concatenate([[0], np.cumsum(0.5 * (pdf[1:] + pdf[:-1]) * np.diff(g))]); cdf /= cdf[-1]
    return np.interp(rng.uniform(0, 1, n), cdf, g)


def old_giants(n_hb, tip, hb_mv, hb_T, rgb_T, agb_T, agb_frac, rng, bottom=3.6):
    """post-main-sequence stars of an old population: RGB (+ subgiants) with dN/dM_V ~ 10^(0.3 M_V) normalised so
    N_HB / N_RGB(brighter than the HB) = R = 1.3, horizontal branch, AGB. -> (M_V, Teff)"""
    n_up = n_hb / 1.3
    k = 0.3 * math.log(10)
    tot = n_up * (math.exp(k * bottom) - math.exp(k * tip)) / (math.exp(k * hb_mv) - math.exp(k * tip))
    n_rgb = int(round(tot))
    u = rng.uniform(0, 1, n_rgb)
    mv = np.log(math.exp(k * tip) + u * (math.exp(k * bottom) - math.exp(k * tip))) / k
    T_rgb = np.interp(mv, [tip, bottom], rgb_T)
    hb_m = hb_mv + rng.normal(0, 0.15, int(n_hb))
    hT = rng.choice(hb_T[0], int(n_hb), p=hb_T[1]) * rng.uniform(0.9, 1.1, int(n_hb))
    hb_m = hb_m + np.where(hT > 9000, (hT - 9000) / 4000, 0)               # hot blue HB stars are fainter in V
    n_agb = int(round(agb_frac * n_hb))
    agb_m = rng.uniform(tip - 0.3, hb_mv - 0.3, n_agb)
    agb_t = np.interp(agb_m, [tip, hb_mv], agb_T)
    return (np.concatenate([mv, hb_m, agb_m]), np.concatenate([T_rgb, hT, agb_t]),
            dict(rgb=n_rgb, hb=int(n_hb), agb=n_agb))


def plummer_r(n, a, rmax, rng):
    u = rng.uniform(0, 1, n) * (1 / (1 + (a / rmax) ** 2)) ** 1.5            # truncated at rmax
    return a / np.sqrt(u ** (-2 / 3) - 1)


def powerlaw_r(n, rng, r_b=0.2, g_in=1.2, g_out=1.8, rmax=10.0):
    """broken power-law density rho ~ r^-g_in (r < r_b), r^-g_out (r > r_b) -> radii by numeric inverse CDF"""
    g = np.logspace(-3, math.log10(rmax), 6000)
    rho = np.where(g < r_b, (g / r_b) ** -g_in, (g / r_b) ** -g_out)
    m = np.concatenate([[0], np.cumsum(0.5 * (rho[1:] * g[1:] ** 2 + rho[:-1] * g[:-1] ** 2) * np.diff(g))]); m /= m[-1]
    return np.interp(rng.uniform(0, 1, n), m, g), (g, m)


def iso_dirs(n, rng):
    v = rng.standard_normal((n, 3)); return v / np.linalg.norm(v, axis=1, keepdims=True)


# ------------------------------------------------------------------------------------------- clusters
# real bright members: (name, V, B-V) -> M_V with the cluster's distance modulus
PLEIADES_BRIGHT = [("Alcyone", 2.87, -0.09), ("Atlas", 3.62, -0.07), ("Electra", 3.70, -0.11), ("Maia", 3.86, -0.07),
                   ("Merope", 4.18, -0.06), ("Taygeta", 4.30, -0.11), ("Pleione", 5.05, -0.08), ("Celaeno", 5.45, -0.04),
                   ("Asterope", 5.76, -0.05)]
HYADES_BRIGHT = [("theta2 Tau", 3.40, 0.18), ("epsilon Tau", 3.53, 1.01), ("gamma Tau", 3.65, 0.99),
                 ("delta1 Tau", 3.76, 0.98), ("theta1 Tau", 3.84, 0.95)]


def bv_temp(ci):
    return 4600.0 * (1.0 / (0.92 * ci + 1.7) + 1.0 / (0.92 * ci + 0.62))


CL = {
    # Pleiades: 136 pc (Gaia; 444 ly), ~1,000-1,300 members (Lodieu et al. 2019), age ~110 Myr (turnoff ~5 Msun),
    # core radius ~2 pc, tidal radius ~12 pc. Massive stars more concentrated (mass segregation).
    "pleiades": dict(N=1100, mlo=0.10, mhi=5.0, ms=MS_SOLAR, a=2.6, a_big=1.6, rmax=12.0, r_obs=1.0, dm=5.67,
                     bright=PLEIADES_BRIGHT, seed=103),
    # Hyades: 47 pc (153 ly), ~700 members within 30 pc (Lodieu et al. 2019; Roeser et al. 2019), age ~650 Myr
    # (turnoff ~2.4 Msun), core ~2.7 pc, tidal radius ~10 pc. The 4 orange giants + theta2 Tau injected.
    "hyades": dict(N=700, mlo=0.10, mhi=2.4, ms=MS_SOLAR, a=3.5, a_big=2.0, rmax=10.0, r_obs=1.0, dm=3.36,
                   bright=HYADES_BRIGHT, seed=12),
    # Omega Centauri: ~10 million stars, ~4e6 Msun, 5.4 kpc (17,000 ly); metal-poor, ~12 Gyr; half-light radius ~7.6 pc,
    # central density ~1e4 stars/pc^3 (~4,000 Msun/pc^3). Plummer a = 6 pc. ~3,000 horizontal-branch stars, many blue.
    "omega": dict(N=10_000_000, mlo=0.08, mhi=0.80, ms=MS_POOR, a=6.0, a_big=6.0, rmax=80.0, r_obs=1.0,
                  giants=dict(n_hb=3000, tip=-2.5, hb_mv=0.6, hb_T=([5200, 6500, 8000, 11000, 16000, 22000],
                              [0.25, 0.15, 0.15, 0.2, 0.15, 0.10]), rgb_T=(4150, 5200), agb_T=(4000, 5600), agb_frac=0.12),
                  seed=13),
    # Milky Way nuclear star cluster around Sgr A* (8.2 kpc, 26,700 ly): ~1e6 Msun of stars within 1 pc (Genzel et al.
    # 2010; Schoedel et al. 2018), rho ~ r^-1.2 inside 0.2 pc, ~r^-1.8 outside; mostly old, ~solar metallicity.
    # ~1.5 million stars within 1 pc (3.3 ly) -> 2.5e7 within 10 pc. Plus the young central cluster: ~100 O/B/Wolf-Rayet
    # stars in 0.04-0.5 pc (Paumard et al. 2006; Lu et al. 2009), and the red supergiant IRS 7.
    "nsc": dict(N=25_000_000, mlo=0.08, mhi=1.0, ms=MS_SOLAR, r_obs=1.0, n1pc=1.5e6,
                giants=dict(n_hb=8100, tip=-1.6, hb_mv=0.8, hb_T=([4700, 5000], [0.5, 0.5]), rgb_T=(3700, 4900),
                            agb_T=(3200, 4300), agb_frac=0.15),
                seed=14),
}


def population(c, n, rng, first):
    """absolute magnitudes, temperatures and 'big' flags for n stars (giants / injected stars only in the first chunk)"""
    m = kroupa(n, c["mlo"], c["mhi"], rng)
    mv, T = ms_lookup(c["ms"], m)
    big = m > 1.8
    extra = {}
    if first and "giants" in c:
        g = c["giants"]
        nscale = c["N"] / 1e7
        gm, gT, cnt = old_giants(g["n_hb"] * (nscale if c is CL["omega"] else 1.0), g["tip"], g["hb_mv"], g["hb_T"],
                                 g["rgb_T"], g["agb_T"], g["agb_frac"], rng)
        # the giants replace the same number of main-sequence stars (keep N)
        k = len(gm); mv[:k], T[:k] = gm, gT; big[:k] = False; extra.update(cnt)
    if first and "bright" in c:
        order = np.argsort(-m)[:len(c["bright"])]
        for j, (nm, V, bv) in zip(order, c["bright"]):
            mv[j] = V - c["dm"]; T[j] = bv_temp(bv)
    return m, mv, T, big, extra


def positions(c, key, n, rng, big):
    if key == "nsc":
        r, _ = powerlaw_r(n, rng)
    else:
        r = plummer_r(n, c["a"], c["rmax"], rng)
        if big.any(): r[big] = plummer_r(int(big.sum()), c["a_big"], c["rmax"], rng)
    return r[:, None] * iso_dirs(n, rng)


def young_nsc(rng):
    """young central cluster around Sgr A*: Wolf-Rayet + O supergiants + B stars (clockwise disk + S-stars), IRS 7"""
    mv, T, r = [], [], []
    for nn, mlo, mhi, tlo, thi, rlo, rhi in ((30, -7.0, -5.0, 30000, 45000, 0.04, 0.5),     # WR / Ofpe (IRS 16, IRS 13)
                                              (60, -6.0, -4.5, 25000, 35000, 0.04, 0.5),     # O / B supergiants
                                              (40, -3.2, -1.8, 18000, 25000, 0.003, 0.04),   # S-stars (B dwarfs)
                                              (150, -3.0, -1.0, 14000, 25000, 0.05, 0.6)):   # B dwarfs of the disk
        mv.append(rng.uniform(mlo, mhi, nn)); T.append(rng.uniform(tlo, thi, nn)); r.append(np.exp(rng.uniform(np.log(rlo), np.log(rhi), nn)))
    mv, T, r = np.concatenate(mv), np.concatenate(T), np.concatenate(r)
    d = iso_dirs(len(mv), rng)
    # flatten most of them into the clockwise disk (inclination ~127 deg; here a plane tilted 50 deg to the observer axis)
    nrm = np.array([0.0, math.sin(math.radians(50)), math.cos(math.radians(50))])
    flat = rng.uniform(0, 1, len(mv)) < 0.6
    d[flat] -= (d[flat] @ nrm)[:, None] * nrm[None] * 0.85
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    pos = r[:, None] * d
    # IRS 7: red supergiant (M2 I), ~0.23 pc north of Sgr A*, M_V ~ -7.5
    pos = np.vstack([pos, [[0.0, 0.0, 0.23]]]); mv = np.append(mv, -7.5); T = np.append(T, 3600.0)
    return pos, mv, T


def build(key):
    c = CL[key]; rng = np.random.default_rng(c["seed"])
    # observer: r_obs from the centre along -z (the cluster centre is then towards +z, the "core direction")
    obs = np.array([0.0, 0.0, -c["r_obs"]])
    keep_v, keep_d, keep_T, keep_pc = [], [], [], []
    fmap = np.zeros((MH, MW))
    near = 1e9; tot_flux = 0.0; n_sirius = 0; n6 = 0; n_bright_mv = 0; extra = {}
    n_done = 0; first = True
    N = c["N"]
    while n_done < N:
        n = min(CHUNK, N - n_done)
        m, mv, T, big, ex = population(c, n, rng, first); extra.update(ex)
        pos = positions(c, key, n, rng, big)
        if first and key == "nsc":
            yp, ym, yT = young_nsc(rng)
            pos = np.vstack([pos, yp]); mv = np.concatenate([mv, ym]); T = np.concatenate([T, yT])
            extra["young"] = len(ym)
        first = False
        rel = pos - obs
        d = np.linalg.norm(rel, axis=1)
        ok = d > 1e-4                                                        # (never put a star on top of us)
        rel, d, mv, T = rel[ok], d[ok], mv[ok], T[ok]
        V = mv + 5 * np.log10(d / 10.0)
        u = rel / d[:, None]
        near = min(near, float(d.min()))
        f = 10 ** (-0.4 * V)
        tot_flux += float(f.sum()); n_sirius += int((V < V_SIRIUS).sum()); n6 += int((V < 6.0).sum())
        kp = V < V_KEEP
        keep_v.append(V[kp]); keep_d.append(u[kp]); keep_T.append(T[kp]); keep_pc.append(d[kp])
        # faint stars -> integrated-light map (equirect, flux per pixel)
        fp = ~kp
        ra = (np.degrees(np.arctan2(u[fp, 1], u[fp, 0])) % 360.0); de = np.degrees(np.arcsin(np.clip(u[fp, 2], -1, 1)))
        xi = np.clip((ra / 360 * MW).astype(int), 0, MW - 1); yi = np.clip(((90 - de) / 180 * MH).astype(int), 0, MH - 1)
        fmap += np.bincount(yi * MW + xi, weights=f[fp], minlength=MW * MH).reshape(MH, MW)
        n_done += n
        print(f"  {key}: {n_done:,}/{N:,}", flush=True)
    V = np.concatenate(keep_v); D = np.concatenate(keep_d); T = np.concatenate(keep_T); P = np.concatenate(keep_pc)
    o = np.argsort(V); V, D, T, P = V[o], D[o], T[o], P[o]
    # flux per steradian of the faint map
    dec_c = 90 - (np.arange(MH) + 0.5) / MH * 180
    pix_sr = (2 * np.pi / MW) * (np.pi / MH) * np.cos(np.radians(dec_c))
    sb = fmap / pix_sr[:, None]
    np.savez(os.path.join(SCR, f"cl_{key}.npz"), V=V.astype(np.float32), dirs=D.astype(np.float32), T=T.astype(np.float32),
             pc=P.astype(np.float32), faint=sb.astype(np.float32))
    tot_V = -2.5 * math.log10(tot_flux)
    # illuminance on the ground ~ sum over the upper hemisphere of flux * sin(alt): for an isotropic sky ~ total/4
    st = dict(N=N, n_V6=n6, n_sirius=n_sirius, n_kept=int(len(V)), nearest_pc=near, nearest_ly=near * LY,
              nearest_au=near * 206265, total_V=tot_V, brightest=[round(float(x), 2) for x in V[:12]],
              n_brighter_than_venus=int((V < -4.4).sum()), n_brighter_than_jupiter=int((V < -2.5).sum()),
              faint_V_total=-2.5 * math.log10(max(fmap.sum(), 1e-30)), **extra)
    # mean sky surface brightness of the faint (unresolved) part, mag/arcsec^2 (natural dark sky ~ 22)
    sr_as2 = (180 / math.pi * 3600) ** 2
    st["faint_mag_arcsec2_mean"] = -2.5 * math.log10(fmap.sum() / (4 * math.pi) / sr_as2)
    st["all_mag_arcsec2_mean"] = -2.5 * math.log10(tot_flux / (4 * math.pi) / sr_as2)
    # local stellar number density around the observer
    return st


def local_density(key):
    c = CL[key]
    if key == "nsc":
        _, (g, m) = powerlaw_r(10, np.random.default_rng(0))
        Nin = c["N"]
        # density at r_obs from the numeric cumulative profile
        r = c["r_obs"]; i = np.searchsorted(g, r)
        dm = (m[i + 1] - m[i - 1]) / (g[i + 1] - g[i - 1]) * Nin
        n1 = float(np.interp(1.0, g, m) * Nin)
        return dm / (4 * math.pi * r * r), n1
    a = c["a"]; r = c["r_obs"]
    return 3 * c["N"] / (4 * math.pi * a ** 3) * (1 + (r / a) ** 2) ** -2.5, None


if __name__ == "__main__":
    keys = sys.argv[1:] or list(CL)
    path = os.path.join(SCR, "stats.json")
    stats = json.load(open(path)) if os.path.exists(path) else {}
    for k in keys:
        st = build(k)
        n_loc, n1 = local_density(k)
        st["local_density_pc3"] = n_loc; st["x_solar_neighbourhood"] = n_loc / 0.10
        st["typical_nearest_ly"] = 0.554 * n_loc ** (-1 / 3) * LY
        if n1: st["N_within_1pc"] = n1
        stats[k] = st
        print(k, json.dumps(st, indent=1))
    json.dump(stats, open(path, "w"), indent=1)
