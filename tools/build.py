#!/usr/bin/env python3
"""Build papers/<id>/paper.js + papers/index.js from tools/src/<id>.txt
Run from repo root or tools/:  python3 tools/build.py
MAT (Q1-40) is included when all 40 figures exist in papers/<id>/ and a key is known:
  - scanned figures  q01.png ... (or q05a.png + q05b.png)  with @key1 in the source file, or
  - generated practice figures  q01.svg ...  with tools/gen/<id>.json  (written by tools/matgen.py)."""
import json, os, re, glob, struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'tools', 'src')
END = ' Darken the circle in the OMR Answer Sheet against the number corresponding to the question.'
END2 = ' Indicate your answer by darkening the circle in the OMR Answer Sheet against the number corresponding to the question.'
END_HI = ' अपने उत्तर को दर्शाने के लिए ओ० एम० आर० उत्तर-पत्रिका में प्रश्न की संगत संख्या के सामने वाले वृत्त को काला करें।'

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

MAT_HI = [
 ('', 'प्रश्न संख्या **1** से **4** में, प्रत्येक प्रश्न में चार चित्र (A), (B), (C) और (D) दर्शाए गए हैं। इन चार चित्रों में से तीन चित्र किसी विधि से एकसमान हैं, जबकि एक चित्र अन्य से भिन्न है। अन्य से भिन्न चित्र का चयन करें।' + END_HI),
 ('प्रश्न चित्र', 'प्रश्न संख्या **5** से **8** में, बाईं ओर एक प्रश्न चित्र दिया गया है तथा दाईं ओर (A), (B), (C) और (D) से चिह्नित चार उत्तर चित्र दिए गए हैं। उत्तर चित्रों में से प्रश्न चित्र के समरूप चित्र को चुनें।' + END_HI),
 ('प्रश्न चित्र', 'प्रश्न संख्या **9** से **12** में, बाईं ओर एक प्रश्न चित्र दिया गया है, जिसका एक भाग लुप्त दर्शाया गया है। दाईं ओर दिए गए उत्तर चित्र (A), (B), (C) और (D) पर ग़ौर करें तथा उस उत्तर चित्र का पता लगाएँ जिसको **बिना दिशा परिवर्तन** के प्रश्न चित्र के पैटर्न को पूरा करने के लिए प्रश्न चित्र के लुप्त भाग में बिठाया जा सके।' + END_HI),
 ('प्रश्न चित्र', 'प्रश्न संख्या **13** से **16** में, बाईं ओर तीन प्रश्न चित्र दर्शाए गए हैं तथा चौथे चित्र के लिए स्थान छोड़ा गया है। प्रश्न चित्र श्रेणीक्रम में हैं। श्रेणीक्रम को पूरा करने के लिए दाईं ओर उपलब्ध उत्तर चित्रों में से एक चित्र का चयन करें जिसे बाईं ओर दिए गए प्रश्न चित्र के खाली स्थान में प्रतिस्थापित किया जा सके।' + END_HI),
 ('प्रश्न चित्र', 'प्रश्न संख्या **17** से **20** में, प्रत्येक प्रश्न में दो प्रश्न चित्रों के दो सेट दिए गए हैं। दूसरे सेट में एक प्रश्न चिह्न (?) है। प्रथम सेट के दो प्रश्न चित्रों में एक निश्चित सम्बन्ध है। इसी तरह का सम्बन्ध दूसरे सेट के तीसरे तथा चौथे प्रश्न चित्र में भी होना आवश्यक है। उत्तर चित्रों में से उस चित्र का चयन करें जो प्रश्न चिह्न को प्रतिस्थापित करेगा।' + END_HI),
 ('प्रश्न चित्र', 'प्रश्न संख्या **21** से **24** में, प्रश्न चित्र के रूप में ज्यामितीय चित्र (त्रिभुज, वर्ग, वृत्त) के एक भाग को बाईं ओर दर्शाया गया है तथा दाईं ओर दूसरे भाग को चार उत्तर चित्रों के रूप में (A), (B), (C) और (D) से दर्शाया गया है। दाईं ओर के चित्रों में से ज्यामितीय चित्र को पूर्ण करने वाले चित्र को ज्ञात करें।' + END_HI),
 ('प्रश्न चित्र', 'प्रश्न संख्या **25** से **28** में, बाईं ओर एक प्रश्न चित्र दिया गया है तथा दाईं ओर (A), (B), (C) और (D) से चिह्नित चार उत्तर चित्र दिए गए हैं। किसी दर्पण को XY के अनुदिश रखे जाने पर प्रश्न चित्र के सही दर्पण प्रतिबिंब को उत्तर चित्रों में से चुनें।' + END_HI),
 ('प्रश्न चित्र', 'प्रश्न संख्या **29** से **32** में, बाईं ओर प्रश्न चित्र में दर्शाए अनुसार काग़ज़ के एक टुकड़े को मोड़कर पंच किया गया है तथा दाईं ओर (A), (B), (C) और (D) से चिह्नित चार उत्तर चित्र दिए गए हैं। काग़ज़ के टुकड़े की तह को खोलने पर वह जिस प्रकार दिखेगा वैसा ही चित्र उत्तर चित्रों में से चुनें।' + END_HI),
 ('प्रश्न चित्र', 'प्रश्न संख्या **33** से **36** में, बाईं ओर एक प्रश्न चित्र दिया गया है तथा दाईं ओर (A), (B), (C) और (D) से चिह्नित चार उत्तर चित्र दिए गए हैं। उत्तर चित्रों में से उस चित्र का चयन करें जिसे प्रश्न चित्र में उपलब्ध कट-आउट टुकड़ों से बनाया जा सकता हो।' + END_HI),
 ('प्रश्न चित्र', 'प्रश्न संख्या **37** से **40** में, बाईं ओर एक प्रश्न चित्र दिया गया है तथा दाईं ओर (A), (B), (C) और (D) से चिह्नित चार उत्तर चित्र दिए गए हैं। उत्तर चित्रों में से उस चित्र को चुनें जिसमें प्रश्न चित्र छिपा/सम्मिलित है।' + END_HI),
]

