#!/usr/bin/env python3
"""Generates Section I (Mental Ability, Q1-40) as SVG figures for papers that have no scanned figures.

These are NEW practice questions drawn by code on the JNVST pattern (10 parts x 4 questions).
They are NOT the figures of the original booklets.  Every question is checked by the program:
the four options are pairwise different and the keyed answer follows from the rule.

    python3 matgen.py            # all papers listed in PAPERS
    python3 matgen.py 2023       # one paper

Output: papers/<id>/qNN.svg | qNNa.svg + qNNb.svg  and  tools/gen/<id>.json (key + review notes)
"""
import math, os, random, json, sys
from PIL import Image, ImageDraw
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAPERS = ['2021', '2022', '2023', '2024', '2025']
W = 2.0            # stroke width in cell units (a cell is 100 x 100)
ABCD = 'ABCD'
sin = lambda d: math.sin(math.radians(d))
cos = lambda d: math.cos(math.radians(d))


class Retry(Exception):
    pass


# ------------------------------------------------------------------ figure model
class Fig:
    def __init__(self, items=None):
        self.items = list(items or [])

    def pl(self, pts, closed=False, fill=None, w=W):
        self.items.append(('pl', [tuple(p) for p in pts], closed, fill, w)); return self

    def line(self, x1, y1, x2, y2, w=W):
        return self.pl([(x1, y1), (x2, y2)], w=w)

    def poly(self, pts, fill=None, w=W):
        return self.pl(pts, closed=True, fill=fill, w=w)

    def dash(self, x1, y1, x2, y2, on=5.0, off=4.0, w=1.4):
        L = math.hypot(x2 - x1, y2 - y1); ux, uy = (x2 - x1) / L, (y2 - y1) / L; s = 0.0
        while s < L:
            e = min(L, s + on)
            self.line(x1 + ux * s, y1 + uy * s, x1 + ux * e, y1 + uy * e, w=w); s += on + off
        return self

    def circle(self, cx, cy, r, fill=None, w=W):
        self.items.append(('ci', (cx, cy), r, fill, w)); return self

    def dot(self, cx, cy, r=4.2):
        return self.circle(cx, cy, r, 'k')

    def arc(self, cx, cy, r, a1, a2, w=W):
        """a1 -> a2 in degrees, measured clockwise from 'up'"""
        n = max(2, int(abs(a2 - a1) / 6) + 1)
        return self.pl([(cx + r * sin(a1 + (a2 - a1) * i / n), cy - r * cos(a1 + (a2 - a1) * i / n)) for i in range(n + 1)], w=w)

    def text(self, x, y, s, size=14):
        self.items.append(('tx', (x, y), s, size)); return self

    def add(self, *others):
        for o in others: self.items += o.items
        return self

    def map(self, f, k=1.0):
        out = []
        for it in self.items:
            if it[0] == 'pl': out.append(('pl', [f(p) for p in it[1]]) + it[2:])
            elif it[0] == 'ci': out.append(('ci', f(it[1]), it[2] * k) + it[3:])
            else: out.append(('tx', f(it[1])) + it[2:])
        return Fig(out)


def rot(fig, deg, c=(50, 50)):
    """rotate clockwise (as seen on screen) by deg"""
    cs, sn = cos(deg), sin(deg)
    return fig.map(lambda p: (c[0] + (p[0] - c[0]) * cs - (p[1] - c[1]) * sn, c[1] + (p[0] - c[0]) * sn + (p[1] - c[1]) * cs))


def flipH(fig, cx=50): return fig.map(lambda p: (2 * cx - p[0], p[1]))
def flipV(fig, cy=50): return fig.map(lambda p: (p[0], 2 * cy - p[1]))
def move(fig, dx, dy): return fig.map(lambda p: (p[0] + dx, p[1] + dy))
def scale(fig, k, c=(50, 50)): return fig.map(lambda p: (c[0] + (p[0] - c[0]) * k, c[1] + (p[0] * 0 + p[1] - c[1]) * k), k)


def dihedral(fig, c=(50, 50)):
    """the 8 images of a figure under rotations and reflections"""
    out = []
    for f in (fig, flipH(fig, c[0])):
        for k in range(4): out.append(rot(f, 90 * k, c))
    return out


def ngon(n, cx=50, cy=50, r=38, a0=0):
    return [(cx + r * sin(a0 + 360.0 * i / n), cy - r * cos(a0 + 360.0 * i / n)) for i in range(n)]


def shape(name, cx=50, cy=50, r=38):
    """outline points of a named shape (a circle is returned as None)"""
    if name == 'circle': return None
    if name == 'square': return ngon(4, cx, cy, r * 1.18, 45)
    if name == 'triangle': return ngon(3, cx, cy + r * 0.12, r * 1.12)
    if name == 'pentagon': return ngon(5, cx, cy + r * 0.04, r)
    if name == 'hexagon': return ngon(6, cx, cy, r, 30)
    if name == 'diamond': return ngon(4, cx, cy, r)
    raise KeyError(name)


def add_shape(f, name, cx=50, cy=50, r=38, fill=None, w=W):
    pts = shape(name, cx, cy, r)
    if pts is None: f.circle(cx, cy, r * 0.95, fill, w)
    else: f.poly(pts, fill, w)
    return f


# ------------------------------------------------------------------ raster (used only for checks)
RS = 1.6


def ras(fig):
    """black/white picture of a figure; the result does not depend on the order in which points are listed"""
    im = Image.new('L', (160, 160), 255); d = ImageDraw.Draw(im)
    col = {'k': 0, 'w': 255}
    def seg(a, b):
        a, b = sorted([(round(a[0] * RS, 2), round(a[1] * RS, 2)), (round(b[0] * RS, 2), round(b[1] * RS, 2))])
        d.line([a, b], fill=0, width=4)
        for x, y in (a, b): d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=0)
    for it in fig.items:
        if it[0] == 'pl':
            pts = it[1]
            if it[2] and it[3]:
                k = min(range(len(pts)), key=lambda i: pts[i]); q = pts[k:] + pts[:k]
                if len(q) > 2 and q[1] > q[-1]: q = [q[0]] + q[:0:-1]
                d.polygon([(round(x * RS, 2), round(y * RS, 2)) for x, y in q], fill=col[it[3]])
            for i in range(len(pts) - (0 if it[2] else 1)): seg(pts[i], pts[(i + 1) % len(pts)])
        elif it[0] == 'ci':
            (x, y), r = it[1], it[2]
            box = [round((x - r) * RS, 2), round((y - r) * RS, 2), round((x + r) * RS, 2), round((y + r) * RS, 2)]
            d.ellipse(box, fill=col.get(it[3]), outline=0, width=4)
    return np.asarray(im) < 128


def diff(a, b):
    return int(np.count_nonzero(ras(a) ^ ras(b)))


def distinct(figs, thr=70):
    R = [ras(f) for f in figs]
    for i in range(len(R)):
        for j in range(i + 1, len(R)):
            if np.count_nonzero(R[i] ^ R[j]) < thr: return False
    return True


def need(cond):
    if not cond: raise Retry()


# ------------------------------------------------------------------ SVG output
def n1(v):
    s = '%.1f' % v
    return s[:-2] if s.endswith('.0') else s


def svg_items(fig):
    out = []
    col = {'k': '#000', 'w': '#fff', None: 'none'}
    for it in fig.items:
        if it[0] == 'pl':
            d = 'M' + 'L'.join('%s %s' % (n1(x), n1(y)) for x, y in it[1]) + ('Z' if it[2] else '')
            out.append('<path d="%s" fill="%s" stroke-width="%s"/>' % (d, col[it[3]], n1(it[4])))
        elif it[0] == 'ci':
            out.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke-width="%s"/>' % (n1(it[1][0]), n1(it[1][1]), n1(it[2]), col[it[3]], n1(it[4])))
        else:
            out.append('<text x="%s" y="%s" font-size="%s" stroke="none" fill="#000">%s</text>' % (n1(it[1][0]), n1(it[1][1]), it[3], it[2]))
    return ''.join(out)


def strip(cells, cs, gaps, labels=False):
    """cells: list of (fig|None, frame, width_units).  Returns (svg, width, height)."""
    x = 0.0; body = []; s = cs / 100.0
    for i, (fig, frame, wu) in enumerate(cells):
        g = '<g transform="translate(%s,1) scale(%s)">' % (n1(x + 1), ('%.3f' % s).rstrip('0'))
        if frame: g += '<rect x="0" y="0" width="%s" height="100" fill="none" stroke-width="1"/>' % wu
        if fig is not None: g += svg_items(fig)
        body.append(g + '</g>')
        if labels:
            body.append('<text x="%s" y="%s" font-size="15" stroke="none" fill="#000">(%s)</text>' % (n1(x + 1 + cs * wu / 200.0), n1(cs + 19), ABCD[i]))
        x += cs * wu / 100.0 + (gaps[i] if i < len(cells) - 1 else 0)
    wpx = int(math.ceil(x + 2)); hpx = int(cs + 2 + (24 if labels else 0))
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" fill="none" stroke="#000" '
           'stroke-linecap="round" stroke-linejoin="round" font-family="\'Times New Roman\',Times,serif" font-weight="bold" text-anchor="middle">%s</svg>\n'
           % (wpx, hpx, wpx, hpx, ''.join(body)))
    return svg, wpx, hpx


