#!/usr/bin/env python3
"""Carry each scene's timed fields (walk, steps, pointers, inserts, pills…) across a re-cut.

Usage: python3 tools/retime_edl.py <old brief> <new brief> <edl>     (rewrites the EDL in place)

A scene-local time is mapped old film time -> source time (old sourceSpans + padBefore) -> new film time
(new sourceSpans + padBefore). A time that fell inside a stretch the new cut removed lands on the join.
Camera moves and cursor travel are shortened if a cut brought two keyframes closer than the move takes.
"""
import json, sys

def layout(scene):
    pad = float(scene.get('padBefore') or 0.0)
    out, t = [], pad
    for a, b in scene['sourceSpans']:
        out.append((t, a, b)); t += b - a
    return pad, out

def mapper(old, new):
    opad, osp = layout(old)
    npad, nsp = layout(new)
    def f(t):
        # which old span (and so which source range) the time belongs to
        k = 0
        for i, (off, a, b) in enumerate(osp):
            if t >= off - 1e-9:
                k = i
        off, a, b = osp[k]
        src = a + (t - off) if t >= opad else a - (opad - t)
        # new spans cut from that old span's source range
        cands = [(noff, na, nb) for noff, na, nb in nsp if nb > a - 1e-6 and na < b + 1e-6] or nsp
        for noff, na, nb in cands:
            if na - 1e-6 <= src <= nb + 1e-6:
                return round(noff + (src - na), 3)
        best = min(cands, key=lambda s: min(abs(src - s[1]), abs(src - s[2])))
        noff, na, nb = best
        return round(noff if abs(src - na) <= abs(src - nb) else noff + (nb - na), 3)
    return f

def retime(scene, f):
    n = 0
    def m(obj, key):
        nonlocal n
        if isinstance(obj, dict) and isinstance(obj.get(key), (int, float)):
            obj[key] = f(obj[key]); n += 1
    w = scene.get('walk')
    if w:
        for c in w.get('camera', []): m(c, 't')
        for c in w.get('cursor', []): m(c, 't')
        for s in w.get('shots', []): m(s, 'from')
        for tp in w.get('tips', []) or []: m(tp, 'from'); m(tp, 'to')
        if 'clicks' in w: w['clicks'] = [f(c) for c in w['clicks']]; n += len(w['clicks'])
        m(w, 'cursorOut')
        cams = w.get('camera', [])
        for c0, c1 in zip(cams, cams[1:]):
            room = c1['t'] - c0['t'] - 0.05
            if 'dur' in c1 and c1['dur'] > room:
                c1['dur'] = round(max(0.3, room), 3)
        cur = w.get('cursor', [])
        for c0, c1 in zip(cur, cur[1:]):
            room = c1['t'] - c0['t'] - 0.05
            if c1.get('d', 0.5) > room:
                c1['d'] = round(max(0.25, room), 3)
    for key in ('steps', 'pointers', 'pills', 'highlights', 'links', 'inserts'):
        for it in scene.get(key, []) or []:
            m(it, 'from'); m(it, 'to'); m(it, 'until')
            if isinstance(it.get('sel'), list):
                it['sel'] = [[f(a), f(b)] for a, b in it['sel']]; n += 2 * len(it['sel'])
    node = scene.get('node')
    if isinstance(node, dict) and isinstance(node.get('sel'), list):
        node['sel'] = [[f(a), f(b)] for a, b in node['sel']]
    return n

def main():
    old = {s['id']: s for s in json.load(open(sys.argv[1]))['scenes']}
    new = {s['id']: s for s in json.load(open(sys.argv[2]))['scenes']}
    edl = json.load(open(sys.argv[3]))
    for sc in edl['scenes']:
        o, nw = old.get(sc['id']), new.get(sc['id'])
        if not (o and nw and o.get('sourceSpans') and nw.get('sourceSpans')):
            continue
        if o['sourceSpans'] == nw['sourceSpans'] and (o.get('padBefore') or 0) == (nw.get('padBefore') or 0):
            continue
        k = retime(sc, mapper(o, nw))
        print(f"  {sc['id']:9s} {o['duration']:6.2f}s -> {nw['duration']:6.2f}s, {k} times moved")
    json.dump(edl, open(sys.argv[3], 'w'), indent=1)

if __name__ == '__main__':
    main()
