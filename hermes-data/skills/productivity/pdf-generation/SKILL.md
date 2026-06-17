---
name: pdf-generation
description: Generate PDF documents on macOS with CJK (Chinese/Japanese/Korean) font support. Use when user asks for a PDF report, export to PDF, or generate a PDF from structured content (tables, analysis, slides content). Trigger whenever user says "发我PDF", "generate PDF", "export to PDF", "create PDF report", or when you need to deliver a document-style output as a file.
version: 1.0.0
author: hermes
platforms: [macos]
---

# PDF Generation on macOS (CJK-aware)

## Key Insight

**macOS built-in tools cannot handle CJK in PDFs:**
- `textutil -convert pdf` → fails with "Invalid output format" for multi-page HTML with CJK
- `cupsfilter` (HTML → PDF) → error: "无滤镜可从text/html转换成application/pdf" — no filter available for text/html to PDF
- `fpdf2` / `reportlab` in `execute_code` sandbox → module not found (sandbox has minimal packages)

**Solution: Use `/usr/bin/python3` + reportlab + system CJK fonts.**

---

## Environment Setup

### Python path (critical)
```
execute_code sandbox Python:    /usr/bin/python3  ← USE THIS
reportlab site-packages:        /Users/omi/.hermes/profiles/main/home/Library/Python/3.9/lib/python/site-packages
```

Always use `/usr/bin/python3` for reportlab scripts. Never use `execute_code` for PDF generation — it lacks the required packages.

### Add site-packages to sys.path
```python
import sys
sys.path.insert(0, '/Users/omi/.hermes/profiles/main/home/Library/Python/3.9/lib/python/site-packages')
```

### Register CJK fonts (reportlab cannot use TTC directly)
```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont('Heiti', '/System/Library/Fonts/STHeiti Medium.ttc'))
```

Available macOS CJK fonts:
| Font | File | Coverage |
|------|------|----------|
| Heiti SC (黑体简体) | `/System/Library/Fonts/STHeiti Medium.ttc` | Simplified Chinese |
| Songti SC (宋体简体) | `/System/Library/Fonts/Supplemental/Songti.ttc` | Simplified Chinese serif |
| Heiti TC (黑体繁体) | `/System/Library/Fonts/STHeiti Light.ttc` | Traditional Chinese |

---

## Workflow

### Step 1: Generate the PDF via /usr/bin/python3

Write a Python script to a temp path, run it with `/usr/bin/python3`. Always output to `/tmp/` first.

```python
import sys
sys.path.insert(0, '/Users/omi/.hermes/profiles/main/home/Library/Python/3.9/lib/python/site-packages')

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont('Heiti', '/System/Library/Fonts/STHeiti Medium.ttc'))

doc = SimpleDocTemplate('/tmp/output.pdf', pagesize=A4, rightMargin=1.5*cm, leftMargin=1.5*cm, topMargin=2*cm, bottomMargin=2*cm)

# Style factory
teal = colors.HexColor('#008080')
white = colors.white
light_gray = colors.HexColor('#F5F5F5')

def S(name, **kw):
    defaults = dict(fontName='Heiti', fontSize=10, leading=14)
    defaults.update(kw)
    return ParagraphStyle(name, **defaults)

title_s  = S('title', fontSize=18, textColor=teal, spaceAfter=8, leading=22)
subtitle_s = S('sub', fontSize=11, textColor=colors.HexColor('#555'), spaceAfter=20, leading=14)
section_s = S('sec', fontSize=13, textColor=teal, spaceBefore=16, spaceAfter=6, leading=16)
body_s    = S('body', fontSize=10, spaceAfter=6, leading=15)
cell_s    = S('cell', fontSize=9, leading=12)
hdr_s     = S('hdr', fontSize=9, leading=12, textColor=white)

def P(text, style): return Paragraph(text, style)

# Build story [...]
doc.build(story)
print("Done:", output_path)
```

### Step 2: Write the script to file (use write_file tool)

### Step 3: Run via terminal with background=true, timeout=300

