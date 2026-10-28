#!/usr/bin/env python3
"""Batch pipeline: cuts -> finished clips in deliverables/.

    python3 tools/export_clips.py <slug>... | --all [--platform tiktok|reels|shorts|linkedin|x|youtube|feed-4x5|square|widescreen]
                                  [--ratio 9:16|4:5|1:1|16:9] [--no-render] [--force] [other make_clip_brief.py options]

Per slug: build_cut.py (if the cut changed) -> make_clip_brief.py (reframe + briefs/<slug>.clip.json) -> Remotion render
(_work/<slug>-raw.mp4) -> finish.py (loudness for the platform, from tools/presets.json) -> deliverables/:
    <Title> vN.mp4      N = next free version; older versions of the same title move to _work/superseded/
    <Title> vN.srt      captions
    <Title> TN.png      thumbnail (sharpest of 5 frames near 1.5 s)
Steps whose outputs are already newer than their inputs are skipped, so re-running is cheap. --no-render stops after the
briefs are written. Extra options (--hook, --name, --caption-style, --layout, --outro, --music ...) go to make_clip_brief.py.
"""
import argparse, glob, json, os, re, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_clip_brief
from ff import FF
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def safe_name(title, fallback):
    t = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '', title or '')
    t = re.sub(r'\s+', ' ', t).strip(' .')
    return t[:80].strip(' .') or fallback


def mt(p):
    return os.path.getmtime(p) if os.path.exists(p) else 0.0


def srt_time(t):
    ms = int(round(t * 1000))
    return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'


def write_srt(captions, path):
    lines = []
    for i, c in enumerate(captions, 1):
        end = max(c['end'], c['start'] + 0.3)
        lines += [str(i), f"{srt_time(c['start'])} --> {srt_time(end)}", c['text'], '']
    open(path, 'w').write('\n'.join(lines))


def sharpness(img):
    from PIL import ImageFilter, ImageStat
    g = img.convert('L')
    g.thumbnail((540, 960))
    lap = g.filter(ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], scale=1, offset=128))
    return ImageStat.Stat(lap).var[0]


def thumbnail(video, seconds, out_png):
    """Highest Laplacian variance among 5 frames around 1.5 s (a blink or a motion blur scores low)."""
    from PIL import Image
    tmp = tempfile.mkdtemp()
    best, best_v = None, -1.0
    for k, t in enumerate([1.1, 1.3, 1.5, 1.7, 1.9]):
        t = min(t, max(0.0, seconds - 0.3))
        p = os.path.join(tmp, f't{k}.png')
        subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-ss', f'{t:.2f}', '-i', video, '-frames:v', '1', p])
        if os.path.exists(p):
            v = sharpness(Image.open(p))
            if v > best_v:
                best, best_v = p, v
    if best:
        shutil.copyfile(best, out_png)
    shutil.rmtree(tmp, ignore_errors=True)
    return bool(best)


def next_version(deliver, title):
    top = 0
    for f in glob.glob(os.path.join(deliver, '*.mp4')):
        m = re.fullmatch(re.escape(title) + r' v(\d+)\.mp4', os.path.basename(f))
        if m:
            top = max(top, int(m.group(1)))
    return top + 1


def supersede(deliver, title):
    """Move every earlier version of this title (video, captions, thumbnail) out of deliverables/."""
    dest = os.path.join(ROOT, '_work', 'superseded')
    for f in os.listdir(deliver):
        if re.fullmatch(re.escape(title) + r' (v\d+\.(mp4|srt)|T\d+\.png)', f):
            os.makedirs(dest, exist_ok=True)
            shutil.move(os.path.join(deliver, f), os.path.join(dest, f))


def remotion_cmd():
    local = os.path.join(ROOT, 'node_modules', '.bin', 'remotion')
    if not os.path.exists(local):
        raise SystemExit('The video renderer is not installed yet. Run  bash setup.sh  once, then try again.')
    return [local]


