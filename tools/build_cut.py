#!/usr/bin/env python3
"""Build one cut from an edit decision list (cuts/<name>.edl.json).

For every scene's source spans it:
  1. snaps each in/out point to the 30 fps frame grid, nudged to the quietest
     nearby moment so cuts land between words,
  2. renders public/media/<slug>/stringout.mp4 (the spans back to back, video only),
  3. renders public/voice/<slug>.wav (same spans, 25 ms fades at every join,
     mono voice, gentle compression, one fixed gain to -16 LUFS, true-peak limited),
  4. writes briefs/<slug>.json: the scene list with stringout offsets filled in,
     plus timed captions remapped from the on-device transcript.

Usage: python3 tools/build_cut.py cuts/<slug>.edl.json [--no-media]
(the EDL names its recording in "source" and its analysis folder in "sourceId"; see skill/references/story-and-cutting.md)

Caption spelling: likely mis-hearings of the glossary in public/brand/brand.json are fixed automatically (tools/brand.py),
then the EDL's own "captionFixes" ([[regex, replacement], ...]) are applied. A leading "Um," / "Uh," is dropped.
"""
import json, math, os, re, struct, subprocess, sys, wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ff import FF
import brand
FPS = 30

# ---------------------------------------------------------------- audio probe
# Every cut decision is measured on the recording's analysis audio, source/<sourceId>/audio16k.wav, written by
# tools/prepare_source.py together with source/<sourceId>/transcript.json.
SOURCE_ID = [None]
_wav = None
_SR = 16000

def use_source(source_id):
    global _wav, _SR
    SOURCE_ID[0] = source_id
    path = os.path.join(ROOT, 'source', source_id, 'audio16k.wav')
    if not os.path.exists(path):
        raise SystemExit(f'missing {path}: run  python3 tools/prepare_source.py <recording> {source_id}')
    _wav = wave.open(path, 'rb')
    _SR = _wav.getframerate()

