// The premium motion vocabulary every beat shares: motion curves, display type that rises out of a mask, the one uppercase
// body-font voice for labels and notes, the presence pill, the standard 1920x1080 layout, and a clock that turns
// transcript words into film times. See skill/references/motion-language.md for the rules behind each value.
import React from 'react';
import {AbsoluteFill, Easing, interpolate} from 'remotion';
import type {Brief} from '../schema';
import {ACCENT as THEME_ACCENT, COLORS, FONT_BODY, FONT_DISPLAY, MOTION, accent as themeAccent, inkA} from '../theme';

export {MOTION};

// ---------------------------------------------------------------- motion: one entrance curve, one camera curve, one exit curve,
// and a soft sine for things that should melt away rather than snap
export const E = {out: Easing.bezier(0.16, 1, 0.3, 1), inOut: Easing.bezier(0.65, 0, 0.35, 1), in: Easing.bezier(0.7, 0, 0.84, 0)};
export const GENTLE = Easing.bezier(0.37, 0, 0.63, 1);
export const POP = Easing.bezier(0.23, 1, 0.32, 1);          // tooltip/dialog pop
const cl = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
/** eased 0..1 (or x..y) between film times a and b, clamped */
export const k = (t: number, a: number, b: number, x: number, y: number, e = E.out) => interpolate(t, [a, b], [x, y], {...cl, easing: e});
/** stepped values (pixel sizes that change in whole steps, like a resolution change) */
export const stepped = (t: number, keys: Array<[number, number]>) => { let v = keys[0][1]; for (const [at, val] of keys) if (t >= at) v = val; return v; };

// ---------------------------------------------------------------- colour and type
export const DISPLAY = FONT_DISPLAY;
export const INK = COLORS.ink;
export const GREY = COLORS.muted;                            // the grey half of a two-tone headline
export const ACCENT = THEME_ACCENT;                          // the brand accent as [r, g, b]: the presence colour
/** the accent at an alpha: pills, focus boxes, ticks */
export const accent = themeAccent;
export const mix = (a: number[], b: number[], p: number) => `rgb(${a.map((v, i) => Math.round(v + (b[i] - v) * p)).join(',')})`;
/** the one italic accent word of a headline */
export const It = ({children}: {children: React.ReactNode}) => <span style={{fontStyle: 'italic'}}>{children}</span>;

/** Display lines that rise out of a mask with a slight blur while moving; `out` lifts and blurs them away. */
export function Rise({t, at, lines, size, x, y, w, align = 'left', out, outDur = 0.6, outEase = E.in, stagger = 0.1, color = INK, lh = 1.04, dur = 1.2, shadow, weight = 400}:
  {t: number; at: number; lines: React.ReactNode[]; size: number; x: number; y: number; w?: number; align?: 'left' | 'center'; out?: number; outDur?: number; outEase?: (n: number) => number; stagger?: number; color?: string; lh?: number; dur?: number; shadow?: string; weight?: number}) {
  return <div style={{position: 'absolute', left: x, top: y, width: w, textAlign: align, fontFamily: DISPLAY, fontSize: size, lineHeight: lh, letterSpacing: '-0.025em', fontWeight: weight, textShadow: shadow}}>
    {lines.map((ln, i) => {
      const a = at + i * stagger; const p = k(t, a, a + dur, 0, 1);
      const o = out !== undefined ? k(t, out + i * 0.05, out + outDur + i * 0.05, 0, 1, outEase) : 0;
      if (p <= 0.001 || o >= 0.999) return <div key={i} style={{height: size * lh}}/>;
      return <div key={i} style={{overflow: 'hidden', padding: `${size * 0.08}px ${size * 0.1}px ${size * 0.18}px`, margin: `${-size * 0.08}px ${-size * 0.1}px ${-size * 0.18}px`}}>
        <div style={{color, transform: `translateY(${(1 - p) * 100}%) translateY(${-o * size * 0.25}px)`, opacity: (0.2 + 0.8 * p) * (1 - o), filter: p < 0.985 || o > 0.015 ? `blur(${(1 - p) * 6 + o * 4}px)` : undefined}}>{ln}</div>
      </div>;
    })}
  </div>;
}

/** Micro label: 15 px uppercase body font, muted colour. "[1] Step", "Tactile Paradox · 6 of 21 Training Images". No dashes. */
export const Micro = ({x, y, children, o = 1, color = COLORS.muted, align = 'left', size = 15}: {x: number; y: number; children: React.ReactNode; o?: number; color?: string; align?: 'left' | 'right'; size?: number}) =>
  <div style={{position: 'absolute', left: align === 'left' ? x : undefined, right: align === 'right' ? 1920 - x : undefined, top: y, fontFamily: FONT_BODY, fontSize: size, letterSpacing: '0.08em', textTransform: 'uppercase', color, opacity: o, whiteSpace: 'nowrap'}}>{children}</div>;
