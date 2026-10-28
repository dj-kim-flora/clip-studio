#!/usr/bin/env python3
"""Contact strip of a rendered film for reviewing a transition: 8 frames (4x2) from t0 every `step` seconds.

    python3 tools/strips.py _work/film.mp4 24.6 0.4 [out.png]

Look for double images (a beat still melting while the next rises in the same place), anything touching the frame edge,
text over a face or captions, and holds that are too short to read.
"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ff import FF
video, t0, step = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
out = sys.argv[4] if len(sys.argv) > 4 else os.path.splitext(video)[0] + f'-strip-{t0:g}.png'
subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-ss', f'{t0}', '-i', video, '-vf', f'fps=1/{step},scale=480:-2,tile=4x2', '-frames:v', '1', out], check=True)
print(out, f'(frames at {", ".join(f"{t0 + i * step:.2f}" for i in range(8))} s)')
