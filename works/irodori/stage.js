/* ============================================================
   映像ステージ
   背景の動画は画面に敷いたまま、文章はふつうのページと同じように流れる。
   ページを下へ進めるほど動画も進み、各場面（.scene）が画面中央を
   通過する間に、その場面の秒数（data-from 〜 data-to）が再生される。
   - 文章の行（.ln）は、画面に入ってきたものから1行ずつフェードイン
   - 日本酒・名物は場面を長く取り（--h）、動画をゆっくり進める
   動きを減らす設定・データセーバー・読み込み失敗時は、静止画版に切り替える。
   ============================================================ */
(function () {
  'use strict';

  var root = document.documentElement;
  var stage = document.getElementById('top');
  var video = document.getElementById('stageVideo');
  if (!stage || !video) return;

  var LERP = 0.22;          // 映像が目標の秒数へ追いつく速さ（0〜1）
  var FADE_IN = 0.88;       // 行の上端が画面のこの位置（上から）より上に来たら表示
  var FADE_OUT = 0.18;      // 行の下端が画面のこの位置より上に抜けたら隠す（ヘッダーまわりを空ける）

  var scenes = [].slice.call(stage.querySelectorAll('.scene')).map(function (el) {
    return {
      el: el,
      body: el.querySelector('.scene__body'),
      from: parseFloat(el.getAttribute('data-from')),
      to: parseFloat(el.getAttribute('data-to')),
      top: 0, h: 0, hasOn: false
    };
  });
  var lines = [].slice.call(stage.querySelectorAll('.ln')).map(function (el) {
    return { el: el, on: false, scene: el.closest('.scene') };
  });
  var hud = document.getElementById('stageHud');
  var chapters = [].slice.call(stage.querySelectorAll('.progress__ch')).map(function (a) {
    var id = a.getAttribute('href').slice(1);
    for (var i = 0; i < scenes.length; i++) if (scenes[i].el.id === id) return { a: a, idx: i };
    return { a: a, idx: 0 };
  });
  var fill = document.getElementById('progressFill');
  var now = document.getElementById('chapterNow');
  var status = document.getElementById('stageStatus');
  var small = window.matchMedia('(max-width: 820px)');
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  var END = scenes[scenes.length - 1].to;

  var active = false, ready = false, failed = false;
  var vpH = window.innerHeight, vpW = window.innerWidth;
  var anchors = [], stageBottom = 0;
  var target = 0, shown = 0;
  var raf = 0, loadTimer = 0, sceneIndex = -1, chapterIndex = -1, graded = null, hudOn = null;

  /* ---------- 位置の計測：画面中央の位置 ⇄ 動画の秒数 ---------- */
  function setViewport() {
    vpH = window.innerHeight;
    vpW = window.innerWidth;
    root.style.setProperty('--vh', (vpH / 100) + 'px');
    root.style.setProperty('--vp-h', vpH + 'px');
  }
  function measure() {
    if (!active) return;
    var y = window.scrollY;
    anchors = [];
    scenes.forEach(function (s, i) {
      var r = s.el.getBoundingClientRect();
      s.top = r.top + y;
      s.h = r.height;
      // 最初の場面だけは、ページ最上部（画面中央 = 高さの半分）を0秒にする
      anchors.push([i === 0 ? s.top + vpH / 2 : s.top, s.from]);
    });
    var last = scenes[scenes.length - 1];
    anchors.push([last.top + last.h, last.to]);
    stageBottom = stage.getBoundingClientRect().bottom + y;
    schedule();
  }
  function timeAtCenter(c) {
    if (c <= anchors[0][0]) return anchors[0][1];
    for (var i = 1; i < anchors.length; i++) {
      var a = anchors[i - 1], b = anchors[i];
      if (c <= b[0]) return a[1] + (b[1] - a[1]) * (c - a[0]) / Math.max(1, b[0] - a[0]);
    }
    return anchors[anchors.length - 1][1];
  }
  function centerAtTime(t) {
    for (var i = 1; i < anchors.length; i++) {
      var a = anchors[i - 1], b = anchors[i];
      if (t <= b[1]) return a[0] + (b[0] - a[0]) * (t - a[1]) / Math.max(0.001, b[1] - a[1]);
    }
    return anchors[anchors.length - 1][0];
  }

  /* ---------- 描画 ---------- */
  function paintLines() {
    var inY = small.matches ? vpH - 150 : vpH * FADE_IN;
    var outY = vpH * FADE_OUT;
    for (var i = 0; i < scenes.length; i++) scenes[i].hasOn = false;
    for (var j = 0; j < lines.length; j++) {
      var l = lines[j], r = l.el.getBoundingClientRect();
      var on = r.top < inY && r.bottom > outY;
      if (on !== l.on) { l.on = on; l.el.classList.toggle('is-on', on); }
      if (on) for (var k = 0; k < scenes.length; k++) if (scenes[k].el === l.scene) scenes[k].hasOn = true;
    }
    for (var m = 0; m < scenes.length; m++) {
      var s = scenes[m];
      if (s.body && s.body.classList.contains('has-on') !== s.hasOn) s.body.classList.toggle('has-on', s.hasOn);
    }
  }
  function paintScene(c) {
    var idx = 0;
    for (var i = 0; i < scenes.length; i++) if (c >= scenes[i].top) idx = i;
    if (idx !== sceneIndex) {
      sceneIndex = idx;
      var s = scenes[idx].el;
      stage.setAttribute('data-side', s.getAttribute('data-side'));
      stage.style.setProperty('--pos', small.matches ? (s.getAttribute('data-pos') || '50%') : '50%');
      var g = s.hasAttribute('data-graded');
      if (g !== graded) { graded = g; stage.classList.toggle('is-graded', g); }
    }
    var ch = 0;
    for (var j = 0; j < chapters.length; j++) if (idx >= chapters[j].idx) ch = j;
    if (ch !== chapterIndex) {
      if (chapters[chapterIndex]) { chapters[chapterIndex].a.classList.remove('is-active'); chapters[chapterIndex].a.removeAttribute('aria-current'); }
      chapterIndex = ch;
      chapters[ch].a.classList.add('is-active');
      chapters[ch].a.setAttribute('aria-current', 'step');
      if (now) now.textContent = chapters[ch].a.textContent;
    }
  }
  function frame() {
    raf = 0;
    if (!active) return;
    var y = window.scrollY;
    var c = y + vpH / 2;
    target = timeAtCenter(c);

    // 映像はなめらかに目標の秒数へ追いつかせる
    var diff = target - shown;
    shown = Math.abs(diff) < 0.004 ? target : shown + diff * LERP;

    paintLines();
    paintScene(c);
    if (fill) fill.style.transform = 'scaleX(' + Math.min(1, shown / END).toFixed(4) + ')';
    var on = stageBottom - y > vpH * 1.15; // 和紙がせり上がってきたら章ナビを消す
    if (on !== hudOn) { hudOn = on; hud.classList.toggle('is-on', on); }
    seek(shown);

    if (shown !== target) schedule();
  }
  function seek(t) {
    if (!ready || failed || video.seeking || document.hidden) return;
    var d = video.duration;
    var to = Math.min(t, (isFinite(d) ? d : END) - 1 / 30);
    if (Math.abs(video.currentTime - to) < 1 / 60) return;
    try { video.currentTime = to; } catch (e) { /* 次のフレームで再試行 */ }
  }
  function schedule() {
    if (active && !raf) raf = requestAnimationFrame(frame);
  }

  /* ---------- 読み込み ---------- */
  // 回線が遅いときだけ軽い版を使う（通常はPC・スマホとも720pの高画質版）
  function pickSource() {
    var mp4 = video.canPlayType('video/mp4; codecs="avc1.640028"');
    var ext = mp4 ? 'mp4' : (video.canPlayType('video/webm; codecs="vp9"') ? 'webm' : 'mp4');
    var c = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    var slow = !!(c && (/(^|-)(2g|3g)$/.test(c.effectiveType || '') || (c.downlink && c.downlink < 1.5)));
    var name = slow ? (small.matches ? '480' : '720') : '720-hq';
    return 'assets/video/irodori-' + name + '.' + ext;
  }
  // すぐ読み終わるときは出さない（load() で0.6秒後に解禁）。表示は5%刻みで更新する
  var progressArmed = false, lastPct = -1;
  function showProgress(ratio) {
    if (!progressArmed || ready || window.scrollY >= stageBottom) return;
    var pct = ratio == null ? -1 : Math.floor(ratio * 20) * 5;
    if (pct === lastPct && !status.hidden) return;
    lastPct = pct;
    status.textContent = pct < 0 ? '映像を読み込んでいます' : '映像を読み込んでいます ' + pct + '%';
    status.hidden = false;
  }
  // 読み込みながら進み具合を表示し、最後に1つのBlobにまとめる
  function fetchWithProgress(src) {
    return fetch(src).then(function (r) {
      if (!r.ok) throw new Error(r.status);
      var total = parseInt(r.headers.get('Content-Length'), 10);
      var type = r.headers.get('Content-Type') || (src.slice(-4) === 'webm' ? 'video/webm' : 'video/mp4');
      if (!r.body || !r.body.getReader || !total) { showProgress(null); return r.blob(); }
      var reader = r.body.getReader(), chunks = [], got = 0;
      function pump() {
        return reader.read().then(function (res) {
          if (res.done) return new Blob(chunks, { type: type });
          chunks.push(res.value);
          got += res.value.length;
          showProgress(Math.min(1, got / total));
          return pump();
        });
      }
      return pump();
    });
  }

  /* ---------- 読み込み ---------- */
  function load() {
    var src = pickSource();
    status.hidden = true;
    loadTimer = setTimeout(function () { progressArmed = true; showProgress(null); }, 600);
    var hardTimeout = setTimeout(function () { if (!ready) toStatic(); }, 45000);
    video.addEventListener('loadeddata', function () {
      if (ready) return;
      ready = true;
      clearTimeout(loadTimer); clearTimeout(hardTimeout);
      status.hidden = true;
      // iOS Safariは一度再生しないとシーク後のフレームを描かないため、再生→即停止しておく
      var p = video.play();
      var done = function () { video.pause(); stage.classList.add('is-ready'); schedule(); };
      if (p && p.then) p.then(done).catch(function () { stage.classList.add('is-ready'); schedule(); });
      else done();
    });
    video.addEventListener('seeked', schedule);
    video.addEventListener('error', function () { clearTimeout(hardTimeout); toStatic(); });

    // Blobとして丸ごと読み込むと、シークが通信待ちにならず滑らかになる
    if (window.fetch && window.URL && URL.createObjectURL) {
      fetchWithProgress(src).then(function (blob) {
        if (failed) return;
        video.src = URL.createObjectURL(blob);
        video.load();
      }).catch(function () {
        if (failed) return;
        video.src = src; video.preload = 'auto'; video.load();
      });
    } else {
      video.src = src; video.preload = 'auto'; video.load();
    }
  }

  function toStatic() {
    if (failed) return;
    failed = true; active = false;
    if (raf) cancelAnimationFrame(raf);
    raf = 0;
    clearTimeout(loadTimer);
    status.hidden = true;
    try { video.pause(); } catch (e) {}
    root.classList.remove('is-scrub');
    lines.forEach(function (l) { l.el.classList.remove('is-on'); });
  }

  function start() {
    active = true;
    setViewport();
    load();
    measure();
    frame();
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', function () {
      // アドレスバーの伸縮（高さだけの小さな変化）では場面の長さを組み直さない
      if (window.innerWidth === vpW && Math.abs(window.innerHeight - vpH) < 120) return;
      setViewport();
      measure();
    }, { passive: true });
    window.addEventListener('load', measure);
    window.addEventListener('pageshow', measure);
    if ('ResizeObserver' in window) new ResizeObserver(measure).observe(document.body);
    document.addEventListener('visibilitychange', function () { if (!document.hidden) schedule(); });
    var onReduce = function () { if (reduce.matches) toStatic(); };
    if (reduce.addEventListener) reduce.addEventListener('change', onReduce);
    else if (reduce.addListener) reduce.addListener(onReduce);
  }

  /* ---------- 外部から使う：場面への移動（その場面の文章が画面中央に来る位置へ） ---------- */
  function goTo(id, smooth) {
    if (!active) return false;
    for (var i = 0; i < scenes.length; i++) {
      var s = scenes[i];
      if (s.el.id !== id) continue;
      var top = i === 0 ? 0 : s.top + s.h / 2 - vpH / 2;
      window.scrollTo({ top: Math.round(top), behavior: smooth === false ? 'auto' : 'smooth' });
      return true;
    }
    return false;
  }
  window.IrodoriStage = {
    isActive: function () { return active; },
    goTo: goTo,
    scrollYFor: function (t) { return Math.max(0, Math.round(centerAtTime(t) - vpH / 2)); }
  };

  if (root.classList.contains('is-scrub')) start();
}());