def rms_at(t, win=0.02):
    """RMS (dBFS) of a short window centred on source time t."""
    n = int(win * _SR)
    pos = max(0, int(t * _SR) - n // 2)
    if pos >= _wav.getnframes():      # past the end of the recording: silence
        return -120.0
    _wav.setpos(pos)
    raw = _wav.readframes(n)
    if not raw:
        return -120.0
    vals = struct.unpack('<%dh' % (len(raw) // 2), raw)
    ms = sum(v * v for v in vals) / len(vals)
    return 10 * math.log10(ms / 32768.0 ** 2 + 1e-12)

def snap(t, search=0.12, prefer='none'):
    """Move t to the quietest frame boundary within +/-search seconds."""
    best, best_db = None, 1e9
    k0, k1 = math.floor((t - search) * FPS), math.ceil((t + search) * FPS)
    for k in range(k0, k1 + 1):
        c = k / FPS
        db = rms_at(c)
        # tiny bias toward the requested point so ties keep the editor's choice
        db += abs(c - t) * 4
        if db < best_db:
            best, best_db = c, db
    return round(best * FPS) / FPS

PAUSE_DB = -64     # below this is a pause. Soft consonants (s, f, th) and word tails reach -55..-62 dB,
                   # so -55 mistook them for silence and clipped them; room tone is ~-82 dBFS
PAUSE_MIN = 0.05   # a pause must last at least this long
LEAD, TAIL = 0.12, 0.15   # breathing room kept before speech starts / after it ends

def _runs(a, b, step=0.01):
    """Silence runs [(start, end)] between a and b."""
    runs, cur = [], None
    t = a
    while t <= b:
        quiet = rms_at(t, 0.02) < PAUSE_DB
        if quiet and cur is None:
            cur = t
        if not quiet and cur is not None:
            if t - cur >= PAUSE_MIN:
                runs.append((cur, t))
            cur = None
        t += step
    if cur is not None and b - cur >= PAUSE_MIN:
        runs.append((cur, b))
    return runs

def _frame_in(lo, hi, want):
    ks = [k for k in range(math.ceil(lo * FPS), math.floor(hi * FPS) + 1)]
    if not ks:
        return round(((lo + hi) / 2) * FPS) / FPS
    return min(ks, key=lambda k: abs(k / FPS - want)) / FPS

FLOOR_DB = -68   # a word's tail has fully decayed below this (room tone is about -82 dBFS)

def _settled(t, direction, limit=0.6, hold=4):
    """Walk from t until the signal has stayed below FLOOR_DB for `hold` 10 ms steps.
    Returns the first time of that settled stretch (walking forward) or its last time (walking back)."""
    run, u = 0, t
    for _ in range(int(limit / 0.01)):
        if rms_at(u, 0.02) < FLOOR_DB:
            run += 1
            if run >= hold:
                return u - 0.01 * (hold - 1) * direction
        else:
            run = 0
        u += 0.01 * direction
    return None

def refine_start(t, search=0.5):
    """Cut point inside the pause before speech that begins near t: ahead of any breath or rise
    before the onset, and about LEAD before the onset."""
    runs = [r for r in _runs(t - search, t + 0.12) if r[0] <= t + 0.06]
    if not runs:
        return None
    s0, s1 = runs[-1]
    want = s1 - LEAD
    settled = _settled(s1, -1, limit=min(0.6, s1 - s0 + 0.01))   # where the pre-onset rise begins, walking back
    if settled is not None:
        want = min(want, settled - 0.04)
    clean_from = _settled(s0, +1, limit=min(0.6, s1 - s0 + 0.01), hold=2)  # previous sound fully gone
    lo = max(s0 + 0.01, clean_from if clean_from is not None else s0 + 0.01)
    return _frame_in(lo, s1, max(lo, want))

def refine_end(t, search=0.5):
    """Cut point inside the pause after speech that ends near t: after the word's tail has fully
    decayed to room tone, then a little air."""
    runs = [r for r in _runs(t - 0.12, t + search) if r[1] >= t - 0.06]
    if not runs:
        return None
    e0, e1 = runs[0]
    want = e0 + TAIL
    settled = _settled(e0, +1, limit=min(0.6, e1 - e0 + 0.01))    # where the tail has died away
    if settled is not None:
        want = max(want, settled + 0.05)
    clean_until = _settled(e1, -1, limit=min(0.6, e1 - e0 + 0.01), hold=2)  # before the next sound rises
    hi = min(e1 - 0.01, clean_until if clean_until is not None else e1 - 0.01)
    return _frame_in(e0, hi, min(hi, want))

def end_hold(b, hold, limit=2.0, speech_db=-48, force=False):
    """Extend a final out point to give the last line `hold` seconds after the speech stops.
    Only real speech (above speech_db) stops the hold; faint clicks and breaths sit under the long fade."""
    off, _ = _walk_quiet(b, -1)
    if force:   # the audio is faded out anyway: hold the full time even if the speaker talks again (the payoff covers the rest)
        return math.floor((off + hold) * FPS) / FPS
    u = b
    for _ in range(int(limit / 0.01)):
        if rms_at(u, 0.02) >= speech_db:
            break
        u += 0.01
    return math.floor(min(u - 0.15, off + hold) * FPS) / FPS

GAP_TARGET = 0.30   # silence to leave at each join (end-of-phrase tail + next lead-in)

EXTEND_DB = -60   # when borrowing extra pause, faint clicks and breaths below this don't count as sound

def _walk_quiet(t, direction, limit=0.6, db=None, blips=0):
    """From t, step (direction -1 back / +1 forward) while it stays quiet. Returns (last quiet time, hit speech?).
    With blips=n, a tick shorter than n steps (a mouse click or lip smack) doesn't end the walk."""
    db = PAUSE_DB if db is None else db
    u, last = t, t
    steps = int(limit / 0.01)
    k = 0
    while k < steps:
        if rms_at(u, 0.02) >= db:
            ahead = [rms_at(u + 0.01 * direction * j, 0.02) < db for j in range(1, blips + 3)]
            if blips and any(ahead[:blips]) and all(ahead[blips - 1 + ahead[:blips].index(True):][:2] or [False]):
                u += 0.01 * direction; k += 1
                continue
            return last, True
        last = u
        u += 0.01 * direction
        k += 1
    return last, False

def balance_join(x, y):
    """x, y = [a, b, pin_in, pin_out] spans that meet at a cut. Give the join about GAP_TARGET of
    silence in total, borrowing it from whichever side has a real pause to spare."""
    off, _ = _walk_quiet(x[1], -1)          # where x's speech stops (last quiet point walking back)
    on, _ = _walk_quiet(y[0], +1)           # where y's speech starts
    tail, lead = max(0.0, x[1] - off), max(0.0, on - y[0])
    short = GAP_TARGET - (tail + lead)
    if short <= 0.02:
        return 0.0
    added = 0.0
    if not y[2]:
        qs, _ = _walk_quiet(y[0], -1, db=EXTEND_DB, blips=2)   # earliest contiguous quiet before y's start
        new_a = math.ceil(max(qs + 0.03, y[0] - short) * FPS) / FPS
        if new_a < y[0] - 1e-6:
            added += y[0] - new_a; short -= y[0] - new_a; y[0] = new_a
    if short > 0.02 and not x[3]:
        qe, _ = _walk_quiet(x[1], +1, db=EXTEND_DB, blips=2)   # latest contiguous quiet after x's end
        new_b = math.floor(min(qe - 0.03, x[1] + short) * FPS) / FPS
        if new_b > x[1] + 1e-6:
            added += new_b - x[1]; x[1] = new_b
    return added

# ---------------------------------------------------------------- captions
FILLERS = {'um', 'uh', 'um,', 'uh,', 'um.', 'uh.'}

def clean_text(text):
    """Generic fixes, then the glossary: a near-miss of a glossary term takes the glossary spelling."""
    text = re.sub(r"^\s*(um|uh)[,.]?\s+", '', text, flags=re.I)
    return brand.glossary_fix(text)

def load_words():
    segs = json.load(open(os.path.join(ROOT, 'source', SOURCE_ID[0], 'transcript.json')))
    return [w for s in segs for w in s['words']]

_EFF = {}
def eff(w):
    """Start/end of the audible part of a word. The on-device transcript folds
    pauses into long words (before or after the speech), so for anything longer
    than 0.45 s the loud region is measured from the audio itself."""
    s, e = w['s'], w['e']
    if e - s <= 0.45:
        return s, e
    key = (s, e)
    if key not in _EFF:
        loud = [k / 100 for k in range(int(s * 100), int(e * 100) + 1) if rms_at(k / 100, 0.02) > -50]
        _EFF[key] = (loud[0], loud[-1] + 0.02) if loud else (s, e)
    return _EFF[key]

def loud_time(a, b, step=0.01, thresh=-50):
    """Seconds of speech (RMS above thresh) between a and b."""
    n, t = 0, a
    while t < b:
        if rms_at(t + step / 2, 0.02) > thresh:
            n += 1
        t += step
    return n * step

def assign_words(words, spans):
    """Map word index -> span index. Each word goes to the span whose overlap with
    it holds the most speech; a word that only grazes a cut with a silent sliver
    (< 30 ms of speech and its midpoint outside) belongs to no span."""
    cand = {}
    for si, (a, b) in enumerate(spans):
        for wi, w in enumerate(words):
            if w['e'] <= a or w['s'] >= b:
                continue
            lo, hi = max(a, w['s']), min(b, w['e'])
            cand.setdefault(wi, []).append((loud_time(lo, hi), si, a, b))
    owner = {}
    for wi, opts in cand.items():
        lt, si, a, b = max(opts)
        w = words[wi]
        mid = (w['s'] + w['e']) / 2
        if lt >= 0.03 or a <= mid < b:
            owner[wi] = si
    return owner

def words_in(words, a, b):
    """Words whose audible midpoint falls inside [a, b)."""
    out = []
    for w in words:
        s, e = eff(w)
        if a <= s + min(0.2, (e - s) / 2) < b:
            out.append(w)
    return out

FUNCTION = {'a', 'an', 'the', 'to', 'of', 'and', 'or', 'in', 'on', 'is', 'like', 'that', 'with', 'for', 'your', 'my', 'this', 'i'}
def _glossary_words():
    return [g for g in brand.glossary()]

def _nobreak():
    """Word pairs that must not be split across caption lines: a few generic phrases, plus every pair inside a glossary term."""
    pairs = {('you', 'know'), ('trigger', 'word')}
    for term in _glossary_words():
        ws = [w.lower().strip(',.') for w in term.split()]
        pairs.update(zip(ws, ws[1:]))
    return pairs

def _units():
    """Glossary names that are followed by a version number ("Name 2"): never break between them."""
    names = sorted({re.escape(t.split()[0]) for t in _glossary_words()}, key=len, reverse=True)
    return re.compile(r'^(' + '|'.join(names + [r'V\d+', r'2\.5']) + r')$', re.I)

NOBREAK = _nobreak()
UNITS = _units()

def build_cues(timed, max_chars=32, max_dur=5.0, fix=lambda t: t):
    max_chars = CAPTION_CHARS[0] or max_chars
    """timed: [(text, start, end, scene)] -> caption cues of 1-2 balanced lines.
    Words are grouped into phrases (punctuation, pauses, scene cuts), phrases are
    packed into cues, and over-long phrases split at the least awkward word."""
    phrases, cur = [], []
    for i, (t, s, e, sc, brk) in enumerate(timed):
        if cur and (sc != cur[-1][3] or s - cur[-1][2] > 0.5 or brk):
            phrases.append(cur); cur = []
        cur.append((t, s, e, sc, brk))
        if re.search(r'[.?!,;:]$', t):
            phrases.append(cur); cur = []
    if cur:
        phrases.append(cur)
    limit = max_chars * 2
    def text(ws):
        return ' '.join(w[0] for w in ws)
    def split_phrase(ph):
        """Split a phrase that is too long for one cue into chunks."""
        if len(text(ph)) <= limit and ph[-1][2] - ph[0][1] <= max_dur + 0.4:
            return [ph]
        best, score = None, 1e9
        for k in range(2, len(ph) - 1):
            a, b = ph[:k], ph[k:]
            sc = 0.5 * abs(len(text(a)) - len(text(b)))
            if a[-1][0].lower().strip(',.') in FUNCTION: sc += 40
            if UNITS.match(b[0][0].strip(',.')) and k > 0: sc += 80
            first_b = b[0][0].lower()
            if first_b in ('because', 'and', 'but', 'so', 'while', 'which', 'then'): sc -= 30
            elif first_b in ('a', 'the', 'in', 'that', 'with', 'for', 'to'): sc -= 8
            if sc < score:
                best, score = k, sc
        if best is None:
            return [ph]
        return split_phrase(ph[:best]) + split_phrase(ph[best:])
    chunks = [c for ph in phrases for c in split_phrase(ph)]
    cues, cue = [], []
    def fits(ws):
        return len(text(ws)) <= limit and ws[-1][2] - ws[0][1] <= max_dur
    for ci, ch in enumerate(chunks):
        if cue:
            same_scene = cue[-1][3] == ch[0][3]
            sentence_end = re.search(r'[.?!]$', cue[-1][0])
            nxt = chunks[ci + 1] if ci + 1 < len(chunks) else None
            orphan_ahead = (nxt is not None and nxt[0][3] == ch[0][3] and len(text(nxt)) < 16
                            and fits(cue + ch) and not fits(cue + ch + nxt) and fits(ch + nxt))
            forced = ch[0][4]
            if not same_scene or forced or not fits(cue + ch) or (sentence_end and len(text(cue)) > 20) or orphan_ahead:
                cues.append(cue); cue = []
        cue += ch
    if cue:
        cues.append(cue)
    out = []
    for i, c in enumerate(cues):
        first = i == 0 or c[0][3] != cues[i - 1][0][3] or re.search(r'[.?!]$', cues[i - 1][-1][0])
        t = fix(text(c))
        if first and t[:1].islower():
            t = t[0].upper() + t[1:]
        out.append({'start': c[0][1], 'end': c[-1][2], 'text': t, '_raw': c})
    for i, c in enumerate(out):
        c['text'] = balance(c['text'], max_chars)
        c['words'] = cue_words(c['text'], c.pop('_raw'))
        nxt = out[i + 1]['start'] if i + 1 < len(out) else None
        c['end'] = max(c['end'], c['start'] + 0.9)
        if nxt is not None:
            c['end'] = min(c['end'] + 0.15, nxt - 0.03)
        c['start'] = round(c['start'], 3)
        c['end'] = round(c['end'], 3)
    return out

def cue_words(text, raw):
    """Displayed caption tokens -> [token, start, end, line], from the transcript words the cue was built from.
    Fixes rename, merge or drop words, so tokens are matched to raw words by similarity, and unmatched tokens get
    interpolated times. The transcriber stamps words inside a phrase a little late, so those starts move 0.15 s
    earlier (a highlight that lands early reads as in sync; one that lands late reads as lag)."""
    import difflib
    norm = lambda x: re.sub(r"[^a-z0-9]", '', x.lower())
    toks = [(tok, li) for li, line in enumerate(text.split('\n')) for tok in line.split(' ') if tok]
    rw = [(w[0], w[1], w[2]) for w in raw]
    sm = difflib.SequenceMatcher(a=[norm(w[0]) for w in rw], b=[norm(t) for t, _ in toks], autojunk=False)
    times = [None] * len(toks)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal' or (op == 'replace' and i2 - i1 == j2 - j1):
            for q in range(j2 - j1):
                times[j1 + q] = (rw[i1 + q][1], rw[i1 + q][2])
        elif op == 'replace':
            s0, e0, n = rw[i1][1], rw[i2 - 1][2], j2 - j1
            for q in range(n):
                times[j1 + q] = (s0 + (e0 - s0) * q / n, s0 + (e0 - s0) * (q + 1) / n)
    for j in range(len(toks)):
        if times[j] is None:
            prev = next((times[p] for p in range(j - 1, -1, -1) if times[p]), None)
            nxt = next((times[q] for q in range(j + 1, len(toks)) if times[q]), None)
            s0 = prev[1] if prev else (nxt[0] if nxt else rw[0][1])
            e0 = nxt[0] if nxt else s0 + 0.25
            times[j] = (s0, max(s0 + 0.05, e0))
    out, last = [], None
    for j, ((tok, li), (s0, e0)) in enumerate(zip(toks, times)):
        if j > 0:
            s0 = max(last + 0.08, s0 - 0.15)
        last = s0
        out.append([tok, round(s0, 3), round(max(e0, s0 + 0.05), 3), li])
    return out

def balance(text, max_chars):
    if '¦' in text:
        return '\n'.join(p.strip() for p in text.split('¦', 1))
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) <= max_chars:
        return text
    words = text.split(' ')
    best, best_score = text, 1e9
    for i in range(1, len(words)):
        a, b = ' '.join(words[:i]), ' '.join(words[i:])
        score = abs(len(a) - len(b)) + (0 if re.search(r'[,.?!]$', a) else 6)
        if words[i - 1].lower().strip(',.') in FUNCTION:
            score += 10
        if words[i].lower() in ('a', 'the', 'in', 'and', 'that', 'with', 'for', 'to', 'because', 'but', 'so'):
            score -= 5
        if UNITS.match(words[i - 1]) and re.match(r'^[0-9.]+[,.]?$', words[i]):
            score += 100
        if (words[i - 1].lower().strip(',.'), words[i].lower().strip(',.')) in NOBREAK:
            score += 40
        if max(len(a), len(b)) > max_chars + 4:
            score += 50
        if score < best_score:
            best, best_score = a + '\n' + b, score
    return best

# ---------------------------------------------------------------- media
def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-3000:])
        raise SystemExit(f'ffmpeg failed: {" ".join(cmd[:6])}…')
    return r

