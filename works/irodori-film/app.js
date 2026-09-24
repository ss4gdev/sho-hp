/* ============================================================
 * 📝 お知らせ・ブログ機能（Googleスプレッドシート連携／Headless CMS）
 * ------------------------------------------------------------
 * 【スプレッドシートの準備】
 *  1. Googleスプレッドシートを新規作成し、1行目（見出し行）に左から順に
 *     「公開状態」「投稿日」「カテゴリ」「タイトル」「画像URL」「本文」と入力
 *  2. 2行目以降に記事を1行ずつ入力してください
 *       公開状態 … "公開" と入力した行だけサイトに表示されます（下書きは別の文言でOK）
 *       投稿日   … "2026.09.01" の形式。この日付順に自動で並び替わります
 *       カテゴリ … "お知らせ" "新メニュー" "イベント" 推奨（他の文言でも自動で標準色が付きます）
 *       画像URL … 空欄のままでもOK（店舗のデフォルト画像が自動で使われます）
 *       本文     … 改行はそのまま改行として表示され、本文中のURLは自動でリンクになります
 *  3. 「ファイル」→「共有」→「ウェブに公開」→ 対象シートを選択 →
 *     形式を「カンマ区切りの値(.csv)」にして公開
 *  4. 発行されたURL（.../pub?output=csv）を、下の NEWS_SHEET_CSV_URL に貼り付ける
 *
 * URL未設定の間、および取得に失敗した場合は、自動的に NEWS_FALLBACK_POSTS の
 * デモデータが表示されるため、サイトが空白になることはありません。
 * ============================================================ */
const NEWS_SHEET_CSV_URL = ""; // 例: "https://docs.google.com/spreadsheets/d/xxxxxxxx/pub?output=csv"
const NEWS_PAGE_SIZE = 6;      // 初期表示・「過去のお知らせを見る」1回あたりの追加件数
const NEWS_DEFAULT_IMAGE = "assets/img/news-default.webp"; // 画像URLが空、または読み込み失敗時に使う店舗のデフォルト画像

// スプレッドシート未接続時、または取得失敗時に表示されるデモ用ダミーデータ
const NEWS_FALLBACK_POSTS = [
  { status: "公開", date: "2026.08.20", category: "新メニュー", title: "本日入荷！新鮮な真鯛と平政の刺身盛り合わせ", image: "assets/img/news-sashimi.webp",
    content: "本日は気仙沼から脂の乗った旬の魚が入荷しました。\nまずは刺身でその美味しさをお楽しみください。\n\n目利きが選んだ新鮮な魚を、その日のうちにお造りとしてご提供しています。数量限定となりますので、お早めのご来店をおすすめいたします。\n\n詳しいメニューはこちら：https://www.irodori-kagurazaka.example.com/#ch-signature" },
  { status: "公開", date: "2026.08.15", category: "お知らせ", title: "天然鮎、今シーズンも解禁しました", image: "assets/img/news-ayu.webp",
    content: "清流育ちの天然鮎が入荷しました。\n塩焼きでシンプルに、香りごとお楽しみください。\n\n毎年この時期を心待ちにしてくださるお客様も多い、当店の名物のひとつです。数に限りがございますので、お早めにご注文いただけますと幸いです。" },
  { status: "公開", date: "2026.08.10", category: "イベント", title: "秋の新メニュー「炭火焼き鳥食べ比べ」始めました", image: "assets/img/news-yakitori.webp",
    content: "備長炭で丁寧に焼き上げた串を、部位ごとに食べ比べできる新メニューが登場しました。\n\nもも・つくね・ねぎま・レバー・ハツの5種盛りで、いろいろな部位を少しずつ楽しみたい方にぴったりの一皿です。ぜひコースやお好きな一杯と一緒にお試しください。" },
  { status: "公開", date: "2026.08.05", category: "お知らせ", title: "8月26日（水）は臨時休業とさせていただきます", image: "",
    content: "誠に勝手ながら、設備点検のため8月26日（水）は臨時休業とさせていただきます。\n\nご来店をご検討いただいていたお客様にはご迷惑をおかけいたしますが、何卒よろしくお願い申し上げます。翌27日（木）は通常通り17:00より営業いたします。" },
  { status: "公開", date: "2026.07.28", category: "イベント", title: "厳選日本酒の利き酒フェア、好評開催中です", image: "",
    content: "全国の蔵元から取り寄せた10種類の日本酒を、飲み比べセットでお楽しみいただけます。\n\n辛口から甘口まで、店主が季節に合わせて厳選しました。気になる銘柄が見つかったら、ボトルでのご注文も承っております。" },
  { status: "公開", date: "2026.07.15", category: "お知らせ", title: "夏の営業時間のお知らせ", image: "",
    content: "夏季期間（7月〜9月）も通常通り17:00〜24:00で営業しております。\n\n多くのお客様にご来店いただいており、特に週末は満席となることがございます。確実にご案内するため、事前のネット予約をおすすめしております。" },
  { status: "公開", date: "2026.06.30", category: "新メニュー", title: "季節の炙り〆鯖、始めました", image: "",
    content: "脂の乗った〆鯖を、皮目だけ炭火で軽く炙った季節の一品です。\n\n爽やかな酸味と炙りの香ばしさが同時に楽しめます。日本酒との相性も抜群ですので、ぜひご賞味ください。" },
  { status: "下書き", date: "2026.08.25", category: "お知らせ", title: "（下書き）年末年始の営業について", image: "",
    content: "この記事は「公開状態」が「公開」以外のため、サイトには表示されません。" },
];

