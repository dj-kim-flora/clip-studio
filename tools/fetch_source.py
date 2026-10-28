#!/usr/bin/env python3
"""Bring a recording into the kit: download a link, or link a local file. The original is never modified.

    python3 tools/fetch_source.py <url-or-path> <source-id> [--copy]

Writes source/<source-id>/original.<ext> and prints the next command.
  link        yt-dlp downloads the best video up to 1080p (YouTube, Vimeo, X, TikTok and many more) as mp4 when possible.
              Only download what you own or have the right to reuse.
  local file  a symlink to the file (no second copy on disk); --copy makes a real copy instead.
source-id: letters, digits, dot, dash, underscore (for example podcast-ep12).
"""
import os, re, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTS = ('.mp4', '.mov', '.mkv', '.webm', '.m4v', '.mp3', '.m4a', '.wav', '.aac', '.flac', '.ogg', '.opus')


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 2:
        raise SystemExit(__doc__)
    where, sid = args
    if not re.fullmatch(r'[A-Za-z0-9._-]+', sid):
        raise SystemExit('The source id may only use letters, digits, dot, dash and underscore (for example podcast-ep12).')
    out_dir = os.path.join(ROOT, 'source', sid)
    existing = [f for f in (os.listdir(out_dir) if os.path.isdir(out_dir) else []) if f.startswith('original.')]
    if existing:
        print(f'source/{sid}/{existing[0]} is already here. Nothing to fetch.')
        print(f'Next: python3 tools/prepare_source.py source/{sid}/{existing[0]} {sid}')
        return
    is_url = bool(re.match(r'^https?://', where))
    if not is_url and not os.path.isfile(os.path.abspath(os.path.expanduser(where))):
        raise SystemExit(f'I cannot find a file at {os.path.abspath(os.path.expanduser(where))}. Check the path (drag the file into the terminal to paste it).')
    os.makedirs(out_dir, exist_ok=True)
    if is_url:
        tool = shutil.which('yt-dlp')
        if not tool:
            raise SystemExit('Downloading a link needs yt-dlp, which is not installed. Install it with:  brew install yt-dlp\n'
                             'then run this again. (Or download the video yourself and give me the file path instead.)')
        print('Downloading (up to 1080p)…')
        r = subprocess.run([tool, '--no-playlist', '-f', 'bv*[height<=1080]+ba/b[height<=1080]/b', '--merge-output-format', 'mp4',
                            '-o', os.path.join(out_dir, 'original.%(ext)s'), where], text=True)
        got = [f for f in os.listdir(out_dir) if f.startswith('original.') and not f.endswith(('.part', '.ytdl'))]
        if r.returncode != 0 or not got:
            raise SystemExit('The download did not work. Check that the link opens in a browser and is public (private, '
                             'members-only or age-gated videos need a downloaded file instead). Try  brew upgrade yt-dlp  if it '
                             'used to work.')
        dest = os.path.join(out_dir, got[0])
        print(f'Saved source/{sid}/{got[0]}')
    else:
        path = os.path.abspath(os.path.expanduser(where))
        if not os.path.isfile(path):
            raise SystemExit(f'I cannot find a file at {path}. Check the path (drag the file into the terminal to paste it).')
        ext = os.path.splitext(path)[1].lower()
        if ext not in EXTS:
            print(f'Note: {ext or "this file"} is not a usual video or audio type; I will still try.')
        dest = os.path.join(out_dir, 'original' + (ext or '.mp4'))
        if '--copy' in sys.argv:
            shutil.copy2(path, dest); print(f'Copied to source/{sid}/{os.path.basename(dest)}')
        else:
            try:
                os.symlink(path, dest); print(f'Linked source/{sid}/{os.path.basename(dest)} -> {path} (the original stays where it is)')
            except OSError:
                shutil.copy2(path, dest); print(f'Could not link, copied to source/{sid}/{os.path.basename(dest)}')
    print(f'Next: python3 tools/prepare_source.py source/{sid}/{os.path.basename(dest)} {sid}')


if __name__ == '__main__':
    main()
