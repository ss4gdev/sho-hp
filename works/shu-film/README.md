# SHU 映像版（works/shu-film）

現行の SHU（`works/shu`）を、**ヒーロー映像を主役にしたレイアウト**へ組み直した作業用コピーです。
ブランド名・コピー・メニュー・スタッフ・店舗情報・色・書体は現行 SHU のものをそのまま使っています。
`works/shu` のファイルには一切手を入れていません。

公開URL（main に反映後）: https://ss4gdev.github.io/sho-hp/works/shu-film/

```
works/shu-film/
├─ index.html              ページ本体（HTML / CSS / JavaScript のみ。フレームワークなし）
├─ style.css               デザイン
├─ app.js                  ヘッダー / メニュー / 表示アニメーション / ヒーロー動画 / 予約バー
├─ assets/
│  ├─ hero/                ヒーローのポスター画像（動画が無い・読めないときに表示）
│  ├─ img/                 写真（AVIF / WebP / JPG）
│  └─ video/               ← ヒーロー動画をここに置く（現在は未配置）
└─ _tools/build_images.py  写真の書き出しスクリプト
```

---

## 1. ヒーロー動画

想定している映像：15秒ループ（ロングヘアの女性 → 美容師がカット → ショートヘア完成）、音声なし。

### ファイル

| 置く場所 | 用途 | サイズの目安 |
| --- | --- | --- |
| `assets/video/hero-pc.mp4` | 横長の画面（PC・タブレット横） | 1920×1080（16:9）/ H.264 / 6MB 以下 |
| `assets/video/hero-pc.webm` | 同上（対応ブラウザではこちらを優先） | 同上 / VP9 または AV1 |
| `assets/video/hero-sp.mp4` | 縦長の画面（スマホ・タブレット縦） | 1080×1920（9:16）/ H.264 / 5MB 以下 |
| `assets/video/hero-sp.webm` | 同上 | 同上 / VP9 または AV1 |

### 構図

- **PC版**：人物は画面の中央〜やや右（横 55〜70% あたり）。左側 40% には文字が載るので、明るすぎる物や細かい柄を置かない。
- **スマホ版**：顔は画面の上から 20〜45% あたり。下 35% には文字が載る。
- 文字の読みやすさのために、左側（PC）/ 下側（スマホ）にだけ薄いグラデーションを重ねています。画面全体は暗くしません。

### 差し替え手順

1. 上の4ファイルを `assets/video/` に置く
2. `index.html` の `<section class="hero" id="top" data-hero data-video="off" …>` の `off` を **`on`** にする
3. （推奨）ポスター画像を動画の1コマ目に替える
   - 1コマ目を書き出し（下の例）、`_tools/build_images.py` の `hero/poster-pc` と `hero/poster-sp` の `src` を差し替えて実行
   - `hero/poster-pc` の `"extend"`（いまの仮画像を横長にするための処理）と、`hero/poster-sp` の `"crop"` は消してください

スマホ用（hero-sp）を作らない場合は、`index.html` の `data-media` が付いた `<source>` 2行を削除すると、全画面で hero-pc を使います。

### 書き出し例（ffmpeg）

```sh
# PC（横長）
ffmpeg -i master.mov -an -t 15 -vf "scale=1920:-2,fps=30" -c:v libx264 -preset slow -crf 24 -pix_fmt yuv420p -movflags +faststart assets/video/hero-pc.mp4
ffmpeg -i master.mov -an -t 15 -vf "scale=1920:-2,fps=30" -c:v libvpx-vp9 -b:v 0 -crf 36 -row-mt 1 assets/video/hero-pc.webm

# スマホ（縦長）
ffmpeg -i master-vertical.mov -an -t 15 -vf "scale=1080:-2,fps=30" -c:v libx264 -preset slow -crf 25 -pix_fmt yuv420p -movflags +faststart assets/video/hero-sp.mp4
ffmpeg -i master-vertical.mov -an -t 15 -vf "scale=1080:-2,fps=30" -c:v libvpx-vp9 -b:v 0 -crf 38 -row-mt 1 assets/video/hero-sp.webm

# ポスター用の1コマ目
ffmpeg -i assets/video/hero-pc.mp4 -frames:v 1 poster-pc.png
ffmpeg -i assets/video/hero-sp.mp4 -frames:v 1 poster-sp.png
```

容量が目安を超える場合は `-crf` の数字を 2 ずつ上げてください（数字が大きいほど軽く・粗くなります）。

### 動画まわりの動き（app.js）

