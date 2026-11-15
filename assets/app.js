/* JNVST mock tests – plain ES5, no dependencies, works from any static host (GitHub Pages) */
(function () {
  'use strict';
  var V = 4;
  var $app = document.getElementById('app');
  var $toast = document.getElementById('toast');
  var INDEX = window.JNV_INDEX || [];
  var PAPERS = {};
  var L = ['A', 'B', 'C', 'D'];
  var MARK = 1.25;
  var S = null;          // running exam state
  var tick = null;       // timer handle
  var view = '';         // current view name
  var curPaper = null;   // active loaded paper for re-rendering on language switch
  var focusActiveQ = null;

  var MEM = {};          // fallback when localStorage is blocked (private mode etc.)
  function get(k, d) { var v; try { v = localStorage.getItem('jnv:' + k); } catch (e) { v = MEM[k]; } if (v == null) v = MEM[k]; try { return v == null ? d : JSON.parse(v); } catch (e2) { return d; } }
  function set(k, v) { if (v === null) delete MEM[k]; else MEM[k] = JSON.stringify(v); try { if (v === null) localStorage.removeItem('jnv:' + k); else localStorage.setItem('jnv:' + k, MEM[k]); } catch (e) { } }

  var lang = get('lang', 'hi') === 'en' ? 'en' : 'hi';
  document.documentElement.lang = lang;

  function hi() { return lang === 'hi'; }
  function t(h, e) { return lang === 'hi' ? h : e; }
  function fld(obj, k) { return (lang === 'hi' && obj[k + '_hi'] != null) ? obj[k + '_hi'] : obj[k]; }
  function resKey(p, res) {
    var l = (res && res.lang) ? res.lang : lang;
    return (l === 'hi' && p.key_hi) ? p.key_hi : p.key;
  }

  /* ---------- tiny helpers ---------- */
  function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
  function fmt(s) {
    return esc(s)
      .replace(/\{([^{}\/]+)\/([^{}]+)\}/g, '<span class="fr"><span>$1</span><span>$2</span></span>')
      .replace(/⦃/g, '{').replace(/⦄/g, '}')
      .replace(/\^(\d+)/g, '<sup>$1</sup>')
      .replace(/~([^~]+)~/g, '<span style="text-decoration:overline">$1</span>')
      .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
      .replace(/\*(.+?)\*/g, '<b><i>$1</i></b>')
      .replace(/_{3,}/g, '<span class="blank"></span>')
      .replace(/¶/g, '<br>');
  }
  function up(el, attr) { while (el && el !== document) { if (el.getAttribute && el.getAttribute(attr) != null) return el; el = el.parentNode; } return null; }
  function all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function toast(msg, ms) { $toast.textContent = msg; $toast.className = 'show'; clearTimeout(toast.t); toast.t = setTimeout(function () { $toast.className = ''; }, ms || 2600); }
  function mmss(sec) { sec = Math.max(0, Math.round(sec)); var h = Math.floor(sec / 3600), m = Math.floor(sec % 3600 / 60), s = sec % 60; return (h ? h + ':' : '') + (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s; }
  function marks(n) { var v = n * MARK; return v % 1 ? v.toFixed(2) : String(v); }
  function meta(id) { for (var i = 0; i < INDEX.length; i++) if (INDEX[i].id === id) return INDEX[i]; return null; }
  function beep() {
    try {
      var AC = window.AudioContext || window.webkitAudioContext; if (!AC) return;
      var ac = beep.ac || (beep.ac = new AC()), t0 = ac.currentTime;
      for (var i = 0; i < 3; i++) {
        var o = ac.createOscillator(), g = ac.createGain();
        o.frequency.value = 880; o.connect(g); g.connect(ac.destination);
        g.gain.setValueAtTime(0.0001, t0 + i * 0.45); g.gain.exponentialRampToValueAtTime(0.3, t0 + i * 0.45 + 0.02); g.gain.exponentialRampToValueAtTime(0.0001, t0 + i * 0.45 + 0.35);
        o.start(t0 + i * 0.45); o.stop(t0 + i * 0.45 + 0.4);
      }
    } catch (e) { }
  }
  function langSwitcherHtml() {
    return '<div class="langsw no-print" role="group" aria-label="' + t('भाषा चुनें', 'Choose language') + '">' +
      '<button type="button" data-act="lang" data-lang="hi" class="' + (hi() ? 'on' : '') + '" aria-pressed="' + hi() + '">हिन्दी</button>' +
      '<button type="button" data-act="lang" data-lang="en" class="' + (!hi() ? 'on' : '') + '" aria-pressed="' + (!hi()) + '">English</button></div>';
  }

  /* ---------- data ---------- */
  window.JNV_LOAD = function (p) { PAPERS[p.id] = p; };
  function loadPaper(id, cb) {
    if (PAPERS[id]) { curPaper = PAPERS[id]; return cb(PAPERS[id]); }
    var s = document.createElement('script');
    s.src = 'papers/' + id + '/paper.js?v=' + V;
    s.onload = function () { if (PAPERS[id]) { curPaper = PAPERS[id]; cb(PAPERS[id]); } else fail(); };
    s.onerror = fail;
    function fail() {
      $app.innerHTML = '<div class="sheet ui"><p>' + t('पेपर लोड नहीं हो पाया। इंटरनेट जाँचकर दुबारा प्रयास कीजिए।', 'Could not load the paper. Please check your connection and try again.') +
        '</p><p><a class="btn" href="#/">' + t('होम', 'Home') + '</a></p></div>';
    }
    document.head.appendChild(s);
  }
  function secPassages(sec, forceLang) {
    var useHi = forceLang ? (forceLang === 'hi') : hi();
    return (useHi && sec.passages_hi && sec.passages_hi.length) ? sec.passages_hi : sec.passages;
  }
  function qList(p) {
    var out = [];
    p.sections.forEach(function (sec) {
      (sec.parts || []).forEach(function (pt) { pt.qs.forEach(function (q) { out.push({ q: q, sec: sec }); }); });
      (sec.qs || []).forEach(function (q) { out.push({ q: q, sec: sec }); });
      (secPassages(sec) || []).forEach(function (ps) { ps.qs.forEach(function (q) { out.push({ q: q, sec: sec }); }); });
    });
    return out;
  }
  /* booklet pages, numbered like the real booklet (cover = page 1) */
  function buildPages(p, forceLang) {
    var pages = [], no = p.full ? 2 : 12;
    p.sections.forEach(function (sec) {
      var shortLbl = fld(sec, 'short');
      if (sec.parts) sec.parts.forEach(function (pt, i) {
        pages.push({ no: no++, sec: sec, head: i === 0, part: pt, qs: pt.qs, label: fld(pt, 'part').replace('–', '-') });
      });
      if (sec.qs) for (var i = 0; i < sec.qs.length; i += 10) {
        pages.push({ no: no++, sec: sec, head: i === 0, qs: sec.qs.slice(i, i + 10), cols: true, label: shortLbl });
      }
      var psList = secPassages(sec, forceLang);
      if (psList) for (var j = 0; j < psList.length; j += 2) {
        var ps = psList.slice(j, j + 2), qs = [];
        ps.forEach(function (x) { qs = qs.concat(x.qs); });
        pages.push({ no: no++, sec: sec, head: j === 0, passages: ps, pidx: j, qs: qs, cols: true, label: shortLbl });
      }
    });
    return pages;
  }

  /* ---------- question rendering ---------- */
  function bubbles(n, ans, key, cls) {
    var h = '<div class="bub ' + (cls || '') + '">';
    L.forEach(function (o) {
      var c = 'b';
      if (key) { if (o === key) c += ' ok'; else if (o === ans) c += ' bad'; }
      else if (o === ans) c += ' on';
      h += '<button type="button" class="' + c + '" data-act="ans" data-q="' + n + '" data-o="' + o + '" aria-label="' + t('प्रश्न ' + n + ' विकल्प ' + o, 'Question ' + n + ' option ' + o) + '"' + (key ? ' disabled' : '') + '>' + o + '</button>';
    });
    return h + '</div>';
  }
  function verdict(ans, key) {
    if (!key || key === '-') return '';
    if (!ans) return '<div class="verdict v-skip">' + t('उत्तर नहीं दिया · सही उत्तर: (' + key + ')', 'Not attempted · Correct answer: (' + key + ')') + '</div>';
    if (ans === key) return '<div class="verdict v-ok">✔ ' + t('सही · (' + key + ')', 'Correct · (' + key + ')') + '</div>';
    return '<div class="verdict v-bad">✘ ' + t('आपका उत्तर: (' + ans + ') · सही उत्तर: (' + key + ')', 'Your answer: (' + ans + ') · Correct answer: (' + key + ')') + '</div>';
  }
  function renderQ(p, q, ans, key) {
    var h, st = key ? (!ans ? 'skip' : ans === key ? 'ok' : 'bad') : '';
    if (q.strip || q.a) {
      var im = function (f, w, hh, alt) { return '<img src="papers/' + p.id + '/' + f + '" width="' + w + '" height="' + hh + '" loading="lazy" decoding="async" alt="' + esc(alt) + '">'; };
      var capQ = t('प्रश्न चित्र', 'Question Figure'), capA = t('उत्तर चित्र', 'Answer Figures');
      h = '<div class="q fig" id="q' + q.n + '" data-st="' + st + '"><div class="qn">' + q.n + '.</div><div class="qb">' +
        (q.a ? '<div class="figrow" style="--r:' + Math.min(1, q.aw / q.bw).toFixed(3) + '"><div class="fq" data-cap="' + capQ + '" style="flex:' + q.aw + ' 1 0%">' + im(q.a, q.aw, q.ah, t('प्रश्न ' + q.n + ': प्रश्न चित्र', 'Question ' + q.n + ': question figure')) + '</div><div class="fa" data-cap="' + capA + '" style="flex:' + q.bw + ' 1 0%">' + im(q.b, q.bw, q.bh, t('प्रश्न ' + q.n + ': उत्तर चित्र (A), (B), (C), (D)', 'Question ' + q.n + ': answer figures (A), (B), (C), (D)')) + '</div></div>'
          : '<div class="figone">' + im(q.strip, q.w, q.h, t('प्रश्न ' + q.n + ': चित्र (A), (B), (C), (D)', 'Question ' + q.n + ': figures (A), (B), (C), (D)')) + '</div>') +
        bubbles(q.n, ans, key) + verdict(ans, key) + '</div></div>';
      return h;
    }
    var qTxt = (hi() && q.q_hi) ? q.q_hi : q.q;
    var qOpts = (hi() && q.o_hi) ? q.o_hi : q.o;
    var long = false;
    qOpts.forEach(function (o) { if (o.replace(/\{[^}]*\}/g, 'xx').length > 20) long = true; });
    h = '<div class="q" id="q' + q.n + '" data-st="' + st + '"><div class="qn">' + q.n + '.</div><div class="qb"><p class="qt">' + fmt(qTxt) + '</p>';
    if (q.img) h += '<img class="qimg" src="papers/' + p.id + '/' + q.img + '" width="' + q.w + '" height="' + q.h + '" loading="lazy" decoding="async" alt="' + t('प्रश्न ' + q.n + ' का चित्र', 'Figure for question ' + q.n) + '">';
    h += '<ul class="opts' + (long ? ' long' : '') + '">';
    qOpts.forEach(function (o, i) {
      var c = '';
      if (key) { if (L[i] === key) c = 'right'; else if (L[i] === ans) c = 'wrong'; }
      else if (L[i] === ans) c = 'sel';
      h += '<li class="' + c + '" data-act="ans" data-q="' + q.n + '" data-o="' + L[i] + '"><span class="lb">(' + L[i] + ')</span><span>' + fmt(o) + '</span></li>';
    });
    h += '</ul>' + bubbles(q.n, ans, key, 'left') + verdict(ans, key) + '</div></div>';
    return h;
  }
  function renderPage(p, pg, ansMap, keyed, keyOverride) {
    var odd = pg.no % 2, code = fld(p, 'booklet') + ' – ' + p.code;
    var keyStr = keyOverride || ((lang === 'hi' && p.key_hi) ? p.key_hi : p.key);
    var pNotes = (hi() && p.notes_hi) ? p.notes_hi : p.notes;
    var h = '<div class="runhead">' + (odd ? '<span></span><span class="pg">( ' + pg.no + ' )</span><span>' + esc(code) + '</span>' : '<span>' + esc(code) + '</span><span class="pg">( ' + pg.no + ' )</span><span></span>') + '</div>';
    if (pg.head) h += '<div class="sec-h">' + esc(fld(pg.sec, 'name')) + '<br>' + esc(fld(pg.sec, 'title')) + '</div>';
    if (pg.head && pg.sec.id === 'mat' && p.matgen) {
      h += '<p class="qnote" style="margin:0 0 10px">' + t(
        'इस खण्ड के चित्र इस साइट के लिए बनाए गए <b>नए अभ्यास प्रश्न</b> हैं (पैटर्न वही, 10 भाग × 4 प्रश्न) — ये ' + esc(fld(p, 'title')) + ' की असली पुस्तिका के चित्र नहीं हैं।',
        'The figures in this Section are <b>newly generated practice questions</b> (same 10 parts × 4 questions pattern) — not scans from the original ' + esc(fld(p, 'title')) + ' booklet.'
      ) + '</p>';
    }
    if (pg.head && pg.sec.id === 'la' && p.langgen && hi()) {
      h += '<p class="qnote" style="margin:0 0 10px">इस पेपर की असली हिन्दी पुस्तिका का पाठ ऑनलाइन उपलब्ध न होने के कारण, इस खण्ड में JNVST पैटर्न पर लिखे गए <b>नए हिन्दी अभ्यास गद्यांश</b> दिए गए हैं।</p>';
    }
    if (pg.part) {
      h += '<div class="sec-h">' + esc(fld(pg.part, 'part')) + '</div><p class="dir"><b>' + t('निर्देश :', 'Directions :') + '</b> ' + fmt(fld(pg.part, 'dir')) + '</p>';
      var cap = fld(pg.part, 'cap');
      if (cap) { var f = pg.part.qs[0]; h += '<div class="cap"><span style="flex:' + (f.aw || 1) + ' 1 0%">' + esc(cap) + '</span><span style="flex:' + (f.bw || 3) + ' 1 0%">' + t('उत्तर चित्र', 'Answer Figures') + '</span></div>'; }
    } else if (pg.head) h += '<p class="dir"><b>' + t('निर्देश :', 'Directions :') + '</b> ' + fmt(fld(pg.sec, 'dir')) + '</p>';
    function qs(list) {
      return list.map(function (q) {
        var x = renderQ(p, q, ansMap[q.n], keyed ? keyStr.charAt(q.n - 1) : null);
        if (keyed && pNotes && pNotes[q.n]) x = x.replace(/<\/div><\/div>$/, '<div class="qnote">ℹ ' + esc(pNotes[q.n]) + '</div></div></div>');
        return x;
      }).join('');
    }
    if (pg.passages) {
      h += '<div class="cols">';
      pg.passages.forEach(function (ps, i) {
        h += '<div class="passage"><h4>' + t('अनुच्छेद – ', 'Passage – ') + (pg.pidx + i + 1) + '</h4><p>' + fmt(ps.text).replace(/<br>/g, '</p><p>') + '</p></div>' + qs(ps.qs);
      });
      h += '</div>';
    } else h += '<div class="' + (pg.cols ? 'cols' : '') + '">' + qs(pg.qs) + '</div>';
    if (pg.cols && !pg.passages) h += '<div class="rough">' + t('कच्चे कार्य के लिए जगह', 'SPACE FOR ROUGH WORK') + '</div>';
    return h;
  }

  /* ---------- HOME ---------- */
  function home() {
    view = 'home'; curPaper = null;
    var h = '<div class="home"><div class="masthead">' +
      '<div class="masthead-top"><span style="font-weight:700;letter-spacing:1.5px">' + t('परीक्षण पुस्तिका', 'TEST BOOKLET') + '</span>' + langSwitcherHtml() + '</div>' +
      '<h1>' + t('जवाहर नवोदय विद्यालय चयन परीक्षा', 'Jawahar Navodaya Vidyalaya Selection Test') + '</h1>' +
      '<p>' + t('कक्षा VI · <b>पिछले वर्षों के असली प्रश्न-पत्रों</b> पर आधारित मॉक टेस्ट', 'Class VI · Mock Tests from <b>Real Previous Year Papers</b>') + '</p>' +
      '<span class="tag">' + t('समय : 2 घण्टे &nbsp;|&nbsp; अधिकतम अंक : 100', 'Time : 2 Hours &nbsp;|&nbsp; Maximum Marks : 100') + '</span></div>' +
      '<div class="note">' + t(
        '<b>ध्यान दें:</b> ये मॉक टेस्ट पिछले वर्षों के असली प्रश्न-पत्रों से बने हैं, इसलिए इनका पैटर्न पुराना है (मानसिक योग्यता 40 + अंकगणित 20 + भाषा 20)। 28 नवम्बर 2026 की JNVST 2027 परीक्षा में नया पैटर्न है (मानसिक योग्यता 20 + पर्यावरण अध्ययन 20 + अंकगणित 20 + भाषा 20) — अंकगणित, भाषा और मानसिक योग्यता के अभ्यास के लिए ये पेपर पूरी तरह उपयोगी हैं।',
        '<b>Note:</b> These mocks are built from real previous year papers (Mental Ability 40 + Arithmetic 20 + Language 20). The 28 Nov 2026 JNVST 2027 exam uses a revised pattern (Mental Ability 20 + EVS 20 + Arithmetic 20 + Language 20) — these papers remain fully useful for practising Arithmetic, Language, and Mental Ability.'
      ) + '</div><div class="grid">';
    INDEX.forEach(function (m) {
      var best = get('best:' + m.id, null), run = get('run:' + m.id, null);
      var desc = '';
      if (m.full) {
        desc = '<span class="badge">' + t('पूरा पेपर', 'FULL PAPER') + '</span><br>' + t('80 प्रश्न · 100 अंक · 2 घण्टे', '80 questions · 100 marks · 2 hours') + '<br>';
        if (hi()) {
          if (!m.matgen && !m.langgen) desc += 'असली चित्र व प्रश्न + आधिकारिक उत्तर कुंजी';
          else if (m.matgen && m.langgen) desc += 'खण्ड II असली पेपर से · खण्ड I व III इसी पैटर्न के नए अभ्यास प्रश्न';
          else if (m.matgen) desc += 'खण्ड II व III असली पेपर से · खण्ड I इसी पैटर्न के नए अभ्यास चित्र';
          else desc += 'खण्ड I व II असली पेपर से · खण्ड III नए अभ्यास गद्यांश';
        } else {
          desc += m.matgen ? 'Section II + III from real paper · Section I practice figures in same pattern' : 'Real figures + official answer key';
        }
      } else {
        desc = '<span class="badge part">' + t('खण्ड II + III', 'SECTION II + III') + '</span><br>' + m.questions + t(' प्रश्न (41–80) · ', ' questions (Q41–80) · ') + marks(m.questions) + t(' अंक · 1 घण्टा', ' marks · 1 hour');
      }
      h += '<div class="card"><span class="code">' + esc(m.code) + '</span><h2>' + esc(fld(m, 'title')) + '</h2>' +
        '<div class="meta">' + t('परीक्षा तिथि: ', 'Exam date: ') + esc(fld(m, 'date')) + '<br>' + t('पुस्तिका: ', 'Booklet: ') + esc(fld(m, 'booklet')) + ' · ' + t('कोड ', 'Code ') + esc(m.code) + '<br>' + desc + '</div>' +
        (best ? '<div class="best">' + t('सर्वश्रेष्ठ स्कोर: ', 'Best score: ') + '<b>' + best.m + ' / ' + best.max + '</b></div>' : '') +
        '<a class="btn primary" href="#/p/' + m.id + (run ? '/exam' : '') + '">' + (run ? t('टेस्ट जारी रखें ▶', 'Resume test ▶') : t('पुस्तिका खोलें ▶', 'Open booklet ▶')) + '</a></div>';
    });
    h += '</div><div class="foot"><p>' + t(
      '<b>कैसे उपयोग करें:</b> पुस्तिका खोलें → सामान्य निर्देश पढ़ें → टेस्ट शुरू करें। हर प्रश्न के नीचे दिए गए OMR वृत्त (A/B/C/D) को काला करें; आप ऊपर से पूरी OMR उत्तर-पत्रिका कभी भी देख सकते हैं। हर 30 मिनट पर घंटी बजेगी। समय समाप्त होते ही पेपर अपने आप जमा हो जाएगा और तुरंत परिणाम व सही उत्तर दिखाई देंगे। आपके उत्तर केवल आपके फ़ोन/कम्प्यूटर में ही सुरक्षित रहते हैं।',
      '<b>How to use:</b> Open a booklet → read the instructions → start the test. Fill the OMR circle (A/B/C/D) below each question, or open the OMR sheet anytime from the top bar. A bell rings every 30 minutes. When time runs out, the paper auto-submits and shows your score with correct answers immediately. Your answers are saved locally on your device only.'
    ) + '</p><p>' + t(
      'प्रश्न-पत्र © नवोदय विद्यालय समिति। यह वेबसाइट केवल निःशुल्क अभ्यास के लिए है, NVS से संबद्ध नहीं है। आधिकारिक जानकारी: navodaya.gov.in',
      'Question papers © Navodaya Vidyalaya Samiti. This site is for free practice only and is not affiliated with NVS. Official site: navodaya.gov.in'
    ) + '</p></div></div>';
    $app.innerHTML = h;
    document.title = t('नवोदय (JNVST) कक्षा 6 मॉक टेस्ट – पिछले वर्षों के असली प्रश्न-पत्र', 'Navodaya (JNVST) Class 6 Mock Tests – Real Previous Year Papers');
  }

  /* ---------- COVER ---------- */
  function cover(p) {
    view = 'cover'; curPaper = p;
    var n = qList(p).length, name = get('name', ''), roll = get('roll', null);
    if (!roll) { roll = String(Math.floor(10000000 + Math.random() * 89999999)); set('roll', roll); }
    var secRows = '';
    p.sections.forEach(function (s) {
      var l = qList({ sections: [s] });
      secRows += '<tr><td>' + esc(fld(s, 'name')) + '</td><td>' + esc(fld(s, 'title')) + '</td><td>' + l[0].q.n + (hi() ? ' से ' : ' to ') + l[l.length - 1].q.n + '</td><td>' + l.length + '</td><td>' + marks(l.length) + '</td></tr>';
    });
    var yrNum = p.title.replace(/\D/g, '');
    var h = '<div class="sheet cover">' +
      '<div class="cover-bar"><a class="btn small" href="#/">◀ ' + t('सभी पेपर', 'All papers') + '</a>' + langSwitcherHtml() + '</div>' +
      '<div class="top"><div><small>' + t('परीक्षण पुस्तिका क्र.', 'Test Booklet No.') + '</small><br><span class="box">' + roll.slice(0, 7) + '</span></div>' +
      '<div class="tb">' + t('परीक्षण पुस्तिका', 'TEST BOOKLET') + '<br><span class="box">' + esc(fld(p, 'booklet')) + '</span></div>' +
      '<div class="codebox">' + t('परीक्षण पुस्तिका कोड', 'Test Booklet Code') + '<b>' + esc(p.code) + '</b>' + t('हिन्दी', 'ENGLISH') + '</div></div>' +
      '<h2>' + t('जवाहर नवोदय विद्यालय चयन परीक्षा – ' + yrNum, 'JAWAHAR NAVODAYA VIDYALAYA SELECTION TEST – ' + yrNum) + '</h2>' +
      '<p class="sub">' + t('कक्षा VI · परीक्षा तिथि: ', 'Class VI · Exam held on ') + esc(fld(p, 'date')) + '</p>' +
      '<div class="cand"><label for="nm">' + t('परीक्षार्थी का नाम :', 'Name of the Candidate :') + '</label><input id="nm" type="text" maxlength="40" autocomplete="name" value="' + esc(name) + '" placeholder="' + t('अपना नाम लिखिए', 'Enter your name') + '"></div>' +
      '<div class="cand"><label>' + t('रोल नम्बर :', 'Roll Number :') + '</label><span class="box">' + roll + '</span></div>' +
      '<div class="tm"><span>' + t('समय : ' + (p.minutes === 120 ? '2 घण्टे' : '1 घण्टा'), 'Time : ' + (p.minutes === 120 ? '2 Hours' : '1 Hour')) + '</span><span>' + t('अधिकतम अंक : ', 'Maximum Marks : ') + marks(n) + '</span></div>' +
      (p.matgen ? '<p class="note ui">' + t(
        '<b>ध्यान दें:</b> खण्ड II (अंकगणित)' + (p.langgen ? '' : ' और खण्ड III (भाषा)') + ' असली ' + esc(fld(p, 'title')) + ' पेपर के प्रश्न हैं। <b>खण्ड I (मानसिक योग्यता, प्रश्न 1–40) उस वर्ष के असली चित्र नहीं हैं</b> — ये उसी 10-भाग पैटर्न पर इस साइट के लिए बनाए गए नए अभ्यास प्रश्न हैं, ताकि पूरा 80 प्रश्न / 2 घण्टे का मॉक टेस्ट दिया जा सके।',
        '<b>Note:</b> Section II (Arithmetic) and Section III (Language) are from the real ' + esc(p.title) + ' paper. <b>Section I (Mental Ability, Q1–40)</b> uses newly generated practice figures following the exact 10-part pattern so you can take a full 80-question, 2-hour mock.'
      ) + '</p>' : '') +
      (p.langgen && hi() ? '<p class="note ui"><b>भाषा खण्ड सूचना:</b> इस पेपर की असली हिन्दी पुस्तिका का पाठ ऑनलाइन उपलब्ध न होने के कारण, <b>खण्ड III (भाषा परीक्षण, प्रश्न 61–80)</b> में JNVST पैटर्न पर लिखे गए नए हिन्दी अभ्यास गद्यांश दिए गए हैं।</p>' : '') +
      '<h3>' + t('परीक्षार्थियों के लिए सामान्य निर्देश', 'GENERAL INSTRUCTIONS FOR CANDIDATES') + '</h3><ol>' +
      (hi() ? (
        '<li>इस परीक्षण पुस्तिका में <b>' + n + ' प्रश्न</b> हैं। सभी प्रश्न अनिवार्य हैं तथा प्रत्येक प्रश्न के लिए समान अंक (<b>1.25 अंक</b>) हैं।</li>' +
        '<li>प्रत्येक प्रश्न के लिए चार संभावित उत्तर (A), (B), (C) और (D) दिए गए हैं, जिनमें से केवल <b>एक</b> उत्तर सही है। सही उत्तर के संगत वृत्त को काला करें। उदाहरण – यदि प्रश्न सं. 37 का उत्तर (C) है: <b>37.</b><span class="omr-eg"><i>A</i><i>B</i><i class="f">C</i><i>D</i></span></li>' +
        '<li>परीक्षा की कुल अवधि बिना किसी अवकाश के <b>' + (p.minutes === 120 ? '2 घण्टे' : '1 घण्टा') + '</b> होगी। पुस्तिका खोलते ही घड़ी शुरू हो जाएगी।</li>' +
        '<li>परीक्षा में निम्नलिखित खण्ड होंगे :<div class="tblwrap"><table><tr><th>खण्ड</th><th>परीक्षण का प्रकार</th><th>प्रश्न संख्या</th><th>प्रश्न</th><th>अंक</th></tr>' + secRows +
        '<tr><th colspan="3">कुल योग</th><th>' + n + '</th><th>' + marks(n) + '</th></tr></table></div></li>' +
        '<li>प्रत्येक खण्ड में क्वालिफाई करना आवश्यक है, इसलिए सारा समय किसी एक खण्ड पर न लगाएँ। खण्ड–I में <b>दस भाग</b> हैं और प्रत्येक भाग के अलग निर्देश हैं — उन्हें ध्यान से पढ़ें।</li>' +
        '<li>असली परीक्षा में OMR उत्तर-पत्रिका पर केवल नीले/काले बॉल-पॉइंट पेन का उपयोग होता है और <b>एक बार उत्तर भरने के बाद बदलाव की अनुमति नहीं होती</b>। यही नियम अपनाने के लिए नीचे "सख्त OMR मोड" चुनें।</li>' +
        '<li>कच्चा कार्य अलग काग़ज़ पर या टेस्ट में दिए गए <b>रफ़ कार्य</b> पैड पर करें।</li>' +
        '<li>प्रत्येक 30 मिनट पर घंटी बजेगी।</li>' +
        '<li>किसी भी प्रकार की <b>ऋणात्मक मार्किंग नहीं</b> है। हर प्रश्न का उत्तर दें।</li>' +
        '<li>समय पूरा होने पर पेपर अपने आप जमा हो जाएगा और तुरंत आपका परिणाम व सही उत्तर दिखेंगे।</li>'
      ) : (
        '<li>This Test Booklet has <b>' + n + ' questions</b> in three Sections. All questions are compulsory and carry equal marks (<b>1.25 marks</b> each).</li>' +
        '<li>Each question has four probable answers marked (A), (B), (C) and (D). Only <b>one</b> of them is correct. Darken the circle of the correct answer. Example – if the answer to Question No. 37 is (C): <b>37.</b><span class="omr-eg"><i>A</i><i>B</i><i class="f">C</i><i>D</i></span></li>' +
        '<li>The total time for the test is <b>' + (p.minutes === 120 ? '2 hours' : '1 hour') + '</b> without any break. The clock starts as soon as you open the booklet.</li>' +
        '<li>The test has the following Sections :<div class="tblwrap"><table><tr><th>Section</th><th>Name of Test</th><th>Question Nos.</th><th>Questions</th><th>Marks</th></tr>' + secRows +
        '<tr><th colspan="3">Total</th><th>' + n + '</th><th>' + marks(n) + '</th></tr></table></div></li>' +
        '<li>A candidate has to qualify in each Section separately, so do not spend all your time on one Section. Section I has <b>ten Parts</b> with separate directions for each Part – read them carefully.</li>' +
        '<li>In the real examination only a blue/black ball-point pen is used on the OMR Answer Sheet and <b>no change of answer is allowed</b>. Tick “Strict OMR” below if you want the same rule here.</li>' +
        '<li>Do rough work on a separate paper or use the <b>Rough Work</b> pad given in the test.</li>' +
        '<li>A bell will ring after every 30 minutes.</li>' +
        '<li>There is <b>no negative marking</b>. Attempt every question.</li>' +
        '<li>When the time is over the paper is submitted automatically and your result with correct answers is shown.</li>'
      )) + '</ol>' +
      '<div class="start no-print"><label><input type="checkbox" id="strict"><span><b>' + t('सख्त OMR मोड', 'Strict OMR mode') + '</b> – ' + t('एक बार गोला भर दिया तो बदला नहीं जा सकता (असली परीक्षा जैसा)', 'once a circle is darkened it cannot be changed (like the real exam)') + '</span></label>' +
      '<label><input type="checkbox" id="agree"><span>' + t('मैंने सभी सामान्य निर्देश पढ़ लिए हैं और मैं परीक्षा शुरू करने के लिए तैयार हूँ।', 'I have read all the instructions and am ready to begin the test.') + '</span></label>' +
      '<div class="row"><a class="btn" href="#/">◀ ' + t('सभी पेपर', 'All papers') + '</a><button type="button" class="btn primary" data-act="start" disabled id="go">' + t('पुस्तिका खोलें और परीक्षा शुरू करें', 'Open Booklet & Start Test') + '</button></div></div></div>';
    $app.innerHTML = h;
    document.title = fld(p, 'title') + ' – ' + t('परीक्षण पुस्तिका', 'Test Booklet');
    var ag = document.getElementById('agree'), go = document.getElementById('go');
    ag.onchange = function () { go.disabled = !ag.checked; };
    document.getElementById('nm').onchange = function () { set('name', this.value.trim()); };
    window.scrollTo(0, 0);
  }

  /* ---------- EXAM ---------- */
  function startExam(p, resume) {
    var saved = resume ? get('run:' + p.id, null) : null;
    S = { p: p, pages: buildPages(p), list: qList(p), ans: saved ? saved.ans : {}, left: saved ? saved.left : p.minutes * 60, page: saved ? saved.page : 0, strict: saved ? !!saved.strict : !!(document.getElementById('strict') || {}).checked, total: p.minutes * 60 };
    S.deadline = Date.now() + S.left * 1000;
    S.bell = Math.floor((S.total - S.left) / 1800);
    focusActiveQ = null;
    save();
    examView();
  }
  function save() { if (S) set('run:' + S.p.id, { ans: S.ans, left: S.left, page: S.page, strict: S.strict }); }
  function answered() { var c = 0; for (var k in S.ans) if (S.ans[k]) c++; return c; }
  function omrHtml() {
    var h = '<div class="omr"><h3>' + t('ओ० एम० आर० उत्तर-पत्रिका', 'OMR ANSWER SHEET') + '</h3><p class="sm">' + esc(fld(S.p, 'booklet')) + ' · ' + t('कोड ', 'Code ') + esc(S.p.code) + (S.strict ? t(' · सख्त मोड', ' · Strict mode') : '') + '</p>';
    S.p.sections.forEach(function (sec) {
      h += '<h4>' + esc(fld(sec, 'name')) + ' : ' + esc(fld(sec, 'title')) + '</h4><div class="rows">';
      qList({ sections: [sec] }).forEach(function (x) {
        var n = x.q.n;
        h += '<div class="r" data-r="' + n + '"><button type="button" class="n" data-act="goto" data-q="' + n + '" aria-label="' + t('प्रश्न ' + n + ' पर जाएँ', 'Go to question ' + n) + '">' + n + '</button>';
        L.forEach(function (o) { h += '<button type="button" class="b' + (S.ans[n] === o ? ' on' : '') + '" data-act="ans" data-q="' + n + '" data-o="' + o + '" aria-label="' + t('प्र.' + n + ' ' + o, 'Q' + n + ' ' + o) + '">' + o + '</button>'; });
        h += '</div>';
      });
      h += '</div>';
    });
    return h + '<div class="stat"><span>' + t('भरे गए:', 'Darkened:') + ' <b class="cnt">' + answered() + '</b> / ' + S.list.length + '</span><span>' + t('प्रश्न पर जाने के लिए संख्या दबाएँ', 'Tap a number to open that question') + '</span></div></div>';
  }
  function qRangeLabel(pg, activeQ) {
    if (activeQ) return t('प्र. ' + activeQ, 'Q' + activeQ);
    return t('प्र. ' + pg.qs[0].n + '–' + pg.qs[pg.qs.length - 1].n, 'Q' + pg.qs[0].n + '–' + pg.qs[pg.qs.length - 1].n);
  }
  function examView() {
    view = 'exam'; curPaper = S.p;
    S.pages = buildPages(S.p);
    var opts = S.pages.map(function (pg, i) {
      return '<option value="' + i + '">' + t('पृष्ठ ', 'Page ') + pg.no + ' · ' + esc(pg.label) + ' (' + t('प्र.', 'Q') + pg.qs[0].n + '–' + pg.qs[pg.qs.length - 1].n + ')</option>';
    }).join('');
    var curPg = S.pages[Math.max(0, Math.min(S.pages.length - 1, S.page))];
    $app.innerHTML = '<div class="bar"><span class="ttl">' + esc(fld(S.p, 'title')) + ' · ' + esc(fld(S.p, 'booklet')) + ' – ' + esc(S.p.code) + '</span>' +
      '<span class="qind" id="qind">' + qRangeLabel(curPg, focusActiveQ) + '</span>' +
      '<span class="timer" id="timer" aria-label="' + t('शेष समय', 'Time left') + '">' + mmss(S.left) + '</span>' +
      '<button type="button" class="btn only-narrow" data-act="omr">OMR <b class="cnt">' + answered() + '</b>/' + S.list.length + '</button>' +
      '<button type="button" class="btn" data-act="rough">' + t('रफ़', 'Rough') + '</button>' +
      langSwitcherHtml() +
      '<button type="button" class="btn sub" data-act="submit">' + t('जमा करें', 'Submit') + '</button></div>' +
      '<div class="layout"><div class="main"><div class="sheet" id="sheet"></div></div><aside class="side" id="side">' + omrHtml() + '</aside></div>' +
      '<div class="nav"><button type="button" class="btn" data-act="prev">◀ ' + t('पिछला', 'Prev') + '</button><select id="pgsel" aria-label="' + t('पृष्ठ चुनें', 'Go to page') + '">' + opts + '</select><button type="button" class="btn" data-act="next">' + t('अगला', 'Next') + ' ▶</button></div>';
    document.getElementById('pgsel').onchange = function () { focusActiveQ = null; showPage(+this.value); };
    document.title = mmss(S.left) + ' · ' + fld(S.p, 'title');
    showPage(S.page, true, focusActiveQ);
    clearInterval(tick); tick = setInterval(onTick, 1000);
  }
  function showPage(i, quiet, focusQ) {
    i = Math.max(0, Math.min(S.pages.length - 1, i));
    S.page = i;
    var sh = document.getElementById('sheet'), pg = S.pages[i];
    sh.innerHTML = renderPage(S.p, pg, S.ans, false);
    sh.className = 'sheet'; void sh.offsetWidth; if (!quiet) sh.className = 'sheet turn';
    document.getElementById('pgsel').value = i;
    var qi = document.getElementById('qind');
    if (qi) qi.textContent = qRangeLabel(pg, focusQ || null);
    all('.omr .r').forEach(function (r) { var n = +r.getAttribute('data-r'); r.className = 'r' + (n >= pg.qs[0].n && n <= pg.qs[pg.qs.length - 1].n ? ' cur' : ''); });
    var b = all('.nav [data-act="prev"],.nav [data-act="next"]');
    b[0].disabled = i === 0; b[1].textContent = i === S.pages.length - 1 ? t('समाप्त ✔', 'Finish ✔') : t('अगला ▶', 'Next ▶');
    if (focusQ) { var el = document.getElementById('q' + focusQ); if (el && el.scrollIntoView) el.scrollIntoView({ block: 'center' }); }
    else if (!quiet) window.scrollTo(0, 0);
    save();
  }
  function setAns(n, o) {
    if (!S || view !== 'exam') return;
    var cur = S.ans[n];
    if (S.strict && cur) { toast(t('सख्त OMR: एक बार भरा हुआ गोला बदला नहीं जा सकता।', 'Strict OMR: once filled, a circle cannot be changed.')); return; }
    S.ans[n] = cur === o ? null : o;
    focusActiveQ = n;
    var qi = document.getElementById('qind');
    if (qi) qi.textContent = t('प्र. ' + n, 'Q' + n);
    var v = S.ans[n];
    all('[data-q="' + n + '"][data-o]').forEach(function (el) {
      var on = el.getAttribute('data-o') === v;
      if (el.tagName === 'LI') el.className = on ? 'sel' : '';
      else el.className = 'b' + (on ? ' on' : '');
    });
    all('.cnt').forEach(function (el) { el.textContent = answered(); });
    save();
  }
  function gotoQ(n) {
    focusActiveQ = n;
    for (var i = 0; i < S.pages.length; i++) {
      var q = S.pages[i].qs;
      if (n >= q[0].n && n <= q[q.length - 1].n) { closeDrawer(); showPage(i, true, n); return; }
    }
  }
  function onTick() {
    if (!S) return;
    S.left = Math.round((S.deadline - Date.now()) / 1000);
    var tEl = document.getElementById('timer');
    if (tEl) { tEl.textContent = mmss(S.left); tEl.className = 'timer' + (S.left <= 300 ? ' low' : ''); }
    document.title = mmss(S.left) + ' · ' + fld(S.p, 'title');
    var b = Math.floor((S.total - S.left) / 1800);
    if (b > S.bell && S.left > 0) {
      S.bell = b; beep();
      toast('🔔 ' + t('घंटी: ' + (b * 30) + ' मिनट पूरे · ' + Math.round(S.left / 60) + ' मिनट शेष', 'Bell: ' + (b * 30) + ' minutes over · ' + Math.round(S.left / 60) + ' minutes left'), 5000);
    }
    if (S.left % 5 === 0) save();
    if (S.left <= 0) { beep(); finish(true); }
  }
  function openDrawer() {
    var d = document.createElement('div'); d.className = 'drawer'; d.id = 'drawer';
    d.innerHTML = '<div class="drawer-panel"><div class="drawer-top"><button type="button" class="btn small" data-act="closeomr">✕ ' + t('बन्द करें', 'Close') + '</button></div>' + omrHtml() + '</div>';
    d.onclick = function (e) { if (e.target === d) closeDrawer(); };
    document.body.appendChild(d);
    var pg = S.pages[S.page];
    all('.r', d).forEach(function (r) { var n = +r.getAttribute('data-r'); if (n >= pg.qs[0].n && n <= pg.qs[pg.qs.length - 1].n) r.className = 'r cur'; });
    var c = d.querySelector('.r.cur'); if (c && c.scrollIntoView) c.scrollIntoView({ block: 'center' });
  }
  function closeDrawer() { var d = document.getElementById('drawer'); if (d) d.parentNode.removeChild(d); }
  function modal(html) {
    closeModal();
    var m = document.createElement('div'); m.className = 'modal'; m.id = 'modal'; m.innerHTML = '<div class="inner" role="dialog" aria-modal="true">' + html + '</div>';
    document.body.appendChild(m);
  }
  function closeModal() { var m = document.getElementById('modal'); if (m) m.parentNode.removeChild(m); }
  function askSubmit() {
    var a = answered(), n = S.list.length;
    modal('<h3>' + t('क्या टेस्ट जमा करें?', 'Submit the test?') + '</h3><p>' + t('भरे गए प्रश्न:', 'Darkened:') + ' <b>' + a + '</b> / ' + n + '<br>' + t('छोड़े गए प्रश्न:', 'Not attempted:') + ' <b>' + (n - a) + '</b><br>' + t('शेष समय:', 'Time left:') + ' <b>' + mmss(S.left) + '</b></p>' +
      (n - a ? '<p>' + t('कोई ऋणात्मक मार्किंग नहीं है — खाली प्रश्न भी भर दीजिए।', 'There is no negative marking — feel free to attempt the remaining questions.') + '</p>' : '') +
      '<div class="row"><button type="button" class="btn" data-act="closemodal">' + t('टेस्ट जारी रखें', 'Continue test') + '</button><button type="button" class="btn primary" data-act="finish">' + t('जमा करें और परिणाम देखें', 'Submit & see result') + '</button></div>');
  }
  function finish(auto) {
    if (!S) return;
    clearInterval(tick); closeModal(); closeDrawer(); closePad();
    var p = S.p, keyStr = (lang === 'hi' && p.key_hi) ? p.key_hi : p.key, res = { ans: S.ans, used: S.total - Math.max(0, S.left), when: Date.now(), auto: !!auto, lang: lang }, c = 0;
    S.list.forEach(function (x) { if (S.ans[x.q.n] && S.ans[x.q.n] === keyStr.charAt(x.q.n - 1)) c++; });
    set('last:' + p.id, res); set('run:' + p.id, null);
    var best = get('best:' + p.id, null), m = c * MARK;
    if (!best || m > parseFloat(best.m)) set('best:' + p.id, { m: marks(c), max: marks(S.list.length) });
    S = null; focusActiveQ = null;
    if (location.hash === '#/p/' + p.id + '/result') route(); else location.hash = '#/p/' + p.id + '/result';
    if (auto) toast(t('समय समाप्त — पेपर अपने आप जमा हो गया।', 'Time over — paper submitted automatically.'), 4000);
  }

  /* rough work pad */
  var pad = null;
  function openPad() {
    if (!pad) {
      pad = document.createElement('div'); pad.className = 'pad';
      pad.innerHTML = '<div class="phead"><span id="padttl"></span><button type="button" class="btn small" id="padclr"></button><button type="button" class="btn small" id="padcls"></button></div><canvas></canvas>';
      document.body.appendChild(pad);
      var cv = pad.querySelector('canvas'), cx = cv.getContext('2d'), down = false, r = window.devicePixelRatio || 1;
      cv.width = cv.clientWidth * r; cv.height = cv.clientHeight * r; cx.scale(r, r); cx.lineWidth = 2; cx.lineCap = 'round'; cx.strokeStyle = '#101b4a';
      var pos = function (e) { var b = cv.getBoundingClientRect(), pt = e.touches ? e.touches[0] : e; return [pt.clientX - b.left, pt.clientY - b.top]; };
      var st = function (e) { down = true; var q = pos(e); cx.beginPath(); cx.moveTo(q[0], q[1]); e.preventDefault(); };
      var mv = function (e) { if (!down) return; var q = pos(e); cx.lineTo(q[0], q[1]); cx.stroke(); e.preventDefault(); };
      var en = function () { down = false; };
      if (window.PointerEvent) { cv.addEventListener('pointerdown', st); cv.addEventListener('pointermove', mv); window.addEventListener('pointerup', en); }
      else { cv.addEventListener('mousedown', st); cv.addEventListener('mousemove', mv); window.addEventListener('mouseup', en); cv.addEventListener('touchstart', st, { passive: false }); cv.addEventListener('touchmove', mv, { passive: false }); cv.addEventListener('touchend', en); }
      pad.clear = function () { cx.clearRect(0, 0, cv.width, cv.height); };
    }
    document.getElementById('padttl').textContent = t('कच्चे कार्य के लिए स्थान', 'SPACE FOR ROUGH WORK');
    var bClr = document.getElementById('padclr'); bClr.textContent = t('साफ़ करें', 'Clear'); bClr.setAttribute('data-act', 'clearpad');
    var bCls = document.getElementById('padcls'); bCls.textContent = '✕ ' + t('पेपर पर लौटें', 'Back to paper'); bCls.setAttribute('data-act', 'closepad');
    pad.hidden = false;
  }
  function closePad() { if (pad) pad.hidden = true; }

  /* ---------- RESULT + REVIEW ---------- */
  function result(p) {
    view = 'result'; curPaper = p;
    var res = get('last:' + p.id, null);
    if (!res) { location.hash = '#/p/' + p.id; return; }
    var keyStr = resKey(p, res), rows = '', T = { n: 0, a: 0, c: 0 };
    var mismatchLang = p.langgen && res.lang && res.lang !== lang;
    p.sections.forEach(function (sec) {
      var l = qList({ sections: [sec] }), a = 0, c = 0;
      l.forEach(function (x) { var v = res.ans[x.q.n]; if (v) { a++; if (v === keyStr.charAt(x.q.n - 1)) c++; } });
      T.n += l.length; T.a += a; T.c += c;
      rows += '<tr><td>' + esc(fld(sec, 'short')) + '</td><td>' + l.length + '</td><td>' + a + '</td><td>' + c + '</td><td>' + (a - c) + '</td><td><b>' + marks(c) + '</b> / ' + marks(l.length) + '</td><td>' + Math.round(c * 100 / l.length) + '%</td></tr>';
    });
    var name = get('name', ''), kn = fld(p, 'keynote');
    $app.innerHTML = '<div class="sheet result">' +
      '<div class="cover-bar no-print"><a class="btn small" href="#/">◀ ' + t('सभी पेपर', 'All papers') + '</a>' + langSwitcherHtml() + '</div>' +
      '<h2>' + t('परिणाम', 'RESULT') + ' – ' + esc(fld(p, 'title')) + '</h2>' +
      '<p style="text-align:center;margin:0">' + esc(fld(p, 'booklet')) + ' · ' + t('कोड ', 'Code ') + esc(p.code) + ' · ' + esc(fld(p, 'date')) + (name ? '<br>' + t('परीक्षार्थी: ', 'Candidate: ') + '<b>' + esc(name) + '</b>' : '') + '</p>' +
      '<div class="score"><b>' + marks(T.c) + '</b>' + t(marks(T.n) + ' अंकों में से · ' + Math.round(T.c * 100 / T.n) + '%', 'out of ' + marks(T.n) + ' marks · ' + Math.round(T.c * 100 / T.n) + '%') + '</div>' +
      '<div class="tblwrap"><table><tr><th>' + t('खण्ड', 'Section') + '</th><th>' + t('प्रश्न', 'Qs') + '</th><th>' + t('प्रयास', 'Attempted') + '</th><th>' + t('सही', 'Correct') + '</th><th>' + t('ग़लत', 'Wrong') + '</th><th>' + t('अंक', 'Marks') + '</th><th>%</th></tr>' + rows +
      '<tr><th>' + t('कुल योग', 'Total') + '</th><th>' + T.n + '</th><th>' + T.a + '</th><th>' + T.c + '</th><th>' + (T.a - T.c) + '</th><th>' + marks(T.c) + ' / ' + marks(T.n) + '</th><th>' + Math.round(T.c * 100 / T.n) + '%</th></tr></table></div>' +
      '<p style="text-align:center">' + t('लिया गया समय: ', 'Time used: ') + '<b>' + mmss(res.used) + '</b>' + (res.auto ? t(' (समय समाप्त, स्वतः जमा)', ' (time over, auto-submitted)') : '') + ' · ' + t('छोड़े गए: ', 'Not attempted: ') + '<b>' + (T.n - T.a) + '</b></p>' +
      '<p style="font-size:13.5px">' + t(
        'असली परीक्षा में हर खण्ड में अलग से क्वालिफाई करना होता है और चयन ज़िले की मेरिट से होता है, इसलिए कोई निश्चित पास अंक नहीं होते। जिस खण्ड में प्रतिशत सबसे कम है, पहले उसका अभ्यास कीजिए।',
        'In the real exam you must qualify in each Section separately and selection depends on district merit, so there is no fixed pass mark. Practise the Section with your lowest percentage first.'
      ) + '</p>' +
      '<div class="row no-print"><a class="btn primary" href="#/p/' + p.id + '/review">' + t('उत्तरों की जाँच करें', 'Review answers') + '</a><a class="btn" href="#/p/' + p.id + '">' + t('फिर से हल करें', 'Attempt again') + '</a><a class="btn" href="#/">' + t('सभी पेपर', 'All papers') + '</a><button type="button" class="btn" data-act="print">' + t('प्रिंट करें', 'Print') + '</button></div>' +
      (mismatchLang ? '<p class="qnote">' + t('नोट: आपने यह टेस्ट अंग्रेज़ी माध्यम में दिया था, इसलिए खण्ड–III के अंक अंग्रेज़ी उत्तर कुंजी के अनुसार हैं।', 'Note: You attempted this test in Hindi medium, so Section III marks use the Hindi practice key.') + '</p>' : '') +
      (kn ? '<p class="keynote"><b>' + t('उत्तर कुंजी:', 'Answer key:') + '</b> ' + esc(kn) + '</p>' : '') + '</div>';
    document.title = t('परिणाम', 'Result') + ' · ' + fld(p, 'title');
    window.scrollTo(0, 0);
  }
  function review(p) {
    view = 'review'; curPaper = p;
    var res = get('last:' + p.id, null) || { ans: {} };
    var keyStr = resKey(p, res);
    var forcePassLang = (p.langgen && res.lang) ? res.lang : null;
    var h = '<div class="bar"><span class="ttl" style="display:block">' + t('उत्तर समीक्षा', 'Answer review') + ' · ' + esc(fld(p, 'title')) + '</span>' +
      langSwitcherHtml() +
      '<a class="btn" href="#/p/' + p.id + '/result">' + t('परिणाम', 'Result') + '</a><a class="btn sub" href="#/">' + t('होम', 'Home') + '</a></div>' +
      '<div class="filter no-print"><button type="button" class="btn small primary" data-act="flt" data-f="">' + t('सभी', 'All') + '</button>' +
      '<button type="button" class="btn small" data-act="flt" data-f="bad">' + t('ग़लत', 'Wrong') + '</button>' +
      '<button type="button" class="btn small" data-act="flt" data-f="skip">' + t('छोड़े गए', 'Not attempted') + '</button>' +
      '<button type="button" class="btn small" data-act="flt" data-f="ok">' + t('सही', 'Correct') + '</button></div><div class="review" id="rev">';
    buildPages(p, forcePassLang).forEach(function (pg) { h += '<div class="sheet">' + renderPage(p, pg, res.ans, true, keyStr) + '</div>'; });
    $app.innerHTML = h + '</div>';
    document.title = t('उत्तर समीक्षा', 'Review') + ' · ' + fld(p, 'title');
    window.scrollTo(0, 0);
  }
  function filter(f, btn) {
    all('.filter .btn').forEach(function (b) { b.className = 'btn small' + (b === btn ? ' primary' : ''); });
    all('#rev .q').forEach(function (q) { q.hidden = !!f && q.getAttribute('data-st') !== f; });
    all('#rev .sheet').forEach(function (s) { s.hidden = !!f && !s.querySelector('.q:not([hidden])'); });
    all('#rev .passage, #rev .dir, #rev .cap, #rev .rough').forEach(function (e) { e.hidden = !!f; });
  }
  function switchLang(next) {
    if (next !== 'hi' && next !== 'en') return;
    if (next === lang) return;
    lang = next;
    set('lang', lang);
    document.documentElement.lang = lang;
    if (view === 'home') return home();
    if (view === 'cover' && curPaper) return cover(curPaper);
    if (view === 'exam' && S) return examView();
    if (view === 'result' && curPaper) return result(curPaper);
    if (view === 'review' && curPaper) return review(curPaper);
    route();
  }

  /* ---------- events + router ---------- */
  document.addEventListener('click', function (e) {
    var el = up(e.target, 'data-act'); if (!el) return;
    var act = el.getAttribute('data-act');
    if (act === 'lang') switchLang(el.getAttribute('data-lang'));
    else if (act === 'ans') { if (!el.disabled) setAns(+el.getAttribute('data-q'), el.getAttribute('data-o')); }
    else if (act === 'goto') gotoQ(+el.getAttribute('data-q'));
    else if (act === 'prev') { focusActiveQ = null; showPage(S.page - 1); }
    else if (act === 'next') { if (S.page === S.pages.length - 1) askSubmit(); else { focusActiveQ = null; showPage(S.page + 1); } }
    else if (act === 'omr') openDrawer();
    else if (act === 'closeomr') closeDrawer();
    else if (act === 'submit') askSubmit();
    else if (act === 'closemodal') closeModal();
    else if (act === 'finish') finish(false);
    else if (act === 'rough') openPad();
    else if (act === 'closepad') closePad();
    else if (act === 'clearpad') pad.clear();
    else if (act === 'print') window.print();
    else if (act === 'flt') filter(el.getAttribute('data-f'), el);
    else if (act === 'start') {
      var id = location.hash.split('/')[2];
      set('run:' + id, null);
      var nm = document.getElementById('nm'); if (nm) set('name', nm.value.trim());
      startExam(PAPERS[id], false);
      try { history.replaceState(null, '', '#/p/' + id + '/exam'); } catch (er) { location.hash = '#/p/' + id + '/exam'; }
      window.scrollTo(0, 0);
    }
    else if (act === 'restart') { closeModal(); set('run:' + el.getAttribute('data-id'), null); location.hash = '#/p/' + el.getAttribute('data-id'); }
  });
  document.addEventListener('keydown', function (e) {
    if (view !== 'exam' || !S || /INPUT|SELECT|TEXTAREA/.test(e.target.tagName)) return;
    if (e.key === 'ArrowRight' && S.page < S.pages.length - 1) { focusActiveQ = null; showPage(S.page + 1); }
    else if (e.key === 'ArrowLeft') { focusActiveQ = null; showPage(S.page - 1); }
    else if (e.key === 'Escape') { closeDrawer(); closeModal(); closePad(); }
  });
  document.addEventListener('visibilitychange', function () { if (S) { onTick(); save(); } });
  window.addEventListener('beforeunload', function () { if (S) save(); });

  function route() {
    var parts = location.hash.replace(/^#\/?/, '').split('/');
    closeDrawer(); closeModal(); closePad();
    if (parts[0] !== 'p' || !meta(parts[1])) { leaveExam(); return home(); }
    var id = parts[1], sub = parts[2] || '';
    if (sub !== 'exam') leaveExam();
    loadPaper(id, function (p) {
      if (sub === 'exam') {
        if (S && S.p.id === id) return examView();
        if (get('run:' + id, null)) return startExam(p, true);
        location.hash = '#/p/' + id; return;
      }
      if (sub === 'result') return result(p);
      if (sub === 'review') return review(p);
      cover(p);
      if (get('run:' + id, null)) modal('<h3>' + t('अधूरा टेस्ट मिला', 'Unfinished test found') + '</h3><p>' + t('इस पेपर का एक टेस्ट बीच में छूटा हुआ है। वहीं से आगे बढ़ना है?', 'You have an unfinished test for this paper. Resume from where you left off?') + '</p><div class="row"><button type="button" class="btn" data-act="restart" data-id="' + id + '">' + t('नया शुरू करें', 'Start fresh') + '</button><a class="btn primary" href="#/p/' + id + '/exam">' + t('जारी रखें ▶', 'Resume ▶') + '</a></div>');
    });
  }
  function leaveExam() { if (S) { save(); S = null; } clearInterval(tick); }
  window.addEventListener('hashchange', route);
  route();
})();
