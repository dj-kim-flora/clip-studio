#!/usr/bin/env python3
"""Mine a long recording for standalone short clips. Pure heuristics: no network, no AI model.

    python3 tools/farm.py <source-id> [--min 20] [--max 60] [--top 12] [--topic "pricing, churn"] [--allow-adjacent]
    python3 tools/farm.py <source-id> --emit-edls --pick 1,3,5 --prefix podcast-ep12

Reads source/<id>/transcript.json (and source/<id>/audio16k.wav for loudness) made by tools/prepare_source.py.
Writes _work/farm/<id>/candidates.json and candidates.md (plain English, for you and for the agent).

How it picks: it slides a window over sentence boundaries (a sentence ends at . ? ! or a pause over 0.7 s), keeps windows
that start on a sentence start, end on a sentence end and last between --min and --max seconds, and scores each one for
  opening hook (question, number, "here's", "the truth", warning, bold claim), self-contained start (no "and"/"so"/"it" with
  nothing before it), question followed by an answer, numbers and concrete claims, energy (louder than the rest, emphasis
  peaks, exclamations, laughter), speaking pace, a clean short last line, and a --topic match,
minus filler words (um, uh, you know), long silences and dead air. Then it keeps the best non-overlapping ones, at least
20 s apart unless --allow-adjacent.
It does NOT understand meaning. Read candidates.md and choose; then --emit-edls writes cuts/<prefix>-NN.edl.json for the
chosen numbers (NN = candidate number), ready for tools/build_cut.py.
"""
import argparse, array, json, math, os, re, sys, wave
from itertools import accumulate

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TERMINAL = re.compile(r'[.?!]["\')\]]*$')
FRAME = 0.1            # seconds per energy frame
SPEECH_DB = -45.0      # frames above this count as speech
GAP_SENTENCE = 0.7     # a silence this long ends a sentence
GAP_BIG = 1.5          # a silence this long inside a clip is dead air

FILLER_WORDS = {'um', 'uh', 'er', 'erm', 'ah', 'hmm', 'uhm', 'umm', 'mm'}
CONNECT = {'so', 'and', 'but', 'because', 'which', 'then', 'also', 'or', 'however', 'anyway', 'well', 'yeah', 'right', 'okay', 'ok', 'cause', 'plus', 'while', 'although', 'though'}
PRONOUN = {'it', 'this', 'that', 'they', 'he', 'she', 'them', 'those', 'these', 'its', 'his', 'her', 'their'}
STRONG = {'never', 'always', 'worst', 'best', 'biggest', 'insane', 'crazy', 'wrong', 'mistake', 'mistakes', 'lie', 'lies', 'myth',
          'secret', 'surprising', 'shocking', 'nobody', 'nothing', 'everything', 'only', 'huge', 'killer', 'game-changer', 'actually', 'honestly'}