# ------------------------------------------------------------------ building blocks
LAT = [20, 40, 60, 80]


def walk(rng, nseg, size=4):
    """self-avoiding lattice walk made of straight and diagonal steps"""
    steps = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1), (2, 0), (-2, 0), (0, 2), (0, -2)]
    for _ in range(200):
        pts = [(rng.randrange(size), rng.randrange(size))]; last = None; ok = True
        while len(pts) < nseg + 1:
            x, y = pts[-1]
            cand = [(x + dx, y + dy, (dx, dy)) for dx, dy in steps
                    if 0 <= x + dx < size and 0 <= y + dy < size and (x + dx, y + dy) not in pts
                    and (dx, dy) != last and (last is None or (dx * last[0] + dy * last[1]) >= 0 or abs(dx * last[1] - dy * last[0]) > 0)]
            # never step straight back over the previous segment, never pass through a visited point
            cand = [c for c in cand if not (abs(c[2][0]) == 2 and (x + c[2][0] // 2, y) in pts) and not (abs(c[2][1]) == 2 and (x, y + c[2][1] // 2) in pts)]
            cand = [c for c in cand if last is None or not (c[2][0] == -last[0] and c[2][1] == -last[1])]
            if not cand: ok = False; break
            c = rng.choice(cand); pts.append((c[0], c[1])); last = c[2]
        if ok: return pts
    raise Retry()


def glyph(rng, nseg=None, marker=None):
    """an asymmetric line figure with an end marker; all 8 dihedral images are different"""
    for _ in range(60):
        n = nseg or rng.choice([3, 4, 4, 5])
        pts = walk(rng, n)
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        if max(xs) - min(xs) < 2 or max(ys) - min(ys) < 2: continue
        f = Fig().pl([(LAT[x], LAT[y]) for x, y in pts])
        m = marker or rng.choice(['dot', 'ring', 'sq', 'tri', 'bar'])
        ex, ey = LAT[pts[-1][0]], LAT[pts[-1][1]]
        px, py = LAT[pts[-2][0]], LAT[pts[-2][1]]
        L = math.hypot(ex - px, ey - py); ux, uy = (ex - px) / L, (ey - py) / L
        if m == 'dot': f.dot(ex, ey, 5)
        elif m == 'ring': f.circle(ex + ux * 5, ey + uy * 5, 5)
        elif m == 'sq': f.poly([(ex - 5, ey - 5), (ex + 5, ey - 5), (ex + 5, ey + 5), (ex - 5, ey + 5)], 'k')
        elif m == 'tri': f.poly([(ex + ux * 9, ey + uy * 9), (ex - uy * 6, ey + ux * 6), (ex + uy * 6, ey - ux * 6)], 'k')
        else: f.line(ex - uy * 8, ey + ux * 8, ex + uy * 8, ey - ux * 8)
        if distinct(dihedral(f), 110): return f
    raise Retry()


def sym(name):
    """small oriented symbols drawn around (0, 0), about 18 units across"""
    f = Fig()
    if name == 'arrow': f.line(0, 9, 0, -9).pl([(-5, -3), (0, -9), (5, -3)])
    elif name == 'tri': f.poly([(0, -9), (7, 6), (-7, 6)], 'k')
    elif name == 'L': f.pl([(-5, -9), (-5, 7), (7, 7)])
    elif name == 'flag': f.line(-4, 9, -4, -9).poly([(-4, -9), (7, -4.5), (-4, 0)], 'k')
    elif name == 'half': f.poly([(8 * sin(a), -8 * cos(a)) for a in range(-90, 91, 15)], 'k')
    elif name == 'T': f.line(-8, -7, 8, -7).line(0, -7, 0, 9)
    elif name == 'vee': f.pl([(-8, 5), (0, -6), (8, 5)])
    elif name == 'pin': f.line(0, 9, 0, -3).circle(0, -6, 3.6)
    elif name == 'dotbar': f.line(-8, 6, 8, 6).dot(0, -3, 3.6)
    else: raise KeyError(name)
    return f


SYMS = ['arrow', 'tri', 'L', 'flag', 'half', 'T', 'vee', 'pin', 'dotbar']
CHIRAL = ['L', 'flag']


def place(name, x, y, k):
    return move(rot(sym(name), 90 * k, (0, 0)), x, y)


def arrow(f, x1, y1, x2, y2, h=5, w=1.6):
    f.line(x1, y1, x2, y2, w=w)
    L = math.hypot(x2 - x1, y2 - y1); ux, uy = (x2 - x1) / L, (y2 - y1) / L
    f.pl([(x2 - ux * h - uy * h * 0.6, y2 - uy * h + ux * h * 0.6), (x2, y2), (x2 - ux * h + uy * h * 0.6, y2 - uy * h - ux * h * 0.6)], w=w)
    return f


# ================================================================== PART 1  odd one out
def p1_chiral(rng):
    g = glyph(rng)
    ks = rng.sample(range(4), 3)
    opts = [rot(flipH(g), 90 * rng.randrange(4))] + [rot(g, 90 * k) for k in ks]
    return dict(opts=opts,
                note='बाक़ी तीन आकृतियाँ एक ही आकृति को घुमाने से बनती हैं। ({A}) घुमाने से नहीं बनती — वह उस आकृति का उलटा (दर्पण) रूप है।',
                note_en='The other three figures are rotations of the same figure. ({A}) cannot be obtained by rotation — it is the mirror (flipped) image.')


def p1_count(rng):
    ns = [3, 4, 5, 6]; rng.shuffle(ns)
    mark = rng.choice(['dot', 'ring', 'tick'])
    def one(n, m):
        f = Fig().poly(ngon(n, 50, 50 + (5 if n == 3 else 0), 40, rng.choice([0, 180.0 / n])))
        a0 = rng.randrange(360); cy = 50 + (5 if n == 3 else 0)
        for i in range(m):
            R = 10 if n == 3 else 14; a = a0 + 360.0 * i / m
            x, y = 50 + R * sin(a), cy - R * cos(a)
            if mark == 'dot': f.dot(x, y, 3.2)
            elif mark == 'ring': f.circle(x, y, 3.2, None, 1.6)
            else: f.line(50 + (R - 5) * sin(a), cy - (R - 5) * cos(a), 50 + (R + 4) * sin(a), cy - (R + 4) * cos(a))
        return f
    odd = one(ns[0], ns[0] + rng.choice([1, -1] if ns[0] > 3 else [1]))
    thing_hi = {'dot': 'बिंदुओं', 'ring': 'छोटे गोलों', 'tick': 'छोटी रेखाओं'}[mark]
    thing_en = {'dot': 'dots', 'ring': 'small circles', 'tick': 'short ticks'}[mark]
    return dict(opts=[odd] + [one(n, n) for n in ns[1:]],
                note='बाक़ी तीनों में अंदर के %s की संख्या बाहरी आकृति की भुजाओं के बराबर है। ({A}) में यह संख्या बराबर नहीं है।' % thing_hi,
                note_en='In the other three figures, the number of inner %s equals the number of sides of the outer shape. In ({A}), these counts do not match.' % thing_en)


def p1_inner(rng):
    pool = ['circle', 'triangle', 'square', 'pentagon', 'hexagon']
    outs = rng.sample(pool, 4)
    fillin = rng.choice([None, 'k'])
    def one(o, i):
        f = add_shape(Fig(), o, 50, 50, 38)
        return add_shape(f, i, 50, 52 if o == 'triangle' else 50, 13 if o == 'triangle' else 15, fillin)
    other = rng.choice([s for s in pool if s != outs[0]])
    return dict(opts=[one(outs[0], other)] + [one(o, o) for o in outs[1:]],
                note='बाक़ी तीनों में अंदर वाली आकृति वही है जो बाहर वाली है। ({A}) में अंदर और बाहर की आकृति अलग है।',
                note_en='In the other three figures, the inner shape is the same as the outer shape. In ({A}), the inner and outer shapes are different.')


def p1_turn(rng):
    def one(cw):
        a0 = rng.randrange(0, 360, 30); r = 30
        f = Fig()
        a1, a2 = (a0, a0 + 270) if cw else (a0, a0 - 270)
        f.arc(50, 50, r, a1, a2)
        ex, ey = 50 + r * sin(a2), 50 - r * cos(a2)
        t = a2 + (90 if cw else -90)                         # direction of travel at the tip
        for s in (150, -150):
            f.line(ex, ey, ex + 10 * sin(t + s), ey - 10 * cos(t + s))
        return f.dot(50, 50, 4)
    cw = rng.random() < 0.5
    return dict(opts=[one(not cw), one(cw), one(cw), one(cw)],
                note='बाक़ी तीनों में तीर %s घूम रहा है। ({A}) में तीर उलटी दिशा में घूम रहा है।' % ('घड़ी की दिशा में' if cw else 'घड़ी की उलटी दिशा में'),
                note_en='In the other three figures, the arrow turns %s. In ({A}), it turns in the opposite direction.' % ('clockwise' if cw else 'anticlockwise'))


def p1_half(rng):
    kinds = [('circle', 4), ('circle', 6), ('circle', 8), ('square', 4), ('square', 8), ('hexagon', 6)]
    pick = rng.sample(kinds, 4)
    def one(kind, k, h):
        f = Fig(); c = (50, 50)
        if kind == 'circle': rim = [(50 + 38 * sin(a), 50 - 38 * cos(a)) for a in range(0, 360, 5)]; step = len(rim) // k
        elif kind == 'hexagon': rim = ngon(6, 50, 50, 40, 0); step = 1
        elif k == 4: rim = [(50, 12), (88, 12), (88, 50), (88, 88), (50, 88), (12, 88), (12, 50), (12, 12)]; step = 2
        else: rim = [(50, 12), (88, 12), (88, 50), (88, 88), (50, 88), (12, 88), (12, 50), (12, 12)]; step = 1
        shaded = set(rng.sample(range(k), h))
        for i in range(k):
            seg = [rim[(i * step + j) % len(rim)] for j in range(step + 1)]
            if i in shaded: f.poly([c] + seg, 'k', 1)
        for i in range(k):
            p = rim[(i * step) % len(rim)]; f.line(50, 50, p[0], p[1], w=1.4)
        if kind == 'circle': f.circle(50, 50, 38)
        else: f.poly(rim)
        return f
    k0 = pick[0][1]
    odd = one(pick[0][0], k0, k0 // 2 + rng.choice([1, -1]))
    return dict(opts=[odd] + [one(kd, k, k // 2) for kd, k in pick[1:]],
                note='बाक़ी तीनों में आकृति का ठीक आधा भाग काला (छायांकित) है। ({A}) में आधा भाग काला नहीं है।',
                note_en='In the other three figures, exactly half of the shape is shaded. In ({A}), the shaded portion is not half.')


# ================================================================== PART 2  figure matching
def p2_match(rng):
    frame = rng.choice(['circle', 'square', 'diamond', 'hexagon'])
    div = rng.choice(['plus', 'cross']) if frame in ('circle', 'square') else rng.choice(['plus', 'none'])
    if frame == 'diamond': div = 'plus'
    if div == 'cross' or frame == 'diamond': pos = [(50, 25), (75, 50), (50, 75), (25, 50)]
    else: pos = [(32, 32), (68, 32), (68, 68), (32, 68)]
    if frame == 'diamond': pos = [(50, 27), (73, 50), (50, 73), (27, 50)]
    if frame == 'hexagon': pos = [(36, 34), (64, 34), (64, 66), (36, 66)]
    names = rng.sample(SYMS, 4); ks = [rng.randrange(4) for _ in range(4)]
    def build(names, ks):
        f = Fig()
        if frame == 'circle': f.circle(50, 50, 43)
        elif frame == 'square': f.poly([(8, 8), (92, 8), (92, 92), (8, 92)])
        elif frame == 'diamond': f.poly(ngon(4, 50, 50, 46))
        else: f.poly(ngon(6, 50, 50, 45, 30))
        if div == 'plus' and frame != 'diamond':
            e = {'circle': 43, 'square': 42, 'hexagon': 39}[frame]
            f.line(50, 50 - e, 50, 50 + e, w=1.4)
            e2 = 45 if frame == 'hexagon' else e
            f.line(50 - e2, 50, 50 + e2, 50, w=1.4)
        elif div == 'cross':
            e = 30.4 if frame == 'circle' else 42
            f.line(50 - e, 50 - e, 50 + e, 50 + e, w=1.4).line(50 - e, 50 + e, 50 + e, 50 - e, w=1.4)
        elif frame == 'diamond':
            f.line(27, 27, 73, 73, w=1.4).line(27, 73, 73, 27, w=1.4)
        for nm, k, (x, y) in zip(names, ks, pos): f.add(place(nm, x, y, k))
        return f
    base = build(names, ks)
    cands = []
    for i in range(4):
        for dk in (1, 2, 3):
            k2 = list(ks); k2[i] = (ks[i] + dk) % 4; cands.append(build(names, k2))
    for i in range(4):
        for j in range(i + 1, 4):
            n2 = list(names); n2[i], n2[j] = n2[j], n2[i]; k2 = list(ks); k2[i], k2[j] = k2[j], k2[i]
            cands.append(build(n2, k2))
    rng.shuffle(cands)
    opts = [base]
    for c in cands:
        if distinct(opts + [c], 60): opts.append(c)
        if len(opts) == 4: break
    need(len(opts) == 4)
    return dict(q=[(base, False, 100)], opts=opts,
                note='({A}) ही प्रश्न आकृति जैसी है। बाक़ी तीनों में कोई एक चिह्न घूमा हुआ है या दो चिह्नों की जगह बदली हुई है — हर चिह्न की दिशा ध्यान से मिलाइए।',
                note_en='({A}) is an exact match for the question figure. In the other three, one symbol is rotated or two symbols have swapped places — check the orientation of every symbol carefully.')


# ================================================================== PART 3  pattern completion
def p3_pattern(rng):
    Q = [0, 12.5, 25, 37.5, 50]
    for _ in range(80):
        m = Fig(); segs = []
        C3 = [0, 25, 50]
        for _ in range(3):
            a = (rng.choice(C3), rng.choice(C3)); b = (rng.choice(C3), rng.choice(Q))
            if math.hypot(a[0] - b[0], a[1] - b[1]) < 24: continue
            if any({a, b} == {c, d} for c, d in segs): continue
            if (a[0] == b[0] and a[0] in (0, 50)) or (a[1] == b[1] and a[1] in (0, 50)): continue
            segs.append((a, b))
        if len(segs) < 2: continue
        for a, b in segs: m.line(a[0], a[1], b[0], b[1])
        extra = rng.choice(['tri', 'dot', 'ring', 'sq'])
        ex, ey = rng.choice([12.5, 25, 37.5]), rng.choice([12.5, 25, 37.5])
        if extra == 'tri': m.poly([(ex, ey), (ex + 12.5, ey), (ex, ey + 12.5)], 'k')
        elif extra == 'dot': m.dot(ex, ey, 4.5)
        elif extra == 'ring': m.circle(ex, ey, 5.5)
        else: m.poly([(ex - 5, ey - 5), (ex + 5, ey - 5), (ex + 5, ey + 5), (ex - 5, ey + 5)], 'k')
        big = lambda f: scale(move(f, 25, 25), 1.68)          # a quadrant tile blown up to a full cell
        if not distinct([big(x) for x in dihedral(m, (25, 25))], 150): continue
        mirror = rng.random() < 0.5
        c = (25, 25)
        if mirror: quad = [m, flipH(m, 25), rot(m, 180, c), flipV(m, 25)]          # TL, TR, BR, BL
        else: quad = [m, rot(m, 90, c), rot(m, 180, c), rot(m, 270, c)]
        off = [(0, 0), (50, 0), (50, 50), (0, 50)]
        miss = rng.randrange(4)
        whole = Fig()
        for i in range(4):
            if i != miss: whole.add(move(quad[i], *off[i]))
        ox, oy = off[miss]
        whole.poly([(0, 0), (100, 0), (100, 100), (0, 100)])
        whole.poly([(ox, oy), (ox + 50, oy), (ox + 50, oy + 50), (ox, oy + 50)], 'w', 1.2)
        whole = move(scale(whole, 0.84), 0, 0)
        right = quad[miss]
        # a near miss: the right tile with one line dropped
        nm = Fig(right.items[1:])
        tile = lambda f: big(f).poly([(8, 8), (92, 8), (92, 92), (8, 92)], None, 1.2)
        opts = [tile(right), tile(flipH(right, 25)), tile(rot(right, 90, c)), tile(nm if rng.random() < 0.6 else flipV(right, 25))]
        if not distinct(opts, 110): continue
        return dict(q=[(whole, False, 100)], opts=opts,
                    note=('पूरा पैटर्न %s है। खाली हिस्से में वही टुकड़ा आएगा जो इस नियम से बनता है — वह ({A}) है। बाक़ी टुकड़ों में दिशा उलटी है या एक रेखा कम है।'
                          % ('ऊपर-नीचे और दाएँ-बाएँ दोनों तरफ़ से दर्पण जैसा (सममित)' if mirror else 'बीच के बिंदु के चारों ओर घूम कर बना')),
                    note_en=('The full pattern %s. Only ({A}) follows this rule to fill the missing quarter; the others are flipped or missing a line.'
                             % ('is symmetric both horizontally and vertically' if mirror else 'is formed by rotating around the centre')))
    raise Retry()


# ================================================================== PART 4  series
def p4_rotate(rng):
    v = rng.randrange(3)
    g = Fig()
    if v == 0: g.line(50, 50, 50, 14).poly([(50, 14), (65, 21), (50, 29)], 'k')
    elif v == 1:
        g.line(50, 50, 50, 14).pl([(44, 22), (50, 14), (56, 22)]).line(50, 50, 72, 50).dot(74, 50, 4.5)
    else: g.line(50, 86, 50, 14).circle(50, 20, 6, 'k').line(50, 62, 68, 62)
    step = rng.choice([45, 90, -45, -90, 135, -135])
    a0 = rng.randrange(0, 360, 45)
    fr = lambda a: Fig().circle(50, 50, 44, None, 1.2).add(rot(g, a)).dot(50, 50, 2.6)
    q = [fr(a0 + step * i) for i in range(3)]
    ans = a0 + step * 3
    alts = [ans + 45, ans - 45, ans + 90, ans - 90, ans + 180, a0 + step * 2]
    rng.shuffle(alts)
    opts = [fr(ans)]
    for a in alts:
        c = fr(a)
        if distinct(opts + [c], 90): opts.append(c)
        if len(opts) == 4: break
    need(len(opts) == 4)
    way_hi = 'घड़ी की दिशा में' if step > 0 else 'घड़ी की उलटी दिशा में'
    way_en = 'clockwise' if step > 0 else 'anticlockwise'
    return dict(q=[(x, True, 100) for x in q] + [(None, True, 100)], opts=opts,
                note='हर अगले चित्र में आकृति %s %d° घूमती है। तीसरे चित्र को उतना ही और घुमाने पर ({A}) मिलता है।' % (way_hi, abs(step)),
                note_en='At each step, the figure rotates %d° %s. Rotating the third figure by the same angle gives ({A}).' % (abs(step), way_en))


def p4_move(rng):
    ring = [(18, 18), (50, 18), (82, 18), (82, 50), (82, 82), (50, 82), (18, 82), (18, 50)]      # clockwise
    inner = [(36, 36), (50, 36), (64, 36), (64, 50), (64, 64), (50, 64), (36, 64), (36, 50)]
    s1 = rng.choice([1, 2, 3]); s2 = -rng.choice([1, 2]); a = rng.randrange(8); b = rng.randrange(8)
    kind = rng.choice(['tri', 'ring', 'sq'])
    def fr(i, j):
        f = Fig().poly([(18, 18), (82, 18), (82, 82), (18, 82)], None, 1.4)
        f.dot(ring[i % 8][0], ring[i % 8][1], 6)
        x, y = inner[j % 8]
        if kind == 'tri': f.poly([(x, y - 6), (x + 6, y + 5), (x - 6, y + 5)])
        elif kind == 'ring': f.circle(x, y, 5.5)
        else: f.poly([(x - 5, y - 5), (x + 5, y - 5), (x + 5, y + 5), (x - 5, y + 5)])
        return f
    q = [fr(a + s1 * i, b + s2 * i) for i in range(3)]
    opts = [fr(a + s1 * 3, b + s2 * 3), fr(a + s1 * 3, b + s2 * 2), fr(a + s1 * 2, b + s2 * 3), fr(a + s1 * 4, b + s2 * 4)]
    need(distinct(opts, 60))
    nm_hi = {'tri': 'त्रिभुज', 'ring': 'छोटा गोला', 'sq': 'छोटा वर्ग'}[kind]
    nm_en = {'tri': 'triangle', 'ring': 'small circle', 'sq': 'small square'}[kind]
    return dict(q=[(x, True, 100) for x in q] + [(None, True, 100)], opts=opts,
                note='काला बिंदु हर बार घड़ी की दिशा में %d स्थान आगे बढ़ता है और अंदर का %s घड़ी की उलटी दिशा में %d स्थान। दोनों को एक-एक कदम और बढ़ाने पर ({A}) मिलता है।' % (s1, nm_hi, -s2),
                note_en='The black dot moves %d step(s) clockwise each turn while the inner %s moves %d step(s) anticlockwise. Advancing both one more turn gives ({A}).' % (s1, nm_en, -s2))


def p4_grow(rng):
    v = rng.choice(['spoke', 'side', 'spoke'])
    if v == 'spoke':
        s = rng.choice([1, 2, 3]); a0 = rng.randrange(0, 360, 45); d = rng.choice([1, -1]); tip = rng.choice(['dot', 'ring', 'bar'])
        def fr(angles):
            f = Fig().dot(50, 50, 4)
            for a in angles:
                x, y = 50 + 34 * sin(a), 50 - 34 * cos(a); f.line(50, 50, x, y)
                if tip == 'dot': f.dot(x, y, 4.5)
                elif tip == 'ring': f.circle(50 + 39 * sin(a), 50 - 39 * cos(a), 5)
                else: f.line(x - 7 * cos(a), y - 7 * sin(a), x + 7 * cos(a), y + 7 * sin(a))
            return f
        A = lambda n: [a0 + d * 45 * i for i in range(n)]
        q = [fr(A(s + i)) for i in range(3)]
        opts = [fr(A(s + 3)), fr(A(s + 4)), fr(A(s + 2) + [a0 + d * 45 * (s + 3)]), fr(A(s + 2) + [a0 - d * 45])]
        note = 'हर अगले चित्र में उसी दिशा में एक नई रेखा जुड़ती है (%d, %d, %d …)। चौथे चित्र में %d रेखाएँ होंगी और नई रेखा पिछली के ठीक बाद आएगी — ({A})।' % (s, s + 1, s + 2, s + 3)
        note_en = 'Each step adds one new line in the same direction (%d, %d, %d …). The fourth figure has %d lines, with the new one right after the last — ({A}).' % (s, s + 1, s + 2, s + 3)
    else:
        n = rng.choice([6, 8]); s = rng.choice([1, 2]); a0 = rng.randrange(n); d = rng.choice([1, -1])
        V = ngon(n, 50, 50, 38, 0 if n == 6 else 22.5)
        def fr(edges):
            f = Fig()
            for e in edges:
                p, q2 = V[e % n], V[(e + 1) % n]; f.line(p[0], p[1], q2[0], q2[1])
            for p in V: f.dot(p[0], p[1], 2.4)
            return f
        E = lambda k: [a0 + d * i for i in range(k)]
        q = [fr(E(s + i)) for i in range(3)]
        opts = [fr(E(s + 3)), fr(E(s + 4)), fr(E(s + 2) + [a0 + d * (s + 3)]), fr(E(s + 2) + [a0 - d])]
        note = 'हर अगले चित्र में एक नई भुजा उसी दिशा में जुड़ती जाती है। चौथे चित्र में %d भुजाएँ लगातार जुड़ी होंगी — ({A})।' % (s + 3)
        note_en = 'Each step adds one adjacent side in the same direction. The fourth figure has %d consecutive sides — ({A}).' % (s + 3)
    need(distinct(opts, 60))
    return dict(q=[(x, True, 100) for x in q] + [(None, True, 100)], opts=opts, note=note, note_en=note_en)


def p4_turnfill(rng):
    v = rng.randrange(3); d = rng.choice([1, -1]); k0 = rng.randrange(4); f0 = rng.randrange(2)
    def fr(k, fl):
        f = Fig(); fill = 'k' if fl % 2 else None
        if v == 0: f.poly([(50, 14), (80, 78), (20, 78)], fill)
        elif v == 1: f.poly([(50, 12), (82, 44), (64, 44), (64, 86), (36, 86), (36, 44), (18, 44)], fill)
        else: f.poly([(50 + 36 * sin(a), 56 - 36 * cos(a)) for a in range(-90, 91, 10)], fill)
        return rot(f, 90 * k)
    q = [fr(k0 + d * i, f0 + i) for i in range(3)]
    opts = [fr(k0 + d * 3, f0 + 3), fr(k0 + d * 3, f0 + 2), fr(k0 + d * 2, f0 + 3), fr(k0 + d * 1, f0 + 3)]
    need(distinct(opts, 90))
    return dict(q=[(x, True, 100) for x in q] + [(None, True, 100)], opts=opts,
                note='आकृति हर बार %s 90° घूमती है और उसका रंग बारी-बारी से बदलता है (काला, सफ़ेद, काला …)। इसलिए चौथा चित्र ({A}) होगा।' % ('घड़ी की दिशा में' if d > 0 else 'घड़ी की उलटी दिशा में'),
                note_en='Each step rotates the shape 90° %s and alternates its fill (black, white, black …). Thus the fourth figure is ({A}).' % ('clockwise' if d > 0 else 'anticlockwise'))


# ================================================================== PART 5  analogy
def analogy(a, b, c, opts, note, frame=True, note_en=''):
    frame = True
    q = [(a, frame, 100), (b, frame, 100), (c, frame, 100), (Fig().text(50, 66, '?', 46), True, 100)]
    return dict(q=q, opts=opts, note=note, note_en=note_en, gaps=[8, 34, 8])


def p5_turn(rng):
    ops = {'r90': (lambda f: rot(f, 90), 'घड़ी की दिशा में 90° घुमाया गया है', 'rotated 90° clockwise'),
           'r270': (lambda f: rot(f, 270), 'घड़ी की उलटी दिशा में 90° घुमाया गया है', 'rotated 90° anticlockwise'),
           'r180': (lambda f: rot(f, 180), 'आधा चक्कर (180°) घुमाया गया है', 'rotated 180°'),
           'fh': (flipH, 'दाएँ-बाएँ पलट दिया गया है (खड़ी रेखा में दर्पण)', 'flipped left-to-right'),
           'fv': (flipV, 'ऊपर-नीचे पलट दिया गया है', 'flipped top-to-bottom')}
    key = rng.choice(list(ops)); T, words_hi, words_en = ops[key]
    g1 = glyph(rng); g2 = glyph(rng)
    need(diff(g1, g2) > 200)
    others = [k for k in ops if k != key]; rng.shuffle(others)
    opts = [T(g2)] + [ops[k][0](g2) for k in others[:2]] + [g2]
    need(distinct(opts, 110))
    return analogy(g1, T(g1), g2, opts,
                   'पहले जोड़े में दूसरी आकृति पहली को %s। तीसरी आकृति के साथ वही करने पर ({A}) मिलता है।' % words_hi,
                   note_en='In the first pair, the second figure is the first figure %s. Applying the same rule to the third figure gives ({A}).' % words_en)


def p5_invert(rng):
    def build(kind, pat):
        f = Fig(); c = (50, 50)
        if kind == 'circle': rim = [(50 + 38 * sin(a), 50 - 38 * cos(a)) for a in range(0, 360, 5)]; step = 18
        elif kind == 'square': rim = [(50, 12), (88, 12), (88, 50), (88, 88), (50, 88), (12, 88), (12, 50), (12, 12)]; step = 2
        else: rim = [(12, 12), (50, 12), (88, 12), (88, 50), (88, 88), (50, 88), (12, 88), (12, 50)]; step = 2
        for i in range(4):
            seg = [rim[(i * step + j) % len(rim)] for j in range(step + 1)]
            if pat[i]: f.poly([c] + seg, 'k', 1)
        for i in range(4):
            p = rim[(i * step) % len(rim)]; f.line(50, 50, p[0], p[1], w=1.4)
        if kind == 'circle': f.circle(50, 50, 38)
        else: f.poly(rim)
        return f
    k1, k2 = rng.sample(['circle', 'square', 'xsquare'], 2)
    one = rng.randrange(4); p1 = [i == one for i in range(4)]
    if rng.random() < 0.5: p1 = [not x for x in p1]
    j = rng.randrange(4)
    p3 = rng.choice([[i == j for i in range(4)], [i != j for i in range(4)], [i in (j, (j + 1) % 4) for i in range(4)]])
    inv = [not x for x in p3]
    alts = [p3, inv[1:] + inv[:1], inv[2:] + inv[:2], inv[3:] + inv[:3], [True] * 4, [False] * 4]
    opts = [build(k2, inv)]
    for a in alts:
        c = build(k2, a)
        if distinct(opts + [c], 150): opts.append(c)
        if len(opts) == 4: break
    need(len(opts) == 4)
    return analogy(build(k1, p1), build(k1, [not x for x in p1]), build(k2, p3), opts,
                   'पहले जोड़े में काले हिस्से सफ़ेद और सफ़ेद हिस्से काले हो गए हैं। तीसरी आकृति में यही बदलाव करने पर ({A}) मिलता है।', frame=False,
                   note_en='In the first pair, black and white regions swap colours. Applying the same rule to the third figure gives ({A}).')


def p5_swap(rng):
    pool = ['circle', 'triangle', 'square', 'pentagon', 'hexagon']
    a, b = rng.sample(pool, 2)
    for _ in range(50):
        c, d = rng.sample(pool, 2)
        if {c, d} != {a, b}: break
    fill = rng.choice(['k', None])
    def one(o, i):
        f = add_shape(Fig(), o, 50, 50, 40)
        return add_shape(f, i, 50, 53 if o == 'triangle' else 50, 13 if o == 'triangle' else 16, fill)
    e = rng.choice([s for s in pool if s not in (c, d)])
    opts = [one(d, c), one(c, d), one(d, d), one(rng.choice([d, c]), e)]
    need(distinct(opts, 110))
    return analogy(one(a, b), one(b, a), one(c, d), opts,
                   'पहले जोड़े में अंदर वाली आकृति बाहर आ गई है और बाहर वाली अंदर चली गई है। तीसरी आकृति में यही अदला-बदली करने पर ({A}) मिलता है।', frame=False,
                   note_en='In the first pair, the inner and outer shapes swap places. Applying the same swap to the third figure gives ({A}).')


def p5_sides(rng):
    def one(n, k):
        f = Fig().poly(ngon(n, 50, 50 + (5 if n == 3 else 0), 40, 0))
        gap = 10 if n == 3 else 11; x0 = 50 - gap / 2.0 * (k - 1)
        for i in range(k): f.dot(x0 + gap * i, 66 if n == 3 else 50, 3.4)
        return f
    n1_, n3 = rng.sample([3, 4, 5], 2)
    k1 = rng.choice([2, 3, 4]); k3 = rng.choice([x for x in (2, 3, 4) if x != k1])
    opts = [one(n3 + 1, k3 - 1), one(n3 + 1, k3), one(n3, k3 - 1), one(n3 + 1, k3 + 1)]
    need(distinct(opts, 60))
    return analogy(one(n1_, k1), one(n1_ + 1, k1 - 1), one(n3, k3), opts,
                   'पहले जोड़े में भुजाओं की संख्या 1 बढ़ गई है और बिंदुओं की संख्या 1 घट गई है। तीसरी आकृति में यही करने पर ({A}) मिलता है।', frame=False,
                   note_en='In the first pair, the number of sides increases by 1 and the number of dots decreases by 1. Doing the same to the third figure gives ({A}).')


# ================================================================== PART 6  completing a geometrical figure
def inside(p, poly):
    x, y = p; c = False; n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1): c = not c
    return c


def p6_complete(rng):
    kind = rng.choice(['square', 'circle', 'triangle', 'square', 'circle'])
    for _ in range(100):
        xs = rng.choice([38, 44, 50, 56, 62]); xe = rng.choice([38, 44, 50, 56, 62])
        if kind == 'square':
            B = [(12, 12), (88, 12), (88, 88), (12, 88)]                               # clockwise
            P, Q = (xs, 12), (xe, 88)
            pieceL = lambda path: [P] + path + [Q, (12, 88), (12, 12)]
            pieceR = lambda path: [P, (88, 12), (88, 88), Q] + path[::-1]
        elif kind == 'circle':
            r = 40
            ang = lambda x, top: math.degrees(math.asin((x - 50) / r)) if top else 180 - math.degrees(math.asin((x - 50) / r))
            a1, a2 = ang(xs, True), ang(xe, False)
            pt = lambda a: (50 + r * sin(a), 50 - r * cos(a))
            P, Q = pt(a1), pt(a2)
            arcR = [pt(a1 + (a2 - a1) * i / 30.0) for i in range(31)]                 # P -> Q, by the right side
            arcL = [pt(a2 + (a1 + 360 - a2) * i / 40.0) for i in range(41)]           # Q -> P, by the left side
            B = arcR + arcL[1:-1]
            pieceL = lambda path: [P] + path + arcL
            pieceR = lambda path: arcR + path[::-1]
        else:
            B = [(50, 10), (92, 88), (8, 88)]
            t = rng.choice([0.3, 0.4, 0.5, 0.6]); xe = rng.choice([32, 40, 50, 60, 68])
            lr = rng.random() < 0.5
            if lr: P = (50 - 42 * t, 10 + 78 * t); pieceL = lambda path: [P] + path + [Q, (8, 88)]; pieceR = lambda path: [P, (50, 10), (92, 88), Q] + path[::-1]
            else: P = (50 + 42 * t, 10 + 78 * t); pieceL = lambda path: [P] + path + [Q, (8, 88), (50, 10)]; pieceR = lambda path: [P, (92, 88), Q] + path[::-1]
            Q = (xe, 88)
        L = math.hypot(Q[0] - P[0], Q[1] - P[1]); ux, uy = (Q[0] - P[0]) / L, (Q[1] - P[1]) / L; nx, ny = -uy, ux
        style = rng.choice(['zig', 'step', 'tooth'])
        amp = rng.choice([8, 10, 12])
        def path(offs):
            return [(P[0] + ux * L * f + nx * o, P[1] + uy * L * f + ny * o) for f, o in offs]
        if style == 'zig':
            base = [(0.25, amp), (0.5, -amp), (0.75, amp)]
            alts = [[(0.25, -amp), (0.5, amp), (0.75, -amp)], [(0.2, amp), (0.4, -amp), (0.6, amp), (0.8, -amp)], [(0.33, amp), (0.67, -amp)], [(0.25, amp), (0.5, amp * 0.1), (0.75, amp)]]
        elif style == 'step':
            base = [(0.3, 0), (0.3, amp), (0.65, amp), (0.65, 0)]
            alts = [[(0.3, 0), (0.3, -amp), (0.65, -amp), (0.65, 0)], [(0.2, 0), (0.2, amp), (0.45, amp), (0.45, 0)], [(0.3, 0), (0.3, amp), (0.8, amp), (0.8, 0)], [(0.3, 0), (0.42, amp), (0.53, amp), (0.65, 0)]]
        else:
            base = [(0.35, 0), (0.5, amp * 1.3), (0.65, 0)]
            alts = [[(0.35, 0), (0.5, -amp * 1.3), (0.65, 0)], [(0.2, 0), (0.35, amp * 1.3), (0.5, 0)], [(0.35, 0), (0.35, amp * 1.3), (0.65, amp * 1.3), (0.65, 0)], [(0.3, 0), (0.4, amp), (0.5, 0), (0.6, amp), (0.7, 0)]]
        if rng.random() < 0.5: base = [(f, -o) for f, o in base]; alts = [[(f, -o) for f, o in a] for a in alts]
        allp = [path(base)] + [path(a) for a in alts]
        shrink = [(50 + (x - 50) * 0.9, 50 + (y - 50) * 0.9) for x, y in B]
        if not all(inside(p, shrink) for pp in allp for p in pp): continue
        rng.shuffle(alts)
        def piece(pts):
            xs_ = [p[0] for p in pts]; ys_ = [p[1] for p in pts]
            return move(Fig().poly(pts), 50 - (min(xs_) + max(xs_)) / 2.0, 50 - (min(ys_) + max(ys_)) / 2.0)
        ask_left = rng.random() < 0.5
        give, other = (pieceL, pieceR) if ask_left else (pieceR, pieceL)
        opts = [piece(other(path(base)))]
        for a in alts:
            c = piece(other(path(a)))
            if distinct(opts + [c], 80): opts.append(c)
            if len(opts) == 4: break
        if len(opts) < 4: continue
        nm_hi = {'square': 'वर्ग', 'circle': 'वृत्त (गोला)', 'triangle': 'त्रिभुज'}[kind]
        nm_en = {'square': 'square', 'circle': 'circle', 'triangle': 'triangle'}[kind]
        return dict(q=[(piece(give(path(base))), False, 100)], opts=opts,
                    note='प्रश्न आकृति के कटे हुए किनारे में जो उभार और गड्ढे हैं, ठीक उनके उलटे उभार-गड्ढे ({A}) में हैं। दोनों को जोड़ने पर पूरा %s बनता है।' % nm_hi,
                    note_en='The bumps and notches along the cut edge of ({A}) are the exact opposite of the question figure. Fitting them together completes the %s.' % nm_en)
    raise Retry()


# ================================================================== PART 7  mirror image
def p7_mirror(rng):
    g = glyph(rng, marker=rng.choice(['dot', 'tri', 'bar', 'ring']))
    extra = Fig(); name = rng.choice(['flag', 'L', 'tri', 'half', 'arrow'])
    spots = [(x, y) for x in (22, 50, 78) for y in (22, 50, 78)]
    rng.shuffle(spots)
    gr = ras(g); fgr = ras(flipH(g))
    for x, y in spots:
        ks = list(range(4)); rng.shuffle(ks)
        for k in ks:
            e = place(name, x, y, k)
            if np.count_nonzero(ras(e) & gr) == 0 and np.count_nonzero(ras(e) & fgr) == 0 and diff(e, Fig()) > 0:
                # keep the small symbol clear of both the line figure and its horizontal mirror
                er = ras(e)
                ys_, xs_ = np.nonzero(er)
                y0, y1 = max(0, ys_.min() - 10), ys_.max() + 11
                x0, x1 = max(0, xs_.min() - 10), xs_.max() + 11
                if not gr[y0:y1, x0:x1].any() and not fgr[y0:y1, x0:x1].any():
                    extra = e; break
        if extra.items: break
    need(extra.items)
    full = Fig().add(g, extra)
    need(distinct(dihedral(full), 110))
    right = flipH(full)
    partial = Fig().add(flipH(g), extra)                      # line figure reversed, small symbol left where it was
    cands = [flipV(full), rot(full, 180), partial, full]
    rng.shuffle(cands)
    opts = [right]
    for c in cands:
        if distinct(opts + [c], 90): opts.append(c)
        if len(opts) == 4: break
    need(len(opts) == 4)
    qf = Fig().add(full).line(110, 13, 110, 87, w=1.6).text(110, 10, 'X', 11).text(110, 98.5, 'Y', 11)
    return dict(q=[(qf, False, 122)], opts=opts,
                note='दर्पण खड़ी रेखा XY पर है, इसलिए प्रतिबिंब में दायाँ-बायाँ आपस में बदल जाता है, ऊपर-नीचे वही रहता है। ऐसा चित्र ({A}) है।',
                note_en='The mirror is along the vertical line XY, so left and right reverse while top and bottom stay unchanged. ({A}) is the exact mirror image.')


# ================================================================== PART 8  paper folding and punching
def p8_punch(rng, kind):
    S0, S1 = 10, 90
    def hole(kind, x, y):
        if kind == 'c': return [(x + 4.6 * sin(a), y - 4.6 * cos(a)) for a in range(0, 360, 20)]
        if kind == 's': return [(x - 4.2, y - 4.2), (x + 4.2, y - 4.2), (x + 4.2, y + 4.2), (x - 4.2, y + 4.2)]
        return [(x, y - 5.5), (x + 5.5, y + 4.5), (x - 5.5, y + 4.5)]
    refl = {'V': lambda p: (100 - p[0], p[1]), 'H': lambda p: (p[0], 100 - p[1]), 'D': lambda p: (p[1], p[0]), 'E': lambda p: (100 - p[1], 100 - p[0])}
    shift = {'V': lambda p: ((p[0] + 40 - 10) % 80 + 10, p[1]), 'H': lambda p: (p[0], (p[1] + 40 - 10) % 80 + 10),
             'D': lambda p: (100 - p[0], 100 - p[1]), 'E': lambda p: (100 - p[0], 100 - p[1])}
    for _ in range(100):
        if kind == 1: folds = [rng.choice(['V', 'H'])]
        elif kind == 2: folds = rng.choice([['V', 'H'], ['H', 'V']])
        else: folds = [rng.choice(['D', 'E'])]
        keep = {}                                             # which side stays: sign
        reg = [S0, S0, S1, S1]                                # x0, y0, x1, y1 of the folded packet (axis folds)
        cells = []
        def outline(r): return [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]
        tri = None
        for fd in folds:
            f = Fig()
            if fd in 'VH':
                f.poly(outline(reg), None, 1.6)
                side = rng.choice([0, 1]); keep[fd] = side
                if fd == 'V':
                    f.dash(50, reg[1], 50, reg[3]); ym = (reg[1] + reg[3]) / 2.0
                    arrow(f, 74, ym, 30, ym) if side == 0 else arrow(f, 26, ym, 70, ym)
                    reg = [S0, reg[1], 50, reg[3]] if side == 0 else [50, reg[1], S1, reg[3]]
                else:
                    f.dash(reg[0], 50, reg[2], 50); xm = (reg[0] + reg[2]) / 2.0
                    arrow(f, xm, 74, xm, 30) if side == 0 else arrow(f, xm, 26, xm, 70)
                    reg = [reg[0], S0, reg[2], 50] if side == 0 else [reg[0], 50, reg[2], S1]
            else:
                f.poly(outline(reg), None, 1.6)
                side = rng.choice([0, 1]); keep[fd] = side
                if fd == 'D':                                  # fold line from top-left to bottom-right
                    f.dash(10, 10, 90, 90)
                    arrow(f, 68, 32, 36, 64) if side == 0 else arrow(f, 32, 68, 64, 36)
                    tri = [(10, 10), (90, 90), (10, 90)] if side == 0 else [(10, 10), (90, 10), (90, 90)]
                else:                                          # fold line from top-right to bottom-left
                    f.dash(90, 10, 10, 90)
                    arrow(f, 32, 32, 64, 64) if side == 0 else arrow(f, 68, 68, 36, 36)
                    tri = [(90, 10), (90, 90), (10, 90)] if side == 0 else [(10, 10), (90, 10), (10, 90)]
            cells.append(f)
        last = Fig()
        if tri:
            last.poly(tri, None, 1.6)
            shr = [(tri[0][0] + tri[1][0] + tri[2][0]) / 3.0, (tri[0][1] + tri[1][1] + tri[2][1]) / 3.0]
            small = [(shr[0] + (x - shr[0]) * 0.55, shr[1] + (y - shr[1]) * 0.55) for x, y in tri]
            spots = [(x, y) for x in range(20, 81, 10) for y in range(20, 81, 10) if inside((x, y), small)]
        else:
            last.poly(outline(reg), None, 1.6)
            spots = [(x, y) for x in range(int(reg[0]) + 10, int(reg[2]), 10) for y in range(int(reg[1]) + 10, int(reg[3]), 10)]
        nh = 2 if kind != 2 or rng.random() < 0.5 else 1
        if len(spots) < nh: continue
        hs = rng.sample(spots, nh)
        if nh == 2 and math.hypot(hs[0][0] - hs[1][0], hs[0][1] - hs[1][1]) < 14: continue
        kinds = [rng.choice(['c', 'c', 's', 't']) for _ in hs]
        holes = [hole(k, x, y) for k, (x, y) in zip(kinds, hs)]
        for h in holes: last.poly(h, 'k', 1)
        cells.append(last)
        def unfold(fns):
            out = list(holes)
            for fn in fns:
                out = out + [[fn(p) for p in h] for h in out] if fn else out
            return out
        rev = folds[::-1]
        right = unfold([refl[f] for f in rev])
        wrong = [unfold([shift[f] for f in rev])]
        if len(rev) == 2:
            wrong += [unfold([refl[rev[0]], None]), unfold([shift[rev[0]], refl[rev[1]]]), unfold([refl[rev[0]], shift[rev[1]]])]
        else:
            other = {'V': 'H', 'H': 'V', 'D': 'E', 'E': 'D'}[rev[0]]
            wrong += [unfold([None]), unfold([refl[other]]), [[refl[other](p) for p in h] for h in right]]
        def sheet(hl):
            f = Fig().poly(outline([S0, S0, S1, S1]), None, 1.6)
            for h in hl: f.poly(h, 'k', 1)
            return f
        def tidy(hl):
            """drop exact duplicates; None when two different holes would overlap"""
            out = []
            for h in hl:
                c = (sum(p[0] for p in h) / len(h), sum(p[1] for p in h) / len(h))
                dup = False
                for c2, h2 in out:
                    dd = math.hypot(c[0] - c2[0], c[1] - c2[1])
                    if dd < 0.5 and len(h) == len(h2) and abs(max(p[1] for p in h) - max(p[1] for p in h2)) < 0.5 and abs(max(p[0] for p in h) - max(p[0] for p in h2)) < 0.5: dup = True
                    elif dd < 12: return None
                if not dup: out.append((c, h))
            return [h for c, h in out]
        right = tidy(right)
        if right is None or len(right) != len(holes) * 2 ** len(folds): continue
        wrong = [t for t in (tidy(wv) for wv in wrong) if t]
        rng.shuffle(wrong)
        opts = [sheet(right)]
        for wv in wrong:
            c = sheet(wv)
            if distinct(opts + [c], 45): opts.append(c)
            if len(opts) == 4: break
        if len(opts) < 4: continue
        nf = len(folds)
        return dict(q=[(c, False, 100) for c in cells], opts=opts, gaps=[6] * 4,
                    note='काग़ज़ %d बार मोड़ा गया है, इसलिए हर छेद खोलने पर %d जगह दिखेगा। हर मोड़-रेखा के दोनों तरफ़ छेद बराबर दूरी पर, आमने-सामने (दर्पण की तरह) बनते हैं — ({A})।' % (nf, 2 ** nf),
                    note_en='The paper is folded %d time(s), so each punch unfolds to %d holes symmetric across every fold line — ({A}).' % (nf, 2 ** nf))
    raise Retry()


# ================================================================== PART 9  space visualisation (cut-out pieces)
def area(p):
    return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2.0


def perim(p):
    return sum(math.hypot(p[i][0] - p[(i + 1) % len(p)][0], p[i][1] - p[(i + 1) % len(p)][1]) for i in range(len(p)))


def clean(p):
    out = []
    for q in p:
        if not out or math.hypot(q[0] - out[-1][0], q[1] - out[-1][1]) > 0.01: out.append(q)
    if len(out) > 1 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) < 0.01: out.pop()
    return out


def cut(poly, i, t, j, u):
    n = len(poly)
    lerp = lambda a, b, s: (a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s)
    P = lerp(poly[i], poly[(i + 1) % n], t); Q = lerp(poly[j], poly[(j + 1) % n], u)
    A = clean([P] + poly[i + 1:j + 1] + [Q]); B = clean([Q] + poly[j + 1:] + poly[:i + 1] + [P])
    return A, B, (P, Q)


def partition(rng, outer, ncuts, nice):
    """cut a convex outline with straight lines; returns (pieces, cut lines)"""
    pieces = [list(outer)]; lines = []; tot = area(outer)
    for c in range(ncuts):
        for _ in range(60):
            k = max(range(len(pieces)), key=lambda q: area(pieces[q])) if rng.random() < 0.75 else rng.randrange(len(pieces))
            p = pieces[k]; n = len(p)
            ts = nice if n <= 8 else [0]
            i, j = sorted(rng.sample(range(n), 2)); t, u = rng.choice(ts), rng.choice(ts)
            if n > 8 and (i % 6 or j % 6): continue             # a circle is cut only at 'round' positions
            A, B, ln = cut(p, i, t, j, u)
            if len(A) < 3 or len(B) < 3 or min(area(A), area(B)) < tot * 0.12: continue
            if min(4 * math.pi * area(X) / perim(X) ** 2 for X in (A, B)) < 0.36: continue      # no thin slivers
            ends = [q for l in lines for q in l]
            if any(0.01 < math.hypot(e[0] - q[0], e[1] - q[1]) < 13 for e in ln for q in ends): continue
            # the cut must run through the inside of the piece, not along one of its sides
            mid = ((ln[0][0] + ln[1][0]) / 2.0, (ln[0][1] + ln[1][1]) / 2.0)
            if abs(area(A) + area(B) - area(p)) > 0.5 or not inside(mid, [(x + (sum(q[0] for q in p) / n - x) * 0.02, y + (sum(q[1] for q in p) / n - y) * 0.02) for x, y in p]): continue
            pieces[k:k + 1] = [A, B]; lines.append(ln); break
        else:
            raise Retry()
    return pieces, lines


def sig(pieces):
    return sorted((round(area(p), 1), round(perim(p), 1)) for p in pieces)


def confusable(A, B, tot):
    """could the pieces of A be mistaken for the pieces of B?  (same count and every piece has a look-alike)"""
    import itertools
    if len(A) != len(B): return False
    alike = lambda p, q: min(len(p), 9) == min(len(q), 9) and abs(area(p) - area(q)) < 0.08 * tot and abs(perim(p) - perim(q)) < 16
    return any(all(alike(p, q) for p, q in zip(A, perm)) for perm in itertools.permutations(B))


def p9_pieces(rng):
    name = rng.choice(['square', 'square', 'rect', 'triangle', 'hexagon', 'circle', 'rtri'])
    outer = {'square': [(12, 12), (88, 12), (88, 88), (12, 88)], 'rect': [(8, 24), (92, 24), (92, 76), (8, 76)],
             'triangle': [(50, 12), (92, 85), (8, 85)], 'rtri': [(14, 12), (88, 86), (14, 86)],
             'hexagon': ngon(6, 50, 50, 42, 30), 'circle': ngon(48, 50, 50, 40)}[name]
    ncuts = rng.choice([2, 2, 3])
    nice = [0, 0, 0.5, 0.5, 0.5, 1 / 3.0, 2 / 3.0]
    parts = []
    for _ in range(400):
        try: pc, ln = partition(rng, outer, ncuts, nice)
        except Retry: continue
        s = sig(pc)
        if any(confusable(pc, q[0], area(outer)) for q in parts): continue
        # no two pieces of the right answer should be the same, and lines must not be too close to each other
        parts.append((pc, ln, s))
        if len(parts) == 4: break
    need(len(parts) == 4)
    def whole(ln):
        f = Fig()
        if name == 'circle': f.circle(50, 50, 40)
        else: f.poly(outer)
        for a, b in ln: f.line(a[0], a[1], b[0], b[1], w=1.6)
        return f
    opts = [whole(p[1]) for p in parts]
    need(distinct(opts, 90))
    # question figure: the pieces of the first partition, turned and spread out
    pcs = []
    for p in parts[0][0]:
        k = rng.randrange(4); cs_, sn_ = cos(90 * k), sin(90 * k)
        q = [(x * cs_ - y * sn_, x * sn_ + y * cs_) for x, y in p]
        mx, my = min(x for x, y in q), min(y for x, y in q)
        pcs.append([(x - mx, y - my) for x, y in q])
    pcs.sort(key=lambda p: -max(y for x, y in p))
    for s in (0.62, 0.56, 0.5, 0.45, 0.4, 0.36):
        gap = 7; x = 0; y = 0; rowh = 0; placed = []; ok = True
        for p in pcs:
            w_, h_ = max(a for a, b in p) * s, max(b for a, b in p) * s
            if x > 0 and x + w_ > 96: x = 0; y += rowh + gap; rowh = 0
            if w_ > 96: ok = False; break
            placed.append((p, x, y)); x += w_ + gap; rowh = max(rowh, h_)
        if ok and y + rowh <= 96:
            tw = max(px + max(a for a, b in p) * s for p, px, py in placed); th = y + rowh
            f = Fig()
            for p, px, py in placed:
                f.poly([(a * s + px + (100 - tw) / 2.0, b * s + py + (100 - th) / 2.0) for a, b in p])
            return dict(q=[(f, False, 100)], opts=opts,
                        note='प्रश्न आकृति में %d टुकड़े हैं। हर उत्तर आकृति के टुकड़ों का आकार और नाप मिलाइए — सिर्फ़ ({A}) ठीक इन्हीं टुकड़ों से बनी है, बाक़ी में टुकड़े अलग आकार के हैं।' % len(pcs),
                        note_en='The question figure has %d cut-out pieces. Match the exact shape and size of each piece — only ({A}) can be formed from these exact pieces.' % len(pcs))
    raise Retry()


# ================================================================== PART 10  embedded figure
def all_edges(n=5):
    E = []
    for x in range(n):
        for y in range(n):
            if x + 1 < n: E.append(((x, y), (x + 1, y)))
            if y + 1 < n: E.append(((x, y), (x, y + 1)))
            if x + 1 < n and y + 1 < n: E.append(((x, y), (x + 1, y + 1))); E.append(((x + 1, y), (x, y + 1)))
    return [tuple(sorted(e)) for e in E]


EDGES = all_edges()
BORDER = [e for e in EDGES if (e[0][0] == e[1][0] and e[0][0] in (0, 4)) or (e[0][1] == e[1][1] and e[0][1] in (0, 4))]


def norm(edges):
    mx = min(min(a[0], b[0]) for a, b in edges); my = min(min(a[1], b[1]) for a, b in edges)
    return frozenset(tuple(sorted(((a[0] - mx, a[1] - my), (b[0] - mx, b[1] - my)))) for a, b in edges)


def variants(X):
    out = set()
    for fl in (0, 1):
        for k in range(4):
            E = []
            for a, b in X:
                pts = []
                for (x, y) in (a, b):
                    if fl: x = -x
                    for _ in range(k): x, y = -y, x
                    pts.append((x, y))
                E.append(tuple(pts))
            out.add(norm(E))
    return out


def contains(F, X):
    """is the pattern X (normalised) present in edge set F at some position?"""
    w = max(max(a[0], b[0]) for a, b in X); h = max(max(a[1], b[1]) for a, b in X)
    for dx in range(0, 5 - w):
        for dy in range(0, 5 - h):
            if all(tuple(sorted(((a[0] + dx, a[1] + dy), (b[0] + dx, b[1] + dy)))) in F for a, b in X): return True
    return False


def p10_hidden(rng):
    for _ in range(200):
        # the small figure: 5-7 connected unit lines inside a 2 x 2 block of cells
        local = [e for e in EDGES if max(e[0][0], e[1][0]) <= 2 and max(e[0][1], e[1][1]) <= 2]
        X = [rng.choice(local)]
        k = rng.choice([5, 6, 6, 7])
        while len(X) < k:
            ends = set(p for e in X for p in e)
            cand = [e for e in local if e not in X and (e[0] in ends or e[1] in ends)]
            X.append(rng.choice(cand))
        ends = {}
        for e in X:
            for p in e: ends[p] = ends.get(p, 0) + 1
        diag = sum(1 for a, b in X if a[0] != b[0] and a[1] != b[1])
        if diag < 1 or diag == len(X): continue
        if sum(1 for v in ends.values() if v == 1) > 2: continue          # compact shapes, at most two loose ends
        Xn = norm(X); V = variants(Xn)
        w = max(max(a[0], b[0]) for a, b in Xn); h = max(max(a[1], b[1]) for a, b in Xn)
        if w < 2 or h < 2: continue
        inner = [e for e in EDGES if e not in BORDER]
        def clutter(F, target, forbid):
            tries = 0
            while len(F) < target and tries < 400:
                tries += 1
                if rng.random() < 0.28:                                        # occasional straight line across the square
                    t = rng.choice(['h', 'v', 'd', 'e']); c = rng.randrange(1, 4)
                    if t == 'h': add = [((x, c), (x + 1, c)) for x in range(4)]
                    elif t == 'v': add = [((c, y), (c, y + 1)) for y in range(4)]
                    elif t == 'd': o = rng.randrange(-2, 3); add = [((x, x + o), (x + 1, x + 1 + o)) for x in range(4) if 0 <= x + o and x + 1 + o <= 4]
                    else: o = rng.randrange(2, 7); add = [((x + 1, o - x - 1), (x, o - x)) for x in range(4) if 0 <= o - x - 1 and o - x <= 4]
                    add = [tuple(sorted(e)) for e in add]
                else:
                    add = [rng.choice(inner)]
                G = F | set(add)
                if forbid and any(contains(G, v) for v in V): continue
                F = G
            return F
        target = rng.randrange(24, 29)
        dx, dy = rng.randrange(0, 5 - w), rng.randrange(0, 5 - h)
        good = set(BORDER) | set(tuple(sorted(((a[0] + dx, a[1] + dy), (b[0] + dx, b[1] + dy)))) for a, b in Xn)
        good = clutter(good, target, False)
        if len(good) < target - 2: continue
        figs = [good]; ok = True
        for d in range(3):
            # a near miss: the figure with one line left out, then filled up without ever completing it
            Xl = list(Xn); drop = rng.randrange(len(Xl)); near = Xl[:drop] + Xl[drop + 1:]
            ddx, ddy = rng.randrange(0, 5 - w), rng.randrange(0, 5 - h)
            F = set(BORDER) | set(tuple(sorted(((a[0] + ddx, a[1] + ddy), (b[0] + ddx, b[1] + ddy)))) for a, b in near)
            if any(contains(F, v) for v in V): ok = False; break
            F = clutter(F, target, True)
            if len(F) < target - 4 or any(contains(F, v) for v in V): ok = False; break
            figs.append(F)
        if not ok or not contains(good, Xn): continue
        def draw(F, off=(0, 0), wdt=W):
            f = Fig()
            for a, b in sorted(F): f.line(10 + 20 * a[0] + off[0], 10 + 20 * a[1] + off[1], 10 + 20 * b[0] + off[0], 10 + 20 * b[1] + off[1], w=wdt)
            return f
        opts = [draw(F, wdt=1.7) for F in figs]
        if not distinct(opts, 120): continue
        qf = draw(Xn, (40 - 10 * w, 40 - 10 * h))
        return dict(q=[(qf, False, 100)], opts=opts,
                    note='प्रश्न आकृति की हर रेखा को उत्तर आकृतियों में ढूँढ़िए। सिर्फ़ ({A}) में पूरी आकृति उसी नाप और उसी दिशा में छिपी है; बाक़ी तीनों में उसकी एक रेखा ग़ायब है।',
                    note_en='Trace every segment of the question figure in each option. Only ({A}) contains the exact figure in the same size and orientation; the other three are each missing one segment.')
    raise Retry()


# ================================================================== assembling a paper
def make(gen, rng, pos):
    for _ in range(400):
        try:
            d = gen(rng)
            need(distinct(d['opts'], 40))
            break
        except Retry:
            continue
    else:
        raise RuntimeError('generator failed: %s' % gen)
    opts = d['opts']; right = opts[0]; rest = opts[1:]; rng.shuffle(rest)
    rest.insert(pos, right)
    d['opts'] = rest; d['ans'] = pos
    d['note'] = d['note'].replace('{A}', ABCD[pos])
    d['note_en'] = d['note_en'].replace('{A}', ABCD[pos])
    return d


def build_paper(pid):
    rng = random.Random('navidya-mat-' + pid)
    while True:
        pos = [0, 1, 2, 3] * 10; rng.shuffle(pos)
        if all(len(set(pos[i:i + 4])) > 1 for i in range(37)): break
    yr = int(pid)
    part1 = [p1_chiral, p1_count, p1_inner if yr % 2 else p1_turn, p1_half]; rng.shuffle(part1)
    part4 = [p4_rotate, p4_move, p4_grow, p4_turnfill]; rng.shuffle(part4)
    part5 = [p5_turn, p5_invert, p5_swap if yr % 2 else p5_sides, p5_turn]; rng.shuffle(part5)
    part8 = [lambda r: p8_punch(r, 1), lambda r: p8_punch(r, 2), lambda r: p8_punch(r, 3), lambda r: p8_punch(r, 2)]; rng.shuffle(part8)
    gens = part1 + [p2_match] * 4 + [p3_pattern] * 4 + part4 + part5 + [p6_complete] * 4 + [p7_mirror] * 4 + part8 + [p9_pieces] * 4 + [p10_hidden] * 4
    out = os.path.join(ROOT, 'papers', pid); os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        if f.endswith('.svg'): os.remove(os.path.join(out, f))
    key = ''; notes = {}; notes_en = {}
    for n in range(1, 41):
        part = (n - 1) // 4
        d = make(gens[n - 1], random.Random('navidya-mat-%s-q%d' % (pid, n)), pos[n - 1])     # one stream per question
        key += ABCD[d['ans']]; notes[str(n)] = d['note']; notes_en[str(n)] = d['note_en']
        small = part in (3, 4, 7)
        if part == 0:
            svg, w, h = strip([(f, True, 100) for f in d['opts']], 150, [58] * 4, labels=True)
            open(os.path.join(out, 'q%02d.svg' % n), 'w').write(svg)
            continue
        cs = 104 if small else 132
        frame_opts = part in (1, 3, 4, 6)
        svg, w, h = strip(d['q'], cs, d.get('gaps', [8] * 4))
        open(os.path.join(out, 'q%02da.svg' % n), 'w').write(svg)
        svg, w, h = strip([(f, frame_opts, 100) for f in d['opts']], cs, [10 if small else 16] * 4, labels=True)
        open(os.path.join(out, 'q%02db.svg' % n), 'w').write(svg)
    os.makedirs(os.path.join(ROOT, 'tools', 'gen'), exist_ok=True)
    json.dump({'key': key, 'notes': notes, 'notes_en': notes_en}, open(os.path.join(ROOT, 'tools', 'gen', pid + '.json'), 'w'), ensure_ascii=False, indent=0)
    print(pid, key)


if __name__ == '__main__':
    for p in (sys.argv[1:] or PAPERS): build_paper(p)
