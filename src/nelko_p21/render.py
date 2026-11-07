"""Helpers to render label images (96 dots wide, label length tall)."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

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
    size = w - 4 * margin
    font = load_font(size)
    while size > 8:
        font = load_font(size)
        l, t, r, b = d.textbbox((0, 0), text, font=font)
        if r - l <= h - 6 * margin and b - t <= w - 6 * margin:
            break
        size -= 2
    l, t, r, b = d.textbbox((0, 0), text, font=font)
    d.text(((h - (r - l)) / 2 - l, (w - (b - t)) / 2 - t), text, font=font, fill=0)
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