def merge_contiguous(spans):
    out = []
    for sp in spans:
        a, b = sp[0], sp[1]
        pb = sp[2] if len(sp) > 2 else 0.0
        if out and abs(out[-1][1] - a) < 1e-6 and pb == 0:
            out[-1] = (out[-1][0], b, out[-1][2])
        else:
            out.append((a, b, pb))
    return out

CLIP_TARGET, CLIP_SHARE, CLIP_MAX = -33.0, 0.7, 5.0   # speech level clips are pulled toward, how much, at most (dB)

def clip_gain(a, b):
    """Clip gain (dB) that evens out a span's speech level against the rest: 70% of the way to CLIP_TARGET dBFS,
    at most +/-5 dB, so loud and quiet stretches of the recording sit together without flattening the delivery.
    Measured on the analysis audio over 50 ms blocks above -45 dBFS; spans with under 0.3 s of speech get none."""
    blocks, t = [], a
    while t + 0.05 <= b:
        d = rms_at(t + 0.025, 0.05)
        if d > -45:
            blocks.append(10 ** (d / 10))
        t += 0.05
    if len(blocks) * 0.05 < 0.3:
        return 0.0
    level = 10 * math.log10(sum(blocks) / len(blocks))
    return round(max(-CLIP_MAX, min(CLIP_MAX, CLIP_SHARE * (CLIP_TARGET - level))), 2)

