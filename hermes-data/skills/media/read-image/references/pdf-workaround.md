# PDF Reading Workaround

`mmx vision describe` does NOT support PDF format — only jpg, jpeg, png, webp.

## macOS: Use qlmanage

```bash
# Convert PDF page 1 to PNG
qlmanage -t -s 1200 -o /tmp input.pdf
# Output: /tmp/input.pdf.png

# Then read with mmx
mmx vision describe --image /tmp/input.pdf.png --prompt "describe" --quiet
```

- `-t`: thumbnail mode (renders first page)
- `-s 1200`: output size in pixels (larger = more detail)
- `-o /tmp`: output directory
- Output filename is always `<input>.pdf.png`

## Linux: Use pdftoppm

```bash
pdftoppm -png -r 150 input.pdf /tmp/page
# Output: /tmp/page-1.png
```

Install: `apt install poppler-utils` or `brew install poppler` (macOS).
