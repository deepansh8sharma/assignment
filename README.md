# Personal Handwriting Renderer

Generate a handwriting sample sheet, fill it in, extract your own handwritten characters, and render UTF-8 text into a PDF using those glyphs.

## 1. Install Python packages

Use Python 3.10 or newer. Open a terminal in this folder and run:

```bash
python -m venv .venv
```

Activate the environment:

**Windows PowerShell**
```powershell
.venv\Scripts\Activate.ps1
```

**Windows Command Prompt**
```bat
.venv\Scripts\activate.bat
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

Then install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 2. Generate the handwriting template

```bash
python make_template.py
```

This creates `template.png` and `template.pdf`. Print `template.pdf` at **100% / Actual Size**. Do not use “Fit to page”.

## 3. Fill the sheet

- Use a dark blue or black pen.
- Write each character once in its own box, close to the printed blue baseline.
- Keep every black corner marker visible.
- Do not write over the printed character label.
- Use bright, even lighting when taking a photo. Keep the entire sheet in frame.
- A flatbed scan is better than a phone photo. If photographing, hold the phone parallel to the page.

For better variety, fill and scan a second or third copy too.

## 4. Extract your handwriting

Place your scans/photos in this folder, or use their full paths:

```bash
python extract_glyphs.py glyphs/me scan1.jpg
```

For multiple sheets:

```bash
python extract_glyphs.py glyphs/me scan1.jpg scan2.jpg scan3.jpg
```

If too much ink is missed, try a higher threshold; if paper/noise is being extracted as ink, try a lower one:

```bash
python extract_glyphs.py glyphs/me scan1.jpg --threshold 170
```

The command creates `glyphs/me/meta.json` and one PNG per extracted character. Check the printed missing-character list. Re-scan or correct the sheet if important characters are missing.

**Warning:** the extractor replaces the output folder if it already exists. Do not put unrelated files in `glyphs/me`.

## 5. Create a text file

Create `input.txt` in UTF-8. Example:

```text
My Handwriting

This is a sample paragraph written using my own character shapes.
Numbers: 1234567890
```

Supported characters are A–Z, a–z, 0–9 and:
```text
.,;:!?'"-()/@&%+=_
```

Curly quotes, en/em dashes and ellipses are normalized automatically. Other unsupported characters are skipped and listed after rendering. For Hindi or other scripts, this character sheet must be expanded first.

## 6. Render a PDF

```bash
python renderer.py glyphs/me input.txt output.pdf
```

Optional settings:

```bash
python renderer.py glyphs/me input.txt output.pdf --font-mm 2.8 --line-gap-mm 8 --style ruled --slant 0 --seed 7
```

Styles: `ruled`, `plain`, or `grid`. Add `--scan-effect` for a lightly scanned look. Use `--seed` to make the layout reproducible.

## Troubleshooting

- **Could not find the four black corner markers:** ensure all four corners are visible, the page is upright, and the image is not cropped.
- **No lowercase letters detected:** improve lighting/focus or try `--threshold 170`.
- **Many characters missing:** check that handwriting sits inside the boxes and does not overlap the printed labels; try another threshold.
- **PDF text looks too large/small:** adjust `--font-mm`. This controls lowercase x-height, not total capital height.
- **Output looks repetitive:** supply multiple filled sheets so the extractor has alternate glyphs to choose from.
- **Printed template looks clipped:** print at Actual Size / 100%, not Fit to page.

## Files

- `common.py` — page dimensions and character grid constants
- `make_template.py` — printable template generator
- `extract_glyphs.py` — image rectification and glyph extraction
- `renderer.py` — handwriting PDF renderer
- `requirements.txt` — Python dependencies
