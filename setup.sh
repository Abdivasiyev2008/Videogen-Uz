#!/usr/bin/env bash
# Bir martalik o'rnatish / One-time setup (macOS/Linux)
set -e
cd "$(dirname "$0")"
command -v ffmpeg >/dev/null || { echo "ffmpeg kerak: brew install ffmpeg  (yoki apt install ffmpeg)"; exit 1; }
python3 -m venv .venv
./.venv/bin/pip install -q -r requirements.txt
./.venv/bin/playwright install chromium
echo "✓ Tayyor. Sinov: ./.venv/bin/python make.py --script examples/ai_faktlar.json"
