#!/usr/bin/env python3
"""Tighten hesitations inside spans: split every span at each internal silence of >= --min seconds (default 0.55),
so build_cut.py balances each one to its ~0.3 s join. Run it on a fresh EDL before the first build.

    python3 tools/split_pauses.py cuts/<slug>.edl.json [--min 0.55] [--dry]

- A silence is the analysis audio below -64 dB (the builder's pause threshold), measured on 20 ms windows.
- The new out/in points sit just inside each silence (0.12 s after the word, 0.10 s before the next), never equal:
  equal points read as one continuous take and nothing would be removed.
- Scene boundaries are left alone (the breath between beats carries the visual hand-off), and so are exact-pinned ends.
- Every internal cut is also a jump in any face video; that's the accepted trade for tight delivery.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_cut

def silences(a, b, minlen):
    out, t, run = [], a, None
    while t <= b:
        quiet = build_cut.rms_at(t, 0.02) < build_cut.PAUSE_DB
        if quiet and run is None: run = t
        if not quiet and run is not None:
            if t - run >= minlen: out.append((run, t))
            run = None
        t = round(t + 0.02, 2)
    return out

def main():
    p = sys.argv[1]; minlen = float(sys.argv[sys.argv.index('--min') + 1]) if '--min' in sys.argv else 0.55
    d = json.load(open(p)); build_cut.use_source(d['sourceId']); n = 0
    for sc in d['scenes']:
        if not sc.get('spans'): continue
        new = []
        for sp in sc['spans']:
            a, b = sp[0], sp[1]; mode = sp[2] if len(sp) > 2 else None
            sil = silences(a + 0.25, b - 0.25, minlen); pts = [a]
            for r0, r1 in sil: pts += [r0 + 0.12, r1 - 0.10]
            pts.append(b)
            pieces = [[round(pts[i], 2), round(pts[i + 1], 2)] for i in range(0, len(pts), 2)]
            if mode in ('exact-in', 'exact'): pieces[0].append('exact-in')
            if mode in ('exact-out', 'exact'):
                pieces[-1] = pieces[-1][:2] + (['exact'] if len(pieces) == 1 and mode == 'exact' else ['exact-out'])
            if sil: print(f"{sc['id']:10s} {a:.2f}-{b:.2f}: split at " + ' '.join(f'{r0:.2f}-{r1:.2f}' for r0, r1 in sil)); n += len(sil)
            new += pieces
        sc['spans'] = new
    if '--dry' not in sys.argv: json.dump(d, open(p, 'w'), indent=1)
    print(f'{n} hesitation(s) {"found" if "--dry" in sys.argv else "split"} (>= {minlen} s)')

if __name__ == '__main__':
    main()
