// Geometry and text measuring shared by the clip components. Everything is designed on a 1080 px short side and scaled by `u`.
export type Zones = {u: number; w: number; h: number; side: number; top: number; bottom: number; social: boolean};

/** `u` scales design px (1080 short side) to the frame. With the social safe zone, the top 12% and the bottom 22% stay clear. */
export function zones(width: number, height: number, safeZone: 'social' | 'none' | null | undefined): Zones {
  const social = safeZone !== 'none';
  return {u: Math.min(width, height) / 1080, w: width, h: height, side: width * 0.07,
    top: height * (social ? 0.12 : 0.05), bottom: height * (social ? 0.78 : 0.94), social};
}

let ctx: CanvasRenderingContext2D | null | undefined;
const cache = new Map<string, number>();
/** width in px of a string in a css font; uses a canvas (fonts are loaded before the first frame), with a rough guess as fallback */
export function measure(text: string, px: number, family: string, weight: number | string = 400, style = 'normal'): number {
  const key = `${style}|${weight}|${px}|${family}|${text}`;
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  if (ctx === undefined) {
    try { ctx = document.createElement('canvas').getContext('2d'); } catch { ctx = null; }
  }
  let w: number;
  if (ctx) { ctx.font = `${style} ${weight} ${px}px ${family}`; w = ctx.measureText(text).width; } else w = text.length * px * 0.56;
  cache.set(key, w);
  return w;
}

/** greedy line breaking of `words` into lines no wider than maxW */
export function wrap(words: string[], maxW: number, width: (s: string) => number): string[][] {
  const lines: string[][] = [[]];
  const space = width(' ');
  let used = 0;
  for (const w of words) {
    const ww = width(w);
    const cur = lines[lines.length - 1];
    if (cur.length && used + space + ww > maxW) { lines.push([w]); used = ww; } else { cur.push(w); used += (cur.length > 1 ? space : 0) + ww; }
  }
  return lines;
}
