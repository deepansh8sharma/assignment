"""Render text using extracted handwriting glyphs.
Usage: python renderer.py glyphs/me input.txt output.pdf
"""
import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from common import *


class GlyphSet:
    def __init__(self, folder):
        folder = Path(folder)
        meta_path = folder / "meta.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"Missing {meta_path}. Run extract_glyphs.py first.")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        self.xheight = float(meta["xheight"])
        if self.xheight <= 0:
            raise ValueError("Glyph metadata has an invalid xheight.")
        self.glyphs = {
            ch: [(Image.open(folder / g["file"]).convert("L"), int(g["dy"])) for g in items]
            for ch, items in meta["glyphs"].items()
        }
        if not self.glyphs:
            raise ValueError(f"No glyphs found in {folder}.")


@dataclass
class Options:
    font_mm: float = 2.8
    line_gap_mm: float = 8.0
    letter_spacing_mm: float = 0.4
    word_spacing_mm: float = 2.6
    spacing_jitter: float = 0.25
    size_jitter: float = 0.05
    baseline_jitter_mm: float = 0.25
    line_drift_mm: float = 0.8
    rotation_jitter: float = 2.0
    slant_deg: float = 0.0
    ink_color: tuple = (20, 30, 120)
    ink_opacity: float = 0.92
    pen_weight: float = 1.0
    margin_top_mm: float = 25
    margin_bottom_mm: float = 15
    margin_left_mm: float = 25
    margin_right_mm: float = 12
    page_style: str = "ruled"
    show_margin_line: bool = True
    paper_color: tuple = (251, 250, 245)
    paper_noise: float = 3.0
    scan_effect: bool = False
    seed: int = 1

    def __post_init__(self):
        self.ink_color = tuple(self.ink_color)
        self.paper_color = tuple(self.paper_color)
        if self.page_style not in {"ruled", "plain", "grid"}:
            raise ValueError("page_style must be ruled, plain, or grid")


_MAP = {"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "\u2026": "...", "\t": "    ",
        "\u00a0": " ", "\r": ""}


def normalize(text):
    for key, value in _MAP.items():
        text = text.replace(key, value)
    return text


