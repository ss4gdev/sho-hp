#!/usr/bin/env python3
"""
SHU 映像版 ─ 画像の書き出しスクリプト
============================================================
元画像（JPG/PNG）から、サイトで使う AVIF / WebP / JPG をまとめて書き出します。
元画像は読むだけで、上書き・削除はしません。

  使い方（リポジトリのルートで実行）:
    pip install pillow            # AVIF 対応は Pillow 11.2 以降
    python3 works/shu-film/_tools/build_images.py

  写真を差し替えるとき:
    下の MANIFEST の "src" を新しい写真のパスに変えて実行するだけです。
    書き出し先のファイル名・幅は固定なので、index.html を直す必要はありません。

  書き出されるファイル（例: gallery/01）:
    assets/img/gallery/01-640.avif   01-640.webp
    assets/img/gallery/01-1280.avif  01-1280.webp  01-1280.jpg（非対応ブラウザ用）
"""
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[3]          # リポジトリのルート
OUT = Path(__file__).resolve().parents[1] / "assets"  # works/shu-film/assets

SRC_SHU = "works/shu"

# ------------------------------------------------------------
# 書き出し一覧
#   out     … assets/ からの書き出し先（拡張子・幅なし）
#   src     … リポジトリのルートからの元画像パス
#   widths  … 書き出す幅（px）。最後の幅で JPG も書き出す
#   crop    … 切り抜き (左, 上, 右, 下) ※元画像のピクセル座標。省略可
#   aspect  … 縦横比 (横, 縦) に切り抜く。縦長すぎる写真の無駄な上下を落とす。省略可
#   focus   … aspect で切り抜くときの中心 (横 0〜1, 縦 0〜1)。既定 (0.5, 0.4)＝顔が残りやすい位置
#   extend  … 横長ポスター用。背景を左右に伸ばして人物を右寄せにする（下の関数参照）
# ------------------------------------------------------------
MANIFEST = [
    # HERO ── 動画のポスター（動画が読み込めない/無効のときに表示）
    {"out": "hero/poster-pc", "src": f"{SRC_SHU}/images/hero-main.jpg", "widths": [1280, 1920],
     "extend": {"size": (1920, 1080), "subject_x": 0.62, "subject_center": 0.48}},
    {"out": "hero/poster-sp", "src": f"{SRC_SHU}/images/hero-main.jpg", "widths": [750],
     "crop": (150, 0, 770, 940)},

    # CONCEPT
    {"out": "img/concept/concept", "src": f"{SRC_SHU}/images/gallery/yoshin/yoshin-2.jpg",
     "widths": [640, 1080], "aspect": (4, 5)},

    # TRANSFORMATION ── Before / After
    {"out": "img/transformation/before", "src": f"{SRC_SHU}/images/gallery/yoshin/yoshin-4.jpg",
     "widths": [480, 960], "aspect": (4, 5)},
    {"out": "img/transformation/after", "src": f"{SRC_SHU}/images/gallery/short/short-3.jpg",
     "widths": [640, 1080], "aspect": (4, 5), "focus": (0.5, 0.3)},

    # STYLE GALLERY ── 01・04 が大きい写真（3:4）、ほかは小さい写真（4:5）
    {"out": "img/gallery/01", "src": f"{SRC_SHU}/images/gallery/short/short-1.jpg",
     "widths": [640, 1200], "aspect": (3, 4)},
    {"out": "img/gallery/02", "src": f"{SRC_SHU}/images/gallery/short/short-2.jpg",
     "widths": [480, 800], "aspect": (4, 5), "focus": (0.5, 0.35)},
    {"out": "img/gallery/03", "src": f"{SRC_SHU}/images/gallery/layer/layer-4.jpg",
     "widths": [480, 800], "aspect": (4, 5), "focus": (0.5, 0.3)},
    {"out": "img/gallery/04", "src": f"{SRC_SHU}/images/gallery/yoshin/yoshin-1.jpg",
     "widths": [640, 1200], "aspect": (3, 4)},
    {"out": "img/gallery/05", "src": f"{SRC_SHU}/images/gallery/short/short-4.jpg",
     "widths": [480, 800], "aspect": (4, 5), "focus": (0.55, 0.5)},
    {"out": "img/gallery/06", "src": f"{SRC_SHU}/images/gallery/layer/layer-2.jpg",
     "widths": [480, 800], "aspect": (4, 5), "focus": (0.5, 0.3)},

    # STYLIST
    {"out": "img/stylist/karin", "src": f"{SRC_SHU}/1.jpg", "widths": [640, 1080],
     "aspect": (4, 5), "focus": (0.45, 0.5)},
    {"out": "img/stylist/rise", "src": f"{SRC_SHU}/2.jpg", "widths": [320], "aspect": (4, 5)},
    {"out": "img/stylist/ryoko", "src": f"{SRC_SHU}/3.jpg", "widths": [320], "aspect": (4, 5)},

    # SALON ── 店内（大）と、同じ写真の寄り（小）。店内写真が増えたら小の src を差し替え
    {"out": "img/salon/main", "src": f"{SRC_SHU}/images/concept.jpg", "widths": [640, 1200]},
    {"out": "img/salon/detail", "src": f"{SRC_SHU}/images/concept.jpg", "widths": [480, 800],
     "crop": (170, 280, 578, 790)},
]

