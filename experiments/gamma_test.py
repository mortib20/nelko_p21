"""Experiment: compensate thermal dot gain with a gamma curve.

Four Floyd-Steinberg gradients (black -> white across the head), each
pre-brightened with a different gamma before dithering. Printed at DENSITY 15.
Order on the label (first printed first): gamma 1.0, 1.8, 2.6, 3.4.
A small number of bars next to each strip marks which one it is (1-4 bars).
"""
import sys
from PIL import Image, ImageDraw

sys.path.insert(0, "src")
from nelko_p21.tspl import LabelSize, build_print_job  # noqa: E402

W, H = 96, 320
GAMMAS = [1.0, 1.8, 2.6, 3.4]


def strip(gamma, w, h):
    g = Image.new("L", (w, h))
    g.putdata([int(255 * (x / (w - 1)) ** (1 / gamma)) for y in range(h) for x in range(w)])
    return g.convert("1", dither=Image.Dither.FLOYDSTEINBERG).convert("L")


def build():
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)
    y = 8
    for i, gm in enumerate(GAMMAS):
        img.paste(strip(gm, W - 8, 60), (4, y))
        for b in range(i + 1):  # marker bars below strip
            d.rectangle([4 + b * 8, y + 64, 8 + b * 8, y + 70], fill=0)
        y += 78
    return img


if __name__ == "__main__":
    img = build()
    img.save(sys.argv[1] if len(sys.argv) > 1 else "gamma_test.png")
    if "--print" in sys.argv:
        from nelko_p21 import P21Connection, find_paired_printer
        with P21Connection(find_paired_printer()) as c:
            print("final status:", c.print_job(build_print_job(img, LabelSize(14, 40))))
