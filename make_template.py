"""Generate template.png and template.pdf for handwriting capture."""
import argparse
from PIL import Image, ImageDraw, ImageFont
from common import *


def _font(size):
    for name in ("DejaVuSans.ttf", "Arial.ttf", "arial.ttf", "Helvetica.ttc"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def build_template():
    img = Image.new("RGB", (PAGE_W, PAGE_H), "white")
    d = ImageDraw.Draw(img)
    h = MARK_SIZE // 2
    for cx, cy in MARKERS:
        d.rectangle([cx-h, cy-h, cx+h, cy+h], fill="black")

    d.text((GRID_X0, 140), "HANDWRITING TEMPLATE", fill=(60, 60, 60), font=_font(40))
    d.text((GRID_X0, 195),
           "Dark pen, medium size. Write each character ON the blue line. Keep page upright.",
           fill=(110, 110, 110), font=_font(22))

    label_font = _font(22)
    for i, ch in enumerate(CHARS):
        x, y = cell_origin(i)
        d.rectangle([x, y, x + CELL_W, y + CELL_H], outline=(190, 190, 190), width=2)
        d.text((x + 8, y + 6), ch, fill=(130, 130, 130), font=label_font)
        by = baseline_y(y)
        d.line([x + 8, by, x + CELL_W - 8, by], fill=(170, 205, 240), width=2)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="template", help="Output filename prefix")
    args = ap.parse_args()
    img = build_template()
    img.save(f"{args.prefix}.png")
    img.save(f"{args.prefix}.pdf", "PDF", resolution=DPI)
    print(f"Saved {args.prefix}.png and {args.prefix}.pdf. Print at 100% scale; do not fit to page.")


if __name__ == "__main__":
    main()
