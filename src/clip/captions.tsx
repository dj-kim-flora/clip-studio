// Social captions: word-timed, at most two lines, centred, auto-sized to the frame width, in four styles.
import React from 'react';
import {AbsoluteFill, Easing} from 'remotion';
import {ACCENT, COLORS, FONT_BODY, INK_RGB, MOTION, STYLE, accent, rgbOf, rgba} from '../theme';
import {E, k, mix} from '../premium/core';
import {measure, wrap, Zones} from './layout';
import type {CaptionStyleName, ClipCue} from './types';

export type CapWord = {w: string; s: number; e: number};
export type CapPage = {words: CapWord[]; lines: string[][]; size: number; from: number; to: number};

const WEIGHT = 700;
const END_PUNCT = /[.!?…]["')\]]?$/;

/** a cue's words with times: the word timings when present, else even spacing (weighted by length) across the cue */
export function cueWords(cue: ClipCue): CapWord[] {
  if (cue.words && cue.words.length) return cue.words.filter(w => w && typeof w[0] === 'string' && w[0].trim()).map(w => ({w: w[0].trim(), s: w[1], e: Math.max(w[2], w[1] + 0.05)}));
  const parts = (cue.text || '').split(/\s+/).filter(Boolean);
  if (!parts.length) return [];
  const weights = parts.map(p => p.length + 1), total = weights.reduce((a, b) => a + b, 0);
  const span = Math.max(0.1, cue.end - cue.start);
  let at = cue.start;
  return parts.map((w, i) => { const d = span * weights[i] / total; const o = {w, s: at, e: at + d}; at += d; return o; });
}

/**
 * Break every cue into pages of at most two lines that fit `maxW` at `base` px. A page also ends at a sentence end or a pause.
 * A word wider than the frame shrinks that page's font. Pages hold until the next one starts when the gap is short.
 */
export function paginate(cues: ClipCue[], base: number, maxW: number, padEm: number): CapPage[] {
  const pages: CapPage[] = [];
  const widthAt = (px: number) => (s: string) => measure(s, px, FONT_BODY, WEIGHT) + padEm * 2 * px;
  for (const cue of cues) {
    const ws = cueWords(cue);
    let i = 0;
    while (i < ws.length) {
      // take words until a third line would be needed, a sentence ends (after 3+ words) or a pause > 0.7 s follows
      let n = 0, best: string[][] = [];
      for (let j = i; j < ws.length; j++) {
        const trial = wrap(ws.slice(i, j + 1).map(x => x.w), maxW, widthAt(base));
        if (trial.length > 2) break;
        n = j - i + 1; best = trial;
        if (j + 1 < ws.length && (ws[j + 1].s - ws[j].e > 0.7 || (END_PUNCT.test(ws[j].w) && n >= 3))) break;
      }
      if (n === 0) { n = 1; best = [[ws[i].w]]; }
      const slice = ws.slice(i, i + n);
      const widest = Math.max(...best.map(l => l.reduce((a, w) => a + widthAt(base)(w), 0) + (l.length - 1) * measure(' ', base, FONT_BODY, WEIGHT)));
      const size = Math.max(base * 0.55, base * Math.min(1, maxW / widest));
      pages.push({words: slice, lines: best, size, from: slice[0].s, to: slice[slice.length - 1].e});
      i += n;
    }
  }
  pages.sort((a, b) => a.from - b.from);
  pages.forEach((p, i) => {
    const next = pages[i + 1];
    p.to = next && next.from - p.to <= 0.6 ? Math.max(p.to, next.from) : p.to + 0.25;
    if (next && p.to > next.from) p.to = next.from;
    if (p.to <= p.from) p.to = p.from + 0.2;
  });
  return pages;
}

export function Captions({t, cues, style, pos, z}: {t: number; cues: ClipCue[]; style: CaptionStyleName; pos: 'lower' | 'center' | 'upper'; z: Zones}) {
  const {u} = z;
  const base = 58 * u, maxW = z.w - 2 * z.side;
  const padEm = style === 'pill' ? 0.14 : 0;
  const pages = React.useMemo(() => paginate(cues, base, maxW, padEm), [cues, base, maxW, padEm]);
  if (style === 'none') return null;
  const page = pages.find(p => t >= p.from - 0.02 && t < p.to);
  if (!page) return null;
  const size = page.size;
  const enter = k(t, page.from - 0.02, page.from - 0.02 + 0.14 * MOTION, 0, 1, E.out);
  const exit = k(t, page.to - 0.08, page.to, 1, 0);
  const shadow = `0 ${2 * u}px ${14 * u}px rgba(0,0,0,0.75), 0 0 ${2 * u}px rgba(0,0,0,0.55)`;
  // which word is being said: the last one that has started, held through short gaps
  let active = -1;
  page.words.forEach((w, i) => { if (t >= w.s - 0.02) active = i; });
  const onAt = (i: number) => {
    const w = page.words[i], nx = page.words[i + 1];
    const until = nx ? nx.s : Math.max(w.e, w.s + 0.3);
    return k(t, w.s - 0.02, w.s + 0.05, 0, 1, E.out) * k(t, until, until + 0.1, 1, 0, Easing.linear);
  };
  let idx = 0;
  const lines = page.lines.map((ln, li) => <div key={li} style={{whiteSpace: 'nowrap'}}>
    {ln.map((word, wi) => {
      const i = idx++; const on = i <= active ? onAt(i) : 0; const sp = wi < ln.length - 1 ? ' ' : '';
      if (style === 'pill') return <React.Fragment key={wi}><span style={{display: 'inline-block', padding: `0.02em ${padEm}em 0.1em`, borderRadius: STYLE.radius * u * 0.8,
        background: rgba(COLORS.accentFill, 0.94 * on), boxShadow: `inset 0 0 0 ${2.5 * u}px ${accent(on)}`, textShadow: on > 0.5 ? 'none' : undefined}}>{word}</span>{sp}</React.Fragment>;
      if (style === 'karaoke') return <React.Fragment key={wi}><span style={{display: 'inline-block', color: mix(INK_RGB, ACCENT, on), transform: `scale(${1 + 0.07 * on})`, transformOrigin: '50% 80%'}}>{word}</span>{sp}</React.Fragment>;
      if (style === 'box') return <React.Fragment key={wi}><span style={{color: mix(INK_RGB, rgbOf(COLORS.accentInk), on)}}>{word}</span>{sp}</React.Fragment>;
      return <React.Fragment key={wi}>{word}{sp}</React.Fragment>;
    })}
  </div>);
  const text: React.CSSProperties = {fontFamily: FONT_BODY, fontWeight: WEIGHT, fontSize: size, lineHeight: 1.26, letterSpacing: '-0.01em', color: COLORS.ink, textAlign: 'center',
    textShadow: style === 'box' ? 'none' : shadow};
  const body = style === 'box'
    ? <div style={{...text, padding: `${14 * u}px ${28 * u}px ${18 * u}px`, borderRadius: STYLE.radius * u * 1.2, background: rgba(COLORS.panel, 0.9), border: `${2.5 * u}px solid ${accent(0.85)}`}}>{lines}</div>
    : <div style={text}>{lines}</div>;
  const place: React.CSSProperties = pos === 'upper' ? {top: z.top + 24 * u}
    : pos === 'center' ? {top: z.h * 0.5, transform: 'translateY(-50%)'}
    : {bottom: z.h - z.bottom + 64 * u};
  return <AbsoluteFill style={{pointerEvents: 'none'}}>
    <div style={{position: 'absolute', left: 0, width: z.w, display: 'flex', justifyContent: 'center', ...place}}>
      <div style={{opacity: enter * exit, transform: `translateY(${(1 - enter) * 10 * u}px) scale(${0.96 + 0.04 * enter})`, transformOrigin: '50% 100%'}}>{body}</div>
    </div>
  </AbsoluteFill>;
}