```bash
/usr/bin/python3 /tmp/make_pdf.py
```

Wait via `process action=wait` with 60s timeout.

### Step 4: Deliver path to user

The PDF is at `/tmp/output.pdf` (or whichever path you specified). Tell the user the exact path.

---

## Common Tasks

### Multi-section PDF (e.g., English + Chinese side by side)

Build one `story` list with all sections in order. Use `Spacer(1, N*cm)` for section breaks. Use `ParagraphStyle` with `textColor` for divider lines.

### Tables

```python
from reportlab.platypus import Table, TableStyle

t = Table(rows, colWidths=[4*cm, 7*cm, 5*cm])
t.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), teal),      # Header row
    ('TEXTCOLOR',  (0,0), (-1,0), white),
    ('ALIGN',      (0,0), (-1,-1), 'LEFT'),
    ('VALIGN',     (0,0), (-1,-1), 'TOP'),
    ('FONTNAME',   (0,0), (-1,0), 'Heiti'),
    ('FONTSIZE',   (0,0), (-1,-1), 9),
    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ('TOPPADDING',    (0,0), (-1,-1), 6),
    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CCC')),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [white, light_gray]),
]))
```

### Paragraphs

```python
Paragraph("Text with <b>bold</b> support", body_s)
# Note: reportlab Paragraph supports basic HTML-like markup: <b>, <i>, <u>, <font color="...">
```

---

## What NOT to Do

- **Don't use `execute_code`** — reportlab is not available in that sandbox
- **Don't use textutil or cupsfilter** — they don't support CJK fonts in HTML
- **Don't use `~` or `$HOME` in output paths** in Python scripts run via terminal — the shell HOME is often a profile subdirectory, not `/Users/omi`. Always use absolute paths like `/tmp/` or `/Users/omi/`
- **Don't try to register TTC fonts by filename** — TTFont() accepts TTC but you must pass the TTC file path, not a subset TTF

---

## Quick Reference

| Tool | Works for CJK PDF? | Use case |
|------|-------------------|----------|
| textutil (macOS) | ❌ | Never |
| cupsfilter | ❌ | Never |
| execute_code | ❌ | No reportlab |
| /usr/bin/python3 + reportlab | ✅ | Primary method |
| HTML → PDF web service | ⚠️ | Alternative if available |

---

### Alternative: HTML to PDF via Playwright (Chrome headless)

When you need to convert **HTML → PDF** (not programmatically generated content), use Playwright with Chrome:

**Environment:**
- Mac with Chrome installed at `/Applications/Google Chrome.app`
- playwright installed via pip (not conda/brew)
- **Important**: Use `/usr/bin/python3` NOT the sandboxed python3 in Hermes — playwright is only available under the system python

**Method: playwright (Recommended, works ✅)**

```bash
/usr/bin/python3 -c "
from playwright.sync_api import sync_playwright
import os

html_path = '/path/to/input.html'
pdf_path = '/path/to/output.pdf'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(f'file://{html_path}', wait_until='networkidle')
    page.pdf(
        path=pdf_path,
        format='A4',
        print_background=True,
        margin={'top': '15mm', 'bottom': '15mm', 'left': '15mm', 'right': '15mm'}
    )
    browser.close()

print('OK' if os.path.exists(pdf_path) else 'FAIL')
"
```

**Chrome CLI (Alternative, often times out ❌):**
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --headless=new \
  --no-pdf-header-footer \
  --print-to-pdf="/path/to/output.pdf" \
  --print-to-pdf-no-header \
  "/path/to/input.html"
```

**Failed methods on this Mac (macOS 2026-04-26):**
| Method | Issue |
|--------|-------|
| `weasyprint` | Missing `libgobject-2.0-0` system library |
| `wkhtmltopdf` | Not available in homebrew cask |
| `cupsfilter` | Does not handle text/html MIME type |
| Chrome CLI | Times out (>25s) for complex HTML pages |
| Chrome headless subprocess | Times out in sandboxed environment |