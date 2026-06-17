---
name: read-image
description: Read and analyze local or remote images using mmx vision describe. Always use this for reading/analyzing images instead of the built-in vision_analyze tool.
version: 1.0
author: hermes
---

# Read Image

Use `mmx vision describe` to analyze images. This tool successfully reads both local files and URLs.

## Command

```bash
mmx vision describe --image <path-or-url> --prompt "<question>" --quiet
```

## Preferred Tool and Fallbacks

Use `mmx vision describe` first when available. If `mmx` is not installed, not on PATH, or is blocked by setup state, do **not** stop the task: fall back to the built-in `vision_analyze` tool when it can load the image, then answer from the loaded visual context. Treat missing `mmx` as setup state, not as evidence that image reading is impossible.

Avoid declaring that image analysis cannot be done until at least one fallback path has been tried.

## When to Use

- User shares an image and asks to describe it
- User asks what's in a photo/screenshot
- User wants analysis of any image
- Checking generated images for quality
- User asks to check a medical/lab-report image against a previously defined threshold rule

## User-specific medical/lab report pattern

When Omi asks to check a blood routine / CBC image "按之前的判断标准" or similar, use `mmx vision describe` to extract only the threshold fields and compare them directly against the saved red-line criteria: WBC < 2.5, NEUT/Neu absolute count < 1.5, Hb < 90, PLT < 75. Output a compact normal/abnormal conclusion first, then a four-line itemized comparison. Avoid broad medical interpretation unless asked; note "near threshold" only when a value is close but not below the defined line.

## Example

```bash
# Local file
mmx vision describe --image /tmp/photo.png --prompt "描述这张图片" --quiet

# URL
mmx vision describe --image "https://example.com/image.jpg" --prompt "What is shown?" --quiet
```

## Notes

- PATH must include `$HOME/.local/bin` (mmx installs to `~/.local/bin`)
- Output is JSON, description is in `.content` field
- Works reliably where other vision tools fail on local paths
- **PDF not supported** — mmx only handles jpg/jpeg/png/webp. Convert PDF→PNG first: see `references/pdf-workaround.md`

## Pitfall: MiniMax Vision "Sensitive Content" Rejection

MiniMax's vision API may reject images as `"input image sensitive"` (HTTP 200, error code 1). This is not a tool failure — it's server-side content filtering. When this happens:

1. **Don't retry mmx** — the rejection is deterministic for that image
2. **Fall back to Tesseract** to extract any identifiable text: `tesseract <image> stdout -l jpn+chi_sim --psm 6`
3. **Use the OCR fragments to identify the content** (song title, artist name, document header, etc.)
4. **If the content is a known/public work** (song lyrics, famous text, published document), search the web with `anysearch` to retrieve the full text — this is faster and more accurate than trying to OCR the whole image
5. **If the content is private/unique** (personal screenshot, handwritten note), you'll need an alternative vision provider or ask the user to describe it

Example from practice: a lyrics screenshot was rejected by mmx. Tesseract yielded "丸ノ内サディスティック" + "椎名林檎". Web search found the complete lyrics in <30s.

## Preferred: mmx vision (MiniMax)

Always use `mmx vision describe` as the first choice for image OCR. It consistently produces accurate results with proper formatting, role labels, and correct character recognition.

## Tesseract + LLM Pipeline (deprecated for this user)

**This approach was tried and abandoned (2026-05-30).** The pipeline is:
1. `tesseract <image> stdout -l jpn+chi_sim --psm 6` (free, offline, <1s)
2. Send raw OCR to DeepSeek v4-flash for correction

**Pitfall that killed it**: DeepSeek v4-flash consumes its entire `max_tokens` budget on reasoning tokens (`reasoning_tokens`), leaving zero tokens for actual output (`finish_reason=length, content=""`). This happens unpredictably — simple clean text may work, but garbled OCR output triggers excessive reasoning that overflows any reasonable budget. Even max_tokens=4000 gets fully eaten. v4-pro is worse (even more reasoning overhead).

**Bottom line**: Not reliable enough for daily use. Stick with mmx vision. If you ever retry this approach, consider non-reasoning models only.

Full details: `references/tesseract-llm-pipeline.md`

## Open-Source OCR Alternatives

When the user asks about free/open-source image recognition tools instead of
cloud APIs, see `references/open-source-ocr-tools.md` for a ranked comparison
of Tesseract, PaddleOCR, Qwen VL, DeepSeek-OCR, RolmOCR, and others.

## Common Reference Images

See `references/image-reading-notes.md` for:
- Verified Copilot icon description (correct visual prompt to use)
- Authentication troubleshooting
- Known working patterns
