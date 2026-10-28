#!/bin/bash
# Read-only readiness check. Prints one line per requirement and "READY" or "NOT READY". Changes nothing.
cd "$(dirname "$0")"
ok=1
chk() { if eval "$2" >/dev/null 2>&1; then echo "  ok   $1"; else echo "  MISSING  $1  ->  $3"; ok=0; fi; }
chk "Node 22+"            'node -e "process.exit(+process.versions.node.split(\".\")[0]>=22?0:1)"' "install Node from nodejs.org, or: brew install node"
chk "Node packages"       '[ -d node_modules/remotion ]'                                   "run: bash setup.sh"
chk "Python 3"            'python3 --version'                                              "brew install python"
chk "ffmpeg"              "python3 -c \"import sys; sys.path.insert(0,'tools'); import ff\""  "run: bash setup.sh (or brew install ffmpeg)"
chk "Transcriber"         '{ [ "$(sw_vers -productVersion 2>/dev/null | cut -d. -f1)" -ge 26 ] 2>/dev/null && [ -x tools/transcribe.apple-bin ]; } || .venv/bin/python -c "import mlx_whisper"' "run: bash setup.sh"
chk "Brand file (public/brand/brand.json)" 'python3 -c "import json; d=json.load(open(\"public/brand/brand.json\")); assert isinstance(d, dict) and \"colors\" in d"' "run: bash setup.sh (creates it from the neutral default), or fix the JSON"
# optional extras: shown, never required
[ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ] && node -e "process.exit(typeof WebSocket===\"function\"?0:1)" 2>/dev/null && echo "  ok   Chrome + Node 22 (optional, records web links)" || echo "  --   Chrome or Node 22 missing (optional; needed to record a web link: install Google Chrome, Node 22+)"
command -v yt-dlp >/dev/null 2>&1 && echo "  ok   yt-dlp (optional, downloads links)" || echo "  --   yt-dlp not installed (optional; brew install yt-dlp)"
python3 -c "import cv2" 2>/dev/null && echo "  ok   OpenCV (optional, face tracking)" || echo "  --   OpenCV not installed (optional; pip3 install opencv-python-headless)"
[ "$ok" = 1 ] && echo "READY" || echo "NOT READY: run 'bash setup.sh', then 'bash check.sh' again"
