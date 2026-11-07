"""Helpers to render label images (96 dots wide, label length tall)."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .tspl import LabelSize

_FONT_CANDIDATES = [
    "DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/noto/NotoSans-Bold.ttf",
]


def load_font(size: int) -> ImageFont.ImageFont:
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def text_label(text: str, label: LabelSize, border: bool = True) -> Image.Image:
    """Render text along the label (rotated 90°) so it reads along the strip."""
    w, h = label.width_dots, label.length_dots
    # draw in landscape (h x w), then rotate into the printer's portrait frame
    canvas = Image.new("L", (h, w), 255)
    d = ImageDraw.Draw(canvas)
    margin = 4
    if border:
        d.rectangle([margin, margin, h - 1 - margin, w - 1 - margin], outline=0, width=3)
    # "\n" (or a literal "\n" typed on the command line) starts a new line
    text = text.replace("\\n", "\n")
    inner = 6 * margin if border else 2 * margin
    size = w - 4 * margin
    font = load_font(size)
    while size > 8:
        font = load_font(size)
        l, t, r, b = d.multiline_textbbox((0, 0), text, font=font, align="center", spacing=size // 6)
        if r - l <= h - inner and b - t <= w - inner:
            break
        size -= 1
    spacing = size // 6
    l, t, r, b = d.multiline_textbbox((0, 0), text, font=font, align="center", spacing=spacing)
    d.multiline_text(((h - (r - l)) / 2 - l, (w - (b - t)) / 2 - t), text, font=font,
                     fill=0, align="center", spacing=spacing)
    return canvas.rotate(90, expand=True)


def test_pattern(label: LabelSize) -> Image.Image:
    """Border, corner marker and a ruler — useful to check orientation and offsets."""
    w, h = label.width_dots, label.length_dots
    img = Image.new("L", (w, h), 255)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w - 1, h - 1], outline=0, width=2)
    d.rectangle([4, 4, 20, 20], fill=0)  # marks the top-left corner (first printed)
    for y in range(0, h, 8):  # one tick per mm
        length = 12 if y % 80 == 0 else (8 if y % 40 == 0 else 4)
        d.line([w - 1 - length, y, w - 1, y], fill=0)
    font = load_font(14)
    d.text((26, 6), "P21", font=font, fill=0)
    return img


DEFAULT_PHOTO_GAMMA = 3.0  # see experiments/gamma_test.py – compensates thermal dot gain


def prepare_photo(img: Image.Image, gamma: float = DEFAULT_PHOTO_GAMMA) -> Image.Image:
    """Grayscale + autocontrast, brighten midtones by `gamma`, Floyd-Steinberg dither to pure B/W.

    Thermal dots spread, so a 50 % dither pattern prints almost black.
    Pre-brightening keeps midtones grey on paper.
    """
    gray = ImageOps.autocontrast(img.convert("L"), cutoff=1)
    lut = [round(255 * (v / 255) ** (1 / gamma)) for v in range(256)]
    return gray.point(lut).convert("1", dither=Image.Dither.FLOYDSTEINBERG).convert("L")
