// Pixel dithering: an image (or a line of type) arrives as ordered-dither pixels that switch on outward from a
// centre, burn a little brighter the moment they are born, glow, then sharpen step by step into the real thing. Drawn on a
// canvas each frame: the source is averaged down to a grid of `block`-px cells, each cell is on or off against a 4x4
// Bayer threshold, and the on-cells keep their own colour (or a single ink colour for type).
import React, {useEffect, useLayoutEffect, useRef, useState} from 'react';
import {continueRender, delayRender, staticFile, useCurrentFrame} from 'remotion';
import {COLORS, FONT_DISPLAY} from './theme';

const IMG: Record<string, HTMLImageElement> = {};
const getImage = (src: string) => {
  if (!IMG[src]) { const im = new Image(); im.src = staticFile(src); IMG[src] = im; }
  return IMG[src];
};
const isLoaded = (src: string) => { const im = IMG[src]; return !!im && im.complete && im.naturalWidth > 0; };
/** Optional module-level preload (holds the whole render until the image has decoded). Dither also loads on its own. */
export const preloadImage = (src: string) => {
  if (IMG[src]) return;
  const handle = delayRender(`dither image ${src}`);
  const im = getImage(src);
  im.onload = () => continueRender(handle);
  im.onerror = () => continueRender(handle);
};

export type Seg = {t: string; italic?: boolean};
export type TextSpec = {lines: Seg[][]; size: number; lh?: number; color?: string; align?: 'left' | 'center'; family?: string; tracking?: number};
const TEXT: Record<string, HTMLCanvasElement> = {};
function textCanvas(spec: TextSpec, w: number, h: number, dpr: number) {
  const key = JSON.stringify([spec, w, h, dpr]);
  if (TEXT[key]) return TEXT[key];
  const c = document.createElement('canvas'); c.width = Math.round(w * dpr); c.height = Math.round(h * dpr);
  const g = c.getContext('2d')!; const size = spec.size * dpr, lh = (spec.lh ?? 1.05) * size;
  g.fillStyle = spec.color ?? COLORS.ink; g.textBaseline = 'alphabetic';
  (g as unknown as {letterSpacing: string}).letterSpacing = `${(spec.tracking ?? -0.025) * size}px`;
  const font = (it?: boolean) => `${it ? 'italic ' : ''}400 ${size}px ${spec.family ?? FONT_DISPLAY}`;
  spec.lines.forEach((line, li) => {
    const widths = line.map(s => { g.font = font(s.italic); return g.measureText(s.t).width; });
    const total = widths.reduce((a, b) => a + b, 0);
    let x = spec.align === 'center' ? (c.width - total) / 2 : 0; const y = li * lh + size * 0.86;
    line.forEach((s, si) => { g.font = font(s.italic); g.fillText(s.t, x, y); x += widths[si]; });
  });
  TEXT[key] = c;
  return c;
}

const B4 = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5];
const hash = (i: number, j: number) => { let v = Math.imul(i, 374761393) + Math.imul(j, 668265263) | 0; v = Math.imul(v ^ (v >>> 13), 1274126177); return ((v ^ (v >>> 16)) >>> 0) / 4294967295; };
const clamp01 = (v: number) => v < 0 ? 0 : v > 1 ? 1 : v;
const drawCover = (g: CanvasRenderingContext2D, src: CanvasImageSource & {width: number; height: number}, W: number, H: number, sw: number, sh: number) => {
  const s = Math.max(W / sw, H / sh); const dw = sw * s, dh = sh * s;
  g.drawImage(src, (W - dw) / 2, (H - dh) / 2, dw, dh);
};

export type DitherParams = {
  block: number;              // dither cell size, CSS px
  reveal: number;             // 0..1 progress of the reveal (cells switch on outward from the centre)
  cx?: number; cy?: number;   // reveal centre, 0..1 of the box
  gain?: number;              // brightness of the dither
  crisp: number;              // 0..1 crossfade to the real image
  glow: number;               // 0..1 glow
  ink?: [number, number, number];   // single colour for on-cells (type)
  spread?: number;            // how much of the reveal is distance (vs noise)
  fill?: number;              // 0..1: fade the dither threshold out so every covered cell is on (solid mosaic)
  lift?: number;              // colour boost of on-cells (1 = true colour)
  burn?: number;              // extra brightness of just-born cells
};

