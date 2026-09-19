/* A single paused, compressed video fills the viewport behind the entire page.
   Native document scroll selects its time; one seek at a time, no idle loop. */
(function () {
  'use strict';
  var video = document.getElementById('houseTour');
  if (!video) return;
  var root = document.documentElement;
  var source = video.querySelector('source');
  var hint = document.getElementById('tourHint');
  var toggle = document.getElementById('tourToggle');
  var loading = document.getElementById('tourLoading');
  var bar = document.getElementById('tourProgress');
  var time = document.getElementById('tourTime');
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  var connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  var saveData = !!(connection && (connection.saveData || /(^|-)2g$/.test(connection.effectiveType)));
  var small = window.matchMedia('(max-width: 860px)').matches || saveData;
  var active = false, frozen = false, ready = false, failed = false;
  var raf = 0, resizeTimer = 0, timeout = 0, target = 0, travel = 1, lastTick = -1;
  var end = 30 - 1 / 24;
  source.src = small ? 'assets/video/house-tour-480.mp4' : 'assets/video/house-tour-720.mp4';
  video.muted = true;
  toggle.hidden = false;

  function setHint(text) { if (hint.textContent !== text) hint.textContent = text; }
  function paint(seconds) {
    bar.style.transform = 'scaleX(' + Math.min(1, seconds / end) + ')';
    var tick = Math.round(seconds);
    if (tick !== lastTick) { time.textContent = String(tick).padStart(2, '0'); lastTick = tick; }
  }
  function locked() { return document.body.classList.contains('is-locked'); }
  function measure() {
    if (locked()) return;
    // FAQ, filters and form steps can change the document's scrollable height.
    travel = Math.max(1, root.scrollHeight - window.innerHeight);
    schedule();
  }
  function seek() {
    if (!active || frozen || !ready || document.hidden || video.seeking || failed) return;
    if (Math.abs(video.currentTime - target) < 1 / 48) return;
    try { video.currentTime = target; } catch (_) { /* retry on media readiness */ }
  }
  function update() {
    raf = 0;
    if (!active || frozen || document.hidden || locked()) return;
    target = Math.max(0, Math.min(1, window.scrollY / travel)) * end;
    paint(target);
    seek();
  }
  function schedule() {
    if (active && !frozen && !raf && !document.hidden) raf = requestAnimationFrame(update);
  }
  function fail() {
    failed = true; active = false;
    clearTimeout(timeout);
    if (raf) cancelAnimationFrame(raf);
    raf = 0;
    loading.hidden = true;
    video.pause();
    root.classList.add('film-unavailable');
    toggle.hidden = true;
    setHint('背景映像を読み込めませんでした。ページはそのままご覧いただけます。');
  }
  function staticMode() {
    active = false; frozen = false;
    if (raf) cancelAnimationFrame(raf);
    raf = 0;
    clearTimeout(timeout);
    loading.hidden = true;
    if (video.readyState > 0) video.pause();
    video.preload = 'none';
    toggle.textContent = ready ? '背景映像を動かす' : '背景映像を読み込む';
    toggle.removeAttribute('aria-pressed');
    setHint(saveData ? '通信量を抑えるため、背景映像を停止しています。' : '動きを抑える設定に合わせ、背景映像を停止しています。');
  }
  function enable() {
    if (failed) return;
    active = true; frozen = false;
    video.pause();
    toggle.textContent = '映像を固定';
    toggle.setAttribute('aria-pressed', 'false');
    setHint('下へ進むと映像も進み、上へ戻すと映像も戻ります。');
    if (!ready) {
      loading.hidden = false;
      video.preload = 'auto';
      video.load();
      clearTimeout(timeout);
      timeout = setTimeout(function () { if (!ready) fail(); }, 20000);
    }
    measure();
  }
  video.addEventListener('loadedmetadata', function () {
    if (!Number.isFinite(video.duration) || video.duration <= 0) { fail(); return; }
    end = Math.max(0, video.duration - 1 / 24);
    measure();
  });
  video.addEventListener('loadeddata', function () {
    ready = true;
    loading.hidden = true;
    clearTimeout(timeout);
    schedule();
  });
  video.addEventListener('seeked', schedule);
  video.addEventListener('canplay', schedule);
  video.addEventListener('error', fail);
  source.addEventListener('error', fail);
  toggle.addEventListener('click', function () {
    if (!active) { enable(); return; }
    frozen = !frozen;
    toggle.textContent = frozen ? 'スクロールに連動' : '映像を固定';
    toggle.setAttribute('aria-pressed', String(frozen));
    setHint(frozen ? '背景映像を固定しています。' : '下へ進むと映像も進み、上へ戻すと映像も戻ります。');
    if (!frozen) measure();
  });
  window.addEventListener('scroll', schedule, { passive: true });
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(measure, 120);
  }, { passive: true });
  window.addEventListener('pageshow', measure);
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) {
      if (raf) cancelAnimationFrame(raf);
      raf = 0;
      if (active) video.pause();
    } else measure();
  });
  if ('ResizeObserver' in window) new ResizeObserver(measure).observe(document.body);
  var motionChange = function () { if (reduce.matches) staticMode(); else if (!saveData) enable(); };
  if (reduce.addEventListener) reduce.addEventListener('change', motionChange);
  else if (reduce.addListener) reduce.addListener(motionChange);
  if (reduce.matches || saveData) staticMode(); else enable();
}());
