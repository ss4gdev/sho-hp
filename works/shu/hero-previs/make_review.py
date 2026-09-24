"""
Encode the rendered PNG frames into the preview videos and build the
composition check sheet.

  python3 make_review.py FRAMES_DIR

Outputs (next to this file):
  SHU_Hero_Previs_15s.mp4         clean 16:9 preview (hero background / Higgsfield reference)
  SHU_Hero_Previs_15s_guides.mp4  same, with the left copy area, the 9:16 phone
                                  centre-crop and a timecode / cut label burnt in
  composition_check.png           PC 16:9 with mock copy + phone crops at key moments
"""
import glob, os, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 30
TEXT_ZONE = 0.38  # left share of the frame reserved for web copy
JP_FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
EN_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

CUTS = [
    (0.0, 3.0, "CUT1  Before / long hair (dry)"),
    (3.0, 4.55, "CUT2  Cutting (wet) - lift & cut, long"),
    (4.55, 6.85, "CUT2  Cutting (wet) - medium"),
    (6.85, 7.5, "CUT2  Cutting (wet) - short"),
    (7.5, 10.0, "CUT2  Blow-dry - short"),
    (10.0, 13.0, "CUT3  After / styling - short"),
    (13.0, 15.0, "CUT3  Final hold"),
]


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def label_for(t):
    for a, b, name in CUTS:
        if a <= t < b:
            return name
    return CUTS[-1][2]


def mock_copy(draw, w, h, alpha=255):
    """Mock of the SHU hero copy, left aligned inside the text zone."""
    x = int(w * 0.06)
    y = int(h * 0.36)
    s = h / 1080
    draw.text((x, y), "NAMBA / KOREAN TREND HAIR SALON", font=font(EN_FONT, int(18 * s)), fill=(70, 62, 55, alpha))
    draw.text((x, y + int(48 * s)), "鏡を見るたび、", font=font(JP_FONT, int(58 * s)), fill=(40, 36, 32, alpha))
    draw.text((x, y + int(128 * s)), "もっと自分が好きになる。", font=font(JP_FONT, int(58 * s)), fill=(40, 36, 32, alpha))
    draw.text((x, y + int(222 * s)), "Fall in Love With Your Reflection", font=font(EN_FONT, int(24 * s)), fill=(90, 80, 70, alpha))
    bx, by = x, y + int(290 * s)
    draw.rectangle([bx, by, bx + int(250 * s), by + int(58 * s)], fill=(40, 36, 32, alpha))
    draw.text((bx + int(40 * s), by + int(17 * s)), "WEB予約はこちら", font=font(JP_FONT, int(22 * s)), fill=(245, 243, 240, alpha))


def guides(im, t):
    w, h = im.size
    base = im.convert("RGBA")
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    tz = int(w * TEXT_ZONE)
    d.rectangle([0, 0, tz, h], fill=(255, 255, 255, 40))
    d.line([tz, 0, tz, h], fill=(0, 120, 255, 200), width=3)
    d.text((16, 16), "PC: copy area (left 38%)", font=font(EN_FONT, 22), fill=(0, 90, 220, 230))
    mock_copy(d, w, h, 150)
    cw = h * 9 / 16
    x0, x1 = int((w - cw) / 2), int((w + cw) / 2)
    for x in (x0, x1):
        for yy in range(0, h, 24):
            d.line([x, yy, x, yy + 12], fill=(230, 40, 40, 230), width=3)
    d.text((x0 + 10, 16), "SP 9:16 centre crop", font=font(EN_FONT, 22), fill=(220, 30, 30, 230))
    d.rectangle([0, h - 56, w, h], fill=(0, 0, 0, 150))
    d.text((20, h - 44), f"{t:05.2f}s   {label_for(t)}", font=font(EN_FONT, 28), fill=(255, 255, 255, 255))
    return Image.alpha_composite(base, ov).convert("RGB")


def encode(pattern, out, crf=18):
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", pattern,
                    "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", out], check=True)
    print("wrote", out)


def main():
    src = sys.argv[1]
    frames = sorted(glob.glob(os.path.join(src, "f_*.png")))
    assert frames, "no frames"
    encode(os.path.join(src, "f_%04d.png"), os.path.join(HERE, "SHU_Hero_Previs_15s.mp4"))

    with tempfile.TemporaryDirectory() as tmp:
        for i, f in enumerate(frames):
            guides(Image.open(f), i / FPS).save(os.path.join(tmp, f"g_{i + 1:04d}.png"), compress_level=1)
        encode(os.path.join(tmp, "g_%04d.png"), os.path.join(HERE, "SHU_Hero_Previs_15s_guides.mp4"), 20)

    # composition check sheet: PC view with mock copy + phone crop, at key moments
    moments = [(1.0, "0-3s Before"), (5.0, "3-10s Cutting"), (8.5, "Blow-dry"), (14.5, "14-15s Final")]
    first = Image.open(frames[0])
    w, h = first.size
    pw, ph = 960, 540
    cw = int(ph * 9 / 16)
    sheet = Image.new("RGB", (pw + cw + 60, (ph + 50) * len(moments) + 20), (245, 243, 240))
    d = ImageDraw.Draw(sheet)
    for row, (t, name) in enumerate(moments):
        idx = min(int(round(t * FPS)), len(frames) - 1)
        im = Image.open(frames[idx]).convert("RGB").resize((pw, ph), Image.LANCZOS)
        pc = im.convert("RGBA")
        ov = Image.new("RGBA", pc.size, (0, 0, 0, 0))
        mock_copy(ImageDraw.Draw(ov), pw, ph)
        pc = Image.alpha_composite(pc, ov).convert("RGB")
        y = 20 + row * (ph + 50)
        sheet.paste(pc, (20, y + 30))
        crop = im.crop(((pw - cw) // 2, 0, (pw + cw) // 2, ph))
        sheet.paste(crop, (pw + 40, y + 30))
        d.text((20, y + 2), f"{t:.1f}s  {name}  -  PC 16:9 with mock copy", font=font(EN_FONT, 18), fill=(40, 36, 32))
        d.text((pw + 40, y + 2), "SP 9:16 crop", font=font(EN_FONT, 18), fill=(40, 36, 32))
    out = os.path.join(HERE, "composition_check.png")
    sheet.save(out, optimize=True)
    print("wrote", out)


if __name__ == "__main__":
    main()
