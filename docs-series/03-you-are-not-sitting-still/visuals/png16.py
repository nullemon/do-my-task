"""Minimal reader for the 16-bit RGB PNGs written by andromeda-doc/ch2/gen_textures.py (filter 0 rows)."""
import zlib, struct, numpy as np


def read_png16(path):
    b = open(path, "rb").read()
    pos, idat, w = 8, [], None
    while pos < len(b):
        n = struct.unpack(">I", b[pos:pos + 4])[0]; t = b[pos + 4:pos + 8]; d = b[pos + 8:pos + 8 + n]
        if t == b"IHDR":
            w, h, depth, ctype = struct.unpack(">IIBB", d[:10])
            assert depth == 16 and ctype == 2
        elif t == b"IDAT":
            idat.append(d)
        pos += 12 + n
    raw = np.frombuffer(zlib.decompress(b"".join(idat)), np.uint8).reshape(h, 1 + w * 6)
    assert (raw[:, 0] == 0).all(), "only filter-0 rows supported"
    a = raw[:, 1:].copy().view(">u2").reshape(h, w, 3).astype(np.float32) / 65535.0
    return a          # sRGB-encoded 0..1
