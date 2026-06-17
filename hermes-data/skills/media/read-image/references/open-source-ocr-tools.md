# Open-Source OCR & Vision Tools (2025)

Researched May 2026. When the user asks about free/open-source alternatives to
cloud vision APIs (MiniMax, GPT-4o, Gemini), refer to this list.

## Traditional OCR (lightweight, CPU-friendly)

| Tool | Repo | License | Notes |
|------|------|---------|-------|
| Tesseract | google/tesseract | Apache 2.0 | 100+ languages, CPU-first, weak on handwriting/tables |
| PaddleOCR | PaddlePaddle/PaddleOCR | Apache 2.0 | Best for Chinese/English, tables/formulas, GPU recommended |

## VLM-Based OCR (higher accuracy, needs GPU)

| Model | Repo/Source | License | Notes |
|-------|------------|---------|-------|
| Qwen 2.5/3 VL | QwenLM/Qwen3-VL | Apache 2.0 (some checkpoints) | ~75% accuracy ≈ GPT-4o, tops OCRBench |
| DeepSeek-OCR-2 | deepseek-ai/DeepSeek-OCR-2 | Apache 2.0 | Native transformer OCR, vLLM compatible |
| RolmOCR | reducto/RolmOCR (HF) | Apache 2.0 | Qwen 2.5-VL 7B fine-tune, lightweight |
| InternVL 2.5 | OpenGVLab/InternVL | MIT (some variants) | 1B-78B sizes, general doc understanding |
| GOT-OCR 2.0 | Ucas-HaoranWei/GOT-OCR2.0 | Apache 2.0 | Unified: text/charts/formulas in one pass |
| Llama 4 Vision | meta-llama | Open-source | Moderate OCR, general multimodal |
| Gemma 3 | google/gemma | Open-source | Weak OCR (~43%), similar arch to Gemini 2.0 |
| Mistral OCR | mistralai | Model open, API paid | Purpose-built OCR, per-token billing |

## End-to-End Pipelines

| Tool | Repo | License | Notes |
|------|------|---------|-------|
| Marker (Datalab) | datalab-to/marker | OpenRAIL | PDF/image → Markdown/JSON, optional LLM refinement |

## Quick Recommendations

- **Free + local CPU**: Tesseract
- **Free + local GPU, best Chinese**: PaddleOCR
- **Free + local GPU, best accuracy**: Qwen 3 VL or DeepSeek-OCR-2
- **Free + lightweight GPU**: RolmOCR (7B, single consumer GPU)
- **Structured output pipeline**: Marker

## Key Sources

- https://getomni.ai/blog/benchmarking-open-source-models-for-ocr (April 2025 benchmark)
- https://modal.com/blog/8-top-open-source-ocr-models-compared (updated Nov 2025)
