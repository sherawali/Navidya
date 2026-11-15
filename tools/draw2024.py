#!/usr/bin/env python3
"""Redraws the two Section-II figures of JNVST 2024 (Q41 bar chart, Q42 angles)
from the data printed in the original booklet. Output: ../papers/2024/q41.png, q42.png"""
import math, os
from PIL import Image, ImageDraw, ImageFont
F = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'papers', '2024')
S = 3  # supersample

def font(px): return ImageFont.truetype(F, px * S)

def text(d, xy, s, f, anchor='mm'):
    d.text((xy[0] * S, xy[1] * S), s, font=f, fill=0, anchor=anchor)

def rot_text(im, cx, cy, s, f):
    """text rotated 90 deg (reads bottom to top), centred on (cx, cy)"""
    w, h = [int(v) + 8 * S for v in f.getbbox(s)[2:]]
    t = Image.new('L', (w, h), 255)
    ImageDraw.Draw(t).text((w // 2, h // 2), s, font=f, fill=0, anchor='mm')
    t = t.rotate(90, expand=True)
    im.paste(t, (int(cx * S - t.width / 2), int(cy * S - t.height / 2)))

def line(d, a, b, w=2): d.line([a[0] * S, a[1] * S, b[0] * S, b[1] * S], fill=0, width=w * S)

def dashed(d, a, b, dash=7, gap=6, w=1):
    L = math.hypot(b[0] - a[0], b[1] - a[1]); n = int(L // (dash + gap)) + 1
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    for i in range(n):
        s = i * (dash + gap); e = min(s + dash, L)
        line(d, (a[0] + ux * s, a[1] + uy * s), (a[0] + ux * e, a[1] + uy * e), w)

def finish(im, name, w):
    im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    im = im.point(lambda v: 0 if v < 70 else (255 if v > 215 else v)).quantize(16)
    im.save(os.path.join(OUT, name), optimize=True); print(name, im.size)

def q41():
    W, H = 600, 400
    im = Image.new('L', (W * S, H * S), 255); d = ImageDraw.Draw(im)
    x0, y0, top = 120, 345, 22            # origin, top of axis
    u = (y0 - 40) / 32.0                  # px per match
    Y = lambda v: y0 - v * u
    line(d, (x0, top), (x0, y0)); line(d, (x0, y0), (W - 20, y0))
    f = font(19)
    for v in range(4, 33, 4):
        line(d, (x0 - 6, Y(v)), (x0 + 6, Y(v)), 2)
        text(d, (x0 - 12, Y(v)), str(v), f, 'rm')
    bars = [('INDIA', 30), ('PAKISTAN', 24), ('ENGLAND', 28), ('AUSTRALIA', 32)]
    bw, gap, bx = 46, 68, x0 + 62
    fb = font(17)
    for name, v in bars:
        dashed(d, (x0 + 6, Y(v)), (bx, Y(v)))
        d.rectangle([bx * S, Y(v) * S, (bx + bw) * S, y0 * S], outline=0, width=2 * S)
        rot_text(im, bx + bw / 2, y0 - 8 - fb.getlength(name) / S / 2, name, fb)
        bx += bw + gap
    rot_text(im, 30, (top + y0) / 2 + 6, 'Number of Matches Played', font(19))
    text(d, ((x0 + W - 20) / 2, y0 + 28), 'Countries', font(20))
    finish(im, 'q41.png', 600)

def q42():
    W, H = 520, 400
    im = Image.new('L', (W * S, H * S), 255); d = ImageDraw.Draw(im)
    O = (215, 215)
    # directions as printed in the booklet (figure not to scale)
    rays = [('A', 0, 250, 195), ('B', 17, 250, 195), ('C', 35, 250, 195), ('D', 124, 190, 150), ('E', 263, 160, 120)]
    P = lambda ang, r: (O[0] + r * math.cos(math.radians(ang)), O[1] - r * math.sin(math.radians(ang)))
    f = font(21); fs = font(19)
    for name, ang, L, dot in rays:
        e = P(ang, L); line(d, O, e)
        for s in (154, -154):                         # arrow head
            h = (e[0] + 13 * math.cos(math.radians(ang + s)), e[1] - 13 * math.sin(math.radians(ang + s)))
            line(d, e, h)
        p = P(ang, dot); r = 4.5
        d.ellipse([(p[0] - r) * S, (p[1] - r) * S, (p[0] + r) * S, (p[1] + r) * S], fill=0)
    def arc(a1, a2, r):
        d.arc([(O[0] - r) * S, (O[1] - r) * S, (O[0] + r) * S, (O[1] + r) * S], 360 - a2, 360 - a1, fill=0, width=2 * S)
    arc(0, 17, 118); arc(17, 35, 100); arc(35, 124, 34); arc(124, 263, 52); arc(263, 360, 26)
    text(d, P(8.5, 138), 'x', fs); text(d, P(26, 124), '2x', fs)
    text(d, P(82, 58), '4x', fs); text(d, P(192, 76), '6x', fs); text(d, P(318, 62), '100°', fs)
    lab = {'A': (0, -24), 'B': (6, 20), 'C': (-8, -20), 'D': (24, 2), 'E': (24, 4)}
    for name, ang, L, dot in rays:
        p = P(ang, dot); dx, dy = lab[name]
        text(d, (p[0] + dx, p[1] - dy), name, f)
    text(d, (O[0] - 6, O[1] + 4), 'O', f, 'rt')
    d.ellipse([(O[0] - 3) * S, (O[1] - 3) * S, (O[0] + 3) * S, (O[1] + 3) * S], fill=0)
    finish(im, 'q42.png', 520)

q41(); q42()