AVIF_Q = 55
WEBP_Q = 80
JPG_Q = 82


def extend_canvas(img, size, subject_x, subject_center):
    """
    正方形に近い写真を横長ポスターにする。
    写真を高さに合わせて拡大し、人物（subject_center: 写真内の横位置 0〜1）が
    キャンバスの subject_x（0〜1）に来るよう配置。左右の空きは写真の端の色を
    行ごとに伸ばし、軽い周辺減光と粒子を足してなじませる。
    """
    cw, ch = size
    scale = ch / img.height
    sw = round(img.width * scale)
    scaled = img.resize((sw, ch), Image.LANCZOS)
    left = round(cw * subject_x - sw * subject_center)
    left = max(0, min(left, cw - sw))

    canvas = Image.new("RGB", size)

    def edge_fill(x0, x1, width):
        # 端 x0..x1 の列を 1px 幅に平均 → 縦方向に軽くぼかす → 横に伸ばす
        strip = scaled.crop((x0, 0, x1, ch)).resize((1, ch), Image.BOX)
        strip = strip.filter(ImageFilter.GaussianBlur(2))
        return strip.resize((width, ch), Image.NEAREST)

    blend = 90
    if left > 0:
        fill = edge_fill(0, 18, left + blend)
        # 外側ほど少し暗く（スタジオの周辺減光）
        shade = Image.linear_gradient("L").rotate(90, expand=True).resize((left + blend, ch))
        shade = ImageOps.invert(shade).point(lambda v: 255 - int(v * 0.10))
        fill = ImageChops.multiply(fill, Image.merge("RGB", [shade] * 3))
        canvas.paste(fill, (0, 0))
    right = cw - (left + sw)
    if right > 0:
        fill = edge_fill(sw - 18, sw, right + blend)
        canvas.paste(fill, (cw - right - blend, 0))

    # 写真を重ね、つなぎ目 blend px をグラデーションでなじませる
    mask = Image.new("L", (sw, ch), 255)
    ramp = Image.linear_gradient("L").rotate(90, expand=True).resize((blend, ch))  # 左端 0 → 右 255
    if left > 0:
        mask.paste(ramp, (0, 0))
    if right > 0:
        mask.paste(ImageOps.mirror(ramp), (sw - blend, 0))
    canvas.paste(scaled, (left, 0), mask)

    # 伸ばした部分に写真と同程度の粒子を足す
    noise = Image.effect_noise(size, 6).convert("RGB")
    grain = ImageChops.add(canvas, noise, scale=1.0, offset=-128)
    region = Image.new("L", size, 0)
    if left > 0:
        region.paste(255, (0, 0, left + blend // 2, ch))
    if right > 0:
        region.paste(255, (cw - right - blend // 2, 0, cw, ch))
    canvas = Image.composite(grain, canvas, region.filter(ImageFilter.GaussianBlur(20)))
    return canvas


def crop_to_aspect(img, aspect, focus):
    aw, ah = aspect
    fx, fy = focus
    w, h = img.size
    if w / h > aw / ah:          # 横に余る → 左右を落とす
        nw = round(h * aw / ah)
        x = round((w - nw) * fx)
        return img.crop((x, 0, x + nw, h))
    nh = round(w * ah / aw)      # 縦に余る → 上下を落とす
    y = round((h - nh) * fy)
    return img.crop((0, y, w, y + nh))


def resize_to_width(img, width):
    if img.width == width:
        return img.copy()
    height = round(img.height * width / img.width)
    return img.resize((width, height), Image.LANCZOS)


def build(entry):
    src = ROOT / entry["src"]
    img = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    if "crop" in entry:
        img = img.crop(entry["crop"])
    if "aspect" in entry:
        img = crop_to_aspect(img, entry["aspect"], entry.get("focus", (0.5, 0.4)))
    if "extend" in entry:
        ext = entry["extend"]
        img = extend_canvas(img, ext["size"], ext["subject_x"], ext["subject_center"])

    dest = OUT / entry["out"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    written = []
    for w in entry["widths"]:
        im = resize_to_width(img, w)
        base = f"{dest}-{w}"
        im.save(base + ".avif", quality=AVIF_Q, speed=4)
        im.save(base + ".webp", quality=WEBP_Q, method=6)
        written.append((w, im.height))
    last_w = entry["widths"][-1]
    resize_to_width(img, last_w).save(f"{dest}-{last_w}.jpg", quality=JPG_Q, optimize=True, progressive=True)
    sizes = ", ".join(f"{w}x{h}" for w, h in written)
    print(f"  {entry['out']:<28} {sizes}")


if __name__ == "__main__":
    print(f"書き出し先: {OUT}")
    for e in MANIFEST:
        build(e)
    print("完了")
