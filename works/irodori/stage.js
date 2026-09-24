/* ============================================================
   映像ステージ
   スクロール位置 → 動画の再生位置 → 文字の表示 を常に一致させる。
   - 各行（.ln）は data-in 〜 data-out 秒の間だけ表示（1行ずつフェードイン）
   - 日本酒・名物の区間はスロー（1秒あたりのスクロール量を増やす）
   - 最後のフレームで止まり、和紙色の幕が上がって第2部へ
   動きを減らす設定・データセーバー・読み込み失敗時は、静止画版に切り替える。
   ============================================================ */
(function () {
  'use strict';

  var root = document.documentElement;
  var stage = document.getElementById('top');
  var video = document.getElementById('stageVideo');
  if (!stage || !video) return;

  // [開始秒, 終了秒, 1秒あたりのスクロール量(vh)]
  var SEGMENTS = [
    [0, 9.5, 45],
    [9.5, 11, 130],    // 日本酒（スロー）
    [11, 12.8, 45],
    [12.8, 14.4, 130], // 名物（スロー）
    [14.4, 15, 45]
  ];
  var HOLD_VH = 70;    // 最終フレームで止めて幕を上げる区間
  var LERP = 0.22;     // 映像が目標位置へ追いつく速さ（0〜1）

  var scenes = [].slice.call(stage.querySelectorAll('.scene'));
  var lines = [].slice.call(stage.querySelectorAll('.ln[data-in]')).map(function (el) {
    var out = el.getAttribute('data-out');
    return { el: el, t0: parseFloat(el.getAttribute('data-in')), t1: out === null ? Infinity : parseFloat(out), on: false };
  });
  var chapters = [].slice.call(stage.querySelectorAll('.progress__ch'));
  var fill = document.getElementById('progressFill');
  var now = document.getElementById('chapterNow');
  var status = document.getElementById('stageStatus');
  var small = window.matchMedia('(max-width: 820px)');
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)');

  var END = SEGMENTS[SEGMENTS.length - 1][1];
  var totalVh = SEGMENTS.reduce(function (s, g) { return s + (g[1] - g[0]) * g[2]; }, 0) + HOLD_VH;

  var active = false, ready = false, failed = false;
  var vpH = window.innerHeight, vpW = window.innerWidth;
  var stageTop = 0, travel = 1;
  var target = 0, shown = 0, hold = 0;
  var raf = 0, loadTimer = 0, sceneIndex = -1, chapterIndex = -1, graded = null;

  /* ---------- スクロール量 ⇄ 秒 ---------- */
  function timeAt(px) {
    var v = px / vpH * 100;
    for (var i = 0; i < SEGMENTS.length; i++) {
      var g = SEGMENTS[i], len = (g[1] - g[0]) * g[2];
      if (v <= len) return { t: g[0] + v / g[2], hold: 0 };
      v -= len;
    }
    return { t: END, hold: Math.min(1, v / HOLD_VH) };
  }
  function pxAt(t) {
    var v = 0;
    for (var i = 0; i < SEGMENTS.length; i++) {
      var g = SEGMENTS[i];
      if (t <= g[1]) { v += (Math.max(t, g[0]) - g[0]) * g[2]; break; }
      v += (g[1] - g[0]) * g[2];
    }
    return v / 100 * vpH;
  }

  function measure() {
    if (!active) return;
    vpH = window.innerHeight;
    vpW = window.innerWidth;
    root.style.setProperty('--vp-h', vpH + 'px');
    stage.style.setProperty('--stage-h', (totalVh / 100 * vpH + vpH) + 'px');
    stageTop = stage.getBoundingClientRect().top + window.scrollY;
    travel = totalVh / 100 * vpH;
    schedule();
  }

  /* ---------- 描画 ---------- */
  function paintLines(t) {
    for (var i = 0; i < lines.length; i++) {
      var l = lines[i], on = t >= l.t0 && t < l.t1;
      if (on !== l.on) { l.on = on; l.el.classList.toggle('is-on', on); }
    }
  }
  function paintScene(t) {
    var idx = 0;
    for (var i = 0; i < scenes.length; i++) {
      if (t >= parseFloat(scenes[i].getAttribute('data-from'))) idx = i;
    }
    if (idx !== sceneIndex) {
      sceneIndex = idx;
      var s = scenes[idx];
      stage.setAttribute('data-side', s.getAttribute('data-side'));
      stage.style.setProperty('--pos', small.matches ? (s.getAttribute('data-pos') || '50%') : '50%');
      var g = s.hasAttribute('data-graded');
      if (g !== graded) { graded = g; stage.classList.toggle('is-graded', g); }
    }
    var ch = 0;
    for (var j = 0; j < chapters.length; j++) {
      if (t >= parseFloat(chapters[j].getAttribute('data-time')) - 0.4) ch = j;
    }
    if (ch !== chapterIndex) {
      if (chapters[chapterIndex]) { chapters[chapterIndex].classList.remove('is-active'); chapters[chapterIndex].removeAttribute('aria-current'); }
      chapterIndex = ch;
      chapters[ch].classList.add('is-active');
      chapters[ch].setAttribute('aria-current', 'step');
      if (now) now.textContent = chapters[ch].textContent;
    }
  }
  function frame() {
    raf = 0;
    if (!active) return;
    var px = Math.min(Math.max(window.scrollY - stageTop, 0), travel);
    var pos = timeAt(px);
    target = pos.t;
    hold = pos.hold;

    // 映像と文字は同じ「表示中の秒数」で動かす
    var diff = target - shown;
    shown = Math.abs(diff) < 0.004 ? target : shown + diff * LERP;

    paintLines(shown);
    paintScene(shown);
    stage.style.setProperty('--veil', hold.toFixed(3));
    if (fill) fill.style.transform = 'scaleX(' + Math.min(1, shown / END).toFixed(4) + ')';
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
  function load() {
    // H.264（MP4）を優先し、再生できないブラウザだけVP9（WebM）を使う
    var mp4 = video.canPlayType('video/mp4; codecs="avc1.640028"');
    var ext = mp4 ? 'mp4' : (video.canPlayType('video/webm; codecs="vp9"') ? 'webm' : 'mp4');
    var src = 'assets/video/irodori-' + (small.matches ? '480' : '720') + '.' + ext;
    status.hidden = true;
    loadTimer = setTimeout(function () { if (!ready) status.hidden = false; }, 1500);
    var hardTimeout = setTimeout(function () { if (!ready) toStatic(); }, 30000);
    video.addEventListener('loadeddata', function () {
      if (ready) return;
      ready = true;
      clearTimeout(loadTimer); clearTimeout(hardTimeout);
      status.hidden = true;
      // iOS Safariは一度再生しないとシーク後のフレームを描かないため、再生→即停止しておく
      var p = video.play();
      if (p && p.then) p.then(function () { video.pause(); stage.classList.add('is-ready'); schedule(); })
        .catch(function () { stage.classList.add('is-ready'); schedule(); });
      else { video.pause(); stage.classList.add('is-ready'); schedule(); }
    });
    video.addEventListener('seeked', schedule);
    video.addEventListener('error', function () { clearTimeout(hardTimeout); toStatic(); });

    // Blobとして丸ごと読み込むと、シークが通信待ちにならず滑らかになる
    if (window.fetch && window.URL && URL.createObjectURL) {
      fetch(src).then(function (r) {
        if (!r.ok) throw new Error(r.status);
        return r.blob();
      }).then(function (blob) {
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
    stage.style.removeProperty('--stage-h');
    lines.forEach(function (l) { l.el.classList.remove('is-on'); });
  }

  function start() {
    active = true;
    load();
    measure();
    frame();
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', function () {
      // アドレスバーの伸縮（高さだけの小さな変化）ではスクロール量を組み直さない
      if (window.innerWidth === vpW && Math.abs(window.innerHeight - vpH) < 120) return;
      measure();
    }, { passive: true });
    window.addEventListener('load', measure);
    window.addEventListener('pageshow', measure);
    if ('ResizeObserver' in window) new ResizeObserver(function () {
      if (active) stageTop = stage.getBoundingClientRect().top + window.scrollY;
    }).observe(document.body);
    document.addEventListener('visibilitychange', function () { if (!document.hidden) schedule(); });
    var onReduce = function () { if (reduce.matches) toStatic(); };
    if (reduce.addEventListener) reduce.addEventListener('change', onReduce);
    else if (reduce.addListener) reduce.addListener(onReduce);
  }

  /* ---------- 外部から使う：章への移動 ---------- */
  function goTo(id, smooth) {
    var el = document.getElementById(id);
    if (!el) return false;
    if (!active) return false;
    var t;
    var ch = stage.querySelector('.progress__ch[href="#' + id + '"]');
    if (ch) t = parseFloat(ch.getAttribute('data-time'));
    else if (el.classList.contains('scene')) t = parseFloat(el.getAttribute('data-from')) + 0.3;
    else return false;
    window.scrollTo({ top: Math.round(stageTop + pxAt(t)), behavior: smooth === false ? 'auto' : 'smooth' });
    return true;
  }
  window.IrodoriStage = {
    isActive: function () { return active; },
    goTo: goTo,
    scrollYFor: function (t) { return Math.round(stageTop + pxAt(t)); }
  };

  if (root.classList.contains('is-scrub')) start();
}());
