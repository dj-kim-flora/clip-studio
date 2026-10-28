#!/usr/bin/env python3
"""Finish a rendered film for delivery: one fixed gain to the target loudness, a limiter run at 192 kHz (true peak under
the ceiling), AudioToolbox AAC when available; the video track is copied untouched. Reports what the limiter did.

    python3 tools/finish.py _work/<film>-raw.mp4 "deliverables/<Film name> vN.mp4" [--target -14.3] [--ceiling -2]

Never use single-pass loudnorm (it rides the level: quiet music gets pumped up) and don't trust loudnorm's linear mode
(it silently falls back to dynamic when the peaks don't fit). A limiter doing more than ~3 dB means the mix is too hot:
fix the stems, don't push harder here.
"""
import json, math, os, struct, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ff import FF, aac_encoder

def loud(path):
    out = subprocess.run([FF, '-hide_banner', '-nostats', '-i', path, '-af', 'loudnorm=print_format=json', '-f', 'null', '-'], capture_output=True, text=True).stderr
    m = json.loads(out[out.rindex('{'):out.rindex('}') + 1]); return float(m['input_i']), float(m['input_tp']), float(m['input_lra'])

def floats(path):
    raw = open(path, 'rb').read(); i = raw.index(b'data'); n = struct.unpack('<I', raw[i + 4:i + 8])[0]
    import array; return array.array('f', raw[i + 8:i + 8 + n])

def main():
    src, dst = sys.argv[1], sys.argv[2]
    target = float(sys.argv[sys.argv.index('--target') + 1]) if '--target' in sys.argv else -14.3
    ceiling = float(sys.argv[sys.argv.index('--ceiling') + 1]) if '--ceiling' in sys.argv else -2.0
    i0, tp0, _ = loud(src)
    if i0 < -55:      # silent film (for example a screen-recording reel without music): never gain noise up to the target
        subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-i', src, '-c:v', 'copy', '-c:a', aac_encoder(), '-b:a', '128k', '-movflags', '+faststart', dst], check=True)
        print(f"{os.path.basename(dst)}: silent audio (measured {i0:.0f} LUFS), left silent, no gain applied -> -70.00 LUFS")
        return
    gain = target - i0
    tmp = tempfile.mkdtemp()
    pre, post = os.path.join(tmp, 'pre.wav'), os.path.join(tmp, 'post.wav')
    subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-i', src, '-vn', '-af', f'aresample=192000,volume={gain:.2f}dB,aresample=48000', '-ac', '1', '-c:a', 'pcm_f32le', pre], check=True)
    subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-i', src, '-vn', '-af',
                    f'aresample=192000,volume={gain:.2f}dB,alimiter=limit={10 ** (ceiling / 20):.4f}:attack=5:release=80:level=disabled:latency=1,aresample=48000',
                    '-c:a', 'pcm_f32le', post], check=True)
    subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-i', src, '-i', post, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                    '-c:a', aac_encoder(), '-b:a', '256k', '-movflags', '+faststart', dst], check=True)
    # limiter work, from 10 ms peak windows of the gained signal before/after
    subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-i', post, '-ac', '1', '-c:a', 'pcm_f32le', post + '.m.wav'], check=True)
    a, b = floats(pre), floats(post + '.m.wav'); W = 480; gr = []
    for j in range(0, min(len(a), len(b)) - W, W):
        pa = max(abs(v) for v in a[j:j + W]); pb = max(abs(v) for v in b[j:j + W])
        if pa > 0.05: gr.append(20 * math.log10(pa / max(pb, 1e-9)))
    gr.sort(); n = max(1, len(gr))
    i1, tp1, lra = loud(dst)
    print(f"{os.path.basename(dst)}: {i0:.2f} LUFS / {tp0:.2f} dBTP -> gain {gain:+.2f} dB -> {i1:.2f} LUFS, {tp1:.2f} dBTP, LRA {lra:.1f}")
    if gr:
        print(f"  limiter: median {gr[n // 2]:.1f} dB, p95 {gr[int(n * 0.95)]:.1f} dB, max {gr[-1]:.1f} dB of gain reduction"
              + ('   <-- working too hard: lower the stems or the target' if gr[int(n * 0.95)] > 3 else ''))

if __name__ == '__main__':
    main()
