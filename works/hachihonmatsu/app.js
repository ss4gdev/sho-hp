/* =========================================================================
   八本松建設（架空デモ） — app.js

   制約（START_HERE.md / README.md）:
   - ビルド不要。ES module も fetch も使わない（file:// で動く）。
   - フォームの値は外部送信も永続保存もしない。
   - ユーザー入力を innerHTML に差し込まない（すべて textContent）。
   ========================================================================= */
(function () {
  'use strict';

  var doc = document;
  var root = doc.documentElement;

  var reduceMotion = !!(window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches);

  function $(sel, ctx) { return (ctx || doc).querySelector(sel); }
  function $$(sel, ctx) {
    return Array.prototype.slice.call((ctx || doc).querySelectorAll(sel));
  }

  var FOCUSABLE = [
    'a[href]', 'button:not([disabled])', 'input:not([disabled])',
    'select:not([disabled])', 'textarea:not([disabled])', '[tabindex]:not([tabindex="-1"])'
  ].join(',');

  /* 表示されている操作要素だけを対象にする（hidden な段の入力欄を拾わない） */
  function focusablesIn(el) {
    return $$(FOCUSABLE, el).filter(function (node) {
      return node.offsetWidth > 0 || node.offsetHeight > 0 || node === doc.activeElement;
    });
  }

  /* Tab / Shift+Tab を与えられた要素群の中で循環させる */
  function cycleTab(ev, containers) {
    if (ev.key !== 'Tab') { return; }

    var items = [];
    containers.forEach(function (c) {
      if (c) { items = items.concat(focusablesIn(c)); }
    });
    if (!items.length) { return; }

    var first = items[0];
    var last = items[items.length - 1];
    var active = doc.activeElement;
    var inside = items.indexOf(active) !== -1;

    if (ev.shiftKey) {
      if (!inside || active === first) { ev.preventDefault(); last.focus(); }
    } else if (!inside || active === last) {
      ev.preventDefault();
      first.focus();
    }
  }

  /* ------------------------------------------------------------------ */
  /* 0. topbar の実測高さ                                                */
  /* ------------------------------------------------------------------ */
  /* 告知バーは狭幅で2行に折り返るため高さが固定できない。
     実測値を --topbar-h に書き戻し、メニュー位置と scroll-padding を合わせる。 */
  var topbar = $('#topbar');

  function measureTopbar() {
    if (!topbar) { return; }
    var h = Math.round(topbar.getBoundingClientRect().height);
    if (h > 0) { root.style.setProperty('--topbar-h', h + 'px'); }
  }

  measureTopbar();
  window.addEventListener('resize', measureTopbar);
  window.addEventListener('orientationchange', measureTopbar);
  window.addEventListener('load', measureTopbar);
  /* Web フォントが後から届くと告知バーの行数が変わることがある */
  if (doc.fonts && doc.fonts.ready && typeof doc.fonts.ready.then === 'function') {
    doc.fonts.ready.then(measureTopbar).catch(function () { /* 失敗しても実害なし */ });
  }

  /* ------------------------------------------------------------------ */
  /* 1. 背景スクロールの抑止                                             */
  /* ------------------------------------------------------------------ */
  /* モーダルとモバイルメニューが同時に使うため参照カウントで管理する。
     iOS Safari は body{overflow:hidden} だけでは背面が動くので
     position:fixed + top で位置を保持し、解除時に復元する。 */
  var scrollLocks = 0;
  var savedScrollY = 0;

  function lockScroll() {
    scrollLocks += 1;
    if (scrollLocks > 1) { return; }
    savedScrollY = window.pageYOffset || root.scrollTop || 0;
    var sbw = window.innerWidth - root.clientWidth;
    doc.body.style.top = (-savedScrollY) + 'px';
    doc.body.classList.add('is-locked');
    if (sbw > 0) { doc.body.style.paddingRight = sbw + 'px'; }
  }

  function unlockScroll() {
    scrollLocks = Math.max(0, scrollLocks - 1);
    if (scrollLocks > 0) { return; }
    doc.body.classList.remove('is-locked');
    doc.body.style.top = '';
    doc.body.style.paddingRight = '';
    window.scrollTo(0, savedScrollY);
  }

  /* ------------------------------------------------------------------ */
  /* 2. スクロール演出（施工事例カードのみ）                              */
  /* ------------------------------------------------------------------ */
  (function initReveal() {
    var targets = $$('.reveal');
    if (!targets.length) { return; }
    if (reduceMotion || !('IntersectionObserver' in window)) { return; }

    root.classList.add('js-anim');

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });

    targets.forEach(function (el) { io.observe(el); });
  }());

  /* ------------------------------------------------------------------ */
  /* 3. モバイルメニュー                                                 */
  /* ------------------------------------------------------------------ */
  var navApi = (function initNav() {
    var toggle = $('#navToggle');
    var nav = $('#primaryNav');
    var scrim = $('#navScrim');
    if (!toggle || !nav) { return { close: function () {}, isOpen: function () { return false; } }; }

    var isOpen = false;

    function open() {
      if (isOpen) { return; }
      isOpen = true;
      nav.classList.add('is-open');
      toggle.setAttribute('aria-expanded', 'true');
      if (scrim) { scrim.hidden = false; }
      lockScroll();

      /* C5: 開いたらメニュー内の最初のリンクへ移動する。
         メニューは DOM 上 toggle より前にあるため、移動しないと
         Tab が scrim の背後の本文へ抜けてしまう。 */
      var first = focusablesIn(nav)[0];
      if (first) { first.focus(); }
    }

    function close(returnFocus) {
      if (!isOpen) { return; }
      isOpen = false;
      nav.classList.remove('is-open');
      toggle.setAttribute('aria-expanded', 'false');
      if (scrim) { scrim.hidden = true; }
      unlockScroll();
      if (returnFocus) { toggle.focus(); }
    }

    toggle.addEventListener('click', function () {
      if (isOpen) { close(true); } else { open(); }
    });

    if (scrim) {
      scrim.addEventListener('click', function () { close(false); });
    }

    /* メニュー内のリンクは同一ページ内遷移。押したら閉じてロックも解く */
    nav.addEventListener('click', function (ev) {
      if (ev.target.closest('a')) { close(false); }
    });

    doc.addEventListener('keydown', function (ev) {
      if (!isOpen) { return; }
      if (ev.key === 'Escape') { ev.preventDefault(); close(true); return; }
      /* C5: メニューと開閉ボタンの範囲で Tab を循環させる */
      cycleTab(ev, [nav, toggle]);
    });

    /* PC 幅に戻ったら開いたままにしない（スクロールロックも解除される） */
    var mq = window.matchMedia('(min-width: 861px)');
    var onChange = function (ev) { if (ev.matches) { close(false); } };
    if (mq.addEventListener) { mq.addEventListener('change', onChange); }
    else if (mq.addListener) { mq.addListener(onChange); }

    return { close: close, isOpen: function () { return isOpen; } };
  }());

  /* ------------------------------------------------------------------ */
  /* 4. 施工事例フィルタ                                                 */
  /* ------------------------------------------------------------------ */
  (function initFilters() {
    var chips = $$('.chip[data-filter]');
    var cards = $$('#workGrid .work-card');
    var status = $('#filterStatus');
    var empty = $('#worksEmpty');
    if (!chips.length || !cards.length) { return; }

    function apply(filter, announce) {
      var shown = 0;
      cards.forEach(function (card) {
        var match = (filter === 'all') || (card.getAttribute('data-category') === filter);
        card.classList.toggle('is-hidden', !match);
        if (match) { shown += 1; }
      });

      chips.forEach(function (chip) {
        chip.setAttribute('aria-pressed',
          chip.getAttribute('data-filter') === filter ? 'true' : 'false');
      });

      /* 初期化時は読み上げを起こさない（マークアップと同じ文字列のため） */
      var text = shown + '件を表示中';
      if (status && announce && status.textContent !== text) { status.textContent = text; }
      if (empty) { empty.hidden = shown !== 0; }
    }

    chips.forEach(function (chip) {
      chip.addEventListener('click', function () {
        apply(chip.getAttribute('data-filter'), true);
      });
    });

    apply('all', false);
  }());

  /* ------------------------------------------------------------------ */
  /* 5. モーダル（事例詳細）                                             */
  /* ------------------------------------------------------------------ */
  var modalApi = (function initModals() {
    var openModal = null;
    var lastTrigger = null;

    function close() {
      if (!openModal) { return; }
      var modal = openModal;
      openModal = null;
      modal.hidden = true;
      unlockScroll();
      if (lastTrigger && doc.contains(lastTrigger)) { lastTrigger.focus(); }
      lastTrigger = null;
    }

    function open(id, trigger) {
      var modal = doc.getElementById(id);
      if (!modal) { return; }
      if (openModal) { close(); }

      lastTrigger = trigger || doc.activeElement;
      openModal = modal;
      modal.hidden = false;
      lockScroll();

      var scroller = $('.modal__scroll', modal);
      if (scroller) { scroller.scrollTop = 0; }

      /* ダイアログ本体へフォーカスする。閉じるボタンに当てると
         支援技術が最初に「閉じる」と読み上げ、見出しが伝わらない。 */
      var dialog = $('.modal__dialog', modal);
      if (dialog) { dialog.focus(); }
    }

    $$('[data-modal]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        open(btn.getAttribute('data-modal'), btn);
      });
    });

    $$('.modal').forEach(function (modal) {
      $$('[data-close]', modal).forEach(function (el) {
        el.addEventListener('click', close);
      });
    });

    doc.addEventListener('keydown', function (ev) {
      if (!openModal) { return; }
      if (ev.key === 'Escape') { ev.preventDefault(); close(); return; }
      cycleTab(ev, [$('.modal__dialog', openModal)]);
    });

    return { close: close, isOpen: function () { return !!openModal; } };
  }());

  /* ------------------------------------------------------------------ */
  /* 6. FAQ アコーディオン                                               */
  /* ------------------------------------------------------------------ */
  (function initAccordion() {
    $$('.accordion__btn').forEach(function (btn) {
      var panel = doc.getElementById(btn.getAttribute('aria-controls'));
      if (!panel) { return; }

      btn.addEventListener('click', function () {
        var expanded = btn.getAttribute('aria-expanded') === 'true';
        btn.setAttribute('aria-expanded', expanded ? 'false' : 'true');
        panel.hidden = expanded;
      });
    });
  }());

  /* ------------------------------------------------------------------ */
  /* 7. お問い合わせフォーム（入力 → 確認 → 完了）                        */
  /* ------------------------------------------------------------------ */
  (function initForm() {
    var form = $('#contactForm');
    if (!form) { return; }

    var stepInput = $('#stepInput');
    var stepConfirm = $('#stepConfirm');
    var stepDone = $('#stepDone');
    var progress = $$('#formProgress .progress__item');

    var summary = $('#errorSummary');
    var summaryList = $('#errorSummaryList');

    var currentStep = 'input';

    var FIELDS = [
      { id: 'topic', label: 'ご相談の種別', required: true,
        message: 'ご相談の種別を選択してください。' },
      { id: 'company', label: '会社名・店名', required: false },
      { id: 'name', label: 'お名前', required: true,
        message: 'お名前を入力してください。' },
      { id: 'email', label: 'メールアドレス', required: true,
        message: 'メールアドレスを入力してください。',
        validate: function (v) {
          /* 形式の目安のみ。デモのため送信はしない。 */
          return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)
            ? null : 'メールアドレスの形式をご確認ください。例）example@example.com';
        } },
      { id: 'message', label: 'ご相談内容', required: true,
        message: 'ご相談内容を入力してください。' }
    ];

    function fieldEl(id) { return doc.getElementById(id); }
    function errorEl(id) { return doc.getElementById(id + '-error'); }

    function clearError(id) {
      var input = fieldEl(id);
      var err = errorEl(id);
      if (input) { input.removeAttribute('aria-invalid'); }
      if (err) { err.hidden = true; err.textContent = ''; }
    }

    function showError(id, message) {
      var input = fieldEl(id);
      var err = errorEl(id);
      if (input) { input.setAttribute('aria-invalid', 'true'); }
      if (err) { err.textContent = message; err.hidden = false; }
    }

    function validate() {
      var errors = [];

      FIELDS.forEach(function (f) {
        clearError(f.id);
        var input = fieldEl(f.id);
        if (!input) { return; }
        var value = String(input.value || '').trim();

        if (f.required && value === '') {
          errors.push({ id: f.id, message: f.message });
          return;
        }
        if (value !== '' && typeof f.validate === 'function') {
          var msg = f.validate(value);
          if (msg) { errors.push({ id: f.id, message: msg }); }
        }
      });

      errors.forEach(function (e) { showError(e.id, e.message); });
      return errors;
    }

    /* エラーサマリ。innerHTML は使わず DOM API とテキストで組み立てる。 */
    function renderSummary(errors) {
      if (!summary || !summaryList) { return; }

      while (summaryList.firstChild) { summaryList.removeChild(summaryList.firstChild); }

      errors.forEach(function (e) {
        var li = doc.createElement('li');
        var a = doc.createElement('a');
        a.href = '#' + e.id;
        a.textContent = e.message;
        a.addEventListener('click', function (ev) {
          ev.preventDefault();
          var input = fieldEl(e.id);
          if (input) { input.focus(); }
        });
        li.appendChild(a);
        summaryList.appendChild(li);
      });

      summary.hidden = false;
      summary.focus();
    }

    function hideSummary() {
      if (summary) { summary.hidden = true; }
    }

    function setProgress(step) {
      var order = ['input', 'confirm', 'done'];
      var current = order.indexOf(step);
      progress.forEach(function (item, i) {
        item.classList.toggle('is-current', i === current);
        item.classList.toggle('is-done', i < current);
        if (i === current) { item.setAttribute('aria-current', 'step'); }
        else { item.removeAttribute('aria-current'); }
      });
    }

    function scrollToContact() {
      var anchor = doc.getElementById('contact');
      if (!anchor) { return; }
      anchor.scrollIntoView({
        behavior: reduceMotion ? 'auto' : 'smooth',
        block: 'start'
      });
    }

    function show(step) {
      currentStep = step;
      stepInput.hidden = step !== 'input';
      stepConfirm.hidden = step !== 'confirm';
      stepDone.hidden = step !== 'done';
      setProgress(step);
    }

    function resetAll() {
      form.reset();
      FIELDS.forEach(function (f) { clearError(f.id); });
      hideSummary();
    }

    /* 確認画面への反映。値はすべて textContent（HTML として解釈させない）。 */
    function fillReview() {
      var map = {
        topic: 'rv-topic',
        company: 'rv-company',
        name: 'rv-name',
        email: 'rv-email',
        message: 'rv-message'
      };
      Object.keys(map).forEach(function (id) {
        var input = fieldEl(id);
        var out = doc.getElementById(map[id]);
        if (!input || !out) { return; }
        var value = String(input.value || '').trim();
        out.textContent = value === '' ? '（未入力）' : value;
      });
    }

    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var errors = validate();

      if (errors.length) {
        renderSummary(errors);
        return;
      }

      hideSummary();
      fillReview();
      show('confirm');
      scrollToContact();

      var title = $('#confirmTitle');
      /* preventScroll: scrollIntoView のアニメーションを focus が打ち消さないように */
      if (title) { title.focus({ preventScroll: true }); }
    });

    /* 入力し直したら、その項目のエラー表示だけ消す */
    FIELDS.forEach(function (f) {
      var input = fieldEl(f.id);
      if (!input) { return; }
      var evName = input.tagName === 'SELECT' ? 'change' : 'input';
      input.addEventListener(evName, function () {
        if (input.getAttribute('aria-invalid') === 'true') { clearError(f.id); }
      });
    });

    var backBtn = $('#backToEdit');
    if (backBtn) {
      backBtn.addEventListener('click', function () {
        show('input');
        scrollToContact();
        var first = fieldEl('topic');
        if (first) { first.focus({ preventScroll: true }); }
      });
    }

    var finalBtn = $('#submitFinal');
    if (finalBtn) {
      finalBtn.addEventListener('click', function () {
        /* デモ: ここでは何も送信しない。保存もしない。 */
        show('done');
        scrollToContact();
        var title = $('#doneTitle');
        if (title) { title.focus({ preventScroll: true }); }
      });
    }

    var restartBtn = $('#restartForm');
    if (restartBtn) {
      restartBtn.addEventListener('click', function () {
        resetAll();
        show('input');
        scrollToContact();
        var first = fieldEl('topic');
        if (first) { first.focus({ preventScroll: true }); }
      });
    }

    /* 種別を指定してフォームへ誘導する（採用CTA・モーダル内CTA） */
    function gotoContact(topic) {
      if (modalApi.isOpen()) { modalApi.close(); }
      if (navApi.isOpen()) { navApi.close(false); }

      /* 完了画面から戻る場合、前回の入力が残ったまま再表示されるのを防ぐ */
      if (currentStep === 'done') { resetAll(); }

      show('input');
      hideSummary();

      var select = fieldEl('topic');
      if (select && topic) {
        var matched = $$('option', select).some(function (opt) {
          return opt.value === topic;
        });
        if (matched) {
          select.value = topic;
          clearError('topic');
        }
      }

      scrollToContact();
      if (select) { select.focus({ preventScroll: true }); }
    }

    var recruitCta = $('#recruitCta');
    if (recruitCta) {
      recruitCta.addEventListener('click', function () { gotoContact('採用'); });
    }

    $$('[data-goto-contact]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        gotoContact(btn.getAttribute('data-topic'));
      });
    });

    show('input');
  }());

}());
