#!/usr/bin/env python3
"""Reframe a video to a social format. Output is video only (no sound), 30 fps, H.264, even dimensions.

    python3 tools/reframe.py <in.mp4> <out.mp4> --ratio 9:16|4:5|1:1|16:9 [--mode center|track|blurfill|split]
                             [--focus 0.5,0.4] [--keys keys.json] [--second other.mp4] [--seconds N]

Sizes: 9:16 = 1080x1920, 4:5 = 1080x1350, 1:1 = 1080x1080, 16:9 = 1920x1080.

Modes
  center    crop the middle (or around --focus) to the ratio, scale to size. Default.
  track     follow the first face (OpenCV, sampled every 0.5 s, smoothed). Without OpenCV it says so and uses center.
  blurfill  the whole picture fitted inside the frame over a blurred, enlarged copy of itself (nothing is cropped).
  split     two panels stacked 60/40: top = the whole picture fitted (screen, slides), bottom = a close crop around
            --focus (the speaker). Give --second other.mp4 to use a different video for the bottom panel.
--focus x,y   fractions of the picture (0..1) where the crop is centred, e.g. 0.3,0.4. Default 0.5,0.5.
--keys file   JSON list of timed focus points [{"t": 0, "x": 0.3, "y": 0.5}, {"t": 12, "x": 0.7, "y": 0.5}] (seconds;
              the crop glides between them). Works with center and track (track writes its own).
"""
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ff import FF

SIZES = {'9:16': (1080, 1920), '4:5': (1080, 1350), '1:1': (1080, 1080), '16:9': (1920, 1080)}
FPS = 30
CRF = 16


def probe_size(path):
    err = subprocess.run([FF, '-hide_banner', '-i', path], capture_output=True, text=True).stderr
    line = next((l for l in err.splitlines() if 'Video:' in l and 'attached pic' not in l), None)
    m = re.search(r'[, ](\d{2,5})x(\d{2,5})[, \[]', line or '')
    if not m:
        raise SystemExit(f'I cannot read a picture from {path}. Is it a video file?')
    dur = re.search(r'Duration: (\d+):(\d+):([\d.]+)', err)
    seconds = int(dur[1]) * 3600 + int(dur[2]) * 60 + float(dur[3]) if dur else None
    return int(m.group(1)), int(m.group(2)), seconds


def even(v):
    return max(2, int(round(v / 2.0)) * 2)


def crop_box(iw, ih, W, H):
    """Largest crop of the input with the output's aspect ratio (even sizes)."""
    if iw / ih > W / H:
        ch = ih; cw = ih * W / H
    else:
        cw = iw; ch = iw * H / W
    cw, ch = min(even(cw), iw - iw % 2), min(even(ch), ih - ih % 2)
    return cw, ch


def parse_keys(path):
    data = json.load(open(path))
    keys = []
    for k in data:
        if isinstance(k, dict):
            keys.append((float(k['t']), float(k.get('x', 0.5)), float(k.get('y', 0.5))))
        else:
            keys.append((float(k[0]), float(k[1]), float(k[2])))
    keys.sort()
    if not keys:
        raise SystemExit('The keys file is empty. Give it a list like [{"t": 0, "x": 0.5, "y": 0.5}].')
    return keys


def _expr(vals, lo, hi):
    """Piecewise-linear ffmpeg expression in t through (time, pixel) points, clamped to [lo, hi]. Written as a sum of
    ramps (no nesting), so a few dozen points stay short."""
    vals = [(t, min(hi, max(lo, v))) for t, v in vals]
    if len(vals) == 1:
        return f'{vals[0][1]:.2f}'
    terms = [f'{vals[0][1]:.2f}']
    for (t0, v0), (t1, v1) in zip(vals, vals[1:]):
        d = max(1e-3, t1 - t0)
        terms.append(f'{(v1 - v0) / d:.5f}*max(0,min(t-{t0:.3f},{d:.3f}))')
    return '+'.join(terms)


def simplify(keys, tol=0.012, limit=36):
    """Ramer-Douglas-Peucker on (t, x, y): drops points the crop glides through anyway."""
    def dev(a, b, p):
        f = 0.0 if b[0] == a[0] else (p[0] - a[0]) / (b[0] - a[0])
        return max(abs(a[1] + (b[1] - a[1]) * f - p[1]), abs(a[2] + (b[2] - a[2]) * f - p[2]))
    def rdp(pts, tol):
        if len(pts) < 3:
            return pts
        worst, wi = max((dev(pts[0], pts[-1], p), i) for i, p in enumerate(pts[1:-1], 1))
        if worst <= tol:
            return [pts[0], pts[-1]]
        return rdp(pts[:wi + 1], tol)[:-1] + rdp(pts[wi:], tol)
    out = rdp(list(keys), tol)
    while len(out) > limit:
        tol *= 1.5
        out = rdp(list(keys), tol)
    return out


