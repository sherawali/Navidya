/* JNVST mock tests – plain ES5, no dependencies, works from any static host (GitHub Pages) */
(function () {
  'use strict';
  var V = 2;
  var $app = document.getElementById('app');
  var $toast = document.getElementById('toast');
  var INDEX = window.JNV_INDEX || [];
  var PAPERS = {};
  var L = ['A', 'B', 'C', 'D'];
  var MARK = 1.25;
  var S = null;          // running exam state
  var tick = null;       // timer handle
  var view = '';         // current view name

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
  var MEM = {};          // fallback when localStorage is blocked (private mode etc.)
  function get(k, d) { var v; try { v = localStorage.getItem('jnv:' + k); } catch (e) { v = MEM[k]; } if (v == null) v = MEM[k]; try { return v == null ? d : JSON.parse(v); } catch (e2) { return d; } }
  function set(k, v) { if (v === null) delete MEM[k]; else MEM[k] = JSON.stringify(v); try { if (v === null) localStorage.removeItem('jnv:' + k); else localStorage.setItem('jnv:' + k, MEM[k]); } catch (e) { } }
  function up(el, attr) { while (el && el !== document) { if (el.getAttribute && el.getAttribute(attr) != null) return el; el = el.parentNode; } return null; }
  function all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function toast(msg, ms) { $toast.textContent = msg; $toast.className = 'show'; clearTimeout(toast.t); toast.t = setTimeout(function () { $toast.className = ''; }, ms || 2600); }
  function mmss(sec) { sec = Math.max(0, Math.round(sec)); var h = Math.floor(sec / 3600), m = Math.floor(sec % 3600 / 60), s = sec % 60; return (h ? h + ':' : '') + (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s; }
  function marks(n) { var v = n * MARK; return v % 1 ? v.toFixed(2) : String(v); }
  function meta(id) { for (var i = 0; i < INDEX.length; i++) if (INDEX[i].id === id) return INDEX[i]; return null; }
  function beep() {
    try {
      var AC = window.AudioContext || window.webkitAudioContext; if (!AC) return;
      var ac = beep.ac || (beep.ac = new AC()), t = ac.currentTime;
      for (var i = 0; i < 3; i++) {
        var o = ac.createOscillator(), g = ac.createGain();
        o.frequency.value = 880; o.connect(g); g.connect(ac.destination);
        g.gain.setValueAtTime(0.0001, t + i * 0.45); g.gain.exponentialRampToValueAtTime(0.3, t + i * 0.45 + 0.02); g.gain.exponentialRampToValueAtTime(0.0001, t + i * 0.45 + 0.35);
        o.start(t + i * 0.45); o.stop(t + i * 0.45 + 0.4);
      }
    } catch (e) { }
  }

  /* ---------- data ---------- */
  window.JNV_LOAD = function (p) { PAPERS[p.id] = p; };
  function loadPaper(id, cb) {
    if (PAPERS[id]) return cb(PAPERS[id]);
    var s = document.createElement('script');
    s.src = 'papers/' + id + '/paper.js?v=' + V;
    s.onload = function () { PAPERS[id] ? cb(PAPERS[id]) : fail(); };
    s.onerror = fail;
    function fail() { $app.innerHTML = '<div class="sheet ui"><p>Paper load nahi ho paya. Internet check karke dobara try kijiye.</p><p><a class="btn" href="#/">Home</a></p></div>'; }
    document.head.appendChild(s);
  }
  function qList(p) {
    var out = [];
    p.sections.forEach(function (sec) {
      (sec.parts || []).forEach(function (pt) { pt.qs.forEach(function (q) { out.push({ q: q, sec: sec }); }); });
      (sec.qs || []).forEach(function (q) { out.push({ q: q, sec: sec }); });
      (sec.passages || []).forEach(function (ps) { ps.qs.forEach(function (q) { out.push({ q: q, sec: sec }); }); });
    });
    return out;
  }
  /* booklet pages, numbered like the real booklet (cover = page 1) */
  function buildPages(p) {
    var pages = [], no = p.full ? 2 : 12;
    p.sections.forEach(function (sec) {
      if (sec.parts) sec.parts.forEach(function (pt, i) {
        pages.push({ no: no++, sec: sec, head: i === 0, part: pt, qs: pt.qs, label: pt.part.replace('–', '-') });
      });
      if (sec.qs) for (var i = 0; i < sec.qs.length; i += 10) {
        pages.push({ no: no++, sec: sec, head: i === 0, qs: sec.qs.slice(i, i + 10), cols: true, label: sec.short });
      }
      if (sec.passages) for (var j = 0; j < sec.passages.length; j += 2) {
        var ps = sec.passages.slice(j, j + 2), qs = [];
        ps.forEach(function (x) { qs = qs.concat(x.qs); });
        pages.push({ no: no++, sec: sec, head: j === 0, passages: ps, pidx: j, qs: qs, cols: true, label: sec.short });
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
      h += '<button type="button" class="' + c + '" data-act="ans" data-q="' + n + '" data-o="' + o + '" aria-label="Question ' + n + ' option ' + o + '"' + (key ? ' disabled' : '') + '>' + o + '</button>';
    });
    return h + '</div>';
  }
  function verdict(ans, key) {
    if (!key || key === '-') return '';
    if (!ans) return '<div class="verdict v-skip">Not attempted · Correct answer: (' + key + ')</div>';
    if (ans === key) return '<div class="verdict v-ok">✔ Correct · (' + key + ')</div>';
    return '<div class="verdict v-bad">✘ Your answer: (' + ans + ') · Correct answer: (' + key + ')</div>';
  }
  function renderQ(p, q, ans, key) {
    var h, st = key ? (!ans ? 'skip' : ans === key ? 'ok' : 'bad') : '';
    if (q.strip || q.a) {
      var im = function (f, w, hh, alt) { return '<img src="papers/' + p.id + '/' + f + '" width="' + w + '" height="' + hh + '" loading="lazy" decoding="async" alt="Question ' + q.n + ': ' + alt + '">'; };
      h = '<div class="q fig" id="q' + q.n + '" data-st="' + st + '"><div class="qn">' + q.n + '.</div><div class="qb">' +
        (q.a ? '<div class="figrow" style="--r:' + Math.min(1, q.aw / q.bw).toFixed(3) + '"><div class="fq" style="flex:' + q.aw + ' 1 0%">' + im(q.a, q.aw, q.ah, 'question figure') + '</div><div class="fa" style="flex:' + q.bw + ' 1 0%">' + im(q.b, q.bw, q.bh, 'answer figures (A), (B), (C), (D)') + '</div></div>'
          : '<div class="figone">' + im(q.strip, q.w, q.h, 'figures (A), (B), (C), (D)') + '</div>') +
        bubbles(q.n, ans, key) + verdict(ans, key) + '</div></div>';
      return h;
    }
    var long = false;
    q.o.forEach(function (o) { if (o.replace(/\{[^}]*\}/g, 'xx').length > 20) long = true; });
    h = '<div class="q" id="q' + q.n + '" data-st="' + st + '"><div class="qn">' + q.n + '.</div><div class="qb"><p class="qt">' + fmt(q.q) + '</p>';
    if (q.img) h += '<img class="qimg" src="papers/' + p.id + '/' + q.img + '" width="' + q.w + '" height="' + q.h + '" loading="lazy" decoding="async" alt="Figure for question ' + q.n + '">';
    h += '<ul class="opts' + (long ? ' long' : '') + '">';
    q.o.forEach(function (o, i) {
      var c = '';
      if (key) { if (L[i] === key) c = 'right'; else if (L[i] === ans) c = 'wrong'; }
      else if (L[i] === ans) c = 'sel';
      h += '<li class="' + c + '" data-act="ans" data-q="' + q.n + '" data-o="' + L[i] + '"><span class="lb">(' + L[i] + ')</span><span>' + fmt(o) + '</span></li>';
    });
    h += '</ul>' + bubbles(q.n, ans, key, 'left') + verdict(ans, key) + '</div></div>';
    return h;
  }
  function renderPage(p, pg, ansMap, keyed) {
    var odd = pg.no % 2, code = p.booklet + ' – ' + p.code;
    var h = '<div class="runhead">' + (odd ? '<span></span><span class="pg">( ' + pg.no + ' )</span><span>' + esc(code) + '</span>' : '<span>' + esc(code) + '</span><span class="pg">( ' + pg.no + ' )</span><span></span>') + '</div>';
    if (pg.head) h += '<div class="sec-h">' + pg.sec.name + '<br>' + pg.sec.title + '</div>';
    if (pg.part) {
      h += '<div class="sec-h">' + pg.part.part + '</div><p class="dir"><b>Directions :</b> ' + fmt(pg.part.dir) + '</p>';
      if (pg.part.cap) { var f = pg.part.qs[0]; h += '<div class="cap"><span style="flex:' + (f.aw || 1) + ' 1 0%">' + pg.part.cap + '</span><span style="flex:' + (f.bw || 3) + ' 1 0%">Answer Figures</span></div>'; }
    } else if (pg.head) h += '<p class="dir"><b>Directions :</b> ' + fmt(pg.sec.dir) + '</p>';
    function qs(list) { return list.map(function (q) { var x = renderQ(p, q, ansMap[q.n], keyed ? p.key.charAt(q.n - 1) : null); if (keyed && p.notes && p.notes[q.n]) x = x.replace(/<\/div><\/div>$/, '<div class="qnote">ℹ ' + esc(p.notes[q.n]) + '</div></div></div>'); return x; }).join(''); }
    if (pg.passages) {
      h += '<div class="cols">';
      pg.passages.forEach(function (ps, i) {
        h += '<div class="passage"><h4>Passage – ' + (pg.pidx + i + 1) + '</h4><p>' + fmt(ps.text).replace(/<br>/g, '</p><p>') + '</p></div>' + qs(ps.qs);
      });
      h += '</div>';
    } else h += '<div class="' + (pg.cols ? 'cols' : '') + '">' + qs(pg.qs) + '</div>';
    if (pg.cols && !pg.passages) h += '<div class="rough">SPACE FOR ROUGH WORK</div>';
    return h;
  }

  /* ---------- HOME ---------- */
  function home() {
    view = 'home';
    var h = '<div class="home"><div class="masthead"><p style="font-weight:700;letter-spacing:2px">TEST BOOKLET</p>' +
      '<h1>Jawahar Navodaya Vidyalaya Selection Test</h1><p>Class VI · Mock Tests from <b>Real Previous Year Papers</b></p>' +
      '<span class="tag">Time : 2 Hours &nbsp;|&nbsp; Maximum Marks : 100</span></div>' +
      '<div class="note"><b>Dhyan dein:</b> Ye mock asli purane papers se bane hain, isliye inka pattern purana hai (Mental Ability 40 + Arithmetic 20 + Language 20). ' +
      '28 Nov 2026 ki JNVST 2027 pariksha me naya pattern hai (Mental Ability 20 + EVS 20 + Arithmetic 20 + Language 20) — Arithmetic, Language aur Mental Ability ki practice ke liye ye papers poori tarah kaam ke hain.</div>' +
      '<div class="grid">';
    INDEX.forEach(function (m) {
      var best = get('best:' + m.id, null), run = get('run:' + m.id, null);
      h += '<div class="card"><span class="code">' + esc(m.code) + '</span><h2>' + esc(m.title) + '</h2>' +
        '<div class="meta">Exam date: ' + esc(m.date) + '<br>Booklet: ' + esc(m.booklet) + ' · Code ' + esc(m.code) + '<br>' +
        (m.full ? '<span class="badge">FULL PAPER</span><br>80 questions · 100 marks · 2 hours<br>Real figures + official answer key'
          : '<span class="badge part">SECTION II + III</span><br>' + m.questions + ' questions (Q41–80) · ' + marks(m.questions) + ' marks · 1 hour<br>Arithmetic + Language · Mental Ability figures abhi jode nahi gaye') + '</div>' +
        (best ? '<div class="best">Best score: <b>' + best.m + ' / ' + best.max + '</b></div>' : '') +
        '<a class="btn primary" href="#/p/' + m.id + (run ? '/exam' : '') + '">' + (run ? 'Resume test ▶' : 'Open booklet ▶') + '</a></div>';
    });
    h += '</div><div class="foot"><p><b>Kaise use karein:</b> Booklet kholiye → instructions padhiye → test start kijiye. Har sawal ke niche OMR circle (A/B/C/D) bhariye, upar se OMR sheet kabhi bhi dekh sakte hain. ' +
      'Har 30 minute par bell bajegi. Samay khatm hote hi paper apne aap submit ho jayega aur turant result + sahi uttar dikhenge. Aapke answers sirf aapke phone/computer me save hote hain.</p>' +
      '<p>Question papers © Navodaya Vidyalaya Samiti. Ye site sirf free practice ke liye hai, NVS se judi nahi hai. Official jaankari: navodaya.gov.in</p></div></div>';
    $app.innerHTML = h;
    document.title = 'Navodaya (JNVST) Class 6 Mock Tests – Real Previous Year Papers';
  }

  /* ---------- COVER ---------- */
  function cover(p) {
    view = 'cover';
    var n = qList(p).length, name = get('name', ''), roll = get('roll', null);
    var om = p.omit && p.omit.length ? ' Q' + p.omit.join(', Q') + ' (chitra/option uplabdh nahi) is mock me shamil nahi ' + (p.omit.length > 1 ? 'hain' : 'hai') + ' — kul ' + n + ' sawal.' : '';
    if (!roll) { roll = String(Math.floor(10000000 + Math.random() * 89999999)); set('roll', roll); }
    var secRows = '';
    p.sections.forEach(function (s) {
      var l = qList({ sections: [s] });
      secRows += '<tr><td>' + s.name.replace('SECTION – ', 'Section ') + '</td><td>' + s.title.replace(' TEST', ' Test') + '</td><td>' + l[0].q.n + ' to ' + l[l.length - 1].q.n + '</td><td>' + l.length + '</td><td>' + marks(l.length) + '</td></tr>';
    });
    var h = '<div class="sheet cover"><div class="top"><div><small>Test Booklet No.</small><br><span class="box">' + roll.slice(0, 7) + '</span></div>' +
      '<div class="tb">TEST BOOKLET<br><span class="box">' + esc(p.booklet) + '</span></div>' +
      '<div class="codebox">Test Booklet Code<b>' + esc(p.code) + '</b>ENGLISH</div></div>' +
      '<h2>JAWAHAR NAVODAYA VIDYALAYA SELECTION TEST – ' + esc(p.title.replace(/\D/g, '')) + '</h2>' +
      '<p class="sub">Class VI · Exam held on ' + esc(p.date) + '</p>' +
      '<div class="cand"><label for="nm">Name of the Candidate :</label><input id="nm" type="text" maxlength="40" autocomplete="name" value="' + esc(name) + '" placeholder="Apna naam likhiye"></div>' +
      '<div class="cand"><label>Roll Number :</label><span class="box">' + roll + '</span></div>' +
      '<div class="tm"><span>Time : ' + (p.minutes === 120 ? '2 Hours' : '1 Hour') + '</span><span>Maximum Marks : ' + marks(n) + '</span></div>' +
      (p.full ? '' : '<p class="note ui"><b>Is paper me abhi Section II (Arithmetic) aur Section III (Language) hain — Q41 se Q80.</b> Section I (Mental Ability, Q1–40) ke figures abhi site par jode nahi gaye hain, isliye samay 1 ghanta aur poore ank ' + marks(n) + ' rakhe gaye hain.' + om + '</p>') +
      '<h3>GENERAL INSTRUCTIONS FOR CANDIDATES</h3><ol>' +
      '<li>This Test Booklet has <b>' + n + ' questions</b>' + (p.full ? ' in three Sections' : ' (Question Nos. 41 to 80)') + '. All questions are compulsory and carry equal marks (<b>1.25 marks</b> each).</li>' +
      '<li>Each question has four probable answers marked (A), (B), (C) and (D). Only <b>one</b> of them is correct. Darken the circle of the correct answer. Example – if the answer to Question No. 37 is (C): <b>37.</b><span class="omr-eg"><i>A</i><i>B</i><i class="f">C</i><i>D</i></span></li>' +
      '<li>The total time for the test is <b>' + (p.minutes === 120 ? '2 hours' : '1 hour') + '</b> without any break. The clock starts as soon as you open the booklet.</li>' +
      '<li>The test has the following Sections :<table><tr><th>Section</th><th>Name of Test</th><th>Question Nos.</th><th>Questions</th><th>Marks</th></tr>' + secRows +
      '<tr><th colspan="3">Total</th><th>' + n + '</th><th>' + marks(n) + '</th></tr></table></li>' +
      '<li>A candidate has to qualify in each Section separately, so do not spend all your time on one Section.' + (p.full ? ' Section I has <b>ten Parts</b> with separate directions for each Part – read them carefully.' : '') + '</li>' +
      '<li>In the real examination only a blue/black ball-point pen is used on the OMR Answer Sheet and <b>no change of answer is allowed</b>. Tick “Strict OMR” below if you want the same rule here.</li>' +
      '<li>Do rough work on a separate paper or use the <b>Rough Work</b> page given in the test.</li>' +
      '<li>A bell will ring after every 30 minutes.</li>' +
      '<li>There is <b>no negative marking</b>. Attempt every question.</li>' +
      '<li>When the time is over the paper is submitted automatically and your result with correct answers is shown.</li></ol>' +
      '<div class="start no-print"><label><input type="checkbox" id="strict"> <b>Strict OMR mode</b> – ek baar circle bhar diya to badal nahi sakte (asli pariksha jaisa)</label>' +
      '<label><input type="checkbox" id="agree"> Maine saare instructions padh liye hain. / I have read all the instructions.</label>' +
      '<div class="row"><a class="btn" href="#/">◀ All papers</a><button type="button" class="btn primary" data-act="start" disabled id="go">Open Booklet &amp; Start Test</button></div></div></div>';
    $app.innerHTML = h;
    document.title = p.title + ' – Test Booklet';
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
    save();
    examView();
  }
  function save() { if (S) set('run:' + S.p.id, { ans: S.ans, left: S.left, page: S.page, strict: S.strict }); }
  function answered() { var c = 0; for (var k in S.ans) if (S.ans[k]) c++; return c; }
  function omrHtml() {
    var h = '<div class="omr"><h3>OMR ANSWER SHEET</h3><p class="sm">' + esc(S.p.booklet) + ' · Code ' + esc(S.p.code) + (S.strict ? ' · Strict mode' : '') + '</p>';
    S.p.sections.forEach(function (sec) {
      h += '<h4>' + sec.name + ' : ' + sec.title + '</h4><div class="rows">';
      qList({ sections: [sec] }).forEach(function (x) {
        var n = x.q.n;
        h += '<div class="r" data-r="' + n + '"><button type="button" class="n" data-act="goto" data-q="' + n + '" aria-label="Go to question ' + n + '">' + n + '</button>';
        L.forEach(function (o) { h += '<button type="button" class="b' + (S.ans[n] === o ? ' on' : '') + '" data-act="ans" data-q="' + n + '" data-o="' + o + '" aria-label="Q' + n + ' ' + o + '">' + o + '</button>'; });
        h += '</div>';
      });
      h += '</div>';
    });
    return h + '<div class="stat"><span>Darkened: <b class="cnt">' + answered() + '</b> / ' + S.list.length + '</span><span>Tap a number to open that question</span></div></div>';
  }
  function examView() {
    view = 'exam';
    var opts = S.pages.map(function (pg, i) { return '<option value="' + i + '">Page ' + pg.no + ' · ' + pg.label + ' (Q' + pg.qs[0].n + '–' + pg.qs[pg.qs.length - 1].n + ')</option>'; }).join('');
    $app.innerHTML = '<div class="bar"><span class="ttl">' + esc(S.p.title) + ' · ' + esc(S.p.booklet) + ' – ' + esc(S.p.code) + '</span>' +
      '<span class="timer" id="timer" aria-label="Time left">' + mmss(S.left) + '</span>' +
      '<button type="button" class="btn only-narrow" data-act="omr">OMR <b class="cnt">' + answered() + '</b>/' + S.list.length + '</button>' +
      '<button type="button" class="btn" data-act="rough">Rough</button>' +
      '<button type="button" class="btn sub" data-act="submit">Submit</button></div>' +
      '<div class="layout"><div class="main"><div class="sheet" id="sheet"></div></div><aside class="side" id="side">' + omrHtml() + '</aside></div>' +
      '<div class="nav"><button type="button" class="btn" data-act="prev">◀ Prev</button><select id="pgsel" aria-label="Go to page">' + opts + '</select><button type="button" class="btn" data-act="next">Next ▶</button></div>';
    document.getElementById('pgsel').onchange = function () { showPage(+this.value); };
    document.title = mmss(S.left) + ' · ' + S.p.title;
    showPage(S.page, true);
    clearInterval(tick); tick = setInterval(onTick, 1000);
  }
  function showPage(i, quiet, focusQ) {
    i = Math.max(0, Math.min(S.pages.length - 1, i));
    S.page = i;
    var sh = document.getElementById('sheet'), pg = S.pages[i];
    sh.innerHTML = renderPage(S.p, pg, S.ans, false);
    sh.className = 'sheet'; void sh.offsetWidth; if (!quiet) sh.className = 'sheet turn';
    document.getElementById('pgsel').value = i;
    all('.omr .r').forEach(function (r) { var n = +r.getAttribute('data-r'); r.className = 'r' + (n >= pg.qs[0].n && n <= pg.qs[pg.qs.length - 1].n ? ' cur' : ''); });
    var b = all('[data-act="prev"],[data-act="next"]');
    b[0].disabled = i === 0; b[1].textContent = i === S.pages.length - 1 ? 'Finish ✔' : 'Next ▶';
    if (focusQ) { var el = document.getElementById('q' + focusQ); if (el && el.scrollIntoView) el.scrollIntoView({ block: 'center' }); }
    else if (!quiet) window.scrollTo(0, 0);
    save();
  }
  function setAns(n, o) {
    if (!S || view !== 'exam') return;
    var cur = S.ans[n];
    if (S.strict && cur) { toast('Strict OMR: ek baar bhara hua circle badla nahi ja sakta.'); return; }
    S.ans[n] = cur === o ? null : o;
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
    for (var i = 0; i < S.pages.length; i++) {
      var q = S.pages[i].qs;
      if (n >= q[0].n && n <= q[q.length - 1].n) { closeDrawer(); showPage(i, true, n); return; }
    }
  }
  function onTick() {
    if (!S) return;
    S.left = Math.round((S.deadline - Date.now()) / 1000);
    var t = document.getElementById('timer');
    if (t) { t.textContent = mmss(S.left); t.className = 'timer' + (S.left <= 300 ? ' low' : ''); }
    document.title = mmss(S.left) + ' · ' + S.p.title;
    var b = Math.floor((S.total - S.left) / 1800);
    if (b > S.bell && S.left > 0) { S.bell = b; beep(); toast('🔔 Bell: ' + (b * 30) + ' minutes over · ' + Math.round(S.left / 60) + ' minutes left', 5000); }
    if (S.left % 5 === 0) save();
    if (S.left <= 0) { beep(); finish(true); }
  }
  function openDrawer() {
    var d = document.createElement('div'); d.className = 'drawer'; d.id = 'drawer';
    d.innerHTML = '<div style="width:min(420px,100%);height:100%;overflow:auto;background:#fff5f8"><button type="button" class="btn small close" data-act="closeomr">✕ Close</button>' + omrHtml() + '</div>';
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
    modal('<h3>Submit the test?</h3><p>Darkened: <b>' + a + '</b> / ' + n + '<br>Not attempted: <b>' + (n - a) + '</b><br>Time left: <b>' + mmss(S.left) + '</b></p>' +
      (n - a ? '<p>Negative marking nahi hai — khaali sawal bhi bhar dijiye.</p>' : '') +
      '<div class="row"><button type="button" class="btn" data-act="closemodal">Continue test</button><button type="button" class="btn primary" data-act="finish">Submit &amp; see result</button></div>');
  }
  function finish(auto) {
    if (!S) return;
    clearInterval(tick); closeModal(); closeDrawer(); closePad();
    var p = S.p, res = { ans: S.ans, used: S.total - Math.max(0, S.left), when: Date.now(), auto: !!auto }, c = 0;
    S.list.forEach(function (x) { if (S.ans[x.q.n] && S.ans[x.q.n] === p.key.charAt(x.q.n - 1)) c++; });
    set('last:' + p.id, res); set('run:' + p.id, null);
    var best = get('best:' + p.id, null), m = c * MARK;
    if (!best || m > parseFloat(best.m)) set('best:' + p.id, { m: marks(c), max: marks(S.list.length) });
    S = null;
    if (location.hash === '#/p/' + p.id + '/result') route(); else location.hash = '#/p/' + p.id + '/result';
    if (auto) toast('Time over — paper submit ho gaya.', 4000);
  }

  /* rough work pad */
  var pad = null;
  function openPad() {
    if (!pad) {
      pad = document.createElement('div'); pad.className = 'pad';
      pad.innerHTML = '<div class="phead"><span>SPACE FOR ROUGH WORK</span><button type="button" class="btn small" data-act="clearpad">Clear</button><button type="button" class="btn small" data-act="closepad">✕ Back to paper</button></div><canvas></canvas>';
      document.body.appendChild(pad);
      var cv = pad.querySelector('canvas'), cx = cv.getContext('2d'), down = false, r = window.devicePixelRatio || 1;
      cv.width = cv.clientWidth * r; cv.height = cv.clientHeight * r; cx.scale(r, r); cx.lineWidth = 2; cx.lineCap = 'round'; cx.strokeStyle = '#101b4a';
      var pos = function (e) { var b = cv.getBoundingClientRect(), t = e.touches ? e.touches[0] : e; return [t.clientX - b.left, t.clientY - b.top]; };
      var st = function (e) { down = true; var q = pos(e); cx.beginPath(); cx.moveTo(q[0], q[1]); e.preventDefault(); };
      var mv = function (e) { if (!down) return; var q = pos(e); cx.lineTo(q[0], q[1]); cx.stroke(); e.preventDefault(); };
      var en = function () { down = false; };
      if (window.PointerEvent) { cv.addEventListener('pointerdown', st); cv.addEventListener('pointermove', mv); window.addEventListener('pointerup', en); }
      else { cv.addEventListener('mousedown', st); cv.addEventListener('mousemove', mv); window.addEventListener('mouseup', en); cv.addEventListener('touchstart', st, { passive: false }); cv.addEventListener('touchmove', mv, { passive: false }); cv.addEventListener('touchend', en); }
      pad.clear = function () { cx.clearRect(0, 0, cv.width, cv.height); };
    }
    pad.hidden = false;
  }
  function closePad() { if (pad) pad.hidden = true; }

  /* ---------- RESULT + REVIEW ---------- */
  function result(p) {
    view = 'result';
    var res = get('last:' + p.id, null);
    if (!res) { location.hash = '#/p/' + p.id; return; }
    var rows = '', T = { n: 0, a: 0, c: 0 };
    p.sections.forEach(function (sec) {
      var l = qList({ sections: [sec] }), a = 0, c = 0;
      l.forEach(function (x) { var v = res.ans[x.q.n]; if (v) { a++; if (v === p.key.charAt(x.q.n - 1)) c++; } });
      T.n += l.length; T.a += a; T.c += c;
      rows += '<tr><td>' + sec.short + '</td><td>' + l.length + '</td><td>' + a + '</td><td>' + c + '</td><td>' + (a - c) + '</td><td><b>' + marks(c) + '</b> / ' + marks(l.length) + '</td><td>' + Math.round(c * 100 / l.length) + '%</td></tr>';
    });
    var name = get('name', '');
    $app.innerHTML = '<div class="sheet result"><h2>RESULT – ' + esc(p.title) + '</h2><p style="text-align:center;margin:0">' + esc(p.booklet) + ' · Code ' + esc(p.code) + ' · ' + esc(p.date) + (name ? '<br>Candidate: <b>' + esc(name) + '</b>' : '') + '</p>' +
      '<div class="score"><b>' + marks(T.c) + '</b>out of ' + marks(T.n) + ' marks · ' + Math.round(T.c * 100 / T.n) + '%</div>' +
      '<table><tr><th>Section</th><th>Qs</th><th>Attempted</th><th>Correct</th><th>Wrong</th><th>Marks</th><th>%</th></tr>' + rows +
      '<tr><th>Total</th><th>' + T.n + '</th><th>' + T.a + '</th><th>' + T.c + '</th><th>' + (T.a - T.c) + '</th><th>' + marks(T.c) + ' / ' + marks(T.n) + '</th><th>' + Math.round(T.c * 100 / T.n) + '%</th></tr></table>' +
      '<p style="text-align:center">Time used: <b>' + mmss(res.used) + '</b>' + (res.auto ? ' (time over, auto-submitted)' : '') + ' · Not attempted: <b>' + (T.n - T.a) + '</b></p>' +
      '<p style="font-size:13px">Asli pariksha me har Section me alag se qualify karna hota hai aur selection district ki merit se hota hai, isliye koi fixed pass marks nahi hote. Jis section me % sabse kam hai, pehle uski practice kijiye.</p>' +
      '<div class="row no-print"><a class="btn primary" href="#/p/' + p.id + '/review">Review answers</a><a class="btn" href="#/p/' + p.id + '">Attempt again</a><a class="btn" href="#/">All papers</a><button type="button" class="btn" data-act="print">Print</button></div>' +
      (p.keynote ? '<p class="keynote"><b>Answer key:</b> ' + esc(p.keynote) + '</p>' : '') + '</div>';
    document.title = 'Result · ' + p.title;
    window.scrollTo(0, 0);
  }
  function review(p) {
    view = 'review';
    var res = get('last:' + p.id, null) || { ans: {} };
    var h = '<div class="bar"><span class="ttl" style="display:block">Answer review · ' + esc(p.title) + '</span><a class="btn" href="#/p/' + p.id + '/result">Result</a><a class="btn sub" href="#/">Home</a></div>' +
      '<div class="filter no-print"><button type="button" class="btn small primary" data-act="flt" data-f="">All</button><button type="button" class="btn small" data-act="flt" data-f="bad">Wrong</button><button type="button" class="btn small" data-act="flt" data-f="skip">Not attempted</button><button type="button" class="btn small" data-act="flt" data-f="ok">Correct</button></div><div class="review" id="rev">';
    buildPages(p).forEach(function (pg) { h += '<div class="sheet">' + renderPage(p, pg, res.ans, true) + '</div>'; });
    $app.innerHTML = h + '</div>';
    document.title = 'Review · ' + p.title;
    window.scrollTo(0, 0);
  }
  function filter(f, btn) {
    all('.filter .btn').forEach(function (b) { b.className = 'btn small' + (b === btn ? ' primary' : ''); });
    all('#rev .q').forEach(function (q) { q.hidden = !!f && q.getAttribute('data-st') !== f; });
    all('#rev .sheet').forEach(function (s) { s.hidden = !!f && !s.querySelector('.q:not([hidden])'); });
    all('#rev .passage, #rev .dir, #rev .cap, #rev .rough').forEach(function (e) { e.hidden = !!f; });
  }

  /* ---------- events + router ---------- */
  document.addEventListener('click', function (e) {
    var el = up(e.target, 'data-act'); if (!el) return;
    var act = el.getAttribute('data-act');
    if (act === 'ans') { if (!el.disabled) setAns(+el.getAttribute('data-q'), el.getAttribute('data-o')); }
    else if (act === 'goto') gotoQ(+el.getAttribute('data-q'));
    else if (act === 'prev') showPage(S.page - 1);
    else if (act === 'next') { if (S.page === S.pages.length - 1) askSubmit(); else showPage(S.page + 1); }
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
    else if (act === 'start') { var id = location.hash.split('/')[2]; set('run:' + id, null); var nm = document.getElementById('nm'); if (nm) set('name', nm.value.trim()); startExam(PAPERS[id], false); try { history.replaceState(null, '', '#/p/' + id + '/exam'); } catch (er) { location.hash = '#/p/' + id + '/exam'; } window.scrollTo(0, 0); }
    else if (act === 'restart') { closeModal(); set('run:' + el.getAttribute('data-id'), null); location.hash = '#/p/' + el.getAttribute('data-id'); }
  });
  document.addEventListener('keydown', function (e) {
    if (view !== 'exam' || !S || /INPUT|SELECT|TEXTAREA/.test(e.target.tagName)) return;
    if (e.key === 'ArrowRight' && S.page < S.pages.length - 1) showPage(S.page + 1);
    else if (e.key === 'ArrowLeft') showPage(S.page - 1);
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
      if (get('run:' + id, null)) modal('<h3>Adhura test mila</h3><p>Is paper ka ek test beech me chhoota hua hai. Wahin se aage badhna hai?</p><div class="row"><button type="button" class="btn" data-act="restart" data-id="' + id + '">Naya shuru karein</button><a class="btn primary" href="#/p/' + id + '/exam">Resume ▶</a></div>');
    });
  }
  function leaveExam() { if (S) { save(); S = null; } clearInterval(tick); }
  window.addEventListener('hashchange', route);
  route();
})();
