"""Locate ffmpeg for the kit's tools: $FFMPEG, then `ffmpeg` on PATH, then the one bundled with the imageio-ffmpeg
Python package (`pip3 install imageio-ffmpeg`). Remotion's own ffmpeg can't do the `-f null` measuring passes."""
import os, shutil, subprocess

def find():
    for c in (os.environ.get('FFMPEG'), shutil.which('ffmpeg')):
        if c and os.path.exists(c):
            return c
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    raise SystemExit('ffmpeg not found. Install it (brew install ffmpeg) or run `pip3 install imageio-ffmpeg`, '
                     'or point FFMPEG at a binary.')

FF = find()

def aac_encoder():
    """AudioToolbox AAC when this ffmpeg has it (macOS): ffmpeg's native aac adds ~2 dB of true-peak overshoot."""
    out = subprocess.run([FF, '-hide_banner', '-encoders'], capture_output=True, text=True).stdout
    return 'aac_at' if ' aac_at ' in out else 'aac'
