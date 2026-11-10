"""Real all-sky maps -> galactic equirectangular textures (l = 0 at column 0 increasing to the right, b = +90 at row 0).
Inputs (downloaded once into SCR/dl, see README): Haslam 408 MHz (LAMBDA, NESTED nside 512, mK), Planck HFI 857 GHz
and 100 GHz (PR2, nside 128), Fermi-LAT 3FHL event list (>10 GeV, all sky) and the 4FGL-DR4 catalogue (gll_psc_v35).
Run: PYTHONPATH=SCR/pylib /home/user/ttsenv/bin/python -I prep_maps.py  -> SCR/maps.npz"""
import os, sys
SCR = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/series/S3-gamma-ray-eyes"
sys.path.insert(0, os.path.join(SCR, "pylib"))
import numpy as np, healpy as hp
from astropy.io import fits
from scipy.ndimage import gaussian_filter

DL = os.path.join(SCR, "dl")
W, H = 2048, 1024
l = (np.arange(W) + 0.5) / W * 360.0
b = 90.0 - (np.arange(H) + 0.5) / H * 180.0
L, B = np.meshgrid(l, b)


def hpx_to_eq(m, nest):
    m = np.where(np.isfinite(m) & (m > -1e20), m, np.nanmedian(m))
    return hp.get_interp_val(m, L, B, nest=nest, lonlat=True).astype(np.float32)


def main():
    out = {}
    # radio: Haslam 408 MHz all-sky survey (K)
    m = fits.open(os.path.join(DL, "haslam/lambda_haslam408_nofilt.fits"))[1].data["TEMPERATURE"].ravel().astype(np.float64)
    out["radio"] = hpx_to_eq(m, True) / 1000.0
    # infrared: Planck 857 GHz (350 um) thermal dust, MJy/sr
    m = fits.open(os.path.join(DL, "planck/HFI_SkyMap_857_128_R2.00_NESTED.fits"))[1].data["I"].ravel().astype(np.float64)
    out["ir"] = hpx_to_eq(m, True)
    # microwave: Planck 100 GHz, K_CMB (monopole 2.725 K and the dipole removed -> anisotropy + galaxy)
    m = fits.open(os.path.join(DL, "planck/HFI_SkyMap_100_128_R2.00_RING.fits"))[1].data["I"].ravel().astype(np.float64)
    out["micro"] = hpx_to_eq(m, False) * 1e6                      # uK
    # gamma: Fermi-LAT 3FHL photons (>10 GeV), binned + smoothed (counts; LAT exposure is near-uniform over the sky)
    ev = fits.open(os.path.join(DL, "fermi/fermi_3fhl_events_selected.fits.gz"))[1].data
    gl, gb = np.asarray(ev["L"], float) % 360, np.asarray(ev["B"], float)
    cnt, _, _ = np.histogram2d(90 - gb, gl, bins=[H, W], range=[[0, 180], [0, 360]])
    # equal-area correction of the plate carree bins
    cnt /= np.maximum(np.cos(np.radians(b)), 0.02)[:, None]
    out["gamma"] = (gaussian_filter(cnt, 1.6, mode="wrap") * 1.0).astype(np.float32)
    out["gamma_fine"] = (gaussian_filter(cnt, 0.7, mode="wrap")).astype(np.float32)
    # 4FGL-DR4 blazars (bright ones) for the twinkling points in gamma
    c = fits.open(os.path.join(DL, "fermi/gll_psc_v35.fit.gz"))[1].data
    cls = np.char.strip(np.char.lower(np.asarray(c["CLASS1"]).astype(str)))
    fl = np.asarray(c["Energy_Flux100"], float)
    sel = np.isin(cls, ["bll", "fsrq", "bcu"]) & np.isfinite(fl)
    idx = np.argsort(-fl[sel])[:160]
    out["blz"] = np.stack([np.asarray(c["GLON"], float)[sel][idx], np.asarray(c["GLAT"], float)[sel][idx], fl[sel][idx] / fl[sel][idx][0]], 1).astype(np.float32)
    print("blazars", out["blz"][:5], [n for n in np.asarray(c["ASSOC1"]).astype(str)[sel][idx][:5]])
    for k, v in out.items(): print(k, v.shape, float(np.percentile(v, 1)), float(np.percentile(v, 50)), float(np.percentile(v, 99.9)))
    np.savez_compressed(os.path.join(SCR, "maps.npz"), **out)


if __name__ == "__main__":
    main()
