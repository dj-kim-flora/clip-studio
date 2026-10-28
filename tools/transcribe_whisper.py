#!/usr/bin/env python3
"""Transcriber for macOS < 26 (tools/transcribe picks it automatically): mlx-whisper with word timings.

    tools/transcribe <audio.wav> <out.json>

Writes the kit's transcript shape: [{"s","e","text","words":[{"t","s","e"}]}].
WHISPER_PROMPT biases spelling (names, products); when unset it is built from the glossary in public/brand/brand.json.
WHISPER_MODEL overrides the model.
Word times drift up to ~1 s in slow dictation: the cut builder snaps to measured pauses, and tools/postbrief.py rebuilds
captions from the verified EDL scripts, so neither depends on exact word stamps.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brand
if len(sys.argv) < 3:
    print('usage: transcribe <audio.wav> <out.json>'); sys.exit(1)
import mlx_whisper
MODEL = os.environ.get('WHISPER_MODEL', 'mlx-community/whisper-large-v3-turbo')
r = mlx_whisper.transcribe(sys.argv[1], path_or_hf_repo=MODEL, word_timestamps=True,
                           condition_on_previous_text=False, language='en',
                           initial_prompt=brand.whisper_prompt() or None)
segs = []
for s in r['segments']:
    words = [{'t': w['word'].strip(), 's': round(w['start'], 3), 'e': round(w['end'], 3)}
             for w in s.get('words', []) if w['word'].strip()]
    if not words: continue
    segs.append({'s': words[0]['s'], 'e': words[-1]['e'], 'text': s['text'].strip(), 'words': words})
json.dump(segs, open(sys.argv[2], 'w'))
