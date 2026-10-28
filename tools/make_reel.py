#!/usr/bin/env python3
"""Turn a page/canvas recording (tools/record_page.mjs) into a quick behind-the-scenes reel.

    python3 tools/make_reel.py <capture-slug> [--out name] [--title "How I made it"] [--seconds 30] [--formats reels,widescreen]
        [--export] [--hook "text"] [--music file] [--outro] [--caption-style pill] [--layout fill|blurfill|split] [--min-beat 1.6]

Reads source/<capture-slug>/capture.mp4 and capture.json (the labelled beats). Each beat is sped up just enough that the
whole reel fits --seconds (a beat is never shorter than --min-beat seconds; a beat's own "speed" in the tour wins), cut
together, and the beat labels become the on-screen step captions. Then, per format, it writes the same files a cut does:
    public/media/<slug>/stringout.mp4, public/voice/<slug>.wav (silence), briefs/<slug>.json, cuts/<slug>.edl.json (marker)
and, with --export, runs tools/export_clips.py for each so finished files land in deliverables/.
Slugs: <out> for one format, <out>-<format> for several (each gets its own title so the versions do not replace each other).
"""
import argparse, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_clip_brief, reframe
from ff import FF
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 30


def plan_speeds(beats, target, min_beat):
    """One shared speed-up so the reel fits `target`, never making a beat shorter than min_beat. Beats with their own speed keep it."""
    fixed = [b for b in beats if b.get('speed')]
    free = [b for b in beats if not b.get('speed')]
    spent = sum((b['t1'] - b['t0']) / b['speed'] for b in fixed)
    def total(s):
        return spent + sum(max(min(min_beat, b['t1'] - b['t0']), (b['t1'] - b['t0']) / s) for b in free)
    if total(1.0) <= target:
        s = 1.0
    else:
        lo, hi = 1.0, 8.0
        for _ in range(40):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if total(mid) > target else (lo, mid)
        s = hi
    out = []
    for b in beats:
        d = b['t1'] - b['t0']
        sp = b['speed'] if b.get('speed') else (max(1.0, min(s, d / min(min_beat, d))) if d > 0 else 1.0)
        out.append({**b, 'speed': sp, 'out': d / sp})
    return out


def build_stringout(src, beats, dest, size):
    W, H = size
    parts, labels = [], []
    for i, b in enumerate(beats):
        parts.append(f"[0:v]trim=start={b['t0']:.3f}:end={b['t1']:.3f},setpts=(PTS-STARTPTS)/{b['speed']:.4f},fps={FPS},scale={W}:{H}:flags=lanczos[v{i}]")
        labels.append(f'[v{i}]')
    flt = ';'.join(parts) + ';' + ''.join(labels) + f'concat=n={len(beats)}:v=1:a=0[v]'
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    r = subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-i', src, '-filter_complex', flt, '-map', '[v]', '-c:v', 'libx264',
                        '-crf', '16', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-r', str(FPS), dest], capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(dest):
        raise SystemExit('I could not cut the recording together: ' + r.stderr[-400:])


def link_or_copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        os.remove(dst)
    try:
        os.link(src, dst)
    except OSError:
        import shutil; shutil.copyfile(src, dst)


def passthrough(a):
    """Options that go on to export_clips.py (everything except the ratio, platform and layout, which are per format)."""
    out = []
    for flag, val in (('--hook', a.hook), ('--hook-seconds', a.hook_seconds if a.hook else None), ('--name', a.name), ('--role', a.role or None),
                      ('--music', a.music), ('--caption-style', a.caption_style), ('--caption-pos', a.caption_pos), ('--focus', a.focus if a.focus != '0.5,0.5' else None)):
        if val not in (None, ''):
            out += [flag, str(val)]
    for flag, on in (('--outro', a.outro), ('--no-progress', a.no_progress), ('--force', a.force)):
        if on:
            out.append(flag)
    return out


