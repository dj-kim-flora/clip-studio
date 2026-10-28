#!/usr/bin/env python3
"""Rebuild a built brief's captions from each scene's EDL `script` (run after build_cut.py).

The transcriber's own text can lack punctuation and pick up faint words at span edges. The EDL script is the exact,
verified wording, so captions take their text from it and their timing from the brief's word timings: each script
word is matched in order to a timed word; unmatched script words get interpolated times; timed words the script
doesn't have (inaudible fragments) are dropped. Cues break at sentence ends, long gaps, or two lines of `captionChars`.

    python3 tools/postbrief.py cuts/<slug>.edl.json ["<Speaker name>"]

EDL knobs: captionChars (46 → lines up to ~55 chars, sized for CAP_STAGE at 40 px), captionLines (1 = one straight line,
the default look; 2 = the older two-line pinned label).
"""
import json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
edl = json.load(open(sys.argv[1]))
p = os.path.join(ROOT, 'briefs', f"{edl['slug']}.json"); b = json.load(open(p))
name = sys.argv[2] if len(sys.argv) > 2 else (b.get('face') or {}).get('name') or b.get('cursorName') or 'Speaker'
CH = edl.get('captionChars', 46) or 46
LINES = edl.get('captionLines', 1)
norm = lambda s: re.sub(r'[^a-z0-9]', '', s.lower())
words = b['words']

def align(scene):
    toks = scene['script'].split(); timed = [w for w in words if w[3] == scene['id']]
    out = [None] * len(toks); j = 0
    for w in timed:
        nw = norm(w[0])
        if not nw: continue
        for k in range(j, min(j + 4, len(toks))):
            nt = norm(toks[k])
            if nt and (nt == nw or nt.startswith(nw) or nw.startswith(nt) or (len(nw) > 3 and nt[:4] == nw[:4])):
                out[k] = [w[1], w[2]]; j = k + 1; break
    known = [i for i, v in enumerate(out) if v]
    for i in range(len(toks)):          # interpolate script words the transcriber didn't stamp
        if out[i]: continue
        prev = max([k for k in known if k < i], default=None); nxt = min([k for k in known if k > i], default=None)
        a = out[prev][1] if prev is not None else (out[nxt][0] - 0.3 if nxt is not None else 0)
        z = out[nxt][0] if nxt is not None else a + 0.3
        span = [k for k in range(prev + 1 if prev is not None else 0, nxt if nxt is not None else len(toks))]
        n = span.index(i); step = (z - a) / (len(span) + 0.0001)
        out[i] = [a + n * step, a + (n + 1) * step]
    return list(zip(toks, out))

def lines_of(ws):
    text = ' '.join(t for t, _ in ws)
    if len(text) <= CH: return [len(ws)]
    if LINES == 1: return None
    best = None
    for cut in range(1, len(ws)):
        l1 = len(' '.join(t for t, _ in ws[:cut])); l2 = len(' '.join(t for t, _ in ws[cut:]))
        if l1 <= CH and l2 <= CH:
            score = abs(l1 - l2)
            if best is None or score < best[0]: best = (score, cut)
    return [best[1], len(ws)] if best else None

def fits(ws, slack=0):
    global CH
    c0 = CH; CH = c0 + slack; ok = lines_of(ws) is not None; CH = c0; return ok

WEAK = set('a an the to of and or but from in on with that for as if at by my your this i i\'m it\'s is was just like'.split())
MAXC = CH + 9

