#!/usr/bin/env python3
"""Find phrases in a recording's transcript, with source times and the words around them.

    python3 tools/find.py <sourceId> "pricing page" "free trial" [--context 12]

Matching ignores case and punctuation and tolerates the transcriber's usual mishearings being in the text (search for what
it wrote: a brand name may appear as a similar-sounding common word). Use the times to write spans in cuts/<slug>.edl.json.
"""
import json, os, re, sys
here = os.path.dirname(os.path.abspath(__file__))
args = [a for a in sys.argv[1:]]
ctx = 12
if '--context' in args:
    i = args.index('--context'); ctx = int(args[i + 1]); del args[i:i + 2]
sid, phrases = args[0], args[1:]
segs = json.load(open(os.path.join(here, '..', 'source', sid, 'transcript.json')))
words = [w for s in segs for w in s['words']]
norm = lambda x: re.sub(r"[^a-z0-9]", '', x.lower())
toks = [norm(w['t']) for w in words]
def hms(t):
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"
for ph in phrases:
    target = [norm(p) for p in ph.split() if norm(p)]
    hits = [i for i in range(len(toks) - len(target) + 1) if all(toks[i + j].startswith(target[j]) for j in range(len(target)))]
    print(f'"{ph}": {len(hits)} hit(s)')
    for i in hits:
        a, b = max(0, i - ctx), min(len(words), i + len(target) + ctx)
        text = ' '.join(('[' + w['t'].strip() + ']') if i <= k < i + len(target) else w['t'].strip() for k, w in enumerate(words[a:b], start=a))
        print(f"  {hms(words[i]['s'])}  ({words[i]['s']:.2f} s)  …{text}…")