def main():
    ap = argparse.ArgumentParser(description='Cut a page recording into a behind-the-scenes reel.', parents=[make_clip_brief.options()])
    ap.set_defaults(layout=None)
    ap.add_argument('capture', help='the name used with record_page.mjs (source/<name>/capture.mp4)')
    ap.add_argument('--out', help='name for the reel files (default: <capture>-reel)')
    ap.add_argument('--title', help='reel title and file name (default: the page title)')
    ap.add_argument('--seconds', type=float, default=30.0, help='target length (default 30)')
    ap.add_argument('--min-beat', type=float, default=1.6, help='shortest a labelled beat may get (default 1.6 s)')
    ap.add_argument('--formats', help='comma list of platforms from presets.json, e.g. reels,linkedin,widescreen (default: --platform or reels)')
    ap.add_argument('--export', action='store_true', help='render and finish each format into deliverables/')
    a = ap.parse_args()
    cdir = os.path.join(ROOT, 'source', a.capture)
    cj, cv = os.path.join(cdir, 'capture.json'), os.path.join(cdir, 'capture.mp4')
    if not (os.path.exists(cj) and os.path.exists(cv)):
        raise SystemExit(f'No recording called "{a.capture}". Record one first:  node tools/record_page.mjs <url> {a.capture}')
    cap = json.load(open(cj))
    beats = [b for b in cap['beats'] if b['t1'] - b['t0'] > 0.15]
    if not beats:
        raise SystemExit('The recording has no beats to cut. Record it again with a tour (see tools/record_page.mjs --help).')
    planned = plan_speeds(beats, a.seconds, a.min_beat)
    total = sum(b['out'] for b in planned)
    frames = round(total * FPS)
    seconds = frames / FPS
    caps, t = [], 0.0
    for b in planned:
        if b.get('label'):
            caps.append({'start': round(t + 0.1, 2), 'end': round(max(t + 0.5, t + b['out'] - 0.1), 2), 'text': b['label']})
        t += b['out']
    title = a.title or cap.get('title') or a.capture
    base = a.out or f'{a.capture}-reel'
    formats = [f.strip() for f in a.formats.split(',')] if a.formats else [a.platform or 'reels']
    presets = make_clip_brief.presets()
    for f in formats:
        if f not in presets:
            raise SystemExit(f'Unknown format "{f}". Choose from: {", ".join(sorted(presets))}.')
    if a.hook is None:
        a.hook = 'Behind the scenes'
    if a.caption_style is None:
        a.caption_style = 'plain'      # step labels are not speech: no word-by-word highlight

    master = os.path.join(ROOT, '_work', 'reel', f'{base}-stringout.mp4')
    size = (2560, 1440) if cap['size'][0] * 9 == cap['size'][1] * 16 else (reframe.even(min(cap['size'][0], 2560)), reframe.even(cap['size'][1] * min(cap['size'][0], 2560) / cap['size'][0]))
    build_stringout(cv, planned, master, size)

    jobs = []
    for f in formats:
        slug = base if len(formats) == 1 else f'{base}-{f}'
        t = title if len(formats) == 1 else f"{title} ({presets[f]['label'].replace(':', 'x')})"
        media = os.path.join(ROOT, 'public', 'media', slug)
        link_or_copy(master, os.path.join(media, 'stringout.mp4'))
        os.makedirs(os.path.join(ROOT, 'cuts'), exist_ok=True); os.makedirs(os.path.join(ROOT, 'briefs'), exist_ok=True)
        json.dump({'slug': slug, 'prebuilt': True, 'kind': 'capture-reel', 'source': os.path.relpath(cv, ROOT),
                   'note': 'Written by tools/make_reel.py from a page recording; re-run make_reel.py to change it. It is not a transcript cut.'},
                  open(os.path.join(ROOT, 'cuts', f'{slug}.edl.json'), 'w'), indent=1)
        os.makedirs(os.path.join(ROOT, 'public', 'voice'), exist_ok=True)
        subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=mono', '-t', f'{seconds:.3f}',
                        '-c:a', 'pcm_s16le', os.path.join(ROOT, 'public', 'voice', f'{slug}.wav')], check=True)
        json.dump({'title': t, 'slug': slug, 'fps': FPS, 'scenes': [{'id': 'reel', 'kind': 'capture', 'duration': seconds}], 'captions': caps,
                   'beats': [{'label': b.get('label'), 'speed': round(b['speed'], 2), 'seconds': round(b['out'], 2)} for b in planned]},
                  open(os.path.join(ROOT, 'briefs', f'{slug}.json'), 'w'), indent=1)    # written last: newer than the cut file, so it is not rebuilt
        ratio = presets[f]['ratio']
        rw, rh = reframe.SIZES[ratio]
        same_shape = abs(cap['size'][0] / cap['size'][1] / (rw / rh) - 1) < 0.06     # recorded in the reel's own shape: no blur bars needed
        layout = a.layout or ('fill' if same_shape else 'blurfill')
        jobs.append((slug, f, layout))
        print(f'{slug}: "{t}" {seconds:.1f} s from {cap["seconds"]:.1f} s of recording, {len(caps)} step labels ({ratio}, {layout})')
    print('Speed-up per beat: ' + ', '.join(f"{(b.get('label') or '-')[:22]} x{b['speed']:.1f}" for b in planned))
    over = [f for f in formats if seconds > presets[f]['maxSeconds']]
    if over:
        print(f'  note: longer than the limit for {", ".join(over)}.')
    extra = passthrough(a)
    sys.stdout.flush()
    for slug, f, layout in jobs:
        cmd = [sys.executable, os.path.join(ROOT, 'tools', 'export_clips.py'), slug, '--platform', f, '--layout', layout] + extra
        if a.export:
            r = subprocess.run(cmd, cwd=ROOT)
            if r.returncode != 0:
                raise SystemExit(f'{slug}: the export failed (details above).')
        else:
            print('Next:  python3 tools/export_clips.py ' + ' '.join(cmd[2:]).replace(os.path.join(ROOT, 'tools') + '/', ''))


if __name__ == '__main__':
    main()
