"""Crop MAT question strips out of scanned booklet pages.
usage: python3 crop.py  (edit JOBS below)"""
import numpy as np, os, sys
from PIL import Image, ImageOps

def levels(im, lo=105, hi=205):
    a = np.asarray(im).astype(np.float32)
    a = np.clip((a - lo) * 255.0 / (hi - lo), 0, 255)
    return Image.fromarray(a.astype(np.uint8))

def strip(im, x0, x1, y0, y1, pad=14, thr=140, minrow=10, mincol=3, maxw=920):
    """im: L image. window in px. trims to ink, returns cleaned strip"""
    W, H = im.size
    x0, x1, y0, y1 = max(0, x0), min(W, x1), max(0, y0), min(H, y1)
    a = np.asarray(im)[y0:y1, x0:x1] < thr
    rows = np.where(a.sum(1) >= minrow)[0]
    cols = np.where(a.sum(0) >= mincol)[0]
    if len(rows) == 0 or len(cols) == 0:
        raise SystemExit('empty window')
    r0, r1 = rows[0], rows[-1]
    c0, c1 = cols[0], cols[-1]
    box = (x0 + max(0, c0 - pad), y0 + max(0, r0 - pad), x0 + min(a.shape[1], c1 + pad), y0 + min(a.shape[0], r1 + pad))
    out = levels(im.crop(box))
    if maxw and out.width > maxw:
        out = out.resize((maxw, round(out.height * maxw / out.width)), Image.LANCZOS)
    return out

def trim(im, pad=10, thr=150):
    a = np.asarray(im) < thr
    rows = np.where(a.sum(1) >= 2)[0]; cols = np.where(a.sum(0) >= 2)[0]
    return im.crop((max(0, cols[0] - pad), max(0, rows[0] - pad), min(im.width, cols[-1] + pad), min(im.height, rows[-1] + pad)))

def split(im, win=10, thr=150):
    """find the vertical rule between question figure(s) and answer figures.
    returns (left, right) images or None"""
    a = np.asarray(im) < thr
    H, W = a.shape
    best = None
    for x in range(int(W * 0.10), int(W * 0.66)):
        cov = a[:, x:x + win].any(1).mean()
        if cov >= 0.84 and (best is None or cov > best[1]):
            best = (x, cov)
            if cov == 1.0: break
    if not best: return None
    x = best[0]
    return trim(im.crop((0, 0, x - 3, H))), trim(im.crop((x + win + 3, 0, W, H)))

def emit(im, prefix, maxw=920, dosplit=True):
    """im = full-resolution strip. writes prefix.png, or prefixa.png + prefixb.png"""
    for f in (prefix + '.png', prefix + 'a.png', prefix + 'b.png'):
        if os.path.exists(f): os.remove(f)
    k = min(1.0, maxw / im.width)
    def rs(i): return i.resize((max(1, round(i.width * k)), max(1, round(i.height * k))), Image.LANCZOS) if k < 1 else i
    sp = split(im) if dosplit else None
    if sp:
        save(rs(sp[0]), prefix + 'a.png'); save(rs(sp[1]), prefix + 'b.png'); return 2
    save(rs(im), prefix + '.png'); return 1

def save(im, path):
    q = im.quantize(colors=12, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    q.save(path, optimize=True)
