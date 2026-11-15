"""Lake water segmentation for 03_calm_lake_wooden_pier.png (copied unchanged from ../more-moons/lake.py; cached in SCR/lake.npz).
In SOURCE pixels (941x1672): the shoreline / mirror line is y = 1172. The water is segmented by GrabCut, seeded with
hand-measured polygons for the pier deck, its ten posts and the left shore, then upscaled to the 1080x1920 frame.
Also stores `occ`: how much of each water pixel is a reflection of the shore trees / posts in the photo (dark against the
bright sky reflection), used to keep the photo's own tree and post reflections and replace only the sky's reflection."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [os.path.join(HERE, ".."), HERE]
import lib.core  # noqa
import numpy as np, cv2
from PIL import Image

SRC = "/tmp/claude-0/-home-user-do-my-task/3692798c-2ff9-5c2c-84e7-cdc249cb8847/scratchpad/backgrounds/03_calm_lake_wooden_pier.png"
Y_SHORE = 1172
DECK = [(398, 1218), (518, 1218), (941, 1655), (941, 1672), (0, 1672), (0, 1668), (18, 1668)]
POSTS = [(378, 1200, 401, 1265), (402, 1188, 414, 1240), (410, 1188, 423, 1235), (338, 1216, 371, 1302), (262, 1254, 317, 1392),
         (513, 1188, 531, 1235), (524, 1192, 542, 1245), (540, 1200, 564, 1265), (577, 1216, 611, 1308), (653, 1254, 711, 1412)]
SHORE = [(0, 1378), (40, 1382), (95, 1393), (118, 1410), (120, 1440), (105, 1468), (128, 1500), (140, 1530), (110, 1580), (75, 1640), (40, 1672), (0, 1672)]
ROCK_R = [(890, 1585), (941, 1580), (941, 1650), (900, 1640)]


def build():
    im = np.asarray(Image.open(SRC).convert("RGBA"))
    rgb = np.ascontiguousarray(im[..., :3][..., ::-1]); a = im[..., 3]
    H, W = a.shape
    mask = np.full((H, W), cv2.GC_PR_FGD, np.uint8)
    mask[:Y_SHORE - 4] = cv2.GC_BGD
    mask[a < 128] = cv2.GC_BGD
    bg = np.zeros((H, W), np.uint8)
    cv2.fillPoly(bg, [np.array(DECK, np.int32)], 1)
    for x0, y0, x1, y1 in POSTS: cv2.rectangle(bg, (x0, y0), (x1, y1), 1, -1)
    cv2.fillPoly(bg, [np.array(SHORE, np.int32)], 1); cv2.fillPoly(bg, [np.array(ROCK_R, np.int32)], 1)
    inner = cv2.erode(bg, np.ones((7, 7), np.uint8))
    mask[bg > 0] = cv2.GC_PR_BGD; mask[inner > 0] = cv2.GC_BGD
    # left pine branches hanging over the water: probable background, sure water well away from everything
    pine = np.zeros((H, W), np.uint8); cv2.fillPoly(pine, [np.array([(0, 1160), (130, 1160), (130, 1290), (60, 1360), (0, 1370)], np.int32)], 1)
    far = cv2.dilate(bg | pine, np.ones((41, 41), np.uint8))
    sure = (far == 0) & (np.arange(H)[:, None] > Y_SHORE + 8) & (a > 128)
    mask[sure] = cv2.GC_FGD
    y0 = Y_SHORE - 30
    sub = mask[y0:].copy(); bgm = np.zeros((1, 65), np.float64); fgm = np.zeros((1, 65), np.float64)
    cv2.grabCut(rgb[y0:], sub, None, bgm, fgm, 6, cv2.GC_INIT_WITH_MASK)
    water = np.zeros((H, W), np.float32)
    water[y0:] = ((sub == cv2.GC_FGD) | (sub == cv2.GC_PR_FGD)).astype(np.float32)
    water[:Y_SHORE] = 0
    # keep the largest connected parts only (drop specks in the deck), soften the edge a little
    n, lab, st, _ = cv2.connectedComponentsWithStats((water > 0.5).astype(np.uint8), 8)
    keep = np.zeros(n, bool); keep[1:] = st[1:, cv2.CC_STAT_AREA] > 400
    water = keep[lab].astype(np.float32)
    # the shoreline: fade in over 3 px
    yy = np.arange(H, dtype=np.float32)[:, None]
    water *= np.clip((yy - Y_SHORE) / 3.0, 0, 1)
    # tree / post reflection fraction: luminance against a smooth upper envelope of the open water
    L = (rgb[..., ::-1].astype(np.float32) / 255) @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    Lw = np.where(water > 0.5, L, 0).astype(np.float32)
    env = cv2.dilate(Lw, np.ones((1, 121), np.uint8)); env = cv2.dilate(env, np.ones((41, 1), np.uint8))
    env = cv2.GaussianBlur(env, (0, 0), 25)
    occ = np.clip((1 - L / np.maximum(env, 1e-3) - 0.18) / 0.45, 0, 1).astype(np.float32)
    occ = cv2.GaussianBlur(occ, (0, 0), 0.8) * water
    return water, occ


def to_frame(x, W=1080, H=1920):
    s = W / 941.0; oy = H - 1672 * s
    M = np.array([[s, 0, 0], [0, s, oy]], np.float64)
    return cv2.warpAffine(x, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0), s, oy


def load(scr):
    p = os.path.join(scr, "lake.npz")
    if not os.path.exists(p):
        w, o = build()
        wf, s, oy = to_frame(w); of, _, _ = to_frame(o)
        np.savez_compressed(p, water=wf.astype(np.float32), occ=of.astype(np.float32), y_mirror=Y_SHORE * s + oy)
    z = np.load(p)
    return z["water"], z["occ"], float(z["y_mirror"])


if __name__ == "__main__":
    scr = sys.argv[1]
    w, o, ym = load(scr)
    im = np.asarray(Image.open(SRC).convert("RGB").resize((1080, 1919), Image.LANCZOS)).astype(np.float32) / 255
    im = np.concatenate([np.zeros((1, 1080, 3), np.float32), im])
    vis = im.copy(); vis[..., 0] = np.clip(vis[..., 0] + w * 0.6, 0, 1); vis[..., 2] = np.clip(vis[..., 2] + o * 0.8, 0, 1)
    Image.fromarray((vis[1200:] * 255).astype(np.uint8)).save(os.path.join(scr, "lake_mask.jpg"))
    print("mirror line", ym)