def chunk(ws):
    """One-line mode: split a sentence into balanced lines (<= MAXC chars) by dynamic programming. Breaks after commas
    are cheap, breaks after weak words (and, the, from…) are expensive, and so are very short lines."""
    n = len(ws); L = [len(w[0]) for w in ws]
    def width(i, j): return sum(L[i:j]) + (j - i - 1)
    total = width(0, n); parts = max(1, -(-total // MAXC)); target = total / parts
    best = [0.0] + [float('inf')] * n; back = [0] * (n + 1)
    for j in range(1, n + 1):
        for i in range(j):
            wd = width(i, j)
            if wd > MAXC and j - i > 1: continue
            cost = (wd - target) ** 2 / 40 + (60 if j - i <= 2 and j < n else 0)
            if j < n:
                last = ws[j - 1][0]; nw = re.sub(r'[^a-z\']', '', last.lower())
                if re.search(r'[,;:]$', last): cost -= 25
                elif nw in WEAK: cost += 80
                if ws[j][1][0] - ws[j - 1][1][1] > 0.35: cost -= 15      # a real pause is a natural break
            if best[i] + cost < best[j]: best[j] = best[i] + cost; back[j] = i
    out, j = [], n
    while j > 0: i = back[j]; out.append(ws[i:j]); j = i
    return out[::-1]

cues = []
for sc in edl['scenes']:
    if sc.get('kind') != 'clip': continue
    al = align(sc)
    if LINES == 1:
        sent = []
        for idx, w in enumerate(al):
            if sent and w[1][0] - sent[-1][1][1] > 0.8: cues += chunk(sent); sent = []
            sent.append(w)
            if re.search(r'[.?!]$', w[0]): cues += chunk(sent); sent = []
        if sent: cues += chunk(sent)
        continue
    i = 0; cur = []
    while i < len(al):
        t, (s, e) = al[i]
        if cur and s - cur[-1][1][1] > 0.8:
            cues.append(cur); cur = []
        if cur and not fits(cur + [al[i]]):
            end = next((k for k in range(i, min(i + 2, len(al))) if re.search(r'[.?!]$', al[k][0])), None)
            if end is not None and fits(cur + al[i:end + 1], slack=7):
                cur += al[i:end + 1]; i = end + 1; cues.append(cur); cur = []; continue
            ks = [k for k in range(len(cur) - 2) if re.search(r'[,;:]$', cur[k][0]) and k >= 2]
            if ks:
                k = ks[-1] + 1; cues.append(cur[:k]); cur = cur[k:]
            else:
                cues.append(cur); cur = []
        cur.append(al[i]); i += 1
        if re.search(r'[.?!]$', t) and len(cur) >= 3: cues.append(cur); cur = []
    if cur: cues.append(cur)
# very short sentences ("That's cool.", "Okay.") join the next line when it fits
merged = []
for cw in cues:
    if merged and len(merged[-1]) <= 2 and re.search(r'[.?!]$', merged[-1][-1][0]) and cw[0][1][0] - merged[-1][-1][1][1] < 0.6 \
            and len(' '.join(t for t, _ in merged[-1] + cw)) <= MAXC:
        merged[-1] = merged[-1] + cw
    else:
        merged.append(cw)
cues = merged
# rebalance: a short sentence tail borrows words from the cue before it (same sentence) while both still fit
txt = lambda ws: ' '.join(t for t, _ in ws)
for i in range(1, len(cues) if LINES > 1 else 0):
    a, z = cues[i - 1], cues[i]
    while len(z) <= 2 and len(a) > 3 and not re.search(r'[.?!]$', a[-1][0]) and len(txt([a[-1]] + z)) <= CH \
            and z[0][1][0] - a[-1][1][1] < 0.6:
        z.insert(0, a.pop())
caps = []
for cw in cues:
    br = lines_of(cw)
    if br is None:
        c0 = CH; CH = c0 + 9; br = lines_of(cw) or [len(cw)]; CH = c0
    ws = [[t, round(s, 3), round(e, 3), 0 if i < br[0] else 1] for i, (t, (s, e)) in enumerate(cw)]
    text = ' '.join(w[0] for w in ws if w[3] == 0) + ('\n' + ' '.join(w[0] for w in ws if w[3] == 1) if len(br) > 1 else '')
    caps.append({'start': ws[0][1], 'end': ws[-1][2] + 0.15, 'text': text, 'words': ws})
for a, z in zip(caps, caps[1:]): a['end'] = min(a['end'], z['start'] - 0.03)
b['captions'] = caps
if b.get('voiceover'): b['voiceover']['voice'] = f'{name} (source audio)'
json.dump(b, open(p, 'w'), indent=1)
print(f'{len(caps)} caption cues rebuilt from the EDL scripts')
