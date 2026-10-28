#!/usr/bin/env python3
"""Propose a colour palette (public/brand/brand.json) from reference media, or from colours you already have.

    python3 tools/brand_from_media.py <file-or-folder>... [--out public/brand/brand.json] [--dry] [--force] [--name Acme]
    python3 tools/brand_from_media.py --from-hex "#111111,#FAFAFA,#FF5A36" [--font "Inter"] [--font-file Inter.ttf]
                                      [--logo logo.png] [--name Acme] [--out ...] [--dry] [--force]

Media mode: looks at images and video frames (6 per video, sampled with ffmpeg), finds the dominant colours (median cut),
decides dark or light theme, and proposes background, ink, muted, accent, accentInk and accentFill so the text stays readable
(accent against the background is at least 3:1, text colours at least 4.5:1).
--from-hex: your own colours. One colour = accent. Two = background, accent. Three = background, ink, accent. Four adds muted.
            The rest of the palette is derived. --font sets the font family name (a system font or one you add with
            --font-file, which is copied into public/brand/). --logo copies a logo into public/brand/ and sets logo.mark.

Writes a draft: other brand.json fields (fonts, logo, glossary...) are kept; source becomes "reference-media" or
"guidelines". Also writes _work/brand/palette.png (swatches with hex labels) to look at. An existing brand.json is never
overwritten without --force: the draft goes to brand.draft.json beside it instead. --dry prints and writes nothing.
"""
import argparse, colorsys, glob, json, os, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brand
from ff import FF
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tif', '.tiff')
VID = ('.mp4', '.mov', '.mkv', '.webm', '.m4v', '.avi')


# ------------------------------------------------------------------ colour maths
def lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def lum(rgb):
    r, g, b = rgb
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def hls(rgb):
    h, l, s = colorsys.rgb_to_hls(*(v / 255.0 for v in rgb))
    return h, l, s


def from_hls(h, l, s):
    return tuple(round(v * 255) for v in colorsys.hls_to_rgb(h, max(0, min(1, l)), max(0, min(1, s))))


def mix(a, b, t):
    """t = 0 gives a, t = 1 gives b."""
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def dist(a, b):
    return sum((a[i] - b[i]) ** 2 for i in range(3)) ** 0.5


def hexs(rgb):
    return brand.rgb_to_hex(rgb)


def name_of(rgb):
    h, l, s = hls(rgb)
    if l < 0.08:
        return 'near-black' if s < 0.25 else 'very dark ' + hue_name(h)
    if l > 0.93:
        return 'white' if s < 0.3 else 'very pale ' + hue_name(h)
    if s < 0.10:
        return 'grey' if 0.25 < l < 0.75 else ('dark grey' if l <= 0.25 else 'light grey')
    tone = 'dark ' if l < 0.28 else 'light ' if l > 0.72 else ''
    return tone + hue_name(h)


def hue_name(h):
    d = h * 360
    for top, nm in ((15, 'red'), (40, 'orange'), (65, 'yellow'), (160, 'green'), (190, 'teal'), (250, 'blue'),
                    (290, 'purple'), (335, 'pink'), (361, 'red')):
        if d < top:
            return nm
    return 'red'


def ensure_contrast(fg, bg, need, toward):
    """Shift fg's lightness (keeping hue) until it has `need`:1 against bg; toward = +1 lighter, -1 darker."""
    h, l, s = hls(fg)
    for _ in range(60):
        if contrast(fg, bg) >= need:
            break
        l += 0.02 * toward
        if not 0 <= l <= 1:
            l = max(0.0, min(1.0, l))
            fg = from_hls(h, l, s)
            break
        fg = from_hls(h, l, s)
    return fg


# ------------------------------------------------------------------ reading media
def collect_images(inputs, tmp):
    files = []
    for p in inputs:
        p = os.path.abspath(os.path.expanduser(p))
        if os.path.isdir(p):
            files += sorted(f for f in glob.glob(os.path.join(p, '**', '*'), recursive=True)
                            if f.lower().endswith(IMG + VID))
        elif os.path.exists(p):
            files.append(p)
        else:
            raise SystemExit(f'I cannot find {p}. Check the path (drag the file into the terminal to paste it).')
    if not files:
        raise SystemExit('No images or videos found there. Give me a picture, a video, or a folder of them.')
    out, vids = [], 0
    for f in files[:40]:
        if f.lower().endswith(VID):
            vids += 1
            probe = subprocess.run([FF, '-hide_banner', '-i', f], capture_output=True, text=True).stderr
            import re
            m = re.search(r'Duration: (\d+):(\d+):([\d.]+)', probe)
            dur = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else 10.0
            for k in range(6):
                t = dur * (k + 0.5) / 6
                p = os.path.join(tmp, f'v{vids}-{k}.png')
                subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-ss', f'{t:.2f}', '-i', f, '-frames:v', '1',
                                '-vf', 'scale=320:-2', p])
                if os.path.exists(p):
                    out.append(p)
        else:
            out.append(f)
    if not out:
        raise SystemExit('I could not read any pictures from those files.')
    return out, len(files)