// カテゴリーごとのバッジ色。新しいカテゴリー名を使いたい場合はここに1行追加してください
const NEWS_CATEGORY_COLORS = {
  "お知らせ":       "#0284C7",
  "新メニュー":     "#C4501F",
  "イベント":       "#7E3AAF",
  "店主のつぶやき": "#047857",
};
const NEWS_DEFAULT_CATEGORY_COLOR = "#3A2416"; // 上に登録がないカテゴリー名の場合はこの色になります

// ---- 以下、記事を自動で取得・表示するための処理です（通常は編集不要） ----

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str ?? '';
  return div.innerHTML;
}

// 本文中のURLを自動でリンク化（XSS対策のためエスケープ後に処理）
function linkifyText(str) {
  const escaped = escapeHtml(str);
  return escaped.replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
}

function newsCategoryColor(category) {
  return NEWS_CATEGORY_COLORS[category] || NEWS_DEFAULT_CATEGORY_COLOR;
}

// ---- CSVパーサー（ダブルクォート・カンマ・改行を含むセルに対応した簡易実装） ----
function parseCSV(text) {
  const rows = [];
  let row = [], field = '', inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"') {
        if (text[i + 1] === '"') { field += '"'; i++; }
        else { inQuotes = false; }
      } else {
        field += c;
      }
    } else if (c === '"') {
      inQuotes = true;
    } else if (c === ',') {
      row.push(field); field = '';
    } else if (c === '\n') {
      row.push(field); rows.push(row); row = []; field = '';
    } else if (c === '\r') {
      // 無視（\r\n の \r 部分）
    } else {
      field += c;
    }
  }
  if (field.length > 0 || row.length > 0) { row.push(field); rows.push(row); }
  return rows.filter(r => r.some(cell => cell.trim() !== ''));
}

function csvRowsToPosts(rows) {
  if (rows.length < 2) return [];
  const header = rows[0].map(h => h.trim());
  const idx = {
    status: header.indexOf('公開状態'),
    date: header.indexOf('投稿日'),
    category: header.indexOf('カテゴリ'),
    title: header.indexOf('タイトル'),
    image: header.indexOf('画像URL'),
    content: header.indexOf('本文'),
  };
  return rows.slice(1).map(cols => ({
    status: (cols[idx.status] || '').trim(),
    date: (cols[idx.date] || '').trim(),
    category: (cols[idx.category] || '').trim(),
    title: (cols[idx.title] || '').trim(),
    image: (cols[idx.image] || '').trim(),
    content: (cols[idx.content] || '').trim(),
  }));
}

