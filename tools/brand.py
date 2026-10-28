"""Shared brand helper for the kit's Python tools.

Reads public/brand/brand.json (the one source of look and spelling), falling back to brand.default.json and then to
built-in defaults, so a missing or broken file never stops a tool.

    import brand
    brand.glossary()            # ['Acme', 'Acme Studio', ...]
    brand.colors()              # {'background': '#0A0A0A', 'ink': ..., 'accent': ...}
    brand.glossary_fix(text)    # fixes likely mis-hearings of glossary terms in a caption line
    brand.whisper_prompt()      # transcription spelling hint built from the glossary
"""
import difflib, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRAND_DIR = os.path.join(ROOT, 'public', 'brand')

DEFAULTS = {
    'name': None,
    'source': 'default',
    'colors': {
        'background': '#0A0A0A', 'ink': '#F5F5F0', 'muted': '#969696',
        'accent': '#4C8DFF', 'accentInk': '#9CC2FF', 'accentFill': '#101A2E',
        'panel': '#161616', 'panelBorder': 'rgba(255,255,255,0.12)',
    },
    'fonts': {},
    'logo': {'mark': None, 'wordmark': None, 'animated': None},
    'style': {'backdrop': 'dots', 'radius': 16, 'captionStyle': 'pill', 'headlineCase': 'sentence', 'motion': 'punchy'},
    'outro': {'line': '', 'handle': '', 'cta': ''},
    'glossary': [],
    'music': {'default': None},
    'notes': '',
}


def _read(path):
    try:
        with open(path) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def load(path=None):
    """The active brand as a dict. Missing keys come from the built-in defaults; never raises."""
    data = _read(path or os.path.join(BRAND_DIR, 'brand.json'))
    if data is None:
        data = _read(os.path.join(BRAND_DIR, 'brand.default.json')) or {}
    out = json.loads(json.dumps(DEFAULTS))
    for key, val in data.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key].update(val)
        else:
            out[key] = val
    return out


def colors():
    return load()['colors']


def glossary():
    """Correct spellings of names and terms (strings only, blanks dropped)."""
    return [g.strip() for g in load().get('glossary') or [] if isinstance(g, str) and g.strip()]


def hex_to_rgb(h):
    h = h.strip().lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return '#%02X%02X%02X' % tuple(max(0, min(255, int(round(v)))) for v in rgb)


def _norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


def glossary_fix(text, terms=None, cutoff=0.82):
    """Fix likely mis-hearings of glossary terms in a caption line.

    Runs of words are compared with each glossary term (case and punctuation ignored): the same number of words as the
    term, or one more or fewer when the match is very close. A near match (difflib ratio >= cutoff) or a term with the
    wrong capitalisation is replaced by the glossary spelling. Words that are already right and short words are left alone."""
    terms = glossary() if terms is None else terms
    if not terms or not text:
        return text
    parts = re.split(r'(\s+)', text)                     # keep the original spacing and line breaks
    idx = [i for i, p in enumerate(parts) if p and not p.isspace()]
    out, k = list(parts), 0
    while k < len(idx):
        best = None                                       # (ratio, exact-length?, n, term, lead, trail)
        for term in terms:
            nt = _norm(term)
            kt = len(term.split())
            for n in {kt, kt + 1, max(1, kt - 1)}:
                if k + n > len(idx):
                    continue
                span = idx[k:k + n]
                if any(span[j + 1] != span[j] + 2 for j in range(len(span) - 1)):
                    continue                              # words must be neighbours (one space between)
                raw = ''.join(parts[span[0]:span[-1] + 1])
                m = re.match(r"^([^A-Za-z0-9]*)(.*?)([^A-Za-z0-9]*)$", raw, re.S)
                nc = _norm(m.group(2))
                if len(nc) < 4 or abs(len(nt) - len(nc)) > max(1, len(nt) // 5):
                    continue
                r = 1.0 if nt == nc else difflib.SequenceMatcher(a=nc, b=nt).ratio()
                if r < (cutoff if n == kt else 0.93):
                    continue
                cand = (r, n == kt, n, term, m.group(1), m.group(3))
                if best is None or cand[:3] > best[:3]:
                    best = cand
        if best:
            r, _, n, term, lead, trail = best
            span = idx[k:k + n]
            for j in range(span[0], span[-1] + 1):
                out[j] = ''
            out[span[0]] = lead + term + trail
            k += n
        else:
            k += 1
    return ''.join(out)


def whisper_prompt():
    """Spelling hint for the transcriber: env WHISPER_PROMPT wins, else built from the glossary."""
    env = os.environ.get('WHISPER_PROMPT')
    if env:
        return env
    terms = glossary()
    return (', '.join(terms) + '.') if terms else ''