def clusters_from(images):
    """[(rgb, share)] biggest first, via PIL median cut on a mosaic of the pictures."""
    from PIL import Image
    tiles = []
    for p in images:
        try:
            im = Image.open(p).convert('RGB')
        except Exception:
            continue
        tiles.append(im.resize((96, 96)))     # squashed to a square: only the colour counts, not the shape
    if not tiles:
        raise SystemExit('I could not open any of those pictures.')
    cols = min(8, len(tiles)); rows = -(-len(tiles) // cols)
    mosaic = Image.new('RGB', (cols * 96, rows * 96), (0, 0, 0))
    for k, im in enumerate(tiles):
        mosaic.paste(im, ((k % cols) * 96, (k // cols) * 96))
    # count only real picture pixels: paint the unused mosaic cells with the first tile instead of black
    for k in range(len(tiles), cols * rows):
        mosaic.paste(tiles[k % len(tiles)], ((k % cols) * 96, (k // cols) * 96))
    q = mosaic.quantize(colors=12, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    counts = sorted(q.getcolors(), reverse=True)
    total = float(sum(c for c, _ in counts))
    cl = [((pal[i * 3], pal[i * 3 + 1], pal[i * 3 + 2]), c / total) for c, i in counts]
    merged = []
    for rgb, share in cl:                       # merge near-duplicates
        for k, (r2, s2) in enumerate(merged):
            if dist(rgb, r2) < 28:
                w = s2 + share
                merged[k] = (tuple(round((r2[i] * s2 + rgb[i] * share) / w) for i in range(3)), w)
                break
        else:
            merged.append((rgb, share))
    return sorted(merged, key=lambda c: -c[1])


# ------------------------------------------------------------------ palette choice
def choose(cl):
    mean_lum = sum(lum(c) * s for c, s in cl) / sum(s for _, s in cl)
    dark = mean_lum < 0.30
    big = [c for c in cl if c[1] >= 0.06] or cl
    notes = []
    if dark:
        bg = min(big, key=lambda c: lum(c[0]))[0]
        h, l, s = hls(bg)
        if l > 0.10:
            bg = from_hls(h, 0.07, min(s, 0.5)); notes.append('background darkened a little for contrast')
        ink = (245, 245, 240)
    else:
        bg = max(big, key=lambda c: lum(c[0]))[0]
        h, l, s = hls(bg)
        if l < 0.94:
            bg = from_hls(h, 0.96, min(s, 0.5)); notes.append('background lightened a little for contrast')
        ink = (20, 20, 20)
    # accent: the most colourful cluster with enough area
    cand = [(c, sh) for c, sh in cl if hls(c)[2] >= 0.30 and 0.18 < hls(c)[1] < 0.85 and sh >= 0.01 and dist(c, bg) > 60]
    default_accent = brand.hex_to_rgb(brand.DEFAULTS['colors']['accent'])
    if cand:
        accent = max(cand, key=lambda x: hls(x[0])[2] * (0.6 + min(0.4, x[1] * 2)))[0]
    else:
        accent = default_accent; notes.append('no strong colour found in the media, so the default blue accent is kept')
    accent = ensure_contrast(accent, bg, 3.0, +1 if dark else -1)
    if dark:
        accent_ink = ensure_contrast(mix(accent, (255, 255, 255), 0.45), bg, 4.5, +1)
        fill = mix(bg, accent, 0.12)
        panel = mix(bg, (255, 255, 255), 0.05)
        border = 'rgba(255,255,255,0.12)'
    else:
        accent_ink = ensure_contrast(mix(accent, (0, 0, 0), 0.35), bg, 4.5, -1)
        fill = mix(bg, accent, 0.10)
        panel = mix(bg, (0, 0, 0), 0.04)
        border = 'rgba(0,0,0,0.12)'
    ink = ensure_contrast(ink, bg, 10, +1 if dark else -1)
    muted = ensure_contrast(mix(ink, bg, 0.45), bg, 4.5, +1 if dark else -1)
    colors = {'background': hexs(bg), 'ink': hexs(ink), 'muted': hexs(muted), 'accent': hexs(accent),
              'accentInk': hexs(accent_ink), 'accentFill': hexs(fill), 'panel': hexs(panel), 'panelBorder': border}
    return colors, dark, notes


def from_hex_list(spec):
    vals = []
    for part in spec.split(','):
        part = part.strip()
        if not part:
            continue
        try:
            vals.append(brand.hex_to_rgb(part))
        except ValueError:
            raise SystemExit(f'"{part}" is not a colour. Use hex like #FF5A36.')
    if not vals:
        raise SystemExit('Give me at least one colour, for example --from-hex "#111111,#FAFAFA,#FF5A36".')
    default = brand.hex_to_rgb(brand.DEFAULTS['colors']['background'])
    if len(vals) == 1:
        bg, ink, accent, muted = default, None, vals[0], None
    elif len(vals) == 2:
        bg, ink, accent, muted = vals[0], None, vals[1], None
    else:
        bg, ink, accent = vals[0], vals[1], vals[2]
        muted = vals[3] if len(vals) > 3 else None
    dark = lum(bg) < 0.30
    if ink is None:
        ink = (245, 245, 240) if dark else (20, 20, 20)
    ink = ensure_contrast(ink, bg, 7, +1 if dark else -1)
    accent = ensure_contrast(accent, bg, 3.0, +1 if dark else -1)
    muted = muted or mix(ink, bg, 0.45)
    muted = ensure_contrast(muted, bg, 4.5, +1 if dark else -1)
    if dark:
        accent_ink = ensure_contrast(mix(accent, (255, 255, 255), 0.45), bg, 4.5, +1)
        fill, panel, border = mix(bg, accent, 0.12), mix(bg, (255, 255, 255), 0.05), 'rgba(255,255,255,0.12)'
    else:
        accent_ink = ensure_contrast(mix(accent, (0, 0, 0), 0.35), bg, 4.5, -1)
        fill, panel, border = mix(bg, accent, 0.10), mix(bg, (0, 0, 0), 0.04), 'rgba(0,0,0,0.12)'
    colors = {'background': hexs(bg), 'ink': hexs(ink), 'muted': hexs(muted), 'accent': hexs(accent),
              'accentInk': hexs(accent_ink), 'accentFill': hexs(fill), 'panel': hexs(panel), 'panelBorder': border}
    return colors, dark


# ------------------------------------------------------------------ swatches
def swatch_png(colors, cl, path):
    from PIL import Image, ImageDraw, ImageFont
    def font(n):
        try:
            return ImageFont.load_default(size=n)
        except TypeError:
            return ImageFont.load_default()
    W, pad = 1200, 24
    roles = ['background', 'ink', 'muted', 'accent', 'accentInk', 'accentFill', 'panel']
    bg = brand.hex_to_rgb(colors['background']); ink = brand.hex_to_rgb(colors['ink'])
    im = Image.new('RGB', (W, 560 if cl else 460), bg)
    d = ImageDraw.Draw(im)
    d.text((pad, pad), 'Proposed palette', fill=ink, font=font(28))
    sw = (W - pad * 2) // len(roles)
    for k, r in enumerate(roles):
        x = pad + k * sw
        rgb = brand.hex_to_rgb(colors[r])
        d.rectangle([x, 80, x + sw - 12, 220], fill=rgb, outline=(128, 128, 128))
        d.text((x, 230), r, fill=ink, font=font(18)); d.text((x, 256), colors[r].upper(), fill=ink, font=font(18))
    # sample: how a caption pill and headline would look
    acc, accink, fill = (brand.hex_to_rgb(colors[k]) for k in ('accent', 'accentInk', 'accentFill'))
    d.text((pad, 310), 'Sample headline in the ink colour', fill=ink, font=font(30))
    d.rounded_rectangle([pad, 360, pad + 360, 410], radius=12, fill=fill, outline=acc, width=2)
    d.text((pad + 18, 372), 'Sample accent label', fill=accink, font=font(24))
    d.text((pad + 400, 372), 'Muted secondary text', fill=brand.hex_to_rgb(colors['muted']), font=font(24))
    if cl:
        d.text((pad, 440), 'Dominant colours found in the media (share of pixels)', fill=ink, font=font(18))
        x = pad
        for rgb, share in cl[:10]:
            w = max(60, int((W - pad * 2) * share * 1.0))
            w = min(w, 220)
            d.rectangle([x, 470, x + w - 6, 520], fill=rgb, outline=(128, 128, 128))
            d.text((x, 526), f'{hexs(rgb)} {share * 100:.0f}%', fill=ink, font=font(14))
            x += w
            if x > W - pad - 60:
                break
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description='Propose a brand palette from reference media or hex colours.')
    ap.add_argument('inputs', nargs='*', help='images, videos or folders of them')
    ap.add_argument('--from-hex', help='"#background,#ink,#accent" (1 to 4 colours)')
    ap.add_argument('--font', help='font family name for display and body')
    ap.add_argument('--font-file', help='a font file to copy into public/brand/')
    ap.add_argument('--logo', help='a logo image to copy into public/brand/ (sets logo.mark)')
    ap.add_argument('--name', help='brand name')
    ap.add_argument('--out', default=os.path.join(ROOT, 'public', 'brand', 'brand.json'))
    ap.add_argument('--dry', action='store_true', help='print the proposal, write nothing')
    ap.add_argument('--force', action='store_true', help='overwrite an existing brand.json')
    a = ap.parse_args()
    if not a.inputs and not a.from_hex:
        raise SystemExit('Give me reference media (pictures, videos, a folder) or --from-hex "#111111,#FAFAFA,#FF5A36".')
    out = os.path.abspath(a.out)
    cl, notes, nfiles = [], [], 0
    if a.from_hex:
        colors, dark = from_hex_list(a.from_hex)
        source = 'guidelines'
    else:
        tmp = tempfile.mkdtemp()
        images, nfiles = collect_images(a.inputs, tmp)
        cl = clusters_from(images)
        colors, dark, notes = choose(cl)
        source = 'reference-media'
        shutil.rmtree(tmp, ignore_errors=True)
    existing = brand._read(out) or brand._read(os.path.join(os.path.dirname(out), 'brand.default.json')) or {}
    draft = json.loads(json.dumps(existing)) if existing else brand.load()
    draft.setdefault('colors', {}).update(colors)
    draft['source'] = source
    if a.name:
        draft['name'] = a.name
    fonts_dir = os.path.dirname(out)
    if a.font or a.font_file:
        fam = a.font or os.path.splitext(os.path.basename(a.font_file))[0]
        files = []
        if a.font_file:
            if not os.path.exists(a.font_file):
                raise SystemExit(f'I cannot find the font file {a.font_file}.')
            if not a.dry:
                os.makedirs(fonts_dir, exist_ok=True)
                shutil.copyfile(a.font_file, os.path.join(fonts_dir, os.path.basename(a.font_file)))
            files = [{'file': os.path.basename(a.font_file), 'weight': '100 900', 'style': 'normal'}]
        fb = {'display': 'Georgia, serif', 'body': 'system-ui, sans-serif'}
        draft['fonts'] = {k: {'family': fam, 'files': files, 'fallback': (draft.get('fonts', {}).get(k, {}) or {}).get('fallback', fb[k])}
                          for k in ('display', 'body')}
    if a.logo:
        if not os.path.exists(a.logo):
            raise SystemExit(f'I cannot find the logo file {a.logo}.')
        if not a.dry:
            os.makedirs(fonts_dir, exist_ok=True)
            shutil.copyfile(a.logo, os.path.join(fonts_dir, os.path.basename(a.logo)))
        draft.setdefault('logo', {})['mark'] = os.path.basename(a.logo)
    # say it in plain words
    c = colors
    print(('Looked at %d file(s). ' % nfiles if nfiles else 'Using the colours you gave. ') +
          f"This is a {'dark' if dark else 'light'} theme.")
    for key, label in (('background', 'Background'), ('ink', 'Text'), ('muted', 'Quiet text'), ('accent', 'Accent (highlights, active caption word)'),
                       ('accentInk', 'Accent text'), ('accentFill', 'Label fill')):
        rgb = brand.hex_to_rgb(c[key])
        print(f"  {label}: {name_of(rgb)}, {c[key].upper()}")
    bg = brand.hex_to_rgb(c['background'])
    print(f"  Readability: text {contrast(brand.hex_to_rgb(c['ink']), bg):.1f}:1, accent {contrast(brand.hex_to_rgb(c['accent']), bg):.1f}:1, "
          f"accent text {contrast(brand.hex_to_rgb(c['accentInk']), bg):.1f}:1 against the background (3:1 or more is fine for highlights).")
    for n in notes:
        print(f'  note: {n}')
    if a.dry:
        print('Dry run: nothing written.')
        return
    pal = os.path.join(ROOT, '_work', 'brand', 'palette.png')
    swatch_png(c, cl, pal)
    print(f'Swatches: {os.path.relpath(pal, ROOT)} (open it to see the palette)')
    target = out
    if os.path.exists(out) and not a.force:
        target = os.path.join(os.path.dirname(out), 'brand.draft.json')
        print(f'{os.path.relpath(out, ROOT)} already exists, so I did not overwrite it.')
    os.makedirs(os.path.dirname(target), exist_ok=True)
    json.dump(draft, open(target, 'w'), indent=2)
    print(f'Wrote {os.path.relpath(target, ROOT)}.' +
          (f' To use it: cp {os.path.relpath(target, ROOT)} {os.path.relpath(out, ROOT)}  (or run again with --force).' if target != out else ''))


if __name__ == '__main__':
    main()