async function fetchSheetPosts() {
  if (!NEWS_SHEET_CSV_URL) return NEWS_FALLBACK_POSTS;
  try {
    const res = await fetch(NEWS_SHEET_CSV_URL);
    if (!res.ok) throw new Error('CSVの取得に失敗しました（HTTP ' + res.status + '）');
    const text = await res.text();
    const posts = csvRowsToPosts(parseCSV(text));
    return posts.length ? posts : NEWS_FALLBACK_POSTS;
  } catch (err) {
    console.warn('お知らせスプレッドシートを取得できなかったため、デモデータを表示しています。', err);
    return NEWS_FALLBACK_POSTS;
  }
}

function newsImageHTML(post, lazy) {
  const src = post.image || NEWS_DEFAULT_IMAGE;
  return `<img src="${escapeHtml(src)}" alt="" data-news-img-fallback${lazy ? ' loading="lazy"' : ''}>`;
}

function renderNewsCard(post, index) {
  return `
  <button type="button" class="news-card reveal" data-index="${index}">
    <span class="news-card__img">
      ${newsImageHTML(post, true)}
      <span class="badge" style="background:${newsCategoryColor(post.category)}">${escapeHtml(post.category)}</span>
    </span>
    <span class="news-card__body">
      <span class="news-date">${escapeHtml(post.date)}</span>
      <span class="news-card__title">${escapeHtml(post.title)}</span>
      <span class="news-card__excerpt">${escapeHtml(post.content.replace(/\n+/g, ' '))}</span>
      <span class="news-card__more">続きを読む →</span>
    </span>
  </button>`;
}

// ---- 表示状態（公開記事の一覧・現在の表示件数） ----
let newsAllPosts = [];
let newsShownCount = 0;

function renderNewsGrid() {
  const grid = document.getElementById('news-grid');
  const empty = document.getElementById('news-empty');
  const loadMoreBtn = document.getElementById('news-load-more');

  if (newsAllPosts.length === 0) {
    grid.innerHTML = '';
    empty.hidden = false;
    loadMoreBtn.hidden = true;
    return;
  }
  empty.hidden = true;
  grid.innerHTML = newsAllPosts.slice(0, newsShownCount).map(renderNewsCard).join('');
  loadMoreBtn.hidden = newsShownCount >= newsAllPosts.length;
  grid.querySelectorAll('.reveal').forEach(el => revealObserver ? revealObserver.observe(el) : el.classList.add('revealed'));
}

async function initNews() {
  const rawPosts = await fetchSheetPosts();
  newsAllPosts = rawPosts
    .filter(p => p.status === '公開')
    .sort((a, b) => b.date.localeCompare(a.date));
  newsShownCount = Math.min(NEWS_PAGE_SIZE, newsAllPosts.length);
  renderNewsGrid();
}

document.getElementById('news-load-more').addEventListener('click', () => {
  newsShownCount = Math.min(newsShownCount + NEWS_PAGE_SIZE, newsAllPosts.length);
  renderNewsGrid();
});

// 画像URLが空、または読み込みに失敗した場合、店舗のデフォルト画像に自動で切り替える（キャプチャフェーズで検知）
document.addEventListener('error', (e) => {
  const img = e.target;
  if (!img || img.tagName !== 'IMG') return;
  if (img.dataset.newsImgFallback !== undefined && !img.dataset.newsImgFallbackApplied) {
    img.dataset.newsImgFallbackApplied = '1';
    img.src = NEWS_DEFAULT_IMAGE;
  }
}, true);

