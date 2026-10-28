#!/usr/bin/env python3
"""List every "um"/"uh" and stammer left in a voice stem or a finished film, with the times to listen at.

    python3 tools/find_ums.py public/voice/<slug>.wav            # or a finished .mp4
    python3 tools/find_ums.py <file> --window 0-12               # only a stretch (seconds), e.g. the hook

Why: the default transcribers drop disfluencies, so a transcript that reads clean can still carry "scene by scene? [um]"
at a join. This forces mlx-whisper (even on a Mac that has the Apple transcriber) with a prompt that makes it write them out, then flags
  um / uh / er / ah / hmm / mm tokens, and
  a word or a 2-3 word phrase said twice in a row ("It's not, it's not") - a restart, cut to one.
Whisper also hallucinates an "Um," over digital silence just before a first word: a flag whose stamped stretch is
silent (under -70 dBFS) is marked "(over silence, ignore)". Every other flag is a cut to make: move the span end to the
dip before the filler, or splice the clean word (see story-and-cutting.md, "Ums, uhs and restarts").
"""
import array, json, math, os, re, subprocess, sys, tempfile, wave
DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DIR)
from ff import FF
FILLER = re.compile(r'^(u+m+|u+h+|e+r+m*|a+h+|h+m+|m+|mhm)$')
import brand
PROMPT = ('Um, uh, so, like, you know, uh, um, er. ' + ', '.join(brand.glossary()) + '.').strip()

def main():
    if len(sys.argv) < 2: print(__doc__); sys.exit(1)
    src = sys.argv[1]; lo, hi = 0.0, None
    if '--window' in sys.argv:
        a, b = sys.argv[sys.argv.index('--window') + 1].split('-'); lo, hi = float(a), float(b)
    tmp = tempfile.mkdtemp(); wav, out = os.path.join(tmp, 'a.wav'), os.path.join(tmp, 'a.json')
    cmd = [FF, '-hide_banner', '-loglevel', 'error', '-y', '-i', src, '-vn', '-ac', '1', '-ar', '16000']
    if hi: cmd += ['-ss', str(lo), '-to', str(hi)]
    subprocess.run(cmd + [wav], check=True)
    env = dict(os.environ, FORCE_WHISPER='1', WHISPER_PROMPT=PROMPT)
    subprocess.run([os.path.join(DIR, 'transcribe'), wav, out], env=env, check=True, capture_output=True)
    words = [w for seg in json.load(open(out)) for w in seg['words']]
    norm = lambda s: re.sub(r"[^a-z']", '', s.lower())
    toks = [(norm(w['t']), w['s'] + lo, w['e'] + lo) for w in words]
    hits = [(s, f'"{t}" (filler)') for t, s, e in toks if FILLER.match(t)]
    for n in (3, 2, 1):                       # a phrase repeated straight away
        for i in range(len(toks) - 2 * n + 1):
            a = [t for t, _, _ in toks[i:i + n]]; b = [t for t, _, _ in toks[i + n:i + 2 * n]]
            if a == b and all(len(t) > 1 for t in a) and not (n == 1 and a[0] in ('that', 'had', 'very', 'so')):
                hits.append((toks[i][1], f'"{" ".join(a)}" said twice (restart)'))
    w = wave.open(wav); sr = w.getframerate(); x = array.array('h', w.readframes(w.getnframes())); w.close()
    def loud(t0, t1):   # loudest 20 ms window between two times (file time, not the --window offset)
        a, b = int(max(0, t0 - lo) * sr), int(max(0, t1 - lo) * sr); step = int(0.02 * sr); best = -120.0
        for i in range(a, max(a + 1, b), step):
            seg = x[i:i + step]
            if seg: best = max(best, 10 * math.log10(sum(v * v for v in seg) / len(seg) / 32768 ** 2 + 1e-12))
        return best
    span = {round(s_, 3): e for _, s_, e in toks}
    hits = [(s_, what + (' (over silence, ignore)' if loud(s_, span.get(round(s_, 3), s_ + 0.3) - 0.08) < -70 else '')) for s_, what in hits]
    hits = sorted(set(hits))
    print(f'{len(hits)} filler/restart flag(s) in {os.path.basename(src)}' + (f' [{lo:g}-{hi:g} s]' if hi else ''))
    for s, what in hits: print(f'  {s:7.2f} s  {what}')
    if not hits: print('  none')

if __name__ == '__main__':
    main()