def cover_chain(iw, ih, W, H, focus, keys):
    """Filter text that crops to W:H around the focus (static or keyed) and scales to W x H."""
    cw, ch = crop_box(iw, ih, W, H)
    if keys:
        kx = [(t, x * iw - cw / 2) for t, x, y in keys]
        ky = [(t, y * ih - ch / 2) for t, x, y in keys]
        xs, ys = _expr(kx, 0, iw - cw), _expr(ky, 0, ih - ch)
        return f"crop={cw}:{ch}:x='{xs}':y='{ys}',scale={W}:{H}:flags=lanczos"
    fx, fy = focus
    x = min(max(0, fx * iw - cw / 2), iw - cw); y = min(max(0, fy * ih - ch / 2), ih - ch)
    return f"crop={cw}:{ch}:{x:.0f}:{y:.0f},scale={W}:{H}:flags=lanczos"


def fit_over_blur(W, H, label_in, label_out):
    """Graph text: label_in fitted inside W x H over a blurred, enlarged copy of itself."""
    return (f"[{label_in}]split=2[bg_s][fg_s];"
            f"[bg_s]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},gblur=sigma=40,eq=brightness=-0.08[bgb];"
            f"[fg_s]scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos[fgf];"
            f"[bgb][fgf]overlay=(W-w)/2:(H-h)/2[{label_out}]")


def track_faces(path, iw, ih, seconds, cw, ch):
    """Smoothed face-centre keys [(t, x, y)] using OpenCV Haar detection every 0.5 s, or None if OpenCV is missing
    or no face is ever found."""
    try:
        import cv2
    except Exception:
        print('Face tracking needs OpenCV, which is not installed (pip install opencv-python-headless). Using a centred crop instead.')
        return None
    cap = cv2.VideoCapture(path)
    cascade = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml'))
    if not cap.isOpened() or cascade.empty():
        print('Face tracking could not start (OpenCV could not open the video or its face model). Using a centred crop instead.')
        return None
    pts, t = [], 0.0
    end = seconds if seconds else 1e9
    while t < end:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            break
        scale = 640.0 / frame.shape[1] if frame.shape[1] > 640 else 1.0
        small = cv2.resize(frame, None, fx=scale, fy=scale) if scale != 1.0 else frame
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, 1.15, 5, minSize=(max(24, int(small.shape[1] * 0.05)),) * 2)
        if len(faces):
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            pts.append((t, (x + w / 2) / small.shape[1], (y + h / 2) / small.shape[0]))
        else:
            pts.append((t, None, None))
        t += 0.5
    cap.release()
    found = [p for p in pts if p[1] is not None]
    if not found:
        print('No face found in the video. Using a centred crop instead.')
        return None
    # fill gaps with the nearest known face, then smooth: median of 3, then a dead zone so the crop only moves when it must
    filled, last = [], found[0]
    for p in pts:
        last = p if p[1] is not None else last
        filled.append((p[0], last[1], last[2]))
    def med(vals, i):
        w = sorted(vals[max(0, i - 1):i + 2]); return w[len(w) // 2]
    xs, ys = [p[1] for p in filled], [p[2] for p in filled]
    xs = [med(xs, i) for i in range(len(xs))]; ys = [med(ys, i) for i in range(len(ys))]
    dead_x, dead_y = 0.05 * cw / iw, 0.05 * ch / ih
    sx, sy, out = xs[0], ys[0], []
    for (t, _, _), x, y in zip(filled, xs, ys):
        if abs(x - sx) > dead_x:
            sx += (x - sx) * 0.5
        if abs(y - sy) > dead_y:
            sy += (y - sy) * 0.5
        out.append((t, sx, sy))
    print(f'Face tracking: found a face in {len(found)} of {len(pts)} samples.')
    return simplify(out)


def reframe(inp, out, ratio, mode='center', focus=(0.5, 0.5), keys=None, second=None, seconds=None):
    if ratio not in SIZES:
        raise SystemExit(f'Unknown ratio {ratio}. Choose one of: ' + ', '.join(SIZES))
    for p in (inp, second):
        if p and not os.path.exists(p):
            raise SystemExit(f'I cannot find {p}.')
    W, H = SIZES[ratio]
    iw, ih, dur = probe_size(inp)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    tail = f',setsar=1,fps={FPS},format=yuv420p'
    cmd = [FF, '-hide_banner', '-loglevel', 'error', '-y', '-i', inp]
    if mode == 'track':
        cw, ch = crop_box(iw, ih, W, H)
        keys = keys or track_faces(inp, iw, ih, seconds or dur, cw, ch)
        mode = 'center'
    if mode == 'center':
        graph = f'[0:v]{cover_chain(iw, ih, W, H, focus, keys)}{tail}[v]'
    elif mode == 'blurfill':
        graph = fit_over_blur(W, H, '0:v', 'bf') + f';[bf]{tail[1:]}[v]'
    elif mode == 'split':
        top_h = even(H * 0.6); bot_h = H - top_h
        if second:
            cmd += ['-i', second]
            sw, sh, _ = probe_size(second)
            bot_src, bw, bh = '1:v', sw, sh
        else:
            bot_src, bw, bh = '0:v', iw, ih
        # bottom panel: a tighter crop (about 1.6x closer than the full cover) centred on the focus
        cw, ch = crop_box(bw, bh, W, bot_h)
        zw, zh = even(cw / 1.6) if not second else cw, even(ch / 1.6) if not second else ch
        fx, fy = focus
        zx = min(max(0, fx * bw - zw / 2), bw - zw); zy = min(max(0, fy * bh - zh / 2), bh - zh)
        graph = (fit_over_blur(W, top_h, '0:v', 'top') + ';' +
                 f'[{bot_src}]crop={zw}:{zh}:{zx:.0f}:{zy:.0f},scale={W}:{bot_h}:flags=lanczos[bot];'
                 f'[top][bot]vstack=inputs=2:shortest=1{tail}[v]')
    else:
        raise SystemExit(f'Unknown mode {mode}. Choose one of: center, track, blurfill, split.')
    cmd += ['-filter_complex', graph, '-map', '[v]', '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', str(CRF),
            '-g', '15', '-pix_fmt', 'yuv420p', '-r', str(FPS), '-movflags', '+faststart']
    if seconds:
        cmd += ['-t', f'{seconds:.3f}']
    cmd.append(out)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-2000:])
        raise SystemExit('ffmpeg could not reframe that video (details above).')
    return W, H


