---
name: video-subtitle-workflows
category: media
description: AI subtitle generation + player integration across Windows, macOS, and Apple TV. Covers Whisper-based tools, local player subtitle handling, and Alist/cloud streaming subtitle troubleshooting.
tags: [subtitles, whisper, video-player, potplayer, iina, vidhub, alist, apple-tv, srt, ass]
---

# Video & Subtitle Workflows

Guide for AI subtitle generation and video player integration across platforms.

## Scope

- Generating subtitles from video audio (Whisper-based) on Windows & macOS
- Using subtitles with local players (PotPlayer, IINA, VidHub)
- Fixing subtitle-related playback lag on Apple TV + Alist + cloud storage
- Format conversion (ASS/SSA → SRT)

## AI Subtitle Generation Tools

### Buzz (cross-platform, GUI)
- **macOS**: Download from GitHub releases, run the .dmg. Model pick tiny (~150MB) for speed.
- **Windows**: Two install routes:
  - `winget install ChidiWilliams.Buzz` — downloads ~2.5GB (bundles all models), but works reliably
  - GitHub exe (~70MB) — may fail with "insert disk" error on some systems; cancel and use winget instead
- First run: Model dropdown → tiny, Task → Transcribe, Language → match video audio

### Subtitle Edit (Windows, GUI)
- Best fallback if Buzz installer fails
- Download `.zip` from GitHub releases — no installer, unzip and run
- **Audio to text (Whisper)** dialog:
  - Engine: **CPP** (lightweight CPU, auto-downloads model on first use)
  - Avoid "Purfview's Faster-Whisper-XXL" — 1.4GB download, unnecessary
  - Model: **tiny** (fast, ~150MB total)
  - Language: match video language (Japanese, Chinese, English, etc.)
  - Uncheck "Translate to English" unless you want English output
- Output as .srt, then pair with video in any player

### Whisper CLI (cross-platform, cmdline)
```bash
pip install openai-whisper
whisper video.mp4 --model tiny --language Japanese --output_format srt
```
Note: package name is `openai-whisper`, NOT `buzz-transcriber` or `whisper`.

## Player Subtitle Integration

### PotPlayer (Windows)
- Auto-loads same-name .srt in the same directory
- Real-time translation: right-click → Subtitles → Select subtitle → Real-time translation → Google Translate
- Handles ASS/SSA but may lag with complex effects; SRT is smoother

### IINA (macOS)
- Native macOS player, auto-loads same-name subtitles
- Supports SRT, ASS, SSA

### VidHub (Apple TV)
- Supports Alist/WebDAV backend for cloud storage streaming
- **Known issue**: ASS/SSA subtitles cause severe playback lag on Apple TV
- **Fix**: Convert to SRT format — pure text, no effects, renders instantly

## Apple TV + Alist + Subtitle Lag Troubleshooting

**Symptom**: Video plays fine on Apple TV via VidHub until subtitles load, then stutters/freezes.

**Root cause chain**:
1. Cloud storage (Quark/Quark) + Alist streaming uses bandwidth for video
2. ASS/SSA subtitles with effects require real-time rendering by tvOS player
3. VidHub's subtitle engine on tvOS is less optimized than Infuse's
4. Combined load pushes Apple TV past smooth playback threshold

**Fix**: Convert ASS/SSA subtitles to SRT format. SRT is pure text + timestamps — no rendering overhead.

**If still laggy after SRT**: Try switching player to Infuse (better subtitle rendering on tvOS), or ensure Alist WebDAV is used rather than direct cloud API.

## Subtitle Format Guide

| Format | Rendering overhead | Best for |
|--------|-------------------|----------|
| SRT | Minimal — pure text + timestamps | Apple TV, streaming, all players |
| ASS/SSA | Heavy — fonts, colors, animation, positioning | Desktop players, local playback only |
| VTT | Light — web-subtitle format | Browsers, some players |

Convert ASS/SSA → SRT using: Subtitle Edit, Aegisub, ffmpeg, or online tools.

## Pitfalls

- **Buzz Windows exe "insert disk" error**: Installer may be corrupt. Cancel, use `winget install ChidiWilliams.Buzz` instead (tolerates the ~2.5GB download).
- **pip package name**: `buzz-transcriber` does NOT exist. Use `openai-whisper` for the Python Whisper package.
- **Subtitle Edit XXL engine**: "Purfview's Faster-Whisper-XXL" downloads 1.4GB. Use "CPP" engine + tiny model instead (~150MB total).
- **Apple TV + ASS**: Always convert to SRT before streaming via VidHub. Even with Alist, ASS will lag.
- **Language mismatch**: If the video is in Japanese, set Language to Japanese (not Chinese) in the Whisper tool. Generate native subtitles, then use player real-time translation if needed.
