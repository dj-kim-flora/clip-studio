#!/usr/bin/env python3
"""Get a recording (any video or audio file) ready to cut.

    python3 tools/prepare_source.py <recording> <sourceId> [--every 20] [--no-transcribe]

Writes source/<sourceId>/:
  audio16k.wav     mono 16 kHz analysis audio (every cut decision is measured on this)
  transcript.json  on-device transcript with word timings (tools/transcribe)
  transcript.txt   the same, one line per segment with [h:mm:ss] stamps, for reading and searching
  sheets/          contact sheets, one frame every --every seconds, to find speakers, screen shares and results
                   (video files only: an audio-only file gets no sheets)
  info.json        duration, frame size, fps, audio channels, whether there is video
Nothing here edits or uploads the recording. Steps that already exist are skipped, so it is safe to re-run.
--no-transcribe stops after the audio, info and sheets (use it when you bring your own transcript.json).
"""
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ff import FF
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def hms(t):
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{int(t % 60):02d}"

def main():
    if len(sys.argv) < 3 or sys.argv[1].startswith('-'):
        raise SystemExit(__doc__)
    src, sid = os.path.abspath(sys.argv[1]), sys.argv[2]
    if not os.path.exists(src):
        raise SystemExit(f'I cannot find {src}. Check the path (drag the file into the terminal to paste it).')
    every = float(sys.argv[sys.argv.index('--every') + 1]) if '--every' in sys.argv else 20.0
    out = os.path.join(ROOT, 'source', sid); os.makedirs(os.path.join(out, 'sheets'), exist_ok=True)
    probe = subprocess.run([FF, '-hide_banner', '-i', src], capture_output=True, text=True).stderr
    dur = re.search(r'Duration: (\d+):(\d+):([\d.]+)', probe)
    vline = re.search(r'Stream #\S+.*: Video: .*', probe)
    has_video = bool(vline) and 'attached pic' not in vline.group(0)
    size = re.search(r', (\d{3,5})x(\d{3,5})[, \[]', vline.group(0)) if has_video else None
    fps = re.search(r'([\d.]+) fps', vline.group(0)) if has_video else None
    if not re.search(r'Stream #\S+.*: Audio:', probe):
        raise SystemExit('This file has no audio track, so there is nothing to transcribe or cut by. Try another file.')
    ch = 'stereo' if 'stereo' in probe else 'mono' if 'mono' in probe else '?'
    seconds = int(dur[1]) * 3600 + int(dur[2]) * 60 + float(dur[3]) if dur else None
    info = {'source': src, 'seconds': seconds, 'video': has_video, 'size': [int(size[1]), int(size[2])] if size else None,
            'fps': float(fps[1]) if fps else None, 'audio': ch}
    json.dump(info, open(os.path.join(out, 'info.json'), 'w'), indent=1)
    print(f"{sid}: {hms(seconds or 0)}, {info['size'] or 'audio only'}, {info['fps'] or '-'} fps, {ch} audio")
    wav = os.path.join(out, 'audio16k.wav')
    if not os.path.exists(wav):
        subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-i', src, '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', wav], check=True)
        print('  audio16k.wav written')
    tj = os.path.join(out, 'transcript.json')
    if not os.path.exists(tj) and '--no-transcribe' not in sys.argv:
        tr = os.path.join(ROOT, 'tools', 'transcribe')
        print('  transcribing on this computer (roughly 1 minute per 90 minutes of audio with Apple\'s transcriber; Whisper is slower)…')
        r = subprocess.run([tr, wav, tj], capture_output=True, text=True)
        if r.returncode != 0 or not os.path.exists(tj):
            raise SystemExit('transcription failed: ' + (r.stderr or '')[-800:] +
                             '\nThe Apple transcriber (tools/transcribe.apple-bin) needs macOS 26 or newer. On older macOS the kit falls back to '
                             'mlx-whisper in .venv (installed by  bash setup.sh ; the model, about 1.6 GB, downloads on first use). '
                             'Run  bash setup.sh  and try again, rebuild the Apple one with  bash tools/build-transcribe.sh , or write '
                             'source/<id>/transcript.json yourself in this shape: [{"s","e","text","words":[{"t","s","e"}]}].')
    if os.path.exists(tj):
        segs = json.load(open(tj))
        with open(os.path.join(out, 'transcript.txt'), 'w') as f:
            for s in segs:
                f.write(f"[{hms(s['s'])}] {s['text'].strip()}\n")
        print(f"  transcript: {len(segs)} segments, {sum(len(s['words']) for s in segs)} words -> transcript.txt")
    if not has_video:
        print('  audio-only file: no contact sheets')
        return
    # contact sheets: 4x4 frames per sheet, stamped with the source time (PIL: this ffmpeg build may have no drawtext)
    import glob, tempfile
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype(os.path.join(ROOT, 'public', 'brand', 'geist.ttf'), 22)
    except Exception:
        font = ImageFont.load_default()
    tmp = tempfile.mkdtemp()
    subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-i', src, '-vf', f"fps=1/{every},scale=480:-2",
                    '-fps_mode', 'vfr', os.path.join(tmp, 'f-%05d.jpg')], check=True)
    frames = sorted(glob.glob(os.path.join(tmp, 'f-*.jpg')))
    for n in range(0, len(frames), 16):
        tiles = [Image.open(f) for f in frames[n:n + 16]]; w, h = tiles[0].size
        sheet = Image.new('RGB', (w * 4, h * 4))
        for j, im in enumerate(tiles):
            d = ImageDraw.Draw(im); label = hms((n + j) * every)
            d.rectangle([4, 4, 12 + d.textlength(label, font=font), 34], fill=(0, 0, 0)); d.text((8, 6), label, font=font, fill=(255, 255, 255))
            sheet.paste(im, ((j % 4) * w, (j // 4) * h))
        sheet.save(os.path.join(out, 'sheets', f'sheet-{n // 16 + 1:03d}.jpg'), quality=85)
    print(f"  contact sheets -> source/{sid}/sheets/ (one frame every {every:g} s)")

if __name__ == '__main__':
    main()