def _loudness(path):
    out = run([FF, '-hide_banner', '-nostats', '-i', path, '-af', 'loudnorm=print_format=json', '-f', 'null', '-']).stderr
    m = json.loads(out[out.rindex('{'):out.rindex('}') + 1])
    return float(m['input_i']), float(m['input_tp'])

def has_video(src):
    probe = subprocess.run([FF, '-hide_banner', '-i', src], capture_output=True, text=True).stderr
    return bool(re.search(r'Stream #\S+.*: Video:', probe)) and 'attached pic' not in probe

def render_media(src, spans, slug, clean=(), end_fades=None):
    end_fades = end_fades or {}
    fade_out = {}
    for (a, b), spec in end_fades.items():
        fade_out[round(b, 3)] = spec
    spans = merge_contiguous(spans)
    media_dir = os.path.join(ROOT, 'public', 'media', slug)
    voice_dir = os.path.join(ROOT, 'public', 'voice')
    os.makedirs(media_dir, exist_ok=True)
    os.makedirs(voice_dir, exist_ok=True)
    inputs, vparts, aparts, gains = [], [], [], []
    video = has_video(src)          # an audio-only recording gets the voice track and no stringout
    for i, (a, b, pb) in enumerate(spans):
        d = b - a
        inputs += ['-ss', f'{a:.6f}', '-t', f'{d:.6f}', '-i', src]
        # optional: erase overlay icons (EDL brief.face.clean boxes) so a face tile stays clean
        dl = ''.join(f',delogo=x={x}:y={y}:w={w}:h={h}' for x, y, w, h in clean)
        hold = f',tpad=start_mode=clone:start_duration={pb:.4f}' if pb else ''
        if video:
            vparts.append(f'[{i}:v]setpts=PTS-STARTPTS,fps={FPS}{dl}{hold}[v{i}]')
        fade = 0.025
        # if speech starts within a hair of the cut, shorten the fade-in so the first sound stays intact
        onset, _ = _walk_quiet(a, +1, limit=0.1)
        fin = max(0.005, min(fade, onset - a - 0.005))
        spec = fade_out.get(round(b, 3))
        if spec:   # ending: fade finishes early, afade holds silence to the end of the span
            fst, fout = spec[0] - a, spec[1]
        else:
            fst, fout = max(0, d - fade), fade
        gains.append(clip_gain(a, b))
        aparts.append(
            f'[{i}:a]aresample=48000,pan=mono|c0=0.5*c0+0.5*c1,volume={gains[-1]:.2f}dB,'
            f'atrim=0:{d:.6f},asetpts=PTS-STARTPTS,'
            f'afade=t=in:d={fin:.4f},afade=t=out:st={fst:.6f}:d={fout:.4f}:curve=qsin'
            + (f',adelay=delays={round(pb * 1000)}:all=1' if pb else '') + f'[a{i}]')
    n = len(spans)
    vcat = ''.join(f'[v{i}]' for i in range(n)) + f'concat=n={n}:v=1:a=0[vout]' if video else None
    acat = ''.join(f'[a{i}]' for i in range(n)) + f'concat=n={n}:v=0:a=1[araw]'   # raw voice, levelled per clip
    # pass 1: video + the raw voice (32-bit float, so nothing clips before the gain stages)
    tmp_wav = os.path.join(voice_dir, f'{slug}.raw.wav')
    comp_wav = os.path.join(voice_dir, f'{slug}.comp.wav')
    graph = ';'.join(vparts + aparts + ([vcat] if video else []) + [acat])
    vout = ['-map', '[vout]', '-c:v', 'libx264', '-preset', 'medium', '-crf', '14', '-g', '15',
            '-pix_fmt', 'yuv420p', '-an', os.path.join(media_dir, 'stringout.mp4')] if video else []
    run([FF, '-hide_banner', '-loglevel', 'error', '-y', *inputs, '-filter_complex', graph, *vout,
         '-map', '[araw]', '-c:a', 'pcm_f32le', '-ar', '48000', tmp_wav])
    if not video:
        print('  audio-only recording: no stringout.mp4 written (tools/make_clip_brief.py draws a background from the brand colours)')
    i0, tp0 = _loudness(tmp_wav)
    # pass 2: bring the voice to -20 LUFS, then one moderate RMS compressor (about 5-6 dB on loud syllables; heavier
    # settings pulled breaths and room tone up with the gain). acompressor's makeup is a linear factor: 1 = none
    # (the old makeup=6 was +15.6 dB).
    run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-i', tmp_wav, '-af',
         f'highpass=f=70,volume={-20 - i0:.2f}dB,'
         'acompressor=threshold=-18dB:ratio=2.5:attack=5:release=150:makeup=1:detection=rms',
         '-c:a', 'pcm_f32le', comp_wav])
    i1, tp1 = _loudness(comp_wav)
    # pass 3: ONE fixed gain to -16 LUFS, then a limiter run at 192 kHz for what is left above -1.5 dBTP.
    # Not loudnorm: its linear=true silently falls back to dynamic mode when the peaks don't fit, which pumps the
    # level and lifts room noise and breaths by up to ~35 dB in every pause (audible glitches).
    gain = -16.0 - i1
    out_wav = os.path.join(voice_dir, f'{slug}.wav')
    for _ in range(2):   # the limiter shaves a little loudness off; one correction lands it on -16
        run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-i', comp_wav, '-af',
             f"volume={gain:.2f}dB,aresample=192000,alimiter=limit={10 ** (-1.5 / 20):.4f}:attack=5:release=80:level=disabled:latency=1,aresample=48000",
             '-ac', '2', '-c:a', 'pcm_s16le', out_wav])
        i2, tp2 = _loudness(out_wav)
        if abs(i2 + 16.0) < 0.3:
            break
        gain += -16.0 - i2
    # lip smacks and tongue clicks come up with the gain: repair the isolated ones (tools/declick.py touches ~2 ms each)
    dc = run([sys.executable, os.path.join(ROOT, 'tools', 'declick.py'), out_wav, out_wav]).stdout.strip()
    for f in (tmp_wav, comp_wav):
        os.remove(f)
    print(f'  {dc}')
    print(f"  clip gains (dB): {' '.join(f'{g:+.1f}' for g in gains)}")
    print(f"  voice levels: raw {i0:.1f} LUFS / {tp0:.1f} dBTP -> compressed {i1:.1f} / {tp1:.1f} -> limiter input peak {tp1 + gain:+.1f} dBTP")
    return {'input_i': f'{i0:.2f}', 'output_i': f'{i2:.2f}', 'output_tp': f'{tp2:.2f}', 'gain': round(gain, 2)}

