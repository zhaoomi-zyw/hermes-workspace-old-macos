# Buzz Windows Installation Notes

## Versions encountered
- Buzz 1.4.4 (latest as of June 2026)
- Downloaded from GitHub releases or SourceForge via winget

## Installation methods

### Method 1: GitHub exe (failed with "insert disk" error)
- Download from: https://github.com/chidiwilliams/buzz/releases/latest
- File: `Buzz-1.4.4-windows.exe` (~70MB)
- Error: Installer prompts "Setup Needs the Next Disk" → "Please insert Disk 1" at path E:\
- Root cause: Unknown — possibly corrupted download or installer packaging issue
- Resolution: Cancel and use winget instead

### Method 2: winget (works, but large download)
- Command: `winget install ChidiWilliams.Buzz` (NOT `winget install buzz` — ambiguous with Jeskola.Buzz)
- Downloads from SourceForge: ~2.5GB (bundles all Whisper models in the package)
- Installs silently after download
- First launch: pick tiny model (~150MB additional download on first model use)

### Method 3: pip (wrong package name trap)
- ❌ `pip install buzz-transcriber` — does NOT exist
- ✅ Instead use: `pip install openai-whisper` — the official Whisper package
- Then run: `whisper video.mp4 --model tiny --language Japanese --output_format srt`

## Post-install: selecting tiny model
1. Open Buzz
2. Model dropdown → select `tiny`
3. Task → `Transcribe`
4. Language → match video language
5. Import media file → Run
6. Export as .srt