/* ============================================================
 * モーダル共通処理（予約・お知らせ詳細で共用）
 * ============================================================ */
let lastFocus = null;
function lockScroll(lock) { document.body.style.overflow = lock ? 'hidden' : ''; }
function showModal(modal) {
  lastFocus = document.activeElement;
  modal.hidden = false;
  requestAnimationFrame(() => modal.classList.add('is-open'));
  lockScroll(true);
  const focusable = modal.querySelector('.modal__view:not([hidden]) button, .modal__close');
  if (focusable) setTimeout(() => focusable.focus(), 50);
}
function closeModal(modal) {
  if (modal.hidden) return;
  modal.classList.remove('is-open');
  lockScroll(false);
  setTimeout(() => { modal.hidden = true; }, 300);
  if (lastFocus && lastFocus.focus) lastFocus.focus({ preventScroll: true });
}

// ---- 記事詳細モーダル ----
const newsModal = document.getElementById('news-modal');
const newsModalImage = document.getElementById('news-modal-image');
const newsModalCategory = document.getElementById('news-modal-category');
const newsModalDate = document.getElementById('news-modal-date');
const newsModalTitle = document.getElementById('news-modal-title');
const newsModalContent = document.getElementById('news-modal-content');

function openNewsModal(post) {
  newsModalImage.innerHTML = newsImageHTML(post, false);
  newsModalCategory.textContent = post.category;
  newsModalCategory.style.background = newsCategoryColor(post.category);
  newsModalDate.textContent = post.date;
  newsModalTitle.textContent = post.title;
  newsModalContent.innerHTML = linkifyText(post.content).replace(/\n/g, '<br>');
  showModal(newsModal);
}

document.getElementById('news-grid').addEventListener('click', (e) => {
  const card = e.target.closest('.news-card');
  if (!card) return;
  const post = newsAllPosts[Number(card.dataset.index)];
  if (post) openNewsModal(post);
});
newsModal.querySelectorAll('[data-news-close]').forEach(el => {
  el.addEventListener('click', () => closeModal(newsModal));
});

/* ============================================================
 * 予約フォーム：確認 → 送信中 → 完了 の3ステップ制御
 * ============================================================ */
const form = document.getElementById('reserve-form');
const reserveModal = document.getElementById('reserve-modal');
const modalSummary = document.getElementById('modal-summary');
const viewConfirm = document.getElementById('reserve-view-confirm');
const viewLoading = document.getElementById('reserve-view-loading');
const viewSuccess = document.getElementById('reserve-view-success');
const viewError = document.getElementById('reserve-view-error');
const confirmList = document.getElementById('reserve-confirm-list');

function showReserveView(view) {
  [viewConfirm, viewLoading, viewSuccess, viewError].forEach(v => { v.hidden = true; });
  view.hidden = false;
  const btn = view.querySelector('button, a');
  if (btn && !reserveModal.hidden) btn.focus({ preventScroll: true });
}

// 来店日：本日より前の日付は選択できないようにする
const reserveDateInput = form.querySelector('input[name="date"]');
if (reserveDateInput) {
  const today = new Date();
  const yyyy = today.getFullYear();
  const mm = String(today.getMonth() + 1).padStart(2, '0');
  const dd = String(today.getDate()).padStart(2, '0');
  reserveDateInput.min = `${yyyy}-${mm}-${dd}`;
}

let pendingFormData = null;