def panel_media(spec, scene, slug, pending):
    """What fills the scene's panel. The face tile always plays the stringout."""
    spec = dict(spec)
    media = {k: v for k, v in spec.items() if k not in ('live', 'still', 'broll')}
    size = spec.get('srcSize', [1280, 720])
    if 'src' in spec and 'srcSize' not in spec:
        out = subprocess.run(['sips', '-g', 'pixelWidth', '-g', 'pixelHeight', os.path.join(ROOT, 'public', spec['src'])],
                             capture_output=True, text=True).stdout
        size = [int(x) for x in re.findall(r'pixel(?:Width|Height): (\d+)', out)]
    crop = spec.get('crop', [0, 0, size[0], size[1]])
    media['crop'] = crop
    media['srcSize'] = size
    media['aspect'] = round(crop[2] / crop[3], 5)
    src = EDL_SOURCE[0]
    out_dir = os.path.join(ROOT, 'public', 'media', slug)
    if 'still' in spec:
        t = spec['still']
        name = f'still-{t:.2f}.png'
        media.update(src=f'media/{slug}/{name}', type='image')
        def job(t=t, name=name):
            run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-ss', f'{t:.3f}', '-i', src,
                 '-frames:v', '1', os.path.join(out_dir, name)])
        pending.append(job)
    elif 'broll' in spec:
        start, dur = spec['broll']
        dur = max(dur, scene['duration'] + 0.2)
        name = f'broll-{start:.2f}.mp4'
        media.update(src=f'media/{slug}/{name}', type='video', startSeconds=0)
        def job(start=start, dur=dur, name=name):
            run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-ss', f'{start:.3f}', '-t', f'{dur:.3f}',
                 '-i', src, '-an', '-c:v', 'libx264', '-crf', '14', '-g', '15', '-pix_fmt', 'yuv420p',
                 os.path.join(out_dir, name)])
        pending.append(job)
    elif 'src' not in spec:
        media.update(src=f'media/{slug}/stringout.mp4', type='video', startSeconds=scene['at'])
    return media