def reframe_panel(inp, out, W, H, style='fit', focus=(0.5, 0.5), zoom=1.0, seconds=None):
    """One panel of a split layout at any size. style 'fit' = whole picture over a blurred copy; 'cover' = crop around the
    focus (zoom > 1 is a tighter crop). Used by tools/make_clip_brief.py; output is video only, 30 fps."""
    iw, ih, _ = probe_size(inp)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    tail = f'setsar=1,fps={FPS},format=yuv420p'
    if style == 'fit':
        graph = fit_over_blur(W, H, '0:v', 'p') + f';[p]{tail}[v]'
    else:
        cw, ch = crop_box(iw, ih, W, H)
        zw, zh = even(cw / zoom), even(ch / zoom)
        x = min(max(0, focus[0] * iw - zw / 2), iw - zw); y = min(max(0, focus[1] * ih - zh / 2), ih - zh)
        graph = f'[0:v]crop={zw}:{zh}:{x:.0f}:{y:.0f},scale={W}:{H}:flags=lanczos,{tail}[v]'
    cmd = [FF, '-hide_banner', '-loglevel', 'error', '-y', '-i', inp, '-filter_complex', graph, '-map', '[v]', '-an',
           '-c:v', 'libx264', '-preset', 'medium', '-crf', str(CRF), '-g', '15', '-pix_fmt', 'yuv420p', '-r', str(FPS),
           '-movflags', '+faststart'] + (['-t', f'{seconds:.3f}'] if seconds else []) + [out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-2000:])
        raise SystemExit('ffmpeg could not reframe that video (details above).')


def main():
    a = sys.argv[1:]
    if len(a) < 2 or a[0].startswith('-') or '--ratio' not in a:
        raise SystemExit(__doc__)
    def opt(name, default=None):
        return a[a.index(name) + 1] if name in a else default
    focus = tuple(float(v) for v in opt('--focus', '0.5,0.5').split(','))
    keys = parse_keys(opt('--keys')) if opt('--keys') else None
    seconds = float(opt('--seconds')) if opt('--seconds') else None
    W, H = reframe(a[0], a[1], opt('--ratio'), opt('--mode', 'center'), focus, keys, opt('--second'), seconds)
    print(f'{a[1]}: {W}x{H} ({opt("--ratio")}, {opt("--mode", "center")}), video only, {FPS} fps')


if __name__ == '__main__':
    main()