form.addEventListener('submit', function (e) {
  e.preventDefault();

  // Honeypot チェック：ボットが自動入力した場合は静かに処理を中断（人間には何も表示しない）
  const gotcha = form.querySelector('[name="_gotcha"]').value;
  if (gotcha) { form.reset(); return; }

  const data = new FormData(form);
  pendingFormData = {
    date: data.get('date') || '',
    time: data.get('time') || '',
    guests: data.get('guests') || '',
    course: data.get('course') || '',
    seat: data.get('seat') || '',
    name: data.get('name') || '',
    furigana: data.get('furigana') || '',
    phone: data.get('phone') || '',
    email: data.get('email') || '',
    note: data.get('note') || '',
  };

  const rows = [
    ['来店日', pendingFormData.date],
    ['来店時間', pendingFormData.time],
    ['人数', pendingFormData.guests],
    ['コース', pendingFormData.course],
    ['お席', pendingFormData.seat],
    ['お名前', pendingFormData.name + (pendingFormData.furigana ? `（${pendingFormData.furigana}）` : '')],
    ['お電話番号', pendingFormData.phone],
    ['メールアドレス', pendingFormData.email],
  ];
  if (pendingFormData.note) rows.push(['ご要望', pendingFormData.note]);

  confirmList.innerHTML = rows.map(([label, value]) => `
    <div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`).join('');

  showReserveView(viewConfirm);
  showModal(reserveModal);
});

document.getElementById('reserve-confirm-back').addEventListener('click', () => closeModal(reserveModal));

/* ============================================================
 * 📩 予約フォームの送信先（Google Apps Script Webアプリ）
 * ------------------------------------------------------------
 * 【GAS Webアプリの準備】
 *  1. 予約データを受け取りたいGoogleスプレッドシートを開き、
 *     「拡張機能」→「Apps Script」を開く
 *  2. doPost(e) 関数を用意し、e.postData.contents を JSON.parse して
 *     スプレッドシートへの1行追加・スタッフへの通知メール送信・
 *     お客様への自動返信メール送信（MailApp.sendEmail など）を実装する
 *  3. 「デプロイ」→「新しいデプロイ」→種類「ウェブアプリ」を選択し、
 *     実行するユーザー：自分／アクセスできるユーザー：全員 に設定してデプロイ
 *  4. 発行された「ウェブアプリのURL」（.../exec で終わるURL）を、
 *     下の GAS_RESERVATION_URL に貼り付ける
 *
 * URL未設定の間は、送信を模したデモ動作（実際には送信されません）になります。
 * ============================================================ */
const GAS_RESERVATION_URL = "https://script.google.com/macros/s/AKfycbxsEBS79lm6o_Tz_3Z7GIYLUcqOYgQIL_9KsW8BpYbHqv0AVGAyy79PBOx_hempt7CK/exec";

// 実際の送信処理。GAS Webアプリはブラウザからのfetchに対してCORSヘッダーを
// 返さないため、mode:'no-cors' ＋ Content-Type:'text/plain' で
// プリフライトを避けて送信します（GAS側では e.postData.contents を
// JSON.parse して受け取ってください）。no-cors のレスポンスは中身を
// 読み取れない仕様のため、fetch自体が例外を投げなければ成功とみなします。
async function handleSubmit(payload) {
  if (!GAS_RESERVATION_URL) {
    // デモ用：送信先が未設定のため、疑似的な待機のみ行います。
    await new Promise(resolve => setTimeout(resolve, 1200));
    return true;
  }

  await fetch(GAS_RESERVATION_URL, {
    method: 'POST',
    mode: 'no-cors',
    headers: { 'Content-Type': 'text/plain;charset=utf-8' },
    body: JSON.stringify(payload),
  });
  return true;
}

document.getElementById('reserve-confirm-submit').addEventListener('click', async () => {
  showReserveView(viewLoading);
  try {
    await handleSubmit(pendingFormData);
    modalSummary.textContent = `${pendingFormData.name} 様、${pendingFormData.date} ${pendingFormData.time} ／ ${pendingFormData.guests} でリクエストを受け付けました。店舗より折り返しご連絡いたします。`;
    showReserveView(viewSuccess);
    form.reset();
    document.getElementById('seat-any').checked = true;
  } catch (err) {
    // 送信に失敗した場合（ネットワークエラー等）は、電話予約へ誘導するエラー画面を表示します
    console.error('予約送信エラー:', err);
    showReserveView(viewError);
  }
});