EDL_SOURCE = ['']
CAPTION_CHARS = [0]  # per-cut override (brief.captionChars); 16:9-only cuts can take longer lines

def verify(edl, scenes, slug):
    """Transcribe the finished voice stem and compare each scene with its script, word by word.
    Any missing word of 3+ letters is flagged (a one-word miss once hid a dropped "use")."""
    wav = os.path.join(ROOT, 'public', 'voice', f'{slug}.wav')
    out = os.path.join(ROOT, 'source', f'{slug}.check.json')
    if os.path.exists(out):
        os.remove(out)
    subprocess.run([os.path.join(ROOT, 'tools', 'transcribe'), wav, out], capture_output=True)
    if not os.path.exists(out):
        print('verification skipped: no transcriber is installed here (run  bash setup.sh ). Listen to the cut instead.')
        return
    heard = [w for seg in json.load(open(out)) for w in seg['words']]
    norm = lambda x: re.sub(r"[^a-z0-9' ]", ' ', clean_text(x).lower()).split()
    ok_miss = {'um', 'uh', 'and', 'the', 'a', 'to', 'of', 'it', 'is', 'so', 'you', 'know', 'like'}
    for term in brand.glossary():          # the checker may hear a glossary name differently from the script
        ok_miss.update(w for w in re.sub(r"[^a-z0-9' ]", ' ', term.lower()).split())
    print('verification (heard in the finished voice track vs. intended script):')
    for sc, spec in zip(scenes, edl['scenes']):
        if 'at' not in sc:
            continue
        a, b = sc['at'], sc['at'] + sc['duration']
        got_raw = ' '.join(w['t'].strip() for w in heard if a - 0.05 <= w['s'] + 0.05 < b)
        got = norm(got_raw)
        pool = list(got)
        missing = []
        for w in norm(spec.get('script', '')):
            if w in pool:
                pool.remove(w)
            elif len(w) >= 3 and w not in ok_miss:
                missing.append(w)
        flag = 'OK ' if not missing else 'CHECK'
        print(f"  [{flag}] {sc['id']}: {got_raw}")
        if missing:
            print(f"          not heard: {', '.join(missing)}")

