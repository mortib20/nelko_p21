"""Experiment: resolution + dithering test on one 14x40 label.

Sections along the label (top to bottom, first printed first):
  1. line pairs: 1-dot, 2-dot, 3-dot stripes (horizontal + vertical)
  2. gradient, Floyd-Steinberg dithered
  3. gradient, ordered (Bayer 4x4) dithered
  4. gradient, plain threshold (reference)
  5. dithered radial "photo-like" blob
"""
import sys
from PIL import Image, ImageDraw

sys.path.insert(0, "src")
from nelko_p21.tspl import LabelSize, build_print_job  # noqa: E402

W, H = 96, 320
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def gradient(w, h):
    g = Image.new("L", (w, h))
    g.putdata([int(255 * x / (w - 1)) for y in range(h) for x in range(w)])
    return g


def bayer(img):
    out = Image.new("L", img.size)
    px = img.load(); o = out.load()
    for y in range(img.height):
        for x in range(img.width):
            o[x, y] = 255 if px[x, y] > (BAYER[y % 4][x % 4] + 0.5) * 16 else 0
    return out


def floyd(img):
    return img.convert("1", dither=Image.Dither.FLOYDSTEINBERG).convert("L")


def threshold(img):
    return img.point(lambda p: 255 if p >= 128 else 0)


def blob(w, h):
    b = Image.new("L", (w, h))
    cx, cy, r = w / 2, h / 2, min(w, h) / 2
    b.putdata([int(min(255, 255 * (((x - cx) ** 2 + (y - cy) ** 2) ** 0.5) / r))
               for y in range(h) for x in range(w)])
    return b


def build():
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)
    y = 6
    # 1. line pairs, 3 columns: 1/2/3-dot horizontal stripes, then vertical
    for i, n in enumerate((1, 2, 3)):
        x0 = 4 + i * 30
        for yy in range(y, y + 24, 2 * n):
            d.rectangle([x0, yy, x0 + 26, yy + n - 1], fill=0)
        for xx in range(x0, x0 + 27, 2 * n):
            d.rectangle([xx, y + 28, xx + n - 1, y + 52], fill=0)
    y += 60
    for f in (floyd, bayer, threshold):
        img.paste(f(gradient(W - 8, 50)), (4, y)); y += 56
    img.paste(floyd(blob(W - 8, 80)), (4, y))
    return img


if __name__ == "__main__":
    img = build()
    img.save(sys.argv[1] if len(sys.argv) > 1 else "dither_test.png")
    if "--print" in sys.argv:
        from nelko_p21 import P21Connection, find_paired_printer
        with P21Connection(find_paired_printer()) as c:
            print("final status:", c.print_job(build_print_job(img, LabelSize(14, 40))))
