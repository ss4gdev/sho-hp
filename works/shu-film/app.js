/* ============================================================
   SHU 映像版
   1. ヘッダー（ヒーロー上は透明 → 過ぎたら背景）
   2. モバイルメニュー
   3. ふわっと表示（IntersectionObserver）
   4. ヒーロー動画（data-video="on" のときだけ読み込む／失敗時はポスターのまま）
   5. モバイル予約バー
   ============================================================ */
(() => {
  const body = document.body;
  const header = document.getElementById('site-header');
  const hero = document.querySelector('[data-hero]');
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  /* ---------- 1. ヘッダー ---------- */
  let headerTicking = false;
  const updateHeader = () => {
    headerTicking = false;
    const solid = !hero || hero.getBoundingClientRect().bottom <= header.offsetHeight;
    header.classList.toggle('is-solid', solid);
  };
  const onScroll = () => {
    if (!headerTicking) {
      headerTicking = true;
      requestAnimationFrame(updateHeader);
    }
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);
  updateHeader();

  /* ---------- 2. モバイルメニュー ---------- */
  const menuBtn = document.getElementById('menu-btn');
  const menuLabel = menuBtn.querySelector('.menu-btn__label');
  const drawer = document.getElementById('drawer');
  const main = document.getElementById('main');
  const footer = document.querySelector('.footer');
  let lockY = 0;

  // iOS Safari は body の overflow:hidden だけでは背面がスクロールするため、position:fixed で固定する
  const openDrawer = () => {
    lockY = window.scrollY;
    drawer.inert = false;
    drawer.classList.add('is-open');
    body.classList.add('is-drawer-open');
    menuBtn.setAttribute('aria-expanded', 'true');
    menuLabel.textContent = 'メニューを閉じる';
    main.inert = true;
    footer.inert = true;
    Object.assign(body.style, { position: 'fixed', top: `-${lockY}px`, left: '0', right: '0' });
  };
  const closeDrawer = () => {
    drawer.classList.remove('is-open');
    drawer.inert = true;
    body.classList.remove('is-drawer-open');
    menuBtn.setAttribute('aria-expanded', 'false');
    menuLabel.textContent = 'メニューを開く';
    main.inert = false;
    footer.inert = false;
    Object.assign(body.style, { position: '', top: '', left: '', right: '' });
    window.scrollTo({ top: lockY, behavior: 'instant' });
  };
  const isOpen = () => drawer.classList.contains('is-open');

  menuBtn.addEventListener('click', () => (isOpen() ? closeDrawer() : openDrawer()));
  // リンクを押したら閉じて、そのままアンカー先へ移動
  drawer.querySelectorAll('a').forEach((a) => a.addEventListener('click', () => { if (isOpen()) closeDrawer(); }));
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && isOpen()) {
      closeDrawer();
      menuBtn.focus();
    }
  });
  // PC幅に広げたら閉じる
  window.matchMedia('(min-width: 1024px)').addEventListener('change', (e) => { if (e.matches && isOpen()) closeDrawer(); });

  /* ---------- 3. ふわっと表示 ---------- */
  const reveals = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-in');
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.12 });
    reveals.forEach((el) => io.observe(el));
  } else {
    reveals.forEach((el) => el.classList.add('is-in'));
  }

  /* ---------- 4. ヒーロー ---------- */
  if (hero) {
    // ポスターの読み込み後に、コピーとポスターを静かに表示
    const posterImg = hero.querySelector('.hero__poster img');
    const markReady = () => hero.classList.add('is-ready');
    if (posterImg.complete) requestAnimationFrame(markReady);
    else {
      posterImg.addEventListener('load', markReady, { once: true });
      posterImg.addEventListener('error', markReady, { once: true });
      setTimeout(markReady, 1500);
    }

    setupHeroVideo(hero);
  }

  function setupHeroVideo(section) {
    const video = section.querySelector('.hero__video');
    const toggle = section.querySelector('.hero__toggle');
    const toggleLabel = toggle.querySelector('.hero__toggle-label');
    if (!video || section.dataset.video !== 'on') return;

    // HTML に書かれた <source data-src> を控えておき、画面に合うものだけ src を付けて入れ直す
    const candidates = [...video.querySelectorAll('source')].map((s) => ({
      src: s.dataset.src,
      type: s.type,
      media: s.dataset.media || '',
    })).filter((c) => c.src);
    if (!candidates.length) return;

    const saveData = navigator.connection && navigator.connection.saveData;
    const autoplayAllowed = !reduceMotion.matches && !saveData;
    let userPaused = !autoplayAllowed;
    let inView = true;
    let mountedKey = '';

    const setToggle = (paused) => {
      toggle.hidden = false;
      toggle.setAttribute('aria-pressed', String(paused));
      toggleLabel.textContent = paused ? 'Play' : 'Pause';
      toggle.setAttribute('aria-label', paused ? '背景の映像を再生' : '背景の映像を一時停止');
    };
    const fallbackToPoster = () => {
      section.classList.remove('is-playing');
      section.classList.add('is-video-error');
      toggle.hidden = true;
    };

    const mount = () => {
      const picked = candidates.filter((c) => !c.media || window.matchMedia(c.media).matches);
      const key = picked.map((c) => c.src).join('|');
      if (key === mountedKey) return;
      mountedKey = key;
      video.querySelectorAll('source').forEach((s) => s.remove());
      picked.forEach((c, i) => {
        const s = document.createElement('source');
        s.src = c.src;
        if (c.type) s.type = c.type;
        // 最後の候補まで読み込めなければポスターのまま
        if (i === picked.length - 1) s.addEventListener('error', fallbackToPoster);
        video.appendChild(s);
      });
      section.classList.remove('is-video-error');
      video.preload = 'auto';
      video.load();
      if (!userPaused && inView) play();
    };

    const play = () => {
      const p = video.play();
      if (p && p.catch) {
        // 自動再生がブロックされた（低電力モードなど）→ ポスターのまま、再生ボタンを出す
        // ※ pause()/load() で中断された場合（AbortError）はユーザー操作ではないので何もしない
        p.catch((err) => {
          if (err && err.name === 'NotAllowedError') { userPaused = true; setToggle(true); }
        });
      }
    };

    video.muted = true;
    video.addEventListener('playing', () => {
      section.classList.add('is-playing');
      setToggle(false);
    });
    video.addEventListener('pause', () => setToggle(true));
    video.addEventListener('error', fallbackToPoster);  // 読み込めたが再生できない（デコード失敗など）

    toggle.addEventListener('click', () => {
      if (video.paused) {
        userPaused = false;
        if (!mountedKey) mount();
        play();
      } else {
        userPaused = true;
        video.pause();
      }
    });

    // 画面外では止めて、戻ったら再開（ユーザーが止めた場合は再開しない）
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(([entry]) => {
        inView = entry.isIntersecting;
        if (!mountedKey) return;
        if (!inView && !video.paused) video.pause();
        else if (inView && !userPaused && video.paused) play();
      }, { threshold: 0.05 }).observe(section);
    }

    if (autoplayAllowed) {
      mount();
    } else {
      video.removeAttribute('autoplay');
      setToggle(true);
    }

    // 縦長⇔横長が切り替わったら、合う動画に入れ替える
    candidates.filter((c) => c.media).forEach((c) => {
      window.matchMedia(c.media).addEventListener('change', () => { if (mountedKey) mount(); });
    });
  }

  /* ---------- 5. モバイル予約バー ---------- */
  const bar = document.getElementById('book-bar');
  const endZone = [document.getElementById('reserve'), footer].filter(Boolean);
  if (bar && hero && 'IntersectionObserver' in window) {
    let pastHero = false;
    const inEnd = new Set();
    const updateBar = () => bar.classList.toggle('is-visible', pastHero && inEnd.size === 0);
    new IntersectionObserver(([entry]) => {
      pastHero = !entry.isIntersecting;
      updateBar();
    }, { rootMargin: '0px 0px -70% 0px' }).observe(hero);  // ヒーローの下端が画面上部30%を過ぎたら表示
    const endObserver = new IntersectionObserver((entries) => {
      entries.forEach((e) => (e.isIntersecting ? inEnd.add(e.target) : inEnd.delete(e.target)));
      updateBar();
    });
    endZone.forEach((el) => endObserver.observe(el));
  }
})();
