#!/usr/bin/env python3
"""Flag single frames that differ from both neighbours while the neighbours match (decode glitches, flash frames).

    python3 tools/glitch_scan.py <video> [--fps 30]

Reads the video at 64x36 through ffmpeg and compares each frame with the ones next to it. Pure Python: no numpy needed.
Prints "none" or a list of (time in seconds, how different the frame is, how different its neighbours are).
"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ff import FF

W, H = 64, 36
SIZE = W * H * 3

def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    path = sys.argv[1]
    fps = float(sys.argv[sys.argv.index('--fps') + 1]) if '--fps' in sys.argv else 30.0
    if not os.path.exists(path):
        raise SystemExit(f'No such file: {path}')
    raw = subprocess.run([FF, '-v', 'error', '-i', path, '-an', '-vf', f'fps={fps},scale={W}:{H}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         capture_output=True).stdout
    n = len(raw) // SIZE
    if n < 3:
        raise SystemExit('Too few frames to scan.')
    frames = [raw[i * SIZE:(i + 1) * SIZE] for i in range(n)]
    def d(a, b):
        return sum(abs(x - y) for x, y in zip(a, b)) / SIZE
    hits = []
    for i in range(1, n - 1):
        a, b, c = d(frames[i - 1], frames[i]), d(frames[i], frames[i + 1]), d(frames[i - 1], frames[i + 1])
        if min(a, b) > 6 and min(a, b) > 3 * c:
            hits.append((round(i / fps, 2), round(min(a, b), 1), round(c, 1)))
    print(os.path.basename(path), 'glitches:', hits or 'none')

if __name__ == '__main__':
    main()
