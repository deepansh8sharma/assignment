"""Extract handwritten glyphs from a filled template scan/photo."""
import argparse
import json
import shutil
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from common import *

MIN_AREA = 12


def find_markers(gray):
    h, w = gray.shape
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, bw = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    cnts, _ = cv2.findContours(bw, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    cands = []
    for c in cnts:
        a = cv2.contourArea(c)
        if not (1e-4 * h * w < a < 0.02 * h * w):
            continue
        _, (rw, rh), _ = cv2.minAreaRect(c)
        if min(rw, rh) < 1 or max(rw, rh) / min(rw, rh) > 1.4 or a / max(rw * rh, 1) < 0.85:
            continue
        m = cv2.moments(c)
        if m["m00"]:
            cands.append((a, m["m10"] / m["m00"], m["m01"] / m["m00"]))
    if len(cands) < 4:
        raise ValueError("Could not find the four black corner markers. Include all corners and keep the page upright.")
    pts = np.array([[x, y] for _, x, y in sorted(cands, reverse=True)[:4]], np.float32)
    s, d = pts.sum(1), pts[:, 0] - pts[:, 1]
    return np.array([pts[s.argmin()], pts[d.argmax()], pts[d.argmin()], pts[s.argmax()]], np.float32)


def rectify(img_bgr):
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    src = find_markers(gray)
    matrix = cv2.getPerspectiveTransform(src, np.array(MARKERS, np.float32))
    return cv2.warpPerspective(gray, matrix, (PAGE_W, PAGE_H), flags=cv2.INTER_CUBIC, borderValue=255)


def normalize_page(gray):
    bg = cv2.dilate(gray, np.ones((15, 15), np.uint8))
    bg = cv2.GaussianBlur(bg, (0, 0), 25)
    return np.clip(gray.astype(np.float32) / np.maximum(bg, 1) * 255, 0, 255).astype(np.uint8)


def extract_cells(norm, threshold):
    out = {}
    for i, ch in enumerate(CHARS):
        x, y = cell_origin(i)
        by = baseline_y(y)
        y0, y1 = y + LABEL_H, y + CELL_H - 6
        x0, x1 = x + 8, x + CELL_W - 8
        crop = norm[y0:y1, x0:x1]
        mask = (crop < threshold).astype(np.uint8)
        n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        keep = np.zeros_like(mask)
        for k in range(1, n):
            if stats[k, cv2.CC_STAT_AREA] >= MIN_AREA:
                keep[labels == k] = 1
        if not keep.any():
            continue
        ys, xs = np.where(keep)
        top, bottom = ys.min(), ys.max() + 1
        left, right = xs.min(), xs.max() + 1
        soft = np.clip((200.0 - crop.astype(np.float32)) * 255 / 140, 0, 255)
        dilated = cv2.dilate(keep, np.ones((3, 3), np.uint8))
        alpha = (soft * dilated)[top:bottom, left:right].astype(np.uint8)
        out[ch] = (alpha, int((y0 + bottom) - by))
    return out


def extract_from_images(images, out_dir, threshold=150):
    out = Path(out_dir)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    meta, counts, xheights = {}, {}, []
    for img in images:
        if img is None:
            raise ValueError("At least one image could not be opened. Check the input file path.")
        normalized = normalize_page(rectify(img))
        for ch, (alpha, dy) in extract_cells(normalized, threshold).items():
            index = counts.get(ch, 0)
            counts[ch] = index + 1
            filename = f"u{ord(ch):04x}_{index}.png"
            Image.fromarray(alpha).save(out / filename)
            meta.setdefault(ch, []).append({"file": filename, "dy": dy})
            if ch in XHEIGHT_CHARS:
                xheights.append(alpha.shape[0])
    if not xheights:
        raise ValueError("No lowercase letters detected. Check photo quality and threshold.")
    data = {"xheight": float(np.median(xheights)), "dpi": DPI, "glyphs": meta}
    (out / "meta.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    missing = [ch for ch in CHARS if ch not in meta]
    return missing, len(images)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("out_dir", help="Output glyph folder, e.g. glyphs/me")
    ap.add_argument("images", nargs="+", help="One or more filled-template photos/scans")
    ap.add_argument("--threshold", type=int, default=150, help="Ink threshold, 0-255 (default: 150)")
    args = ap.parse_args()
    if not 1 <= args.threshold <= 254:
        ap.error("--threshold must be between 1 and 254")
    images = [cv2.imread(p) for p in args.images]
    missing, count = extract_from_images(images, args.out_dir, args.threshold)
    print(f"Built glyph set from {count} sheet(s) in {args.out_dir}.")
    print("Missing characters: " + (''.join(missing) if missing else "none"))


if __name__ == "__main__":
    main()
