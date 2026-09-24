# SHU ヒーロー背景動画 プリビズ（SHU_Hero_Video_Previs）

美容室SHU公式HPのヒーロー背景用15秒動画のプリビズです。
フォトリアルさではなく、**構図・人物配置・美容師の動線・髪型変化（ロング→ミディアム→ショート）・タイミング**が一目で分かることを優先しています。
Higgsfield などの動画生成AIに渡す「構図・動き・時間軸のリファレンス」としても使えます。

## ファイル

| ファイル | 内容 |
|---|---|
| `SHU_Hero_Previs_15s.mp4` | 15秒・16:9・音声なしのプレビュー動画（1280×720 / 30fps）。HP背景の確認・Higgsfield参照用のクリーン版 |
| `SHU_Hero_Previs_15s_guides.mp4` | 上と同じ映像に、左側のHPテキスト領域（左38%）・スマホ9:16中央クロップ線・タイムコード／カット名を重ねた確認用 |
| `composition_check.png` | PC 16:9（テキスト仮置き）とスマホ9:16クロップを要所の4時点で並べた構図チェック |
| `SHU_Hero_Video_Previs.blend` | Blender 4.4 のシーン一式（カメラ・人物・セット・アニメーション・髪型切替） |
| `build_previs.py` | `.blend` をゼロから生成するスクリプト（全モデル・全キーフレームをここで定義） |
| `make_review.py` | レンダリング済みフレームから上記 mp4 と構図チェック画像を作るスクリプト |

## タイムライン（30fps・450フレーム）

| 秒 | フレーム | カット | 女性（ほぼ静止） | 美容師（動きの主役） | 髪 |
|---|---|---|---|---|---|
| 0–3 | 1–90 | **CUT1 Before** | 少し喋る・瞬き・わずかな視線移動 | 後ろから髪を触る → 両手で流れを整える → 前に下りた毛先を手に取りバランスを見る → 終盤に毛先を少しカット（2.45s / 2.75s） | ロング・ドライ |
| 3 | 91 | ジャンプカット | — | 立ち位置が変わる（時間経過） | 濡れ髪に切替 |
| 3–4.55 | 91–137 | **CUT2 Cutting** | 静止・瞬き | 頭頂の毛束を持ち上げてカット（3.8 / 4.1 / 4.4s） | ロング・ウェット |
| 4.55 | 138 | 髪型切替 | — | 左サイドでカット → 長い毛が落ちる | **ロング → ミディアム** |
| 4.55–6.85 | 138–205 | CUT2 | 静止・短く一言 | 女性の右側（画面右）へ移動しサイドの形を整えてカット → 後方中央で後頭部の毛束を持ち上げてカット | ミディアム・ウェット |
| 6.85 | 206 | 髪型切替 | — | カット → 毛が落ちる | **ミディアム → ショート** |
| 7.5–10 | 226–300 | CUT2 後半 | 静止 | ハサミをドライヤーに持ち替え、画面左上から乾かす／もう片方の手で頭頂・サイドをほぐす・毛束を持ち上げる | ショート・ウェット→ドライ（風で髪が揺れる） |
| 10 | 301 | ジャンプカット | — | 立ち位置が変わる | スタイリング済みショートに切替 |
| 10–13 | 301–390 | **CUT3 After** | 少し喋る → 鏡を見るように視線を少し動かす | 毛先を整える → スタイリング剤を手になじませる仕草 → 両手で手ぐし → 前髪・顔周りを整える | ショート・ドライ |
| 13–15 | 391–450 | Final hold | 自然に笑顔（13.55sで最大）、以降は瞬きもしない | 両手を女性の肩に置き、鏡（カメラ）を見る。**13.95s以降は大きな動きなし** | ショート完成形 |

Blender のタイムラインには各区間のマーカー（`CUT1 Before / Long` など）を入れてあります。

## 構図

- **カメラは1台・15秒間完全固定**（パン／チルト／ズーム／ドリーなし）。63mm相当の標準〜軽い中望遠、女性の正面からわずかに斜め、目線よりやや高い位置。
- 女性は画面の**中央やや右（約56%）**。顔と髪型の主要シルエットはスマホ9:16中央クロップ（横34〜66%）に収まります。
- **画面左38%はHPテキスト用の余白**（無地の壁のみ・人物や小物なし）。女性の顔・髪にテキストが重なりません。
- 美容師は女性の後方〜斜め後方（主に画面右寄り）。施術に合わせて後方中央・左右へゆっくり移動します。
- サロン要素は画面右奥のアーチミラー＋木製カウンター＋空の椅子のみ。ベージュ／アイボリー／淡いグレー／ナチュラルウッドの配色、明るく柔らかい窓光。

