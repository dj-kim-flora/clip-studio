#!/usr/bin/env python3
"""Mouth-click repair for a voice track.

    python3 tools/declick.py <in.wav> <out.wav> [--report]

Finds sub-millisecond high-frequency bursts (lip smacks, tongue clicks: a spike that rings for well under a
millisecond) that stand far above the voice around them, and low-passes just those ~2 ms, crossfaded in and out.
Everything else is copied bit-for-bit. Sustained high-frequency sound (s, sh, f) and plosive bursts (t, k, p, which
keep going for several ms) are left alone: a click has to fall back within 3 ms, or be a strong spike 12 dB above
the 5 ms around it.
Reads/writes 16-bit PCM or 32-bit float WAV, mono or stereo (channels are repaired together).
"""
import array, math, struct, sys

def read_wav(path):
    raw = open(path, 'rb').read()
    fmt = raw.index(b'fmt ')
    code, ch, sr = struct.unpack('<HHI', raw[fmt + 8:fmt + 16])
    bits = struct.unpack('<H', raw[fmt + 22:fmt + 24])[0]
    d = raw.index(b'data'); n = struct.unpack('<I', raw[d + 4:d + 8])[0]
    body = raw[d + 8:d + 8 + n]
    if bits == 16:
        pcm = array.array('h', body); data = array.array('f', (v / 32768.0 for v in pcm))
    elif bits == 32 and code in (3, 0xFFFE):
        data = array.array('f', body)
    else:
        raise SystemExit(f'unsupported WAV: format {code}, {bits} bits')
    return sr, ch, bits, [data[c::ch] for c in range(ch)]

def write_wav(path, sr, ch, bits, chans):
    n = len(chans[0])
    inter = array.array('f', bytes(4 * n * ch))
    for c in range(ch):
        inter[c::ch] = chans[c]
    if bits == 16:
        body = array.array('h', (max(-32768, min(32767, int(round(v * 32768)))) for v in inter)).tobytes(); code, bps = 1, 2
    else:
        body = inter.tobytes(); code, bps = 3, 4
    hdr = b'RIFF' + struct.pack('<I', 36 + len(body)) + b'WAVE' + b'fmt ' + struct.pack('<IHHIIHH', 16, code, ch, sr, sr * ch * bps, ch * bps, bps * 8)
    open(path, 'wb').write(hdr + b'data' + struct.pack('<I', len(body)) + body)

def detect(x, sr):
    """Start samples of isolated high-frequency bursts."""
    W = max(1, sr // 2000)                     # 0.5 ms windows
    hf = []
    for k in range(2, len(x) - W, W):
        s = 0.0
        for i in range(k, k + W):
            d = x[i] - 2 * x[i - 1] + x[i - 2]
            s += d * d
        hf.append(s / W)
    lvl = []                                   # broadband level of the same windows
    for k in range(2, len(x) - W, W):
        s = 0.0
        for i in range(k, k + W):
            s += x[i] * x[i]
        lvl.append(s / W)
    out, R = [], 40                            # compare with the surrounding +/-20 ms
    for j in range(R, len(hf) - R):
        h = hf[j]
        if h < 1e-6:                           # too faint to hear (d2 rms < -60 dBFS)
            continue
        # a strong spike on top of speech (e.g. a lip smack at a word onset): 12 dB over the +/-5 ms around it
        near = sorted(hf[j - 10:j - 1] + hf[j + 2:j + 11])
        if h > 1e-3 and h > 16 * near[len(near) // 2] and h > 2.0 * lvl[j]:
            out.append(2 + j * W)
            continue
        around = sorted(hf[j - R:j - 2] + hf[j + 3:j + R])
        med = around[len(around) // 2] + 1e-12
        if h < 30 * med:                       # at least ~15 dB above the local high-frequency floor
            continue
        # a click is short: the high-frequency energy is back near the floor within 3 ms, both ways
        if max(hf[j + 3:j + 7]) > 6 * med or max(hf[j - 6:j - 2]) > 6 * med:
            continue
        # and it is mostly high frequency: the spike stands out in d2 far more than in plain level
        if h < 2.0 * lvl[j]:
            continue
        out.append(2 + j * W)
    merged = []
    for s in out:
        if merged and s - merged[-1] < 3 * W:
            continue
        merged.append(s)
    return merged, W

def repair(chans, s, sr):
    """Low-pass ~2 ms around s (9-tap centred moving average, about 5 kHz), crossfaded over 0.5 ms."""
    pre, post, fade = int(0.0006 * sr), int(0.0016 * sr), int(0.0005 * sr)
    a, b = max(4, s - pre - fade), min(len(chans[0]) - 5, s + post + fade)
    for x in chans:
        smooth = [sum(x[i - 4:i + 5]) / 9.0 for i in range(a, b)]
        for i in range(a, b):
            if i < a + fade:
                w = (i - a) / fade
            elif i > b - fade:
                w = (b - i) / fade
            else:
                w = 1.0
            x[i] = x[i] * (1 - w) + smooth[i - a] * w

def main():
    src, dst = sys.argv[1], sys.argv[2]
    sr, ch, bits, chans = read_wav(src)
    mono = chans[0] if ch == 1 else array.array('f', ((chans[0][i] + chans[1][i]) * 0.5 for i in range(len(chans[0]))))
    clicks, W = detect(mono, sr)
    for s in clicks:
        repair(chans, s, sr)
    write_wav(dst, sr, ch, bits, chans)
    print(f'declick: {len(clicks)} clicks repaired')
    if '--report' in sys.argv:
        print('  at', ' '.join(f'{s / sr:.2f}' for s in clicks))

if __name__ == '__main__':
    main()
