#!/usr/bin/env python3
"""Turn a built cut into a reframed video and a clip brief for the `Clip` composition.

    python3 tools/make_clip_brief.py <slug> [--ratio 9:16] [--platform tiktok] [--layout fill|split|blurfill]
        [--mode center|track] [--focus 0.5,0.4] [--second other.mp4] [--caption-style pill] [--caption-pos lower]
        [--hook "text" | --hook auto] [--name "Jane Doe" --role "Founder, Acme"] [--outro] [--music file] [--no-progress]

Needs the output of  python3 tools/build_cut.py cuts/<slug>.edl.json :
  briefs/<slug>.json, public/voice/<slug>.wav, public/media/<slug>/stringout.mp4 (an audio-only recording has no
  stringout: a plain background in the brand colour is drawn instead).
Writes
  public/media/<slug>/reframed.mp4     the cut picture at the platform size, video only (skipped when already up to date)
  briefs/<slug>.clip.json              what the Clip composition renders (captions come from the built brief)
Layouts: fill (one picture fills the frame; --mode track follows a face), blurfill (whole picture fitted over a blurred
copy of itself), split (top 60%: the whole picture; bottom 40%: a close crop around --focus, or --second video; two
panel videos are written, video and video2).
--platform takes the ratio and caption position from tools/presets.json; --ratio overrides the ratio.
"""
import argparse, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brand, reframe
from ff import FF
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 30
SPLIT = 0.6


def presets():
    return json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'presets.json')))


def options():
    """The shared options (also used by export_clips.py as a parent parser)."""
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument('--ratio', choices=sorted(reframe.SIZES), help='9:16, 4:5, 1:1 or 16:9 (default: from --platform, else 9:16)')
    ap.add_argument('--platform', choices=sorted(presets()), help='takes ratio and caption position from presets.json')
    ap.add_argument('--layout', choices=['fill', 'split', 'blurfill'], default='fill')
    ap.add_argument('--mode', choices=['center', 'track'], default='center', help='for layout fill: centre crop or follow a face')
    ap.add_argument('--focus', default='0.5,0.5', help='crop centre as fractions, x,y')
    ap.add_argument('--second', help='split layout: a different video for the bottom panel')
    ap.add_argument('--caption-style', choices=['none', 'pill', 'karaoke', 'plain', 'box'], help='default: the brand style')
    ap.add_argument('--caption-pos', choices=['lower', 'center', 'upper'])
    ap.add_argument('--hook', help='big opening line over the first seconds; "auto" uses the clip title')
    ap.add_argument('--hook-seconds', type=float, default=2.4)
    ap.add_argument('--name', help='lower third: speaker name')
    ap.add_argument('--role', default='', help='lower third: role or company')
    ap.add_argument('--outro', action='store_true', help='add the end card from brand.json "outro"')
    ap.add_argument('--music', help='a music file you may use; it is levelled and ducked under the voice')
    ap.add_argument('--no-progress', action='store_true', help='hide the progress bar')
    ap.add_argument('--force', action='store_true', help='redo the reframed video even if it looks up to date')
    return ap


def parser():
    ap = argparse.ArgumentParser(prog='make_clip_brief.py', parents=[options()],
                                 description='Reframe a built cut and write briefs/<slug>.clip.json.')
    ap.add_argument('slug')
    return ap


def wav_seconds(path):
    import wave
    w = wave.open(path, 'rb'); n = w.getnframes() / w.getframerate(); w.close(); return n


def newer(a, b):
    return os.path.exists(a) and os.path.exists(b) and os.path.getmtime(a) >= os.path.getmtime(b)


