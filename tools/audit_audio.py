#!/usr/bin/env python3
"""Audit a cut's voice stem before (and after) rendering. Prints film times (brief time + --lead) for everything it flags.

    python3 tools/audit_audio.py cuts/<slug>.edl.json [--lead 1.5]

Checks
  pauses      silences >= 0.45 s inside speech (the "too much breath" budget; the cold open and the ending hold are fine)
  slivers     bursts <= 120 ms right at a cut (the start of an um or a breath the join grabbed)
  clicks      sample spikes far above their surroundings (lip smacks the declicker missed, or a cut landing mid-sound)
  dropouts    sudden holes inside speech (a recording glitch, or a cut inside a word)
  alignment   every span sits where the brief says, matched against the analysis audio (catches build/concat bugs)
  loudness    the stem should be about -16 LUFS with true peak under -1.5 dBTP
Everything flagged needs a listen; not everything flagged is wrong (a 't' after a pause can look like a click).
"""
import array, json, math, os, struct, subprocess, sys, wave
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ff import FF
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load(path):
    w = wave.open(path); sr = w.getframerate(); ch = w.getnchannels(); n = w.getnframes()
    pcm = array.array('h', w.readframes(n)); return sr, (pcm[0::ch] if ch > 1 else pcm)

def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith('-') or not sys.argv[1].endswith('.json') or not os.path.exists(sys.argv[1]):
        raise SystemExit(__doc__)
    edl = json.load(open(sys.argv[1])); lead = float(sys.argv[sys.argv.index('--lead') + 1]) if '--lead' in sys.argv else 1.5
    slug, sid = edl['slug'], edl['sourceId']
    brief = json.load(open(os.path.join(ROOT, 'briefs', f'{slug}.json')))
    sr, x = load(os.path.join(ROOT, 'public', 'voice', f'{slug}.wav'))
    W = int(0.005 * sr); db = []
    for i in range(0, len(x) - W, W):
        seg = x[i:i + W]; db.append(10 * math.log10(sum(v * v for v in seg) / W / 32768 ** 2 + 1e-12))
    T = lambda k: k * 0.005 + lead
    # spans in brief time
    spans, at = [], 0.0
    for s in brief['scenes']:
        sp = s.get('sourceSpans')
        if not sp: at += s['duration']; continue
        t = at + float(s.get('padBefore') or 0)
        for (a, b) in sp:
            spans.append((s['id'], t, a, b)); t += b - a
        at += s['duration']
    speech_on = [d > -45 for d in db]
    first = next(i for i, v in enumerate(speech_on) if v); last = len(speech_on) - 1 - next(i for i, v in enumerate(reversed(speech_on)) if v)
    # pauses
    pauses, run = [], None
    for k in range(first, last):
        q = db[k] < -52
        if q and run is None: run = k
        if not q and run is not None:
            if (k - run) * 0.005 >= 0.45: pauses.append((T(run), (k - run) * 0.005))
            run = None
    print(f"pauses >= 0.45 s inside speech: {len(pauses)}" + ''.join(f"\n  {a:7.2f}  {d:.2f} s" for a, d in pauses))
    # slivers at cuts: a short burst (<= 120 ms) with real silence (>= 60 ms under -52 dB) on both sides, within 0.35 s of a cut
    sl = []
    for sid_, t, a, b in spans:
        k0 = int(t / 0.005)
        lo, hi = max(12, k0 - 70), min(len(db) - 12, k0 + 70)
        k = lo
        while k < hi:
            if db[k] > -48:
                j = k
                while j < len(db) and db[j] > -52: j += 1
                if (j - k) * 0.005 <= 0.12 and all(v < -52 for v in db[k - 12:k]) and all(v < -52 for v in db[j:j + 12]):
                    sl.append((T(k), (j - k) * 5, sid_))
                k = j + 1
            else:
                k += 1
    print(f"slivers near cuts: {len(sl)}" + ''.join(f"\n  {a:7.2f}  {ms} ms burst ({s}): an um or breath fragment? listen" for a, ms, s in sl))
    # clicks and dropouts
    clicks = []
    for k in range(len(db)):
        i = k * W; seg = x[i:i + W]
        if len(seg) < 3: continue
        m = max(abs(seg[j] - 2 * seg[j - 1] + seg[j - 2]) for j in range(2, len(seg))) / 32768
        if m > 0.02 and m > 12 * 10 ** (db[k] / 20): clicks.append((T(k), m, db[k]))
    print(f"click candidates: {len(clicks)}" + ''.join(f"\n  {a:7.2f}  spike {m:.3f} at {d:.0f} dB" for a, m, d in clicks[:30]))
    drops = []
    for k in range(2, len(db) - 14):
        if db[k] < -52 and db[k - 2] > -34:
            for L in range(1, 12):
                if db[k + L] > -34 and all(db[k + j] < -45 for j in range(L)):
                    drops.append((T(k), L * 5)); break
    print(f"dropouts inside speech: {len(drops)}" + ''.join(f"\n  {a:7.2f}  {ms} ms (listen: a stop consonant can look like this)" for a, ms in drops))
    # alignment against the analysis audio
    ap = os.path.join(ROOT, 'source', sid, 'audio16k.wav')
    if os.path.exists(ap):
        asr, src = load(ap)
        def envl(xx, rate, t0, t1):
            out, Wn, i = [], int(0.01 * rate), int(t0 * rate)
            while i < int(t1 * rate):
                seg = xx[max(0, i):i + Wn]; out.append(math.log10(sum(v * v for v in seg) / max(1, len(seg)) + 1.0)); i += Wn
            return out
        def corr(p, q):
            n = min(len(p), len(q)); p, q = p[:n], q[:n]; mp, mq = sum(p) / n, sum(q) / n
            num = sum((u - mp) * (v - mq) for u, v in zip(p, q)); den = math.sqrt(sum((u - mp) ** 2 for u in p) * sum((v - mq) ** 2 for v in q)) + 1e-9
            return num / den
        bad = []
        for sid_, t, a, b in spans:
            if b - a < 1.0: continue
            ref = envl(src, asr, a + 0.05, b - 0.05); best = (-2, 0)
            for lag in range(-8, 9):
                c = corr(ref, envl(x, sr, t + 0.05 + lag * 0.01, t + (b - a) - 0.05 + lag * 0.01))
                if c > best[0]: best = (c, lag * 0.01)
            if abs(best[1]) > 0.02: bad.append((sid_, t + lead, best[1]))
        print(f"alignment: {len(spans) - len(bad)}/{len(spans)} spans exactly where the brief says" + ''.join(f"\n  {s} at {t:.2f}: off by {o * 1000:+.0f} ms" for s, t, o in bad))
    else:
        print('alignment: skipped (no analysis audio for this source here)')
    out = subprocess.run([FF, '-hide_banner', '-nostats', '-i', os.path.join(ROOT, 'public', 'voice', f'{slug}.wav'), '-af', 'loudnorm=print_format=json', '-f', 'null', '-'], capture_output=True, text=True).stderr
    m = json.loads(out[out.rindex('{'):out.rindex('}') + 1])
    print(f"loudness: {m['input_i']} LUFS, {m['input_tp']} dBTP (want about -16 and under -1.5)")

if __name__ == '__main__':
    main()
