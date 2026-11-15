import sys; sys.path.insert(0, '.')
from crop import *
SRC = '/home/user/work/hi/p%02d.png'
OUT = '../papers/2026/'
# page -> (x0,x1 in 640-scale, [(y0,y1) per question])
P = {
 1: (85, 615, [(238,345),(400,510),(560,670),(725,832)]),
 2: (68, 612, [(245,350),(405,510),(562,662),(715,815)]),
 3: (85, 620, [(262,365),(435,535),(600,695),(755,860)]),
 4: (52, 615, [(236,318),(398,490),(558,655),(722,825)]),
 5: (78, 632, [(275,370),(430,525),(572,668),(720,815)]),
 6: (62, 612, [(250,355),(422,530),(585,690),(738,850)]),
 7: (68, 610, [(238,360),(418,535),(590,702),(765,882)]),
 8: (58, 610, [(262,368),(440,540),(612,712),(785,890)]),
 9: (68, 615, [(242,368),(418,548),(580,712),(748,868)]),
 10:(58, 585, [(245,352),(425,528),(588,690),(752,852)]),
}
# header remnants to blank out (640-scale boxes)
WHITE = {1: [(30,215,200,241)], 4: [(40,210,640,233)], 9: [(330,222,490,253)]}
q = 1
for pg in range(1, 11):
    im = Image.open(SRC % pg).convert('L')
    s = im.width / 640.0
    x0, x1, rows = P[pg]
    for (a, b, c, d) in WHITE.get(pg, []):
        im.paste(255, (int(a*s), int(b*s), int(c*s), int(d*s)))
    for k, (y0, y1) in enumerate(rows):
        st = strip(im, int(x0*s), int(x1*s), int((y0-(3 if k == 0 else 14))*s), int((y1+14)*s), maxw=0)
        print(q, emit(st, OUT + 'q%02d' % q, dosplit=pg > 1), end='; ')
        q += 1
im = Image.open(SRC % 12).convert('L'); s = im.width / 790.0
st = strip(im, int(412*s), int(722*s), int(545*s), int(848*s), maxw=520)
save(st, OUT + 'q60.png')