export function Dither({src, text, x, y, w, h, p, blend, opacity = 1, mask}: {src?: string; text?: TextSpec; x: number; y: number; w: number; h: number; p: DitherParams; blend?: React.CSSProperties['mixBlendMode']; opacity?: number; mask?: string}) {
  // hold this frame until the image has decoded AND been drawn (a canvas painted before the load stays empty)
  const [ready, setReady] = useState(() => !src || isLoaded(src));
  const [handle] = useState(() => (src && !isLoaded(src) ? delayRender(`dither image ${src}`) : null));
  const released = useRef(false);
  useEffect(() => {
    if (!src || ready) return;
    const im = getImage(src); const done = () => setReady(true);
    if (im.complete && im.naturalWidth) done(); else { im.addEventListener('load', done, {once: true}); im.addEventListener('error', done, {once: true}); }
  }, [src, ready]);
  const ref = useRef<HTMLCanvasElement>(null);
  const cell = useRef<HTMLCanvasElement | null>(null);
  const frame = useCurrentFrame();
  const key = JSON.stringify(p);
  useLayoutEffect(() => {
    const c = ref.current; if (!c) return;
    const dpr = window.devicePixelRatio || 1;
    const W = Math.round(w * dpr), H = Math.round(h * dpr);
    if (c.width !== W) c.width = W;
    if (c.height !== H) c.height = H;
    const g = c.getContext('2d')!; g.clearRect(0, 0, W, H);
    let source: (CanvasImageSource & {width: number; height: number}) | null = null; let sw = 0, sh = 0;
    if (src) { const im = getImage(src); if (!im.complete || !im.naturalWidth) return; source = im; sw = im.naturalWidth; sh = im.naturalHeight; }
    else if (text) { const tc = textCanvas(text, w, h, dpr); source = tc; sw = tc.width; sh = tc.height; }
    if (!source) return;
    const pixelsOn = p.crisp < 1 && (p.reveal > 0.001);
    if (p.crisp > 0.001) {
      g.globalAlpha = Math.min(1, p.crisp * 6); g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high';
      drawCover(g, source, W, H, sw, sh);
      if (p.glow > 0.001) {   // a little of the glow stays on the sharp image
        g.globalCompositeOperation = 'lighter'; g.filter = `blur(${14 * dpr}px)`; g.globalAlpha = p.glow * 0.5 * Math.min(1, p.crisp * 6);
        drawCover(g, source, W, H, sw, sh);
        g.filter = 'none'; g.globalCompositeOperation = 'source-over';
      }
    }
    if (pixelsOn) {
      const gw = Math.max(1, Math.ceil(w / p.block)), gh = Math.max(1, Math.ceil(h / p.block));
      const s = cell.current || (cell.current = document.createElement('canvas'));
      if (s.width !== gw) s.width = gw;
      if (s.height !== gh) s.height = gh;
      const sc = s.getContext('2d', {willReadFrequently: true})!;
      sc.clearRect(0, 0, gw, gh); sc.imageSmoothingEnabled = true; sc.imageSmoothingQuality = 'high';
      drawCover(sc, source, gw, gh, sw, sh);
      const img = sc.getImageData(0, 0, gw, gh); const d = img.data;
      const cx = (p.cx ?? 0.5) * gw, cy = (p.cy ?? 0.5) * gh;
      const maxD = Math.hypot(Math.max(cx, gw - cx), Math.max(cy, gh - cy)) || 1;
      const spread = p.spread ?? 0.72, gain = p.gain ?? 1, fill = p.fill ?? 0, liftP = p.lift, burnP = p.burn ?? 0.9;
      for (let j = 0; j < gh; j++) for (let i = 0; i < gw; i++) {
        const o = (j * gw + i) * 4; const a = d[o + 3] / 255;
        const lum = p.ink ? a : ((0.2126 * d[o] + 0.7152 * d[o + 1] + 0.0722 * d[o + 2]) / 255) * a;
        const tau = (Math.hypot(i - cx, j - cy) / maxD) * spread + hash(i, j) * (1 - spread);
        const local = clamp01((p.reveal * 1.3 - tau) / 0.3);
        const th = ((B4[(i & 3) + ((j & 3) << 2)] + 0.5) / 16) * (1 - fill);
        if (local > 0 && lum * gain * local * 1.1 > th) {
          const burn = 1 + (1 - local) * burnP;   // new pixels burn brighter, then settle
          const r = p.ink ? p.ink[0] : d[o], gg = p.ink ? p.ink[1] : d[o + 1], bb = p.ink ? p.ink[2] : d[o + 2];
          const lift = p.ink ? 1 : (liftP ?? 1.15);
          d[o] = Math.min(255, r * lift * burn); d[o + 1] = Math.min(255, gg * lift * burn); d[o + 2] = Math.min(255, bb * lift * burn); d[o + 3] = 255;
        } else d[o + 3] = 0;
      }
      sc.putImageData(img, 0, 0);
      const dw = gw * p.block * dpr, dh = gh * p.block * dpr, ox = (W - dw) / 2, oy = (H - dh) / 2;
      g.imageSmoothingEnabled = false; g.globalAlpha = 1 - p.crisp;
      g.drawImage(s, ox, oy, dw, dh);
      if (p.glow > 0.001) {
        g.globalCompositeOperation = 'lighter'; g.filter = `blur(${Math.max(3, p.block * 1.6) * dpr}px)`; g.globalAlpha = p.glow * (1 - p.crisp);
        g.drawImage(s, ox, oy, dw, dh);
        g.filter = 'none'; g.globalCompositeOperation = 'source-over';
      }
    }
    g.globalAlpha = 1;
    if (handle !== null && ready && !released.current) { released.current = true; continueRender(handle); }
  }, [frame, src, text, x, y, w, h, key, ready]);
  return <canvas ref={ref} style={{position: 'absolute', left: x, top: y, width: w, height: h, mixBlendMode: blend, opacity, maskImage: mask, WebkitMaskImage: mask}}/>;
}
