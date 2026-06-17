---
name: tesseract-deepseek-ocr
description: ⚠️ DEPRECATED — DeepSeek v4-flash reasoning tokens cause unreliable empty output. Use mmx vision instead. OCR Japanese/Chinese mixed text from screenshots using Tesseract (free, local, CPU) + DeepSeek v4-flash correction (cheap text API). 
version: 1.1
status: deprecated
deprecation_reason: DeepSeek v4-flash reasoning_tokens consume entire max_tokens budget on complex/garbled OCR, returning empty content unpredictably (2026-05-30). Use read-image skill with mmx vision instead.
---

# Tesseract + DeepSeek OCR Correction Pipeline

Two-stage pipeline: Tesseract OCR (free, offline, CPU) → DeepSeek v4-flash text correction (¥0.001-0.003 per image).

## Status: ABANDONED

This pipeline is unreliable and no longer in use. Prefer `read-image` skill (MiniMax vision via `mmx vision describe`) instead.

Root cause: DeepSeek v4 series (both pro and flash) allocates reasoning tokens internally that consume the `max_tokens` budget. On complex or garbled OCR text, ALL 4000 tokens can go to reasoning with zero output content (`finish_reason=length`, `content=''`, `reasoning_tokens=4000`). Increasing max_tokens further only delays the same failure. This makes the pipeline non-deterministic and unsuitable as a default OCR workflow.

## When NOT to Use

- Any OCR task. Use `read-image` skill instead.
- Any pipeline involving DeepSeek v4 for post-processing where the input is noisy or requires significant correction — reasoning token bleed makes it unreliable.

- Japanese/Chinese mixed text extraction from screenshots
- User wants free/cheap OCR without cloud vision API costs
- Image is clean enough for Tesseract to get ~80% accuracy
- Not for: complex layouts, tables, handwriting-heavy images

## Quick Start

Use the bundled script for one-shot pipeline invocation:

```bash
python3 <skill_dir>/scripts/ocr_correct.py <image_path>
```

With a custom correction prompt:

```bash
python3 <skill_dir>/scripts/ocr_correct.py <image_path> --prompt "修正OCR错误，输出日语单词表"
```

The script reads `DEEPSEEK_API_KEY` from `~/.hermes/profiles/main/.env`, runs Tesseract → DeepSeek v4-flash, prints corrected text to stdout, and diagnostics (timing, cost) to stderr.

## Step 1: Tesseract OCR

```bash
# Best for Japanese + Chinese mixed screenshots
tesseract <image_path> stdout -l jpn+chi_sim --psm 6
```

PSM modes:
- `--psm 6` = uniform block of text (best for paragraphs)
- `--psm 3` = auto (try if 6 fails)
- `--psm 4` = single column of variable sizes (word lists)

## Step 2: DeepSeek v4-flash Correction

**Critical**: Use `deepseek-v4-flash`, NOT `deepseek-v4-pro`.

Why:
- v4-pro spends >700 reasoning tokens and hits max_tokens limit → empty output
- v4-flash still has ~2600 reasoning tokens but finishes within 4000 max_tokens
- Set `max_tokens=4000` minimum to accommodate reasoning overhead

### Python code

```python
import urllib.request, json

# Read key from ~/.hermes/profiles/main/.env (DEEPSEEK_API_KEY)
payload = {
    "model": "deepseek-v4-flash",
    "messages": [{"role": "user", "content": f"修正OCR错误，输出日文单词表：\n\n{raw_ocr}"}],
    "max_tokens": 4000
}
req = urllib.request.Request(
    "https://api.deepseek.com/v1/chat/completions",
    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
)
```

## Cost Benchmarks

| Content Type | Tesseract | DeepSeek | Total Time | Cost |
|-------------|-----------|----------|-----------|------|
| Plain prose (paragraph) | <1s | ~5s | ~5s | ¥0.001 |
| Word list (mixed format) | <1s | ~25s | ~26s | ¥0.003 |
| Dialogue (multi-speaker) | <1s | ~31s | ~31s | ¥0.004 |

vs MiniMax vision: ~5s, ¥0.01-0.03 per image.

## Prompt Strategy

- **Keep prompts short**: "修正OCR错误，输出完整日文原文" works better than verbose instructions. DeepSeek v4-flash is smart enough.
- **Add context for ambiguous errors**: When Tesseract produces garbled segments (e.g., "[ES はい" or "販沖"), give DeepSeek a hint about the content type. Example: "这是一段关于田中老师出车祸住院的对话" — this helps it disambiguate between similar-looking corrections.
- **For word lists**: Use "修正OCR错误，输出日文单词表" to get structured output.
- **For prose**: Use "修正OCR错误，输出完整日文原文" for clean paragraphs.

## Cost Benchmarks

| Content Type | Tesseract | DeepSeek | Total Time | Cost |
|-------------|-----------|----------|-----------|------|
| Plain prose (paragraph) | <1s | ~5s | ~5s | ¥0.001 |
| Word list (mixed format) | <1s | ~25s | ~26s | ¥0.003 |
| Dialogue (multi-speaker) | <1s | ~31s | ~31s | ¥0.004 |

vs MiniMax vision: ~5s, ¥0.01-0.03 per image.

## Pitfalls

1. **FATAL — DeepSeek v4 reasoning tokens**: Both v4-pro and v4-flash allocate reasoning tokens that consume `max_tokens`. On complex/garbled OCR input, reasoning can consume 100% of the budget (e.g., 4000/4000 reasoning, 0 output). This is unfixable — the model decides internally how much to "think" and can starve the output. Abandoned for this reason.
2. **v4-pro is worse than v4-flash**: More reasoning overhead, slower, and same failure mode.
3. **Tesseract needs jpn+chi_sim both**: Japanese text often contains kanji. Using only `-l jpn` misses Chinese explanations.
4. **PSM mode matters**: `--psm 6` for paragraphs, `--psm 4` for word lists. Wrong PSM = garbled output.
5. **Tesseract cannot do roles/speakers**: Dialogue with speaker names requires VLM.
5. **Skip DeepSeek when clean**: If Tesseract output is already ~99% correct (only trailing garbage like "S-@ 、"), skip the API call or use a minimal prompt — DeepSeek adds 4-25s latency for no gain. Only use the correction step when there are actual character errors.
6. **Dialogue text is slowest**: Multi-speaker conversations with OCR artifacts take ~30s for DeepSeek to correct (more reasoning needed for speaker attribution, garbled lines).