document.getElementById('reserve-error-retry').addEventListener('click', () => {
  document.getElementById('reserve-confirm-submit').click();
});
document.getElementById('reserve-error-close').addEventListener('click', () => closeModal(reserveModal));
document.getElementById('modal-close').addEventListener('click', () => closeModal(reserveModal));
document.getElementById('modal-backdrop').addEventListener('click', () => closeModal(reserveModal));

/* ============================================================
 * ヘッダー・メニュー・ページ内リンク
 * ============================================================ */
const header = document.getElementById('siteHeader');
const stageEl = document.getElementById('top');
const menuToggle = document.getElementById('menuToggle');
const menuPanel = document.getElementById('menuPanel');
let lastY = window.scrollY;
let headerTick = 0;

function setMenu(open) {
  menuPanel.hidden = !open;
  menuToggle.setAttribute('aria-expanded', String(open));
  menuToggle.setAttribute('aria-label', open ? 'メニューを閉じる' : 'メニューを開く');
  header.classList.remove('is-hidden');
  if (open) header.setAttribute('data-tone', 'dark');
  else updateHeader();
  lockScroll(open);
}
menuToggle.addEventListener('click', () => setMenu(menuPanel.hidden));

function updateHeader() {
  headerTick = 0;
  if (!menuPanel.hidden) return;
  const y = window.scrollY;
  const hdH = header.offsetHeight;
  // 映像ステージの上では透明＋白文字、第2部に入ったら和紙色＋墨文字
  const inStage = stageEl.getBoundingClientRect().bottom > hdH;
  header.setAttribute('data-tone', inStage ? 'dark' : 'light');
  // 下へ進むときは隠して映像を広く見せ、上へ戻すと出す
  if (y > lastY + 6 && y > 160 && !header.contains(document.activeElement)) header.classList.add('is-hidden');
  else if (y < lastY - 6 || y <= 160) header.classList.remove('is-hidden');
  lastY = y;
}
window.addEventListener('scroll', () => { if (!headerTick) headerTick = requestAnimationFrame(updateHeader); }, { passive: true });
header.addEventListener('focusin', () => header.classList.remove('is-hidden'));
updateHeader();

function scrollToTarget(id) {
  if (id === 'top') { window.scrollTo({ top: 0, behavior: 'smooth' }); return; }
  const el = document.getElementById(id);
  if (!el) return;
  // 映像ステージ内の章は、その場面が映る再生位置へスクロールする
  if (el.closest('.stage') && window.IrodoriStage && window.IrodoriStage.goTo(id)) return;
  const top = el.getBoundingClientRect().top + window.scrollY - header.offsetHeight + 1;
  window.scrollTo({ top, behavior: 'smooth' });
}
document.addEventListener('click', (e) => {
  const link = e.target.closest('a[href^="#"]');
  if (!link) return;
  const id = link.getAttribute('href').slice(1);
  if (!id) return;
  if (!document.getElementById(id)) return;
  e.preventDefault();
  if (!menuPanel.hidden) setMenu(false);
  scrollToTarget(id);
  if (id === 'reservation') {
    const first = form.querySelector('input, select');
    if (first) setTimeout(() => first.focus({ preventScroll: true }), 900);
  }
});

document.addEventListener('keydown', (e) => {
  if (e.key !== 'Escape') return;
  if (!menuPanel.hidden) setMenu(false);
  closeModal(reserveModal);
  closeModal(newsModal);
});

/* ---- reveal on scroll ---- */
const revealObserver = 'IntersectionObserver' in window ? new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('revealed');
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.12, rootMargin: '0px 0px -60px 0px' }) : null;
document.querySelectorAll('.reveal').forEach(el => revealObserver ? revealObserver.observe(el) : el.classList.add('revealed'));

initNews();
document.getElementById('year').textContent = new Date().getFullYear();