def make(slug, a):
    """Do the whole job for one slug with parsed args `a`. Returns (clip_json_path, info dict)."""
    bp = os.path.join(ROOT, 'briefs', f'{slug}.json')
    voice = os.path.join(ROOT, 'public', 'voice', f'{slug}.wav')
    media = os.path.join(ROOT, 'public', 'media', slug)
    stringout = os.path.join(media, 'stringout.mp4')
    if not os.path.exists(bp) or not os.path.exists(voice):
        raise SystemExit(f'"{slug}" has not been built yet. Run first:  python3 tools/build_cut.py cuts/{slug}.edl.json')
    b = json.load(open(bp))
    preset = presets().get(a.platform) if a.platform else None
    ratio = a.ratio or (preset['ratio'] if preset else '9:16')
    W, H = reframe.SIZES[ratio]
    seconds = round(sum(round(s['duration'] * FPS) for s in b['scenes']) / FPS, 3) or round(wav_seconds(voice), 3)
    focus = tuple(float(v) for v in a.focus.split(','))
    os.makedirs(media, exist_ok=True)
    video, video2 = f'media/{slug}/reframed.mp4', None
    out = os.path.join(media, 'reframed.mp4')
    params = {'ratio': ratio, 'layout': a.layout, 'mode': a.mode, 'focus': focus, 'second': a.second, 'seconds': seconds}
    pj = os.path.join(media, 'reframed.params.json')
    out2 = os.path.join(media, 'reframed-bottom.mp4')
    fresh = (not a.force and os.path.exists(pj) and json.load(open(pj)) == json.loads(json.dumps(params))
             and newer(out, stringout if os.path.exists(stringout) else voice)
             and (a.layout != 'split' or os.path.exists(out2)))
    if a.layout == 'split':
        video2 = f'media/{slug}/reframed-bottom.mp4'
    if not fresh:
        if not os.path.exists(stringout):
            # audio-only recording: a plain background in the brand colour, as long as the voice
            bg = brand.colors()['background']
            subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', f'color=c={bg}:s={W}x{H}:r={FPS}',
                            '-t', f'{seconds:.3f}', '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', out], check=True)
            video2 = None
        elif a.layout == 'split':
            top_h = reframe.even(H * SPLIT); bot_h = H - top_h
            reframe.reframe_panel(stringout, out, W, top_h, 'fit')
            reframe.reframe_panel(a.second or stringout, out2, W, bot_h, 'cover', focus, 1.0 if a.second else 1.6)
        else:
            mode = 'blurfill' if a.layout == 'blurfill' else a.mode
            reframe.reframe(stringout, out, ratio, mode, focus)
        json.dump(params, open(pj, 'w'))
    elif not os.path.exists(stringout):
        video2 = None
    if not os.path.exists(stringout):
        a.layout = 'fill'
    caption_pos = a.caption_pos or (preset or {}).get('captionPos') or 'lower'
    style = brand.load()['style']
    clip = {
        'kind': 'clip', 'slug': slug, 'title': b.get('title') or slug, 'width': W, 'height': H, 'fps': FPS, 'seconds': seconds,
        'layout': a.layout, 'video': video, 'video2': video2, 'voice': f'voice/{slug}.wav', 'music': None,
        'captions': b.get('captions', []), 'captionStyle': a.caption_style or style.get('captionStyle', 'pill'),
        'captionPos': caption_pos, 'hook': None, 'lowerThird': None, 'progressBar': not a.no_progress, 'outro': None,
        'safeZone': 'social' if ratio in ('9:16', '4:5') else 'none',
    }
    if a.layout == 'split':
        clip['splitRatio'] = SPLIT
    if a.hook:
        text = (clip['title'] if a.hook == 'auto' else a.hook).strip()
        clip['hook'] = {'text': text, 'from': 0.0, 'to': round(min(a.hook_seconds, max(1.0, seconds - 0.5)), 2)}
    if a.name:
        clip['lowerThird'] = {'name': a.name, 'role': a.role, 'from': 1.0, 'to': round(min(5.0, max(2.0, seconds - 0.5)), 2)}
    if a.outro:
        o = brand.load()['outro']
        line = o.get('line') or o.get('cta') or ''
        if line or o.get('handle'):
            clip['outro'] = {'seconds': 2.0, 'line': line, 'handle': o.get('handle', '')}
        else:
            print(f'  note: brand.json has no outro text, so {slug} gets no end card. Add outro.line or outro.handle to use one.')
    if a.music:
        name = f'{slug}-music'
        ducked = os.path.join(ROOT, 'public', 'music', f'{name}-ducked.wav')
        if not (newer(ducked, a.music) and newer(ducked, voice)):
            os.makedirs(os.path.join(ROOT, 'public', 'music'), exist_ok=True)
            r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'music_bed.py'), a.music, voice, '0', f'{seconds:.3f}', name],
                               capture_output=True, text=True)
            if r.returncode != 0:
                raise SystemExit('I could not level that music file (is it a normal audio file?). ' + (r.stderr or '')[-300:])
        clip['music'] = {'src': f'music/{name}-ducked.wav', 'volume': 1}
    cp = os.path.join(ROOT, 'briefs', f'{slug}.clip.json')
    text = json.dumps(clip, indent=1)
    if not (os.path.exists(cp) and open(cp).read() == text):      # keep the timestamp when nothing changed (resumable renders)
        open(cp, 'w').write(text)
    return cp, {'ratio': ratio, 'size': (W, H), 'seconds': seconds, 'title': clip['title'], 'reused': fresh, 'captions': len(clip['captions'])}


def main():
    a = parser().parse_args()
    cp, info = make(a.slug, a)
    print(f"{a.slug}: \"{info['title']}\" {info['size'][0]}x{info['size'][1]} ({info['ratio']}), {info['seconds']:.1f} s, "
          f"{info['captions']} caption cues -> {os.path.relpath(cp, ROOT)}" + (' (picture already up to date)' if info['reused'] else ''))


if __name__ == '__main__':
    main()
