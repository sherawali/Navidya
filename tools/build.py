#!/usr/bin/env python3
"""Build papers/<id>/paper.js + papers/index.js from tools/src/<id>.txt
Run from repo root or tools/:  python3 tools/build.py
MAT (Q1-40) is included only when papers/<id>/q01.png ... q40.png exist and @key1 is given."""
import json, os, re, glob, struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'tools', 'src')
END = ' Darken the circle in the OMR Answer Sheet against the number corresponding to the question.'
END2 = ' Indicate your answer by darkening the circle in the OMR Answer Sheet against the number corresponding to the question.'
MAT = [
 ('', 'In Question Nos. **1** to **4**, four figures (A), (B), (C) and (D) have been given in each question. Of these four figures, three figures are similar in some way and one figure is different. Select the figure which is different.' + END),
 ('Question Figure', 'In Question Nos. **5** to **8**, a question figure is given on the left side and four answer figures marked (A), (B), (C) and (D) are given on the right side. Select the answer figure which is exactly the same as the question figure.' + END),
 ('Question Figure', 'In Question Nos. **9** to **12**, there is a question figure on the left side, a part of which is missing. Observe the answer figures (A), (B), (C) and (D) on the right side and find out the answer figure which, **without changing the direction**, fits in the missing part of the question figure in order to complete the pattern in the question figure.' + END2),
 ('Question Figures', 'In Question Nos. **13** to **16**, there are three question figures on the left side and the space for the fourth figure is left blank. The question figures are in a series. Find out one figure from among the answer figures given on the right side which occupies the blank space for the fourth figure on the left side and completes the series.' + END2),
 ('Question Figures', 'In Question Nos. **17** to **20**, there are two sets of two question figures each. The second set has an interrogation mark (?). There exists a relationship between the first two question figures. Similar relationship should exist between the third and the fourth question figure. Select one of the answer figures which replaces the mark of interrogation.' + END),
 ('Question Figure', 'In Question Nos. **21** to **24**, one part of a geometrical figure (Triangle, Square, Circle) is on the left side as question figure and the other one is among the four answer figures (A), (B), (C) and (D) on the right side. Find the figure on the right side that completes the geometrical figure.' + END),
 ('Question Figure', 'In Question Nos. **25** to **28**, there is a question figure on the left side and four answer figures marked (A), (B), (C) and (D) are given on the right side. Select the answer figure which is exactly the mirror image of the question figure when the mirror is held at XY.' + END2),
 ('Question Figures', 'In Question Nos. **29** to **32**, a piece of paper is folded and punched as shown in the question figures on the left side and four answer figures marked (A), (B), (C) and (D) are given on the right side. Select the answer figure which indicates how the paper will appear when opened (unfolded).' + END2),
 ('Question Figure', 'In Question Nos. **33** to **36**, a question figure is given on the left side and four answer figures marked (A), (B), (C) and (D) are given on the right side. Select the answer figure which can be formed from the cut-out pieces given in the question figure.' + END),
 ('Question Figure', 'In Question Nos. **37** to **40**, a question figure is given on the left side and four answer figures marked (A), (B), (C) and (D) are given on the right side. Select the answer figure in which the question figure is hidden/embedded.' + END),
]
ARITH_DIR = 'For every question, **four** probable answers as (A), (B), (C) and (D) are given. Only **one** out of these is **correct**. Choose the correct answer and darken the circle in the OMR Answer Sheet against the number corresponding to the question.'
LANG_DIR = 'There are **four** passages in this Section. Each passage is followed by **five** questions. Read each passage carefully and answer the questions that follow. For each question, **four** probable answers as (A), (B), (C) and (D) are given. Only **one** out of these is **correct**. Choose the correct answer and darken the circle in the OMR Answer Sheet against the number corresponding to the question.'

def png_size(p):
    with open(p, 'rb') as f:
        h = f.read(24)
    return struct.unpack('>II', h[16:24])

def parse_q(line):
    m = re.match(r'(\d+)\.\s*(.*)$', line)
    n = int(m.group(1)); parts = [x.strip() for x in m.group(2).split(' | ')]
    assert len(parts) == 5, 'Q%d needs 4 options: %r' % (n, line)
    return {'n': n, 'q': parts[0], 'o': parts[1:]}

