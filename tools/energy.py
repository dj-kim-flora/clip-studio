#!/usr/bin/env python3
"""Energy strip around a source time, to see where a word ends and a pause starts.

    python3 tools/energy.py <sourceId> 2964.9 [radius]      '#' per 3 dB above -70 dBFS; room tone is about -80
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_cut
build_cut.use_source(sys.argv[1])
t = float(sys.argv[2]); r = float(sys.argv[3]) if len(sys.argv) > 3 else 0.4
k = round((t - r) * 50)
while k / 50 <= t + r:
    c = k / 50; db = build_cut.rms_at(c, 0.02)
    print(f"{c:9.2f} {db:6.1f} {'#' * max(0, int((db + 70) / 3))}{'  <' if abs(c - t) < 0.011 else ''}")
    k += 1