## .blend の構成

| コレクション / オブジェクト | 役割 |
|---|---|
| `01_Camera / CAM_Hero_Fixed` | 唯一のカメラ（固定） |
| `03_Client / CLIENT_HEAD_CTRL` | 女性の頭のコントローラ（ごく小さな回転のみ）。顔パーツ・髪はこの子 |
| `Client_Mouth` のシェイプキー `Talk` / `Smile` | 口の動き・笑顔 |
| `Client_EyeL/R`（Scale Z）・`Client_IrisL/R`（位置） | 瞬き・視線 |
| `04_Client_Hair / hair_long, hair_medium, hair_short` | 3種類の簡易ヘアモデル。**表示/非表示（Visibility）のキーで切替** |
| マテリアル `M_Hair_Client` のノード `Wetness`（0=ドライ, 1=ウェット） | 濡れ髪表現（色・ツヤ）をキーで変化 |
| `hair_section_lifted` | 美容師が持ち上げる毛束（Stretch To で指先 `grip.L` まで伸びる） |
| `hair_clippings` | カット時に落ちる毛 |
| `05_Stylist / STYLIST_RIG` | 美容師のリグ（本体位置・前傾はこれをキー） |
| `IK_hand.R` / `IK_hand.L` | 美容師の手首ターゲット（腕はIKで追従）。右手＝画面左側の腕（ハサミ／ドライヤー） |
| `stylist_look_target` | 美容師の視線（頭が向く先） |
| `06_Props / Prop_Scissors, Prop_Dryer` | ハサミ（開閉アニメーション）・ドライヤー |

## 再生成・再レンダリング

```bash
pip install bpy==4.4.0 "numpy<2" pillow imageio-ffmpeg
python3 build_previs.py                              # .blend を再生成
python3 build_previs.py --stills out/ --res 960      # 要所の静止画だけ確認
python3 build_previs.py --render frames/ --res 1280 --samples 8   # 全フレーム書き出し
python3 make_review.py frames/                        # mp4 と構図チェック画像を作成
```

`.blend` 自体は 1920×1080 / Cycles 24サンプルに設定してあります。GPU環境ならそのまま Render Animation でフルHD版を書き出せます
（今回の mp4 は CPU のみの環境で出力したため 1280×720・8サンプル＋デノイズです）。

## Higgsfield に渡すときのポイント

- `SHU_Hero_Previs_15s.mp4`（ガイドなし版）を参照動画として使用。ガイド版は文字や線が生成結果に写り込む恐れがあるため渡さないでください。
- 引き継いでほしい要素：固定カメラ、人物の位置関係（女性は中央やや右・美容師は後方）、左側の余白、各区間の時間配分、女性はほぼ動かず美容師が動く、ロング→ショートの変化。
- 置き換えてほしい要素：人物・髪・肌・衣装・店内をフォトリアルな韓国系ヘアサロンの質感に。
- プロンプト例：
  > Static locked-off camera, 16:9. Bright, minimal Korean-style hair salon in beige, ivory and natural wood, soft window light. A young woman sits still in a salon chair wearing an ivory cutting cape, centre-right of frame; a stylist stands behind her and does all the movement. 0–3 s: long dark-brown hair, stylist smooths it and trims the ends. 3–10 s: wet hair, stylist lifts sections and cuts, hair gets shorter in stages (long → shoulder length → short bob), then blow-dries it. 10–15 s: finished short bob with see-through bangs, stylist finger-combs and adjusts the fringe, then rests hands on her shoulders; she smiles softly. Left third of the frame stays plain wall for website text. Calm, elegant, no camera movement.

## チェックリスト

- [x] 15秒の通しプリビズ
- [x] 0〜3秒でロングヘアが明確（毛先が胸元まで見える）
- [x] 3〜10秒でカット工程（持ち上げ・カット・左右移動・後頭部・ドライヤー）が分かる
- [x] 3〜10秒の中で髪が段階的に短くなる（4.55s ミディアム、6.85s ショート）
- [x] 10〜15秒でショート完成が分かる
- [x] 女性はほぼ動かない（頭の回転は最大3°程度、体は呼吸程度）
- [x] 美容師が主に動いている
- [x] カメラは15秒間固定
- [x] 画面左側にHPテキスト用の余白
- [x] 女性の顔・髪型がテキスト領域と重ならない
- [x] 中央クロップでも女性が欠けない
- [x] 13〜15秒で動きが落ち着く（13.95s以降は大きな動きなし、13s以降は瞬きもなし）
- [x] 14〜15秒で完成したショートヘアと笑顔が見やすい
