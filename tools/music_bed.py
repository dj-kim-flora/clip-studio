#!/usr/bin/env python3
"""Level a music bed and write its ducking curve for a composition.

    python3 tools/music_bed.py <music.mp3> <voice.wav> <lead_seconds> <duration_seconds> <out_name>

- public/music/<out_name>.wav : the bed at -24 LUFS by one fixed gain (48 kHz stereo)
- public/music/<out_name>.json: one gain per 30 fps film frame. The voice starts at <lead_seconds> in the film.
  Under speech the bed drops 7 dB (attack 0.1 s, release 0.7 s so it never pumps between words); before the voice
  (the silent cold open) it sits 2.5 dB higher; it fades in over the first 1.8 s and out over the last 1.2 s.
"""
import json, math, os, struct, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ff import FF
FPS = 30

def main():
    music, voice, lead, dur, name = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
    out_wav = os.path.join(ROOT, 'public', 'music', f'{name}.wav')
    # one fixed gain to -24 LUFS (single-pass loudnorm is dynamic: it rides the level of the music)
    meas = subprocess.run([FF, '-hide_banner', '-nostats', '-i', music, '-af', 'loudnorm=I=-24:TP=-3:LRA=7:print_format=json',
                           '-f', 'null', '-'], capture_output=True, text=True).stderr
    m = json.loads(meas[meas.rindex('{'):meas.rindex('}') + 1])
    subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-i', music, '-af', f"volume={-24 - float(m['input_i']):.2f}dB,aresample=48000",
                    '-ac', '2', '-c:a', 'pcm_s16le', out_wav], check=True)
    # voice loudness per film frame (mono 8 kHz is plenty for an envelope)
    raw = subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-i', voice, '-ac', '1', '-ar', '8000', '-f', 's16le', '-'],
                         capture_output=True, check=True).stdout
    n = len(raw) // 2; x = struct.unpack('<%dh' % n, raw); per = 8000 // FPS
    frames = int(round(dur * FPS)); gains = []; env = 0.0
    a_att, a_rel = 1 - math.exp(-1 / (0.1 * FPS)), 1 - math.exp(-1 / (0.7 * FPS))
    def speaking(f):
        vt = f / FPS - lead
        if vt < 0: return 0.0
        i0 = int(vt * 8000); seg = x[i0:i0 + per]
        if not seg: return 0.0
        rms = math.sqrt(sum(v * v for v in seg) / len(seg)) / 32768
        return 1.0 if 20 * math.log10(rms + 1e-9) > -40 else 0.0
    flags = [speaking(f) for f in range(frames)]
    first = next((f / FPS for f, v in enumerate(flags) if v), dur)   # the first word
    for f in range(frames):
        t = f / FPS; speech = flags[f]
        env += (speech - env) * (a_att if speech > env else a_rel)
        g = 10 ** (-7 * env / 20)
        g *= 10 ** ((2.5 * max(0.0, min(1.0, (first - t) / 0.8))) / 20)   # a little fuller before the first word
        g *= min(1.0, max(0.0, (t - 0.1) / 1.8)) * min(1.0, max(0.0, (dur - t) / 1.2))
        gains.append(round(g, 4))
    json.dump(gains, open(os.path.join(ROOT, 'public', 'music', f'{name}.json'), 'w'))
    # bake the curve into the audio (a per-frame volume callback turns into an ffmpeg expression too long to render)
    import array, wave
    w = wave.open(out_wav, 'rb'); sr = w.getframerate(); ch = w.getnchannels()
    pcm = array.array('h', w.readframes(min(w.getnframes(), int(dur * sr)))); w.close()
    nfr = len(pcm) // ch
    for i in range(nfr):
        fpos = i * FPS / sr; f0 = int(fpos); fr = fpos - f0
        g0 = gains[min(f0, frames - 1)]; g1 = gains[min(f0 + 1, frames - 1)]; g = g0 + (g1 - g0) * fr
        for c in range(ch):
            v = int(pcm[i * ch + c] * g)
            pcm[i * ch + c] = 32767 if v > 32767 else -32768 if v < -32768 else v
    ducked = os.path.join(ROOT, 'public', 'music', f'{name}-ducked.wav')
    o = wave.open(ducked, 'wb'); o.setnchannels(ch); o.setsampwidth(2); o.setframerate(sr); o.writeframes(pcm.tobytes()); o.close()
    print(f'{out_wav}: {len(gains)} frames, ducked {sum(1 for g in gains if g < 0.6)} frames -> {ducked}')

if __name__ == '__main__':
    main()
