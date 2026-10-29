"""Shared constants and template geometry. A4 at 200 DPI."""
DPI = 200
PAGE_W, PAGE_H = 1654, 2339
MM = DPI / 25.4

CHARS = list(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    ".,;:!?'\"-()/@&%+=_"
)
COLS, ROWS = 10, 8
assert len(CHARS) == COLS * ROWS, f"Expected 80 characters, got {len(CHARS)}"

CELL_W, CELL_H = 140, 220
GRID_X0 = (PAGE_W - COLS * CELL_W) // 2
GRID_Y0 = 260
LABEL_H = 34
BASE_FRAC = 0.62

MARK_SIZE = 70
MARKERS = [
    (75, 75), (PAGE_W - 75, 75),
    (75, PAGE_H - 75), (PAGE_W - 75, PAGE_H - 75),
]
XHEIGHT_CHARS = "acemnorsuvwxz"


def cell_origin(i):
    r, c = divmod(i, COLS)
    return GRID_X0 + c * CELL_W, GRID_Y0 + r * CELL_H


def baseline_y(cell_y):
    return cell_y + LABEL_H + int(BASE_FRAC * (CELL_H - LABEL_H))