ARITH_DIR = 'For every question, **four** probable answers as (A), (B), (C) and (D) are given. Only **one** out of these is **correct**. Choose the correct answer and darken the circle in the OMR Answer Sheet against the number corresponding to the question.'
ARITH_DIR_HI = 'प्रत्येक प्रश्न के लिए **चार** संभावित उत्तर दिए गए हैं, जिन्हें (A), (B), (C) और (D) क्रम दिया गया है। इनमें से केवल **एक** उत्तर ही **सही** है। सही उत्तर चुनें तथा' + END_HI

LANG_DIR = 'There are **four** passages in this Section. Each passage is followed by **five** questions. Read each passage carefully and answer the questions that follow. For each question, **four** probable answers as (A), (B), (C) and (D) are given. Only **one** out of these is **correct**. Choose the correct answer and darken the circle in the OMR Answer Sheet against the number corresponding to the question.'
LANG_DIR_HI = 'इस खण्ड में **चार** अनुच्छेद हैं। प्रत्येक अनुच्छेद पर **पाँच** प्रश्न हैं। प्रत्येक अनुच्छेद को सावधानी से पढ़ें और उसके नीचे दिए गए प्रश्नों के उत्तर दें। प्रत्येक प्रश्न के लिए **चार** संभावित उत्तर दिए गए हैं, जिनकी क्रम संख्या (A), (B), (C) और (D) है। इनमें से केवल **एक** उत्तर ही **सही** है। सही उत्तर चुनें तथा' + END_HI


def png_size(p):
    with open(p, 'rb') as f:
        h = f.read(24)
    return struct.unpack('>II', h[16:24])


def svg_size(p):
    m = re.search(r'<svg[^>]*\swidth="(\d+)"[^>]*\sheight="(\d+)"', open(p, encoding='utf-8').read(400))
    return int(m.group(1)), int(m.group(2))


def img_size(p):
    return svg_size(p) if p.endswith('.svg') else png_size(p)


def parse_q(line):
    m = re.match(r'(\d+)\.\s*(.*)$', line)
    n = int(m.group(1)); parts = [x.strip() for x in m.group(2).split(' | ')]
    assert len(parts) == 5, 'Q%d needs 4 options: %r' % (n, line)
    return {'n': n, 'q': parts[0], 'o': parts[1:]}