def main():
    ap = argparse.ArgumentParser(description='Build, reframe, render and finish clips.', parents=[make_clip_brief.options()])
    ap.add_argument('slugs', nargs='*')
    ap.add_argument('--all', action='store_true', help='every cuts/*.edl.json except templates (names starting with _)')
    ap.add_argument('--no-render', action='store_true', help='stop after writing the clip briefs')
    args = mb = ap.parse_args()
    if args.all:
        slugs = sorted(os.path.basename(p)[:-len('.edl.json')] for p in glob.glob(os.path.join(ROOT, 'cuts', '*.edl.json'))
                       if not os.path.basename(p).startswith('_'))
    else:
        slugs = args.slugs
    if not slugs:
        raise SystemExit('Name the clips to export (for example  podcast-ep12-01 podcast-ep12-02 ) or use --all.')
    preset = make_clip_brief.presets().get(mb.platform) if mb.platform else None
    target = float(preset['loudness']) if preset else -14.0
    deliver = os.path.join(ROOT, 'deliverables')
    state_dir = os.path.join(ROOT, '_work', 'export')
    os.makedirs(deliver, exist_ok=True); os.makedirs(state_dir, exist_ok=True); os.makedirs(os.path.join(ROOT, '_work'), exist_ok=True)
    rows, titles = [], {}
    for slug in slugs:
        edl = os.path.join(ROOT, 'cuts', f'{slug}.edl.json')
        if not os.path.exists(edl):
            print(f'{slug}: no cuts/{slug}.edl.json, skipped.')
            rows.append((slug, '-', '-', 'no cut file'))
            continue
        # 1. build the cut when it is new or the cut file changed
        brief = os.path.join(ROOT, 'briefs', f'{slug}.json')
        voice = os.path.join(ROOT, 'public', 'voice', f'{slug}.wav')
        prebuilt = bool(json.load(open(edl)).get('prebuilt'))          # written by make_reel.py: already built, not a transcript cut
        if not prebuilt and (mb.force or not os.path.exists(voice) or mt(brief) < mt(edl)):
            r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'build_cut.py'), edl], capture_output=True, text=True, cwd=ROOT)
            if r.returncode != 0 or not os.path.exists(voice):
                sys.stderr.write((r.stdout + r.stderr)[-1500:])
                print(f'{slug}: the cut could not be built (details above), skipped.')
                rows.append((slug, '-', '-', 'build failed'))
                continue
        # 2. reframe + clip brief
        try:
            cp, info = make_clip_brief.make(slug, mb)
        except SystemExit as e:
            print(f'{slug}: {e}')
            rows.append((slug, '-', '-', 'brief failed'))
            continue
        clip = json.load(open(cp))
        title = safe_name(info['title'], slug)
        if titles.get(title, slug) != slug:
            title = safe_name(f'{title} {slug}', slug)
        titles[title] = slug
        secs = info['seconds']
        warn = ''
        if preset and secs > preset['maxSeconds']:
            warn = f" (longer than the {preset['label']} limit of {preset['maxSeconds']} s)"
        if args.no_render:
            print(f"{slug}: \"{title}\" brief ready ({info['size'][0]}x{info['size'][1]}, {secs:.0f} s){warn}; render skipped.")
            rows.append((slug, title, f'{secs:.0f} s', 'brief only'))
            continue
        # 3. render
        raw = os.path.join(ROOT, '_work', f'{slug}-raw.mp4')
        stamp_inputs = [cp, voice, os.path.join(ROOT, 'public', 'media', slug, 'reframed.mp4')]
        if mb.force or mt(raw) < max(mt(p) for p in stamp_inputs):
            cmd = remotion_cmd() + ['render', 'src/index.tsx', 'Clip', os.path.relpath(raw, ROOT), f'--props={os.path.relpath(cp, ROOT)}']
            r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            if r.returncode != 0 or not os.path.exists(raw):
                sys.stderr.write((r.stdout + r.stderr)[-2500:])
                print(f'{slug}: the render failed (details above). Is the "Clip" composition registered in src/index.tsx?')
                rows.append((slug, title, f'{secs:.0f} s', 'render failed'))
                continue
        # 4. finish: loudness, version, captions, thumbnail
        st_path = os.path.join(state_dir, f'{slug}.json')
        st = json.load(open(st_path)) if os.path.exists(st_path) else {}
        current = os.path.join(deliver, st.get('file', '')) if st.get('file') else ''
        if not mb.force and st.get('title') == title and current and os.path.exists(current) and mt(current) >= mt(raw):
            print(f'{slug}: "{title}" is up to date -> deliverables/{st["file"]}{warn}')
            rows.append((slug, title, f'{secs:.0f} s', f'up to date ({st["file"]})'))
            continue
        n = next_version(deliver, title)
        supersede(deliver, title)
        name = f'{title} v{n}'
        mp4 = os.path.join(deliver, name + '.mp4')
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'finish.py'), raw, mp4, '--target', str(target)],
                           capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(mp4):
            sys.stderr.write((r.stdout + r.stderr)[-1500:])
            print(f'{slug}: finishing the audio failed (details above).')
            rows.append((slug, title, f'{secs:.0f} s', 'finish failed'))
            continue
        write_srt(clip['captions'], os.path.join(deliver, name + '.srt'))
        thumb = thumbnail(mp4, secs, os.path.join(deliver, f'{title} T{n}.png'))
        json.dump({'title': title, 'file': name + '.mp4', 'version': n}, open(st_path, 'w'))
        lufs = re.search(r'-> ([-\d.]+) LUFS', r.stdout)
        print(f'{slug}: "{title}" -> deliverables/{name}.mp4 ({secs:.0f} s, {info["size"][0]}x{info["size"][1]}'
              + (f', {lufs.group(1)} LUFS' if lufs else '') + f'{", captions and thumbnail saved" if thumb else ", captions saved"}){warn}')
        rows.append((slug, title, f'{secs:.0f} s', f'{name}.mp4'))
    # summary
    print()
    w = [max(len(r[i]) for r in rows + [('Clip', 'Title', 'Length', 'Result')]) for i in range(4)]
    for r in [('Clip', 'Title', 'Length', 'Result')] + rows:
        print('  '.join(c.ljust(w[i]) for i, c in enumerate(r)))


if __name__ == '__main__':
    main()
