# Tesseract + LLM OCR Correction Pipeline

Free, local-first OCR workflow: Tesseract extracts raw text → LLM corrects recognition errors. ~10x cheaper than cloud vision APIs for Japanese/Chinese mixed text.

## Install

```bash
brew install tesseract tesseract-lang
```

Language packs include `jpn`, `jpn_vert`, `chi_sim`, etc. Verify: `tesseract --list-langs`.

## Run Tesseract

```bash
tesseract image.png stdout -l jpn+chi_sim --psm 6
```

- `-l jpn+chi_sim`: combined Japanese + Simplified Chinese (good for mixed-text screenshots)
- `--psm 6`: treat image as uniform block of text (best for screenshots)
- `--psm 3`: default, auto-detect layout (good for scanned documents)
- PSM modes: 3=auto, 4=single column, 6=uniform block, 11=sparse text

## LLM Correction

Send raw OCR to a text-only LLM to fix recognition errors. Known error patterns in Japanese OCR:

| Raw OCR | Correct |
|---------|---------|
| 証生日 | 誕生日 |
| 語 (out of context) | 話 |
| タ方 | 夕方 |
| 遣う | 遭う |

### Model choice (CRITICAL)

| Model | Suitability | Why |
|-------|------------|-----|
| **gpt-4o-mini** | ✅ Best | No reasoning overhead, reliable output |
| deepseek-v4-flash | ⚠️ Unreliable | Has `reasoning_tokens` overhead (~2600 tokens per call). On simple text it works with `max_tokens=4000`, but on garbled/complex OCR output the reasoning can consume the entire budget → `finish_reason=length, content=""`. **Tested failure 2026-05-30**: 4 attempts on a moderately garbled Japanese dialogue, all 4 returned empty content with all 4000 tokens going to reasoning. |
| deepseek-v4-pro | ❌ Avoid | Even more reasoning overhead than flash, worse failure rate |

**Recommendation**: Avoid DeepSeek v4 series entirely for OCR correction. Use a non-reasoning model like gpt-4o-mini, or any model without `reasoning_tokens` overhead.

### Example prompt

```
以下是Tesseract OCR识别日文图片的结果。请修正OCR错误并输出完整的日文原文。已知错误包括：「証生日」→「誕生日」、「語」→「話」、「タ方」→「夕方」。输出只保留修正后的日文，不要加解释。

{raw_ocr_text}
```

Set `max_tokens: 800` for flash models, `max_tokens: 4000` if you must use a reasoning model.

## Cost Comparison (per image)

| Pipeline | Cost | Speed |
|----------|------|-------|
| MiniMax vision (direct) | ~¥0.01-0.03 | ~5s |
| **Tesseract + DeepSeek v4-flash** | **~¥0.0015** | ~5s |
| Tesseract alone (no correction) | Free | <1s |

## Limitations

- Tesseract struggles with: handwriting, complex tables, low-contrast text, vertical Japanese (`jpn_vert` helps but not perfect)
- LLM correction can't fix completely garbled characters — only context-based errors
- Pure English OCR: Tesseract alone often sufficient, correction rarely needed
- **DeepSeek v4 series UNRELIABLE for this task** (2026-05-30): both v4-pro and v4-flash spend `reasoning_tokens` that consume entire `max_tokens` budget, returning empty output unpredictably. See model choice table above.
