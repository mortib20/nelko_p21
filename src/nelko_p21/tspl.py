"""TSPL command generation for the P21.

The P21 speaks a TSPL dialect (TSC printer language). A print job is plain
ASCII commands plus one raw BITMAP block.

Geometry: the print head is 96 dots (12 mm @ 203 dpi) wide. Labels are fed
lengthwise, so the bitmap is 96 dots wide and (label length) tall.
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

DPI = 203
DOTS_PER_MM = 8  # 203 dpi ~= 8 dots/mm
HEAD_WIDTH_DOTS = 96


@dataclass(frozen=True)
class LabelSize:
    width_mm: float = 14.0   # across the print head
    length_mm: float = 40.0  # in feed direction
    gap_mm: float = 5.0

    @property
    def width_dots(self) -> int:
        return HEAD_WIDTH_DOTS

    @property
    def length_dots(self) -> int:
        return int(self.length_mm * DOTS_PER_MM)

    @classmethod
    def parse(cls, text: str) -> "LabelSize":
        """Parse '14x40' or '14x40+5' (width x length + gap, in mm)."""
        gap = 5.0
        if "+" in text:
            text, g = text.split("+", 1)
            gap = float(g)
        w, l = text.lower().split("x")
        return cls(float(w), float(l), gap)


def image_to_bitmap(img: Image.Image, threshold: int = 128) -> tuple[int, int, bytes]:
    """Convert an image to TSPL BITMAP data.

    Returns (width_bytes, height, data). In TSPL a 0 bit prints black,
    a 1 bit leaves the paper white.
    """
    gray = img.convert("L")
    width_bytes = (gray.width + 7) // 8
    padded = Image.new("L", (width_bytes * 8, gray.height), 255)
    padded.paste(gray, (0, 0))
    # PIL mode "1": pixel value 1 == white -> exactly TSPL's polarity
    bw = padded.point(lambda p: 255 if p >= threshold else 0, mode="1")
    return width_bytes, bw.height, bw.tobytes()


def build_print_job(img: Image.Image, label: LabelSize, density: int = 15, copies: int = 1) -> bytes:
    if img.width > label.width_dots:
        raise ValueError(f"image is {img.width} dots wide, head supports {label.width_dots}")
    width_bytes, height, data = image_to_bitmap(img)
    header = (
        f"SIZE {label.width_mm:.1f} mm,{label.length_mm:.1f} mm\r\n"
        f"GAP {label.gap_mm:.1f} mm,0 mm\r\n"
        "DIRECTION 1,1\r\n"
        f"DENSITY {density}\r\n"
        "CLS\r\n"
        f"BITMAP 0,0,{width_bytes},{height},1,"
    ).encode("ascii")
    footer = f"\r\nPRINT {copies}\r\n".encode("ascii")
    return header + data + footer