- 縦長の画面（縦横比 5:6 以下）では hero-sp を先に試し、無ければ hero-pc を使う
- 読み込み失敗・自動再生のブロック（iPhone の低電力モードなど）→ ポスター画像のまま表示
- 「視差効果を減らす」設定・省データモードでは自動再生しない（右下の Play で再生できる）
- 右下に一時停止ボタン（5秒を超えて自動で動く映像には止める手段が必要なため）
- ヒーローが画面外に出たら一時停止し、戻ったら再開
- 映像はポスターの上にフェードインするので、読み込み中も画面が空白になりません

---

## 2. 写真

`_tools/build_images.py` の `MANIFEST` にある `src`（元画像のパス）を変えて実行すると、
同じファイル名で AVIF / WebP / JPG が書き出されます。**index.html を直す必要はありません。**

```sh
pip install pillow   # AVIF 対応は Pillow 11.2 以降
python3 works/shu-film/_tools/build_images.py   # リポジトリのルートで実行
```

| セクション | 書き出し先（`assets/` 以下） | 表示の比率 | いまの元画像（works/shu） |
| --- | --- | --- | --- |
| Hero | `hero/poster-pc` / `hero/poster-sp` | 16:9 / 縦長 | `images/hero-main.jpg`（PC用は背景を左右に延長） |
| Concept | `img/concept/concept` | 4:5 | `gallery/yoshin/yoshin-2.jpg` |
| Transformation | `img/transformation/before` / `after` | 4:5 | `yoshin-4.jpg` / `short-3.jpg` |
| Style Gallery | `img/gallery/01`〜`06`（01・04 が大きい写真） | 大 3:4〜4:5 / 小 4:5 | short-1, short-2, layer-4, yoshin-1, short-4, layer-2 |
| Stylist | `img/stylist/karin`（大）/ `rise` / `ryoko`（小） | 4:5 | `1.jpg` / `2.jpg` / `3.jpg` |
| Salon | `img/salon/main` / `detail` | 3:2〜4:3 / 4:5 | `images/concept.jpg`（detail は同じ写真の切り抜き） |

- **Transformation** は別々のモデル写真を仮に使っているため、「※ 掲載写真はイメージです。」と注記しています。同じお客様のビフォー・アフターに差し替えたら、`index.html` の `tf__note` 内の注記を消してください。
- **Salon の detail** は店内写真の切り抜き（仮）です。店内の別カット（鏡・シャンプー台・入口など）があれば差し替えてください。
- 手で差し替える場合は、同じ名前の **3形式すべて**（`.avif` `.webp` `.jpg`）を上書きしてください。

---

## 3. レイアウトの決まりごと

- **モバイルを基本**に書き、768px / 1024px / 1200px 以上で PC 用に上書きしています。PC を縮小しただけの画面はありません。
- **ヒーローだけ**は画面の幅ではなく縦横比（5:6）で切り替えます（スマホ横向き・タブレット縦でも自然に見せるため）。
- 余白（`style.css` 冒頭の変数）

  | | モバイル | PC |
  | --- | --- | --- |
  | 左右 `--gutter` | 24px（360px 未満は 20px） | 48〜72px |
  | セクション間 `--section` | 96px | 136〜168px |
  | 見出し下 `--head-gap` | 40px | 72〜88px |

- **Style Gallery**
  - モバイル：大 01 → 小 02/03 → 大 04 → 小 05/06（写真下 16px、スタイル名の後 56px、ブロック間 64px、2枚の間 14px）
  - PC（1024px〜）：[大 01 ｜ 小 02・03 を対角に] → 余白 → [小 05・06 を対角に ｜ 大 04]
- 色は現行 SHU の cream / greige / beige / sand / ink / charcoal に、同系色の ivory（Transformation の帯）を足しただけです。
- アニメーションはフェード・わずかな移動・画像ホバー時の 1.02 倍拡大のみ。「視差効果を減らす」設定では止まります。

---

## 4. 本番（works/shu）への反映

新デザインで確定したら、次のファイルを `works/shu/` にコピーします。

```sh
cp works/shu-film/index.html works/shu-film/style.css works/shu-film/app.js works/shu/
cp -r works/shu-film/assets works/shu-film/_tools works/shu/
```

- `works/shu/images/` と `works/shu/1.jpg〜3.jpg` は `_tools/build_images.py` の元画像なので、**削除せず残してください**。
- 反映後に `works/shu-film/` を残すか消すかは、トップページの制作事例にどう載せるかで決めてください（いろどりは「いろどり」と「いろどり（映像版）」を並べて掲載しています）。
- 予約（Hot Pepper Beauty・LINE）、Instagram、Google マップのリンクは、現行 SHU と同じ仮リンクです。
