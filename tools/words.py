#!/usr/bin/env python3
"""Print the recording's transcript words with source timestamps for time ranges (seconds or h:mm:ss).

    python3 tools/words.py <sourceId> 2950-2982 1:14:05-1:14:30
"""
import json, os, sys
here = os.path.dirname(os.path.abspath(__file__))
sid, ranges = sys.argv[1], sys.argv[2:]
segs = json.load(open(os.path.join(here, '..', 'source', sid, 'transcript.json')))
words = [w for s in segs for w in s['words']]
def hms(t):
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"
def parse(x):
    if ':' in x:
        p = [float(v) for v in x.split(':')]
        return sum(v * 60 ** i for i, v in enumerate(reversed(p)))
    return float(x)
for arg in ranges:
    a, b = (parse(v) for v in arg.split('-'))
    print(f"=== {hms(a)} - {hms(b)} ===")
    line = []
    for w in words:
        if w['e'] < a or w['s'] > b:
            continue
        line.append(f"{w['t'].strip()}@{w['s']:.2f}")
        if len(line) == 8:
            print('  ' + '  '.join(line)); line = []
    if line:
        print('  ' + '  '.join(line))
