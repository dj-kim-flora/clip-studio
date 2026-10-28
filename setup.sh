#!/bin/bash
# One-time setup for Clip Studio. Safe to re-run. Add --no-links to skip step 5 (the agent skill links).
set -e
cd "$(dirname "$0")"
KIT="$(pwd)"
LINKS=1
for a in "$@"; do [ "$a" = "--no-links" ] && LINKS=0; done

echo "1/5  Node packages (Remotion 4, React 19)"
if [ ! -d node_modules ]; then
  if command -v npm >/dev/null 2>&1; then npm ci; else echo "     !! npm not found. Install Node 22+ from nodejs.org (or: brew install node), then re-run."; fi
else echo "     already installed"; fi

echo "2/5  ffmpeg"
if python3 -c "import sys; sys.path.insert(0,'tools'); import ff; print('     ' + ff.FF)" 2>/dev/null; then :; else
  echo "     !! no ffmpeg. Install one: brew install ffmpeg   (or: pip3 install imageio-ffmpeg)"; fi

echo "3/5  On-device transcriber"
MAJOR=$(sw_vers -productVersion 2>/dev/null | cut -d. -f1)
if [ "${MAJOR:-0}" -ge 26 ]; then
  if ./tools/transcribe.apple-bin 2>&1 | grep -q usage; then echo "     Apple SpeechAnalyzer transcriber runs"; else
    echo "     rebuilding…"; bash tools/build-transcribe.sh || echo "     !! could not build it (needs Xcode); falling back to mlx-whisper"; fi
fi
if [ "${MAJOR:-0}" -lt 26 ] || ! ./tools/transcribe.apple-bin 2>&1 | grep -q usage; then
  # macOS < 26 (or no SpeechAnalyzer build): mlx-whisper in a local venv; the model downloads on first use (~1.6 GB)
  if [ ! -x .venv/bin/python ] || ! .venv/bin/python -c "import mlx_whisper" 2>/dev/null; then
    python3 -m venv .venv && .venv/bin/pip install -q mlx-whisper && echo "     mlx-whisper installed in .venv"
  else echo "     mlx-whisper ready in .venv"; fi
fi

echo "4/5  Project files and optional extras"
if [ -f public/brand/brand.json ]; then echo "     public/brand/brand.json present"
elif [ -f public/brand/brand.default.json ]; then cp public/brand/brand.default.json public/brand/brand.json; echo "     created public/brand/brand.json from the neutral default"
else echo "     !! public/brand/brand.default.json is missing; the kit falls back to built-in neutral colours"; fi
if [ ! -f src/films/local-films.ts ] && [ -f src/films/local-films.example.ts ]; then
  cp src/films/local-films.example.ts src/films/local-films.ts; echo "     created src/films/local-films.ts"; fi
if command -v yt-dlp >/dev/null 2>&1; then echo "     optional: yt-dlp found (links can be downloaded)"
else echo "     optional: yt-dlp not installed. Only needed to download links:  brew install yt-dlp"; fi
if python3 -c "import cv2" 2>/dev/null; then echo "     optional: OpenCV found (face-tracking crops work)"
else echo "     optional: OpenCV not installed. Only needed for face-tracking crops:  pip3 install opencv-python-headless"; fi

if [ "$LINKS" = 1 ]; then
echo "5/5  Skill links (one source, every agent)"
# This repository is the only copy. Each agent's skills folder gets a symlink to it: Cursor and other agents that follow
# the shared ~/.agents/skills convention, Claude Code (~/.claude/skills) and Codex (~/.codex/skills). Agents without a
# skills folder (Gemini CLI and others) open this repository and read AGENTS.md. A real folder already at a link path is
# left alone (it may be someone's own copy): move it aside and re-run to link.
NAME=clip-studio
for d in "$HOME/.agents/skills" "$HOME/.claude/skills" "$HOME/.codex/skills"; do
  mkdir -p "$d"; L="$d/$NAME"
  if [ -L "$L" ]; then ln -sfn "$KIT" "$L"; echo "     linked  $L"
  elif [ -e "$L" ]; then echo "     !! $L is a real folder, not a link; left as is"
  else ln -s "$KIT" "$L"; echo "     linked  $L"; fi
done
else
echo "5/5  Skill links skipped (--no-links)"
fi

echo
echo "Done. Check anytime with:  bash check.sh"
echo "Then open this folder in your AI agent and say what you want made (START-HERE.md has the details)."