def build(path):
    meta = {}; arith = []; passages = []; arith_hi = []; passages_hi = []; mode = None
    for raw in open(path, encoding='utf-8'):
        line = raw.rstrip('\n')
        if not line.strip(): continue
        if line.startswith('@'):
            k, _, v = line[1:].partition(' '); meta[k] = v.strip(); continue
        if line.startswith('['): mode = line.strip('[]'); continue
        if line.startswith('#P'):
            target = passages_hi if mode == 'LANG_HI' else passages
            target.append({'text': line[2:].strip(), 'qs': []})
            continue
        q = parse_q(line)
        if mode == 'ARITH': arith.append(q)
        elif mode == 'ARITH_HI': arith_hi.append(q)
        elif mode == 'LANG': passages[-1]['qs'].append(q)
        elif mode == 'LANG_HI': passages_hi[-1]['qs'].append(q)
        else: raise ValueError('Unknown mode %r in %s' % (mode, path))

    pid = meta['id']; pdir = os.path.join(ROOT, 'papers', pid); os.makedirs(pdir, exist_ok=True)
    key = {}; key_hi = {}
    assert len(meta['key41']) == 40
    for i, c in enumerate(meta['key41']):
        key[41 + i] = c
        key_hi[41 + i] = c
    if 'key_hi61' in meta:
        assert len(meta['key_hi61']) == 20, pid
        for i, c in enumerate(meta['key_hi61']):
            key_hi[61 + i] = c

    def figs(n):
        for ext in ('png', 'svg'):
            one = 'q%02d.%s' % (n, ext); a = 'q%02da.%s' % (n, ext); b = 'q%02db.%s' % (n, ext)
            if os.path.exists(os.path.join(pdir, a)) and os.path.exists(os.path.join(pdir, b)):
                (aw, ah), (bw, bh) = img_size(os.path.join(pdir, a)), img_size(os.path.join(pdir, b))
                return {'n': n, 'a': a, 'aw': aw, 'ah': ah, 'b': b, 'bw': bw, 'bh': bh}
            if os.path.exists(os.path.join(pdir, one)):
                w, h = img_size(os.path.join(pdir, one)); return {'n': n, 'strip': one, 'w': w, 'h': h}
        return None

    gen = os.path.join(ROOT, 'tools', 'gen', pid + '.json')
    matgen = False
    notes_en = {k[4:]: v for k, v in meta.items() if re.match(r'note\d+$', k)}
    notes_hi = {k[4:-3]: v for k, v in meta.items() if re.match(r'note\d+_hi$', k)}

    if 'key1' not in meta and os.path.exists(gen):
        g = json.load(open(gen, encoding='utf-8'))
        meta['key1'] = g['key']; matgen = True
        for k, v in g.get('notes', {}).items():
            notes_hi.setdefault(k, v)
        for k, v in g.get('notes_en', g.get('notes', {})).items():
            notes_en.setdefault(k, v)

    has_mat = 'key1' in meta and all(figs(i) for i in range(1, 41))
    matgen = matgen and has_mat
    langgen = meta.get('langgen') in ('1', 'true', 'True')

    if matgen:
        meta['keynote'] = ('Q1–40 (Mental Ability): practice questions generated specifically for this site rather than the original booklet; every answer is verified programmatically. ' + meta.get('keynote', '')).strip()
        meta['keynote_hi'] = ('प्रश्न 1–40 (मानसिक योग्यता): इस साइट के लिए कोड से बनाए गए अभ्यास प्रश्न हैं, असली पुस्तिका के नहीं; हर प्रश्न का उत्तर प्रोग्राम द्वारा जाँचा गया है। ' + meta.get('keynote_hi', '')).strip()

    sections = []
    if has_mat:
        assert len(meta['key1']) == 40
        for i, c in enumerate(meta['key1']):
            key[1 + i] = c
            key_hi[1 + i] = c
        parts = []
        for p in range(10):
            qs = [figs(n) for n in range(p * 4 + 1, p * 4 + 5)]
            parts.append({
                'part': 'PART – %d' % (p + 1),
                'part_hi': 'भाग – %d' % (p + 1),
                'cap': MAT[p][0],
                'cap_hi': MAT_HI[p][0],
                'dir': MAT[p][1],
                'dir_hi': MAT_HI[p][1],
                'qs': qs,
            })
        sections.append({
            'id': 'mat',
            'name': 'SECTION – I', 'name_hi': 'खण्ड – I',
            'title': 'MENTAL ABILITY TEST', 'title_hi': 'मानसिक योग्यता परीक्षण',
            'short': 'Mental Ability', 'short_hi': 'मानसिक योग्यता',
            'parts': parts,
        })

    def fix_imgs(q):
        m = re.search(r'\[\[img:([^\]]+)\]\]', q['q'])
        if m:
            w, h = png_size(os.path.join(pdir, m.group(1)))
            q['img'] = m.group(1); q['w'] = w; q['h'] = h
            q['q'] = re.sub(r'\s*\[\[img:[^\]]+\]\]', '', q['q'])
        return q

    omit = [int(x) for x in meta.get('omit', '').split()]
    assert [q['n'] for q in arith] == list(range(41, 61)), pid
    assert [q['n'] for q in arith_hi] == list(range(41, 61)), (pid, 'ARITH_HI')

    hi_map = {q['n']: q for q in arith_hi}
    merged_arith = []
    for q in arith:
        if q['n'] in omit: continue
        q = fix_imgs(q)
        qh = hi_map[q['n']]
        q['q_hi'] = re.sub(r'\s*\[\[img:[^\]]+\]\]', '', qh['q'])
        q['o_hi'] = qh['o']
        merged_arith.append(q)

    lq = [q['n'] for p in passages for q in p['qs']]
    lq_hi = [q['n'] for p in passages_hi for q in p['qs']]
    assert lq == list(range(61, 81)), pid
    assert lq_hi == list(range(61, 81)), (pid, 'LANG_HI')

    sections.append({
        'id': 'ar',
        'name': 'SECTION – II', 'name_hi': 'खण्ड – II',
        'title': 'ARITHMETIC TEST', 'title_hi': 'अंकगणित परीक्षण',
        'short': 'Arithmetic', 'short_hi': 'अंकगणित',
        'dir': ARITH_DIR, 'dir_hi': ARITH_DIR_HI,
        'qs': merged_arith,
    })
    sections.append({
        'id': 'la',
        'name': 'SECTION – III', 'name_hi': 'खण्ड – III',
        'title': 'LANGUAGE TEST', 'title_hi': 'भाषा परीक्षण',
        'short': 'Language', 'short_hi': 'भाषा',
        'dir': LANG_DIR, 'dir_hi': LANG_DIR_HI,
        'passages': passages,
        'passages_hi': passages_hi,
    })

    paper = {
        'id': pid,
        'title': meta['title'], 'title_hi': meta.get('title_hi', meta['title']),
        'date': meta['date'], 'date_hi': meta.get('date_hi', meta['date']),
        'booklet': meta['booklet'], 'booklet_hi': meta.get('booklet_hi', meta['booklet']),
        'code': meta['code'],
        'full': has_mat, 'matgen': matgen, 'langgen': langgen,
        'minutes': 120 if has_mat else 60,
        'omit': omit,
        'keynote': meta.get('keynote', ''),
        'keynote_hi': meta.get('keynote_hi', meta.get('keynote', '')),
        'sections': sections,
        'key': ''.join(key.get(i, '-') for i in range(1, 81)),
        'key_hi': ''.join(key_hi.get(i, '-') for i in range(1, 81)),
        'notes': notes_en,
        'notes_hi': notes_hi,
    }
    with open(os.path.join(pdir, 'paper.js'), 'w', encoding='utf-8') as f:
        f.write('JNV_LOAD(' + json.dumps(paper, ensure_ascii=False, separators=(',', ':')) + ');\n')
    return {
        'id': pid,
        'title': meta['title'], 'title_hi': paper['title_hi'],
        'date': meta['date'], 'date_hi': paper['date_hi'],
        'booklet': meta['booklet'], 'booklet_hi': paper['booklet_hi'],
        'code': meta['code'],
        'full': has_mat, 'matgen': matgen, 'langgen': langgen,
        'minutes': paper['minutes'],
        'questions': (80 if has_mat else 40) - len(omit),
        'omit': omit,
    }


if __name__ == '__main__':
    idx = [build(p) for p in sorted(glob.glob(os.path.join(SRC, '[0-9]*.txt')), reverse=True)]
    with open(os.path.join(ROOT, 'papers', 'index.js'), 'w', encoding='utf-8') as f:
        f.write('window.JNV_INDEX=' + json.dumps(idx, ensure_ascii=False, separators=(',', ':')) + ';\n')
    for i in idx: print(i)