# ---------------------------------------------------------------- main
def main():
    edl_path = sys.argv[1]
    no_media = '--no-media' in sys.argv
    edl = json.load(open(edl_path))
    slug = edl['slug']
    use_source(edl['sourceId'])
    EDL_SOURCE[0] = edl['source']
    CAPTION_CHARS[0] = edl.get('captionChars', 0)
    words = load_words()
    fixes = [(re.compile(p, re.I), r) for p, r in edl.get('captionFixes', [])]

    all_spans, scenes_out, timed, cut_report, pending, no_pause = [], [], [], [], [], []
    # pass 1: place every cut in a pause (or pin it)
    placed = []
    end_audio = {}
    for scene in edl['scenes']:
        if not scene.get('spans'):
            placed.append(None)
            continue
        lst = []
        for span in scene['spans']:
            a, b = span[0], span[1]
            mode = span[2] if len(span) > 2 else ''
            pin_in = mode in ('exact', 'exact-in')    # pinned where two scenes run straight through
            pin_out = mode in ('exact', 'exact-out')
            if pin_in:
                a2 = round(a * FPS) / FPS
            else:
                ra = refine_start(a)
                if ra is None: no_pause.append(f"{scene['id']} in @{a}")
                a2 = ra if ra is not None else snap(a)
            if pin_out:
                b2 = round(b * FPS) / FPS
            else:
                rb = refine_end(b)
                if rb is None: no_pause.append(f"{scene['id']} out @{b}")
                b2 = rb if rb is not None else snap(b)
            lst.append([a2, b2, pin_in, pin_out])
        if scene.get('endHold'):
            last = lst[-1]
            # audio: fade from where the tail has settled to just before the next click/breath (max 0.25 s)
            fade_st = last[1] - 0.02
            noise, _ = _walk_quiet(last[1], +1, limit=0.4, db=-62)
            fade_end = min(last[1] + 0.25, noise - 0.02)
            end_audio[id(last)] = (fade_st, max(0.08, fade_end - fade_st))
            # picture: keep the real footage running (silent) for the hold
            last[1] = max(last[1], end_hold(last[1], scene['endHold'], force=bool(scene.get('endHoldForce'))))
            last[3] = True   # nothing may trim it back
        placed.append(lst)
    # pass 2: even out the breath at every real join
    flat = [sp for lst in placed if lst for sp in lst]
    borrowed = 0.0
    for x, y in zip(flat, flat[1:]):
        if abs(x[1] - y[0]) > 1e-6:
            borrowed += balance_join(x, y)
    if borrowed:
        print(f"  joins: added {borrowed:.2f}s of natural pause across the cut points")
    # audio fades per span: short at every cut, long at the very end of the film's speech
    fades = {}
    for scene, lst in zip(edl['scenes'], placed):
        if lst and id(lst[-1]) in end_audio:
            fades[(lst[-1][0], lst[-1][1])] = end_audio[id(lst[-1])]   # (absolute fade start, duration)
    # pass 3: film timing
    at = 0.0
    gap_before = 0.0
    span_meta = []  # (span index -> (film offset of its first sample, scene index))
    for scene, lst in zip(edl['scenes'], placed):
        s = {k: v for k, v in scene.items() if k not in ('spans', 'snap')}
        if lst:
            spans = [(a, b) for a, b, _, _ in lst]
            s['at'] = round(at, 4)
            s['sourceSpans'] = [[round(a, 3), round(b, 3)] for a, b in spans]
            total = 0.0
            for j, (a, b) in enumerate(spans):
                pb = float(scene.get('padBefore', 0.0)) if j == 0 else 0.0   # held frame + silence
                span_meta.append((at + pb, len(scenes_out)))
                # scenes without speech before this one (an intro) exist in the film but not in the
                # stringout: hold the first frame silently for them so voice and webcam stay in sync
                lead = gap_before if j == 0 else 0.0
                all_spans.append((a, b, pb + lead))
                if j == 0:
                    gap_before = 0.0
                at += pb + (b - a)
                total += pb + (b - a)
            s['duration'] = round(total, 4)
            cut_report.append((scene['id'], spans))
            s['media'] = panel_media(scene.get('media') or {'live': True}, s, slug, pending)
        else:
            at += scene['duration']
            gap_before += scene['duration']
        scenes_out.append(s)

    owner = assign_words(words, [(x[0], x[1]) for x in all_spans])
    # an ending span keeps running silently after its audio fade: drop words that fall in that silence
    audible_end = {}
    for (a, b), (fst, fdur) in fades.items():
        for k, x in enumerate(all_spans):
            if abs(x[0] - a) < 1e-6 and abs(x[1] - b) < 1e-6:
                audible_end[k] = fst + fdur
    owner = {wi: si for wi, si in owner.items()
             if si not in audible_end or eff(words[wi])[0] < audible_end[si] - 0.05}
    norm_w = lambda x: re.sub(r"[^a-z0-9']", '', x.lower())
    for wi in sorted(owner, key=lambda i: (owner[i], words[i]['s'])):
        w = words[wi]
        t = w['t'].strip()
        if not t or t.lower() in FILLERS:
            continue
        si = owner[wi]
        a, b = all_spans[si][0], all_spans[si][1]
        off, sc = span_meta[si]
        w_s, w_e = eff(w)
        ws = off + min(b - a, max(0, w_s - a))
        we = off + min(b - a, max(0.05, w_e - a))
        if t.lower() in ('a,', 'an,', 'the,', 'and,', 'to,', 'of,'):
            t = t[:-1]  # the transcriber's comma after an article is never real
        timed.append([t, ws, max(we, ws + 0.05), sc, False])
    timed.sort(key=lambda x: x[1])
    for sc_i, spec in enumerate(edl['scenes']):
        for phrase in spec.get('breakBefore', []):
            target = [norm_w(x) for x in phrase.split()]
            idx = [i for i, w in enumerate(timed) if w[3] == sc_i]
            for k in range(len(idx) - len(target) + 1):
                if [norm_w(timed[idx[k + j]][0]) for j in range(len(target))] == target:
                    timed[idx[k]][4] = True
                    break
            else:
                print(f'  warning: breakBefore "{phrase}" not found in {spec["id"]}')
    timed = [tuple(w) for w in timed]

    # caption text: fix terms per word group, then per-cut overrides
    def fix(txt):
        txt = clean_text(txt)
        for rx, rep in fixes:
            txt = rx.sub(rep, txt)
        return txt
    # the transcriber often stamps a phrase's first word late: snap starts back to where the speech really begins
    def film_to_src(t):
        for k, (off, _sc) in enumerate(span_meta):
            a, b = all_spans[k][0], all_spans[k][1]
            if off - 1e-6 <= t < off + (b - a):
                return a + (t - off), off, a
        return None
    def true_onset(t, floor):
        m = film_to_src(t)
        if not m:
            return t
        src, off, a = m
        u, lo = src, max(a, src - 0.35)
        while u - 0.01 >= lo and rms_at(u - 0.01, 0.02) > -58:
            u -= 0.01
        return max(floor, off + (u - a))
    snapped, prev_end = [], 0.0
    for t, ws, we, sc, brk in timed:
        ns = true_onset(ws, prev_end + 0.01) if ws > prev_end + 0.05 else ws
        snapped.append((t, min(ns, ws), we, sc, brk))
        prev_end = we
    timed = snapped
    cues = build_cues(timed, fix=fix)

    brief = dict(edl['brief'])
    brief['scenes'] = scenes_out
    brief['voiceover'] = {'src': f'voice/{slug}.wav', 'voice': 'Speaker (source audio)'}
    brief['captions'] = cues
    # per-word film timings (authoring aid: node connections land on the word being said)
    brief['words'] = [[t, round(ws, 3), round(we, 3), edl['scenes'][sc]['id']] for t, ws, we, sc, _ in timed]
    if 'face' in brief:
        brief['face'] = dict(brief['face'], src=f'media/{slug}/stringout.mp4')
    total = sum(round(s['duration'] * FPS) for s in scenes_out) / FPS
    out = os.path.join(ROOT, 'briefs', f'{slug}.json')
    json.dump(brief, open(out, 'w'), indent=1)
    print(f'{slug}: {len(all_spans)} spans, {total:.2f}s, {len(cues)} caption cues -> {out}')
    # captions: rebuilt from the verified EDL scripts (one straight line by default; see tools/postbrief.py)
    if all(sc.get('script') for sc in edl['scenes'] if sc.get('kind') == 'clip'):
        subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'postbrief.py'), sys.argv[1]], check=False)
    for msg in no_pause:
        print(f"  NO PAUSE FOUND: {msg} (fell back to quietest frame; check by ear)")
    for sid, spans in cut_report:
        levels = [f"{rms_at(a):.0f}/{rms_at(b):.0f}" for a, b in spans]
        loud = [l for l in levels if any(float(x) > -48 for x in l.split('/'))]
        print(f"  {sid:10s} cut dB in/out: {' '.join(levels)}{'   <-- check' if loud else ''}")
    if not no_media:
        m = render_media(edl['source'], all_spans, slug, edl['brief'].get('face', {}).get('clean', ()), fades)
        print(f"voice: input {m['input_i']} LUFS, fixed gain {m['gain']:+.2f} dB -> {m['output_i']} LUFS, {m['output_tp']} dBTP; media/{slug}/stringout.mp4 {'written' if has_video(edl['source']) else 'skipped (audio-only)'}")
        for job in pending:
            job()
        verify(edl, scenes_out, slug)

if __name__ == '__main__':
    main()