LAUGH = re.compile(r'\b(ha(ha)+|haha|hehe|lol|laugh(s|ing|ter)?|chuckl\w*)\b|\[laugh', re.I)
NUMBER_WORDS = {'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'hundred', 'thousand', 'million', 'billion', 'percent'}


def hms(t):
    t = max(0, int(round(t)))
    return f'{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}'


def norm(w):
    return re.sub(r"[^a-z0-9']", '', w.lower())


# ------------------------------------------------------------------ inputs
def load_words(sid):
    p = os.path.join(ROOT, 'source', sid, 'transcript.json')
    if not os.path.exists(p):
        raise SystemExit(f'No transcript yet for "{sid}". Run first:  python3 tools/prepare_source.py <recording> {sid}')
    words = [dict(w, t=w['t'].strip()) for s in json.load(open(p)) for w in s.get('words', []) if w['t'].strip()]
    if len(words) < 30:
        raise SystemExit('The transcript has fewer than 30 words, which is too little to find clips in.')
    return words


def energy_frames(sid):
    """dBFS per 100 ms frame of the analysis audio, or None when it is not there. Stride-sampled to stay fast."""
    p = os.path.join(ROOT, 'source', sid, 'audio16k.wav')
    if not os.path.exists(p):
        return None
    w = wave.open(p, 'rb')
    sr, n = w.getframerate(), w.getnframes()
    per = int(sr * FRAME)
    out = []
    block_frames = per * 600                                  # one minute at a time
    done = 0
    while done < n:
        raw = w.readframes(min(block_frames, n - done))
        done += block_frames
        pcm = array.array('h')
        pcm.frombytes(raw[:len(raw) // 2 * 2])
        for i in range(0, len(pcm) - per + 1, per):
            seg = pcm[i:i + per:4]
            ms = sum(v * v for v in seg) / max(1, len(seg))
            out.append(10 * math.log10(ms / 32768.0 ** 2 + 1e-12))
    w.close()
    return out


# ------------------------------------------------------------------ sentences
def split_sentences(words):
    punct = sum(1 for w in words if TERMINAL.search(w['t']))
    gap = GAP_SENTENCE if punct > len(words) / 40 else 0.4     # a transcript without punctuation breaks on shorter pauses
    sents, start = [], 0
    for i, w in enumerate(words):
        last = i == len(words) - 1
        brk = last or TERMINAL.search(w['t']) or words[i + 1]['s'] - w['e'] > gap
        if not brk and not punct and i - start >= 24:            # no punctuation at all: cap the run length
            brk = True
        if brk:
            sents.append({'a': start, 'b': i, 's': words[start]['s'], 'e': w['e']})
            start = i + 1
    for k, s in enumerate(sents):
        s['text'] = ' '.join(x['t'] for x in words[s['a']:s['b'] + 1])
        s['n'] = s['b'] - s['a'] + 1
        s['gap_after'] = (words[sents[k + 1]['a']]['s'] - s['e']) if k + 1 < len(sents) else 0.0
        s['gap_before'] = (s['s'] - words[sents[k - 1]['b']]['e']) if k else 9.0
        s['ends'] = bool(TERMINAL.search(words[s['b']]['t']))
    return sents


# ------------------------------------------------------------------ feature scoring
def hook_score(text, n_words):
    t = text.strip()
    low = t.lower()
    sc, why = 0.0, []
    def add(v, reason):
        nonlocal sc
        sc += v; why.append(reason)
    if '?' in t:
        add(0.55, 'opens with a question')
    if re.match(r'^\W*(\d|\$)', t) or re.match(r'^\W*(one|two|three|four|five|six|seven|eight|nine|ten)\b', low):
        add(0.35, 'opens with a number')
    if re.search(r"\b(here'?s|heres|here is|here are)\b", low):
        add(0.4, 'opens with "here\'s..."')
    if re.search(r'\bthe (truth|secret|real reason|biggest|worst|best|one thing|only thing|number one)\b', low):
        add(0.45, 'promises "the truth / the secret / the one thing"')
    if re.search(r"\b(nobody|no one|most people|everyone|everybody)\b", low):
        add(0.3, 'makes a bold claim about people')
    if re.match(r"^\W*(no|not|never|don't|do not|stop|you (don't|can't|shouldn't|never|need to stop)|why you (shouldn't|can't))\b", low):
        add(0.35, 'opens with a warning or negation')
    if re.search(r"\b(how to|here'?s how|let me show|the way to|the trick|step one|first thing)\b", low):
        add(0.3, 'promises a how-to')
    if re.search(r'\b(imagine|what if|picture this|guess what)\b', low):
        add(0.3, 'invites the viewer in ("imagine", "what if")')
    strong = sorted({w for w in re.findall(r"[a-z'-]+", low) if w in STRONG})
    if strong:
        add(min(0.4, 0.2 * len(strong)), 'uses strong words (' + ', '.join(strong[:3]) + ')')
    if re.search(r'\b(i (was|used to|made|lost|spent|built|learned|failed)|we (were|made|lost|built))\b', low):
        add(0.2, 'starts a personal story')
    if n_words > 30:
        sc -= 0.3
        why.append('first sentence is very long')
    return max(0.0, min(1.0, sc)), why


def self_contained(sents, i, words):
    s = sents[i]
    toks = [norm(x['t']) for x in words[s['a']:s['b'] + 1]]
    sc, why, warn = 1.0, [], []
    first = toks[0] if toks else ''
    if first in CONNECT:
        sc -= 0.5; warn.append(f'starts with "{first}", so it may need the sentence before it')
    elif first in PRONOUN:
        sc -= 0.35; warn.append(f'starts with "{first}", which may point back to something earlier')
    later = sum(1 for t in toks[1:8] if t in PRONOUN)
    if later:
        sc -= min(0.3, 0.1 * later)
    if i > 0 and not sents[i - 1]['ends'] and s['gap_before'] < 0.2:
        sc -= 0.3; warn.append('starts in the middle of a sentence')
    sc = max(0.0, sc)
    if sc >= 0.9:
        why.append('starts cleanly and makes sense without earlier context')
    return sc, why, warn


def ending_score(sents, j, words):
    s = sents[j]
    if not s['ends']:
        return 0.0, 'does not end on a finished sentence'
    sc = 0.4
    if s['n'] <= 10:
        sc += 0.4
    if '!' in words[s['b']]['t'] or s['n'] <= 6:
        sc += 0.2
    last = norm(words[s['b']]['t'])
    if last in CONNECT:
        sc = 0.0
    return min(1.0, sc), None


def build(words, sents, frames, args):
    n = len(words)
    toks = [norm(w['t']) for w in words]
    pre = lambda flags: [0] + list(accumulate(flags))
    # per-word prefix sums
    fill_p = pre([1 if toks[i] in FILLER_WORDS else 0 for i in range(n)])
    # "you know" and a hedging "like" count as half a filler
    yk = [0.0] * n
    for i in range(n):
        if toks[i] == 'you' and i + 1 < n and toks[i + 1] == 'know':
            yk[i] = 1.0
        elif toks[i] == 'like' and i > 0 and words[i - 1]['t'].endswith(','):
            yk[i] = 0.5
    yk_p = [0.0] + list(accumulate(yk))
    num_p = pre([1 if re.search(r'\d', words[i]['t']) or toks[i] in NUMBER_WORDS or '%' in words[i]['t'] else 0 for i in range(n)])
    excl_p = pre([1 if '!' in words[i]['t'] else 0 for i in range(n)])
    laugh_p = pre([1 if LAUGH.search(words[i]['t']) else 0 for i in range(n)])
    # per-sentence prefix sums
    m = len(sents)
    q_p = pre([1 if ('?' in s['text'] and s['text'].strip().endswith('?')) else 0 for s in sents])
    qa_flags = [1 if (k + 1 < m and '?' in sents[k]['text'] and sents[k + 1]['n'] >= 6) else 0 for k in range(m)]
    qa_p = pre(qa_flags)
    big_p = pre([1 if s['gap_after'] > GAP_BIG else 0 for s in sents])
    # energy prefix sums
    have_e = bool(frames)
    if have_e:
        speech = [d for d in frames if d > SPEECH_DB]
        gm = sum(speech) / max(1, len(speech))
        gs = math.sqrt(sum((d - gm) ** 2 for d in speech) / max(1, len(speech))) or 1.0
        srt = sorted(speech)
        p85 = srt[int(len(srt) * 0.85)] if srt else 0
        sp_p = pre([1 if d > SPEECH_DB else 0 for d in frames])
        db_p = [0.0] + list(accumulate(d if d > SPEECH_DB else 0.0 for d in frames))
        pk_p = pre([1 if d > p85 else 0 for d in frames])
    topic = [norm(t) for t in re.split(r'[,;/]|\s{1,}', args.topic or '') if len(norm(t)) >= 3] if args.topic else []
    hook = [hook_score(s['text'], s['n']) for s in sents]
    selfc = [self_contained(sents, i, words) for i in range(m)]

    out = []
    for i in range(m):
        t0 = sents[i]['s']
        for j in range(i, m):
            t1 = sents[j]['e']
            L = t1 - t0
            if L > args.max:
                break
            if L < args.min:
                continue
            a, b = sents[i]['a'], sents[j]['b'] + 1
            nw = b - a
            why, warn, pts = [], [], {}
            # opening hook (25)
            hs, hw = hook[i]
            pts['hook'] = 25 * hs
            if hs >= 0.3:
                why.append('Strong opening line: ' + ', '.join(hw))
            # self-contained (20)
            ss, sw, swarn = selfc[i]
            pts['selfContained'] = 20 * ss
            why += sw; warn += swarn
            # question -> answer (10)
            has_qa = qa_p[j] - qa_p[i] > 0
            has_q = q_p[j + 1] - q_p[i] > 0
            pts['questionAnswer'] = 10 if has_qa else (3 if has_q else 0)
            if has_qa:
                why.append('Asks a question and answers it')
            # numbers and claims (10)
            nums = num_p[b] - num_p[a]
            pts['claims'] = 10 * min(1.0, nums / 3.0)
            if nums >= 2:
                why.append(f'Concrete numbers or figures ({nums})')
            # energy / emotion (15)
            excl, laugh = excl_p[b] - excl_p[a], laugh_p[b] - laugh_p[a]
            if have_e:
                f0, f1 = int(t0 / FRAME), min(len(frames), int(t1 / FRAME))
                sp = sp_p[f1] - sp_p[f0]
                mean_db = (db_p[f1] - db_p[f0]) / sp if sp else gm
                en = max(0.0, min(1.0, 0.5 + 0.35 * (mean_db - gm) / gs))
                pk = (pk_p[f1] - pk_p[f0]) / sp if sp else 0.0
                emph = min(1.0, pk / 0.3)
                speech_frac = sp / max(1, f1 - f0)
            else:
                en, emph, speech_frac = 0.5, 0.0, 0.8
            emo = 0.45 * en + 0.25 * emph + 0.15 * min(1.0, excl / 2.0) + 0.15 * min(1.0, laugh)
            pts['energy'] = 15 * emo
            if have_e and en >= 0.65:
                why.append('Delivered with more energy than the rest of the recording')
            elif have_e and emph >= 0.7:
                why.append('Has strong emphasis peaks')
            if laugh:
                why.append('Laughter in the clip')
            elif excl >= 2:
                why.append('Exclamations (emotion)')
            # pace (10)
            wps = nw / max(1.0, L * (speech_frac if have_e else 1.0))
            pts['pace'] = 10 * (1 - min(1.0, abs(wps - 2.8) / 1.4))
            if wps >= 3.1:
                why.append('Brisk, lively pace')
            elif wps < 1.9:
                warn.append('slow, drawn-out pace')
            # length fit (5)
            target = min(args.max, max(args.min, 35.0))
            pts['length'] = 5 * max(0.0, 1 - abs(L - target) / max(target, 1))
            # ending (5)
            es, ew = ending_score(sents, j, words)
            pts['ending'] = 5 * es
            if es >= 0.8:
                why.append('Ends on a short, clean line')
            if ew:
                warn.append(ew)
            # penalties
            fillers = (fill_p[b] - fill_p[a]) + (yk_p[b] - yk_p[a])
            pen_fill = min(20.0, fillers / max(1, nw) * 100 * 2.5)
            if fillers >= 3:
                warn.append(f'{fillers:g} filler words (um, uh, you know)')
            big = big_p[j] - big_p[i]
            pen_gap = 8.0 * big
            if big:
                warn.append(f'{big} long silence(s) inside')
            pen_dead = max(0.0, (0.7 - speech_frac) * 30) if have_e else 0.0
            if pen_dead > 3:
                warn.append('a lot of silence or background noise')
            # topic boost (up to 15)
            boost = 0.0
            if topic:
                present = [t for t in topic if any(x.startswith(t[:max(3, len(t) - 2)]) for x in toks[a:b])]
                boost = 15.0 * len(present) / len(topic)
                if present:
                    why.append('Mentions your topic: ' + ', '.join(present))
            pts['topic'] = boost
            score = sum(pts.values()) - pen_fill - pen_gap - pen_dead
            out.append({
                'i': i, 'j': j, 'start': round(t0, 3), 'end': round(t1, 3), 'length': round(L, 1),
                'score': round(max(0.0, min(100.0, score)), 1), 'reasons': why, 'warnings': warn,
                'features': {k: round(v, 1) for k, v in pts.items()},
            })
    return out


def select(cands, top, allow_adjacent):
    chosen = []
    gap = 0.0 if allow_adjacent else 20.0
    for c in sorted(cands, key=lambda c: (-c['score'], c['start'])):
        if any(c['start'] < o['end'] + gap and o['start'] < c['end'] + gap for o in chosen):
            continue
        chosen.append(c)
        if len(chosen) >= top:
            break
    return chosen


# ------------------------------------------------------------------ outputs
def clean_script(text):
    return re.sub(r'\s+', ' ', re.sub(r"\b(um+|uh+|uhm+|erm?)\b[,.]?\s*", '', text, flags=re.I)).strip()


def title_from(text):
    """A working title from the first sentence (the agent or user should still rename it)."""
    first = re.split(r'(?<=[.?!])\s', clean_script(text))[0]
    first = re.sub(r'[.?!,;:]+$', '', first)
    words = first.split()
    if len(first) > 60:
        words = words[:9]
        cut = next((k for k in range(len(words) - 1, 3, -1) if words[k - 1].endswith(',')), None)
        if cut:
            words = words[:cut]
        while len(words) > 3 and re.sub(r'\W', '', words[-1]).lower() in ('a', 'an', 'the', 'we', 'i', 'to', 'of', 'and', 'but', 'so', 'that', 'in', 'on', 'for', 'with', 'is', 'it'):
            words.pop()
        words = [w.rstrip(',') for w in words]
    t = ' '.join(words)
    return (t[:1].upper() + t[1:]) if t else 'Clip'


def write_outputs(sid, picks, args, have_energy, total):
    out_dir = os.path.join(ROOT, '_work', 'farm', sid)
    os.makedirs(out_dir, exist_ok=True)
    for k, c in enumerate(picks, 1):
        c['id'] = k
    js = {'sourceId': sid, 'params': {'min': args.min, 'max': args.max, 'top': args.top, 'topic': args.topic or '',
                                       'allowAdjacent': args.allow_adjacent, 'audioEnergy': have_energy},
          'candidates': [{k: v for k, v in c.items() if k not in ('i', 'j')} for c in picks]}
    json.dump(js, open(os.path.join(out_dir, 'candidates.json'), 'w'), indent=1)
    L = [f'# Clip candidates for "{sid}"', '',
         f'Found {len(picks)} promising clips of {args.min:g} to {args.max:g} seconds, best first. '
         f'The score (0 to 100) is a rough guide from patterns like a strong opening line, a clean start, '
         f'energy and few ums. It does not understand meaning, so **read the text and choose**.', '']
    if not have_energy:
        L += ['_Note: no analysis audio was found, so loudness and energy were not used._', '']
    if args.topic:
        L += [f'Topic boost on: {args.topic}', '']
    L += ['| # | Starts at | Length | Score | Opening line |', '|---|---|---|---|---|']
    for c in picks:
        L.append(f"| {c['id']} | {hms(c['start'])} | {c['length']:.0f} s | {c['score']:.0f} | {c['firstLine'][:70].replace('|', '/')} |")
    L.append('')
    for c in picks:
        L += [f"## {c['id']}. {hms(c['start'])} to {hms(c['end'])} ({c['length']:.0f} s), score {c['score']:.0f}/100", '']
        if c['reasons']:
            L += ['Why it scored well:'] + [f'- {r[:1].upper() + r[1:]}' for r in c['reasons']] + ['']
        if c['warnings']:
            L += ['Watch out for:'] + [f'- {w[:1].upper() + w[1:]}' for w in c['warnings']] + ['']
        L += [f"- First line: \"{c['firstLine']}\"", f"- Last line: \"{c['lastLine']}\"", '', 'Full text:', '', f"> {c['text']}", '']
    L += ['## Next step', '',
          'Tell the agent which numbers you want (for example "1, 3 and 5"). It will run:', '',
          f'    python3 tools/farm.py {sid} --emit-edls --pick 1,3,5 --prefix {sid}', '',
          f'which writes cuts/{sid}-01.edl.json and so on, one per chosen clip, then builds and exports them.', '']
    open(os.path.join(out_dir, 'candidates.md'), 'w').write('\n'.join(L))
    return out_dir


def parse_picks(spec):
    ids = []
    for part in spec.split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            a, b = part.split('-', 1)
            ids += list(range(int(a), int(b) + 1))
        else:
            ids.append(int(part))
    return ids


def emit_edls(sid, args):
    cj = os.path.join(ROOT, '_work', 'farm', sid, 'candidates.json')
    if not os.path.exists(cj):
        raise SystemExit(f'No candidates yet for "{sid}". Run first:  python3 tools/farm.py {sid}')
    cands = {c['id']: c for c in json.load(open(cj))['candidates']}
    picks = parse_picks(args.pick or '')
    if not picks:
        raise SystemExit('Say which clips to write, for example  --pick 1,3,5')
    missing = [p for p in picks if p not in cands]
    if missing:
        raise SystemExit('There is no candidate number ' + ', '.join(map(str, missing)) + f'. Valid numbers: 1 to {len(cands)}.')
    info = {}
    try:
        info = json.load(open(os.path.join(ROOT, 'source', sid, 'info.json')))
    except (OSError, ValueError):
        pass
    src = info.get('source') or ''
    if not src or not os.path.exists(src):
        d = os.path.join(ROOT, 'source', sid)
        orig = [f for f in (os.listdir(d) if os.path.isdir(d) else []) if f.startswith('original.')]
        src = os.path.join(d, orig[0]) if orig else src
    if not src:
        raise SystemExit(f'I cannot tell which recording "{sid}" came from. Put its path in the EDL "source" field.')
    words = load_words(sid)
    prefix = args.prefix or sid
    os.makedirs(os.path.join(ROOT, 'cuts'), exist_ok=True)
    for pid in picks:
        c = cands[pid]
        slug = f'{prefix}-{pid:02d}'
        a, b = c['start'], c['end']
        inside = [w for w in words if w['s'] >= a - 0.01 and w['e'] <= b + 0.01]
        if inside:                                                # snap to word boundaries
            a, b = inside[0]['s'], inside[-1]['e']
        script = clean_script(' '.join(w['t'] for w in inside) if inside else c['text'])
        edl = {
            'slug': slug, 'source': os.path.abspath(src), 'sourceId': sid, 'captionChars': 32, 'captionFixes': [],
            'brief': {'title': title_from(script), 'slug': slug, 'demo': False, 'fps': 30, 'modelLabel': '', 'cursorName': '',
                      'sound': False, 'outro': 'none', 'logos': []},
            'scenes': [{'id': 'clip', 'kind': 'clip', 'spans': [[round(a, 3), round(b, 3)]], 'script': script,
                        'evidence': f"farm candidate {pid}, source {hms(a)} to {hms(b)}; {'; '.join(c['reasons'][:2]) or 'picked by hand'}"}],
            'captionLines': 1,
        }
        p = os.path.join(ROOT, 'cuts', f'{slug}.edl.json')
        json.dump(edl, open(p, 'w'), indent=1)
        print(f'cuts/{slug}.edl.json  {hms(a)} to {hms(b)} ({b - a:.0f} s): "{edl["brief"]["title"]}"')
    print('Next: python3 tools/export_clips.py ' + ' '.join(f'{prefix}-{p:02d}' for p in picks) + ' --ratio 9:16')


def main():
    ap = argparse.ArgumentParser(description='Find standalone short clips in a recording (heuristics only).')
    ap.add_argument('source_id')
    ap.add_argument('--min', type=float, default=20.0, help='shortest clip, seconds')
    ap.add_argument('--max', type=float, default=60.0, help='longest clip, seconds')
    ap.add_argument('--top', type=int, default=12, help='how many candidates to keep')
    ap.add_argument('--topic', default='', help='words to favour, comma separated')
    ap.add_argument('--allow-adjacent', action='store_true', help='allow picks closer than 20 s to each other')
    ap.add_argument('--emit-edls', action='store_true', help='write cuts/<prefix>-NN.edl.json for --pick')
    ap.add_argument('--pick', default='', help='candidate numbers, e.g. 1,3,5 or 2-4')
    ap.add_argument('--prefix', default='', help='name for the written EDLs (default: the source id)')
    args = ap.parse_args()
    sid = args.source_id
    if args.min >= args.max or args.min < 5:
        raise SystemExit('--min must be at least 5 and smaller than --max.')
    if args.emit_edls:
        return emit_edls(sid, args)
    words = load_words(sid)
    sents = split_sentences(words)
    frames = energy_frames(sid)
    total = words[-1]['e']
    cands = build(words, sents, frames, args)
    if not cands:
        raise SystemExit(f'No stretch of {args.min:g} to {args.max:g} seconds starts and ends on a sentence boundary. '
                         'Try a wider range, for example --min 15 --max 90.')
    picks = select(cands, args.top, args.allow_adjacent)
    for c in picks:
        a, b = sents[c['i']]['a'], sents[c['j']]['b']
        c['firstLine'] = sents[c['i']]['text']
        c['lastLine'] = sents[c['j']]['text']
        c['text'] = ' '.join(w['t'] for w in words[a:b + 1])
    out_dir = write_outputs(sid, picks, args, bool(frames), total)
    print(f'{len(sents)} sentences, {len(cands)} possible windows, {len(picks)} kept.')
    for c in picks[:5]:
        print(f"  {c['id']:2d}. {hms(c['start'])}  {c['length']:3.0f} s  score {c['score']:3.0f}  {c['firstLine'][:60]}")
    print(f'Read {os.path.relpath(out_dir, ROOT)}/candidates.md and pick the ones you like.')


if __name__ == '__main__':
    main()