def lines_per_page(o):
    usable = PAGE_H - (o.margin_top_mm + o.margin_bottom_mm) * MM
    return max(1, int(usable // (o.line_gap_mm * MM)))


def layout(text, glyphs, options, rng):
    scale0 = options.font_mm * MM / glyphs.xheight
    max_w = PAGE_W - (options.margin_left_mm + options.margin_right_mm) * MM
    space = options.word_spacing_mm * MM
    missing = set()

    def jitter(value):
        return value * (1 + rng.uniform(-options.spacing_jitter, options.spacing_jitter))

    def make_word(word):
        items, width = [], 0.0
        for ch in word:
            if ch not in glyphs.glyphs:
                missing.add(ch)
                continue
            image, dy = rng.choice(glyphs.glyphs[ch])
            scale = scale0 * (1 + rng.uniform(-options.size_jitter, options.size_jitter))
            char_width = image.width * scale
            items.append({"img": image, "dy": dy, "s": scale, "x": width, "w": char_width,
                          "rot": rng.gauss(0, options.rotation_jitter),
                          "jy": rng.gauss(0, options.baseline_jitter_mm * MM)})
            width += char_width + jitter(options.letter_spacing_mm * MM)
        return items, width

    lines = []
    for paragraph in normalize(text).split("\n"):
        line, cursor = [], 0.0
        for word in paragraph.split(" "):
            if not word:
                cursor += space
                continue
            items, width = make_word(word)
            if not items:
                continue
            if cursor > 0 and cursor + width > max_w:
                lines.append(line)
                line, cursor = [], 0.0
            for item in items:
                item["x"] += cursor
                line.append(item)
            cursor += width + jitter(space)
        lines.append(line)
    return lines, missing


def make_paper(options, noise_rng):
    arr = np.empty((PAGE_H, PAGE_W, 3), np.float32)
    arr[:] = options.paper_color
    if options.paper_noise > 0:
        arr += noise_rng.standard_normal((PAGE_H, PAGE_W, 1), dtype=np.float32) * options.paper_noise
    if options.scan_effect:
        xs = np.linspace(-1, 1, PAGE_W, dtype=np.float32)[None, :, None]
        ys = np.linspace(-1, 1, PAGE_H, dtype=np.float32)[:, None, None]
        arr -= 14 * (0.6 * xs**2 + 0.4 * ys**2) + 6 * xs
    image = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    draw = ImageDraw.Draw(image)
    gap = options.line_gap_mm * MM
    first = options.margin_top_mm * MM + gap
    if options.page_style == "ruled":
        y = first % gap
        while y < PAGE_H:
            draw.line([(0, y), (PAGE_W, y)], fill=(165, 195, 230), width=2)
            y += gap
    elif options.page_style == "grid":
        step = 5 * MM
        y = first % step
        while y < PAGE_H:
            draw.line([(0, y), (PAGE_W, y)], fill=(200, 220, 240), width=1)
            y += step
        x = 0
        while x < PAGE_W:
            draw.line([(x, 0), (x, PAGE_H)], fill=(200, 220, 240), width=1)
            x += step
    if options.show_margin_line and options.page_style != "plain":
        x = options.margin_left_mm * MM - 4 * MM
        draw.line([(x, 0), (x, PAGE_H)], fill=(225, 140, 140), width=2)
    return image


def _lut(options):
    gamma = 1 / max(options.pen_weight, 0.1)
    return [int(255 * ((i / 255) ** gamma) * options.ink_opacity) for i in range(256)]


def _prep(item, options, lut):
    image = item["img"].resize(
        (max(1, round(item["img"].width * item["s"])),
         max(1, round(item["img"].height * item["s"]))), Image.Resampling.LANCZOS)
    if abs(options.slant_deg) > 0.01:
        k = math.tan(math.radians(options.slant_deg))
        w, h = image.size
        offset = -k * h if k > 0 else 0
        image = image.transform((w + int(abs(k) * h) + 1, h), Image.Transform.AFFINE,
                                (1, k, offset, 0, 1, 0), Image.Resampling.BICUBIC)
    if options.pen_weight >= 1.6:
        image = image.filter(ImageFilter.MaxFilter(3))
    if abs(item["rot"]) > 0.05:
        image = image.rotate(item["rot"], expand=True, resample=Image.Resampling.BICUBIC)
    return image.point(lut)


def render_page(lines, options, rng, noise_rng):
    image = make_paper(options, noise_rng)
    lut = _lut(options)
    gap = options.line_gap_mm * MM
    first = options.margin_top_mm * MM + gap
    left = options.margin_left_mm * MM
    max_w = PAGE_W - left - options.margin_right_mm * MM
    for line_index, line in enumerate(lines):
        base0 = first + line_index * gap - 3
        drift = rng.uniform(-1, 1) * options.line_drift_mm * MM / max_w
        for item in line:
            glyph = _prep(item, options, lut)
            width = item["img"].width * item["s"]
            height = item["img"].height * item["s"]
            baseline = base0 + drift * item["x"] + item["jy"]
            cx = left + item["x"] + width / 2
            cy = baseline + item["dy"] * item["s"] - height / 2
            image.paste(options.ink_color, (round(cx - glyph.width / 2), round(cy - glyph.height / 2)), glyph)
    if options.scan_effect:
        image = image.rotate(rng.uniform(-0.4, 0.4), resample=Image.Resampling.BICUBIC,
                             fillcolor=options.paper_color)
        image = image.filter(ImageFilter.GaussianBlur(0.5))
    return image


def render_text(text, glyphs, options=None):
    options = options or Options()
    glyph_set = glyphs if isinstance(glyphs, GlyphSet) else GlyphSet(glyphs)
    rng, noise_rng = random.Random(options.seed), np.random.default_rng(options.seed)
    lines, missing = layout(text, glyph_set, options, rng)
    per_page = lines_per_page(options)
    chunks = [lines[i:i + per_page] for i in range(0, max(len(lines), 1), per_page)]
    return [render_page(chunk, options, rng, noise_rng) for chunk in chunks], missing


def save_pdf(pages, destination):
    if not pages:
        raise ValueError("No pages to save.")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(destination, "PDF", resolution=DPI, quality=95, save_all=True, append_images=pages[1:])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("glyph_dir", help="Glyph folder created by extract_glyphs.py")
    parser.add_argument("input_txt", help="UTF-8 text file to render")
    parser.add_argument("output_pdf", help="Output PDF path")
    parser.add_argument("--font-mm", type=float, default=2.8, help="Lowercase x-height in mm")
    parser.add_argument("--line-gap-mm", type=float, default=8.0)
    parser.add_argument("--style", choices=["ruled", "plain", "grid"], default="ruled")
    parser.add_argument("--slant", type=float, default=0.0, help="Slant angle in degrees")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--scan-effect", action="store_true")
    args = parser.parse_args()
    if args.font_mm <= 0 or args.line_gap_mm <= 0:
        parser.error("--font-mm and --line-gap-mm must be positive")
    options = Options(font_mm=args.font_mm, line_gap_mm=args.line_gap_mm, page_style=args.style,
                      slant_deg=args.slant, seed=args.seed, scan_effect=args.scan_effect)
    text = Path(args.input_txt).read_text(encoding="utf-8")
    pages, missing = render_text(text, args.glyph_dir, options)
    save_pdf(pages, args.output_pdf)
    print(f"Saved {len(pages)} page(s) to {args.output_pdf}.")
    if missing:
        print("Characters without glyphs (skipped): " + "".join(sorted(missing)))


if __name__ == "__main__":
    main()
