#!/usr/bin/env python3
"""Tesseract OCR → DeepSeek v4-flash correction pipeline.

Usage:
    python3 ocr_correct.py <image_path>
    python3 ocr_correct.py <image_path> --prompt "修正OCR错误，输出日语单词表"
    python3 ocr_correct.py <image_path> --no-correct  (Tesseract only)

Reads DEEPSEEK_API_KEY from ~/.hermes/profiles/main/.env.
Prints corrected text to stdout, diagnostics to stderr.
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request


def load_api_key():
    env_path = os.path.expanduser("~/.hermes/profiles/main/.env")
    try:
        with open(env_path) as f:
            for line in f:
                if line.startswith("DEEPSEEK_API_KEY") and "=" in line:
                    return line.strip().split("=", 1)[1].strip('"').strip("'")
    except FileNotFoundError:
        pass
    return os.environ.get("DEEPSEEK_API_KEY")


def tesseract_ocr(image_path, lang="jpn+chi_sim", psm=6):
    """Run Tesseract OCR and return raw text."""
    result = subprocess.run(
        ["tesseract", image_path, "stdout", "-l", lang, "--psm", str(psm)],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        print(f"Tesseract error: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def deepseek_correct(raw_text, api_key, prompt=None, max_tokens=4000):
    """Send raw OCR to DeepSeek v4-flash for correction."""
    if prompt is None:
        prompt = "修正OCR错误，输出完整原文："

    payload = {
        "model": "deepseek-v4-flash",
        "messages": [{
            "role": "user",
            "content": f"{prompt}\n\n{raw_text}"
        }],
        "max_tokens": max_tokens
    }

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )

    start = time.time()
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())
    elapsed = time.time() - start

    msg = result["choices"][0]["message"]["content"]
    tokens = result.get("usage", {})
    total_tokens = tokens.get("total_tokens", 0)
    cost = total_tokens * 0.14 / 1_000_000 * 7.2  # ¥

    print(f"DeepSeek: {elapsed:.1f}s, {total_tokens} tokens, ¥{cost:.5f}", file=sys.stderr)
    return msg


def main():
    parser = argparse.ArgumentParser(description="Tesseract + DeepSeek OCR pipeline")
    parser.add_argument("image", help="Path to image file")
    parser.add_argument("--prompt", default=None,
                        help="Correction prompt (default: '修正OCR错误，输出完整原文：')")
    parser.add_argument("--no-correct", action="store_true",
                        help="Skip DeepSeek correction, output raw Tesseract only")
    parser.add_argument("--lang", default="jpn+chi_sim",
                        help="Tesseract language (default: jpn+chi_sim)")
    parser.add_argument("--psm", type=int, default=6,
                        help="Tesseract PSM mode (default: 6)")
    args = parser.parse_args()

    if not os.path.exists(args.image):
        print(f"File not found: {args.image}", file=sys.stderr)
        sys.exit(1)

    # Step 1: Tesseract
    t0 = time.time()
    raw = tesseract_ocr(args.image, lang=args.lang, psm=args.psm)
    tesseract_time = time.time() - t0
    print(f"Tesseract: {tesseract_time:.1f}s, {len(raw)} chars", file=sys.stderr)

    # Step 2: DeepSeek correction
    if args.no_correct:
        print(raw)
    else:
        api_key = load_api_key()
        if not api_key:
            print("No DEEPSEEK_API_KEY found in ~/.hermes/profiles/main/.env", file=sys.stderr)
            sys.exit(1)
        corrected = deepseek_correct(raw, api_key, prompt=args.prompt)
        print(corrected)


if __name__ == "__main__":
    main()