def build(path):
    meta = {}; arith = []; passages = []; mode = None
    for raw in open(path, encoding='utf-8'):
        line = raw.rstrip('\n')
        if not line.strip(): continue
        if line.startswith('@'):
            k, _, v = line[1:].partition(' '); meta[k] = v.strip(); continue
        if line.startswith('['): mode = line.strip('[]'); continue
        if line.startswith('#P'): passages.append({'text': line[2:].strip(), 'qs': []}); continue
        q = parse_q(line)
        (arith if mode == 'ARITH' else passages[-1]['qs']).append(q)
    pid = meta['id']; pdir = os.path.join(ROOT, 'papers', pid); os.makedirs(pdir, exist_ok=True)
    key = {}
    assert len(meta['key41']) == 40
    for i, c in enumerate(meta['key41']): key[41 + i] = c
    def figs(n):
        one = os.path.join(pdir, 'q%02d.png' % n); a = os.path.join(pdir, 'q%02da.png' % n); b = os.path.join(pdir, 'q%02db.png' % n)
        if os.path.exists(a) and os.path.exists(b):
            (aw, ah), (bw, bh) = png_size(a), png_size(b)
            return {'n': n, 'a': 'q%02da.png' % n, 'aw': aw, 'ah': ah, 'b': 'q%02db.png' % n, 'bw': bw, 'bh': bh}
        if os.path.exists(one):
            w, h = png_size(one); return {'n': n, 'strip': 'q%02d.png' % n, 'w': w, 'h': h}
        return None
    has_mat = 'key1' in meta and all(figs(i) for i in range(1, 41))
    sections = []
    if has_mat:
        assert len(meta['key1']) == 40
        for i, c in enumerate(meta['key1']): key[1 + i] = c
        parts = []
        for p in range(10):
            qs = []
            for n in range(p * 4 + 1, p * 4 + 5):
                qs.append(figs(n))
            parts.append({'part': 'PART – %d' % (p + 1), 'cap': MAT[p][0], 'dir': MAT[p][1], 'qs': qs})
        sections.append({'id': 'mat', 'name': 'SECTION – I', 'title': 'MENTAL ABILITY TEST', 'short': 'Mental Ability', 'parts': parts})
    def fix_imgs(q):
        m = re.search(r'\[\[img:([^\]]+)\]\]', q['q'])
        if m:
            w, h = png_size(os.path.join(pdir, m.group(1)))
            q['img'] = m.group(1); q['w'] = w; q['h'] = h
            q['q'] = re.sub(r'\s*\[\[img:[^\]]+\]\]', '', q['q'])
        return q
    omit = [int(x) for x in meta.get('omit', '').split()]
    assert [q['n'] for q in arith] == list(range(41, 61)), pid
    arith = [fix_imgs(q) for q in arith if q['n'] not in omit]
    lq = [q['n'] for p in passages for q in p['qs']]
    assert lq == list(range(61, 81)), pid
    sections.append({'id': 'ar', 'name': 'SECTION – II', 'title': 'ARITHMETIC TEST', 'short': 'Arithmetic', 'dir': ARITH_DIR, 'qs': arith})
    sections.append({'id': 'la', 'name': 'SECTION – III', 'title': 'LANGUAGE TEST', 'short': 'Language', 'dir': LANG_DIR, 'passages': passages})
    paper = {'id': pid, 'title': meta['title'], 'date': meta['date'], 'booklet': meta['booklet'], 'code': meta['code'],
             'full': has_mat, 'minutes': 120 if has_mat else 60, 'omit': omit, 'keynote': meta.get('keynote', ''),
             'sections': sections, 'key': ''.join(key.get(i, '-') for i in range(1, 81)),
             'notes': {k[4:]: v for k, v in meta.items() if re.match(r'note\d+$', k)}}
    with open(os.path.join(pdir, 'paper.js'), 'w', encoding='utf-8') as f:
        f.write('JNV_LOAD(' + json.dumps(paper, ensure_ascii=False, separators=(',', ':')) + ');\n')
    return {'id': pid, 'title': meta['title'], 'date': meta['date'], 'booklet': meta['booklet'], 'code': meta['code'],
            'full': has_mat, 'minutes': paper['minutes'], 'questions': (80 if has_mat else 40) - len(omit), 'omit': omit}

if __name__ == '__main__':
    idx = [build(p) for p in sorted(glob.glob(os.path.join(SRC, '[0-9]*.txt')), reverse=True)]
    with open(os.path.join(ROOT, 'papers', 'index.js'), 'w', encoding='utf-8') as f:
        f.write('window.JNV_INDEX=' + json.dumps(idx, ensure_ascii=False, separators=(',', ':')) + ';\n')
    for i in idx: print(i)