/** Notes and every other subtext: 19 px uppercase body font, light. Same voice as Micro, one step bigger. */
export const NOTE: React.CSSProperties = {fontFamily: FONT_BODY, fontSize: 19, lineHeight: 1.5, letterSpacing: '0.08em', textTransform: 'uppercase', color: inkA(0.7)};
/** The presence pill (accent at 25% fill, 1.5 px edge): the spoken caption word, a trigger word in a prompt. */
export const wordBox = (on: number, padding = '1px 6px 3px', radius = 9): React.CSSProperties =>
  ({display: 'inline-block', padding, margin: '0 -1px', borderRadius: radius, background: accent(0.25 * on), boxShadow: `inset 0 0 0 1.5px ${accent(on)}`});
export const Vignette = () => <AbsoluteFill style={{pointerEvents: 'none', background: 'radial-gradient(ellipse 80% 75% at 50% 46%, transparent 60%, rgba(0,0,0,0.35) 100%)'}}/>;
export const smoothPath = (pts: Array<[number, number]>) => {
  let d = `M${pts[0][0]} ${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(pts.length - 1, i + 2)];
    d += ` C${p1[0] + (p2[0] - p0[0]) / 6} ${p1[1] + (p2[1] - p0[1]) / 6} ${p2[0] - (p3[0] - p1[0]) / 6} ${p2[1] - (p3[1] - p1[1]) / 6} ${p2[0]} ${p2[1]}`;
  }
  return d;
};
export const cover: React.CSSProperties = {width: '100%', height: '100%', objectFit: 'cover', display: 'block'};

// ---------------------------------------------------------------- the standard layout (screen px on a 1920x1080 canvas)
export type Box = {x: number; y: number; w: number; h: number};
/** left editorial column: micro label, display word, note under it */
export const COL = {x: 98, w: 440, label: 206, word: 232, size: 124};
/** the speaker's webcam as a video card, bottom left, and the captions beside it, bottom-aligned with it */
export const FACE = {x: 96, y: 700, s: 300};
export const CAP = {x: FACE.x + FACE.s + 32, bottom: FACE.y + FACE.s};
/** the stage beside the column: floating app window, node graphs, panels */
export const WIN: Box = {x: 560, y: 146, w: 1240, h: 697.5};
/** captions (default): one line centred on the stage axis, vertically centred in the band between the
 *  window's bottom edge and the webcam node's bottom edge; long lines span about the window's width (40 px, <= ~55 chars) */
export const CAP_STAGE = {cx: WIN.x + WIN.w / 2, cy: (WIN.y + WIN.h + FACE.y + FACE.s) / 2, w: WIN.w, size: 40};
/** hook captions over full-frame footage: centred on the frame, low, over a soft bottom scrim */
export const CAP_HOOK = {cx: 960, cy: 968, w: 1700, size: 46};

// ---------------------------------------------------------------- the clock: film time = brief time + lead (the silent cold open)
export type Word = [string, number, number, string];
export type Seg = {t: string; at?: number};
const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, '');
/**
 * Timing helpers for one film. Every beat should be keyed to a spoken word, never to a hand-typed second:
 *   const c = clock(brief, 1.5);  c.wordT('library', 'styles')  c.wordEnd('images', 'work')  c.sceneAt('speed')
 * Words match by their first letters, ignoring case and punctuation ('krea' finds "Krea's", '25' finds "2.5");
 * nth picks a later occurrence. A word that isn't in the scene throws, so a re-cut can't silently break a beat.
 */
export function clock(brief: Brief, lead: number) {
  const words = ((brief as unknown as {words?: Word[]}).words) || [];
  const find = (scene: string, word: string, nth: number) => {
    const hits = words.filter(w => w[3] === scene && norm(w[0]).startsWith(norm(word)));
    const w = hits[nth];
    if (!w) throw new Error(`clock: no "${word}" (#${nth}) in scene "${scene}". Words there: ${words.filter(x => x[3] === scene).map(x => x[0]).join(' ')}`);
    return w;
  };
  const starts: Record<string, number> = {}; let at = 0;
  for (const s of brief.scenes) { starts[s.id] = at; at += s.duration; }
  const scene = (id: string) => { if (!(id in starts)) throw new Error(`clock: no scene "${id}"`); return brief.scenes.find(s => s.id === id)!; };
  return {
    lead,
    /** film time a word starts */
    wordT: (sc: string, word: string, nth = 0) => find(sc, word, nth)[1] + lead,
    /** film time a word ends */
    wordEnd: (sc: string, word: string, nth = 0) => find(sc, word, nth)[2] + lead,
    /** film time a scene starts / ends */
    sceneAt: (id: string) => { scene(id); return starts[id] + lead; },
    sceneEnd: (id: string) => starts[id] + scene(id).duration + lead,
    scene,
    /** the whole film: the brief plus the cold open */
    total: at + lead,
  };
}
export type Clock = ReturnType<typeof clock>;
