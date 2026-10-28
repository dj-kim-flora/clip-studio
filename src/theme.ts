// The one place the look comes from: public/brand/brand.json (the user's brand), merged over brand.default.json (a neutral
// default), so a partial brand.json still works. Everything else (premium/*, ui.tsx, clip/*) reads colours, fonts and style
// from here. Nothing outside this file imports the JSON.
import {staticFile} from 'remotion';
import userBrand from '../public/brand/brand.json';
import defaultBrand from '../public/brand/brand.default.json';

export type FontFile = {file: string; weight?: string; style?: string};
export type FontSpec = {family: string; files: FontFile[]; fallback: string};
export type Brand = {
  name: string | null;
  source: string;
  colors: {background: string; ink: string; muted: string; accent: string; accentInk: string; accentFill: string; panel: string; panelBorder: string};
  fonts: {display: FontSpec; body: FontSpec};
  logo: {mark: string | null; wordmark: string | null; animated: string | null};
  style: {backdrop: 'dots' | 'grid' | 'gradient' | 'solid'; radius: number; captionStyle: 'pill' | 'karaoke' | 'plain' | 'box'; headlineCase: 'sentence' | 'upper'; motion: 'calm' | 'punchy'};
  outro: {line: string; handle: string; cta: string};
  glossary: string[];
  music: {default: string | null};
  notes: string;
};

const isObj = (v: unknown): v is Record<string, unknown> => !!v && typeof v === 'object' && !Array.isArray(v);
function merge<T>(base: T, over: unknown): T {
  if (!isObj(base) || !isObj(over)) return (over === undefined || over === null ? base : over) as T;
  const out: Record<string, unknown> = {...base};
  for (const key of Object.keys(over)) out[key] = key in base ? merge((base as Record<string, unknown>)[key], over[key]) : over[key];
  return out as T;
}

export const BRAND: Brand = merge(defaultBrand as unknown as Brand, userBrand);
export const COLORS = BRAND.colors;
export const STYLE = BRAND.style;

// ---------------------------------------------------------------- colour helpers
/** [r, g, b] of a #rgb / #rrggbb / rgb()/rgba() colour; null when it is anything else (named colours, hsl, …) */
export function parseColor(c: string): [number, number, number] | null {
  const s = c.trim();
  const hex = s.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (hex) {
    const h = hex[1].length === 3 ? hex[1].split('').map(x => x + x).join('') : hex[1];
    return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
  }
  const rgb = s.match(/^rgba?\(\s*([\d.]+)[ ,]+([\d.]+)[ ,]+([\d.]+)/i);
  return rgb ? [Math.round(+rgb[1]), Math.round(+rgb[2]), Math.round(+rgb[3])] : null;
}
/** a colour at an alpha. Works for any CSS colour (hex and rgb() are computed, the rest go through color-mix). */
export function rgba(color: string, alpha: number): string {
  const c = parseColor(color);
  const a = Math.max(0, Math.min(1, alpha));
  return c ? `rgba(${c.join(',')},${+a.toFixed(4)})` : `color-mix(in srgb, ${color} ${+(a * 100).toFixed(2)}%, transparent)`;
}
const FALLBACK_ACCENT: [number, number, number] = [76, 141, 255];
export const rgbOf = (color: string, fallback: [number, number, number] = [150, 150, 150]) => parseColor(color) ?? fallback;
/** the accent as an RGB tuple */
export const ACCENT = rgbOf(COLORS.accent, FALLBACK_ACCENT);
/** the accent at an alpha: pills, focus boxes, ticks, progress bar */
export const accent = (a: number) => `rgba(${ACCENT.join(',')},${a})`;
export const INK_RGB = rgbOf(COLORS.ink, [245, 245, 240]);
export const MUTED_RGB = rgbOf(COLORS.muted, [150, 150, 150]);
/** the ink colour at an alpha: hairlines, edges, dividers */
export const inkA = (a: number) => rgba(COLORS.ink, a);

// ---------------------------------------------------------------- fonts
const quote = (family: string) => (/^[\w-]+$/.test(family) ? family : `"${family.replace(/"/g, '')}"`);
const stack = (f: FontSpec) => [quote(f.family), f.fallback].filter(Boolean).join(', ');
/** css font-family for display type (hooks, headlines, outro) and for everything else */
export const FONT_DISPLAY = stack(BRAND.fonts.display);
export const FONT_BODY = stack(BRAND.fonts.body);

/** weight for display type: a variable font (a weight range) is set bold, a static file uses the weight it was declared with */
export const DISPLAY_WEIGHT = (() => {
  const w = BRAND.fonts.display.files?.[0]?.weight ?? '400';
  return /\s/.test(w) ? 700 : parseInt(w, 10) || 400;
})();

const FORMAT: Record<string, string> = {ttf: 'truetype', otf: 'opentype', woff: 'woff', woff2: 'woff2'};
/**
 * Load every font file named in brand.json (any number of files, weights and styles) from public/brand/. A file that is
 * missing or cannot be read is skipped with a console warning, and the fallback family is used instead; this never throws.
 */
export async function loadBrandFonts(): Promise<void> {
  const seen = new Set<string>();
  const jobs: Array<Promise<void>> = [];
  for (const spec of [BRAND.fonts.display, BRAND.fonts.body]) {
    for (const f of spec.files || []) {
      const key = `${spec.family}|${f.file}|${f.weight ?? ''}|${f.style ?? ''}`;
      if (!f.file || seen.has(key)) continue;
      seen.add(key);
      const ext = f.file.split('.').pop()?.toLowerCase() ?? 'ttf';
      const face = new FontFace(spec.family, `url('${staticFile(`brand/${f.file}`)}') format('${FORMAT[ext] ?? 'truetype'}')`,
        {weight: f.weight ?? '400', style: f.style ?? 'normal'});
      jobs.push(face.load().then(loaded => { document.fonts.add(loaded); },
        err => { console.warn(`clip-studio: font file "${f.file}" for "${spec.family}" could not be loaded (${String(err)}); using the fallback font.`); }));
    }
  }
  await Promise.all(jobs);
}

// ---------------------------------------------------------------- motion and paths
/** duration multiplier: punchy = 1, calm = 1.5 (slower, softer entrances) */
export const MOTION = STYLE.motion === 'calm' ? 1.5 : 1;
/** a file in public/brand/ as a staticFile url, or null when the brand has none */
export const brandFile = (name: string | null | undefined) => (name ? staticFile(`brand/${name}`) : null);
export const isVideoFile = (name: string) => /\.(mp4|mov|webm|m4v)$/i.test(name);
