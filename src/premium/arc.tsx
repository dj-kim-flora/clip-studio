// The arc: finished pieces floating on a 3D wave, threaded by a thin line. Used as an opener ("the world"), as the sign-off
// ("keep building"), or both. Cards can be stills or clips; clips play one continuous stretch at 1x (no loops restarting
// mid-shot, no montages, no slowed or 25 fps footage: all read as choppy).
import React from 'react';
import {Easing, Img, staticFile} from 'remotion';
import {UI} from '../ui';
import {inkA} from '../theme';
import {E, GENTLE, Micro, cover, k, smoothPath} from './core';
import {Clip} from './stage';
import {ARC6} from './nodes';

export type Slot = {cx: number; cy: number; h: number; z: number; ry: number; rx: number};
/** five bigger cards, centred with ~200 px margins (tuned on the Rhizome film) */
export const ARC5: Slot[] = [
  {cx: 386, cy: 650, h: 264, z: 0, ry: -22, rx: 7},
  {cx: 668, cy: 505, h: 225, z: -80, ry: -18, rx: 6},
  {cx: 950, cy: 640, h: 236, z: 20, ry: -14, rx: 6},
  {cx: 1232, cy: 470, h: 222, z: -70, ry: -10, rx: 5},
  {cx: 1514, cy: 600, h: 225, z: 10, ry: -7, rx: 5},
];
export {ARC6};
export type Card = {src: string; kind?: 'img' | 'vid'; aspect: number; start?: number; loop?: number; scale?: number};

/**
 * Cards rise from below in depth one after another, the line draws through them, one slow push holds the shot, and they
 * drift off at `out`. Far cards paint first so nearer ones sit in front. Keep margins: check the rendered frame's bounding box
 * (skill/references/qa-checklist.md); busy full-frame pictures go in back slots, pieces with type in front.
 */
export function Arc({t, at, out, cards, label, slots = ARC6, end, push = 0.03, maxW = 500, rise = {y: 60, dur: 1.1, stagger: 0.12, delay: 0.35, z: 160},
  line = {from: [430, 760] as [number, number], to: [1990, 330] as [number, number]}, labelAt = {x: 1772, y: 740}, canvas = [1920, 1080] as [number, number]}:
  {t: number; at: number; out?: readonly [number, number]; cards: Card[]; label?: string; slots?: Slot[]; end: number; push?: number; maxW?: number;
   rise?: {y: number; dur: number; stagger: number; delay: number; z: number}; line?: {from: [number, number]; to: [number, number]}; labelAt?: {x: number; y: number}; canvas?: [number, number]}) {
  if (t < at - 0.05 || (out && t > out[1] + 0.05)) return null;
  const pu = 1 + push * k(t, at + 1.2, out ? out[1] : end, 0, 1, Easing.linear);
  const rect = (i: number, c: Card) => {
    const s = slots[i], h = s.h * pu * (c.scale ?? 1), w = Math.min(h * c.aspect, maxW * pu * (c.scale ?? 1)), hh = w / c.aspect;
    const cx = canvas[0] / 2 + (s.cx - canvas[0] / 2) * pu, cy = canvas[1] / 2 + (s.cy - canvas[1] / 2) * pu;
    return {x: cx - w / 2, y: cy - hh / 2, w, h: hh, cx, cy};
  };
  const lineP = k(t, at + 1.3, at + 2.7, 0, 1, E.inOut) * (out ? k(t, out[0], out[0] + 0.8, 1, 0, GENTLE) : 1);
  const centres = cards.map((c, i) => { const r = rect(i, c); return [r.cx, r.cy] as [number, number]; });
  const order = cards.map((_, i) => i).sort((a, b) => slots[a].z - slots[b].z);
  return <>
    {lineP > 0.001 && <svg width={canvas[0]} height={canvas[1]} style={{position: 'absolute', inset: 0}}>
      <path d={smoothPath([line.from, ...centres, line.to])} fill="none" stroke={inkA(0.28)} strokeWidth={1.4} pathLength={1} strokeDasharray={`${lineP} 1`}/>
    </svg>}
    {order.map(i => { const c = cards[i], s = slots[i];
      const a = at + rise.delay + i * rise.stagger, p = k(t, a, a + rise.dur, 0, 1); if (p <= 0.001) return null;
      const leave = out ? k(t, out[0] + i * 0.05, out[0] + i * 0.05 + 0.85, 0, 1, GENTLE) : 0; if (leave >= 0.999) return null;
      const r = rect(i, c);
      return <div key={i} style={{position: 'absolute', inset: 0, perspective: 1700, perspectiveOrigin: '50% 45%'}}>
        <div style={{position: 'absolute', left: r.x, top: r.y + (1 - p) * rise.y + leave * 30, width: r.w, height: r.h, borderRadius: 6, overflow: 'hidden', background: UI.card, opacity: p * (1 - leave),
          transform: `translateZ(${s.z - rise.z * (1 - p)}px) rotateY(${s.ry}deg) rotateX(${s.rx}deg)`, boxShadow: `0 30px 80px rgba(0,0,0,${0.55 * p})`}}>
          {c.kind === 'vid' ? <Clip src={c.src} at={a} start={c.start} loop={c.loop} style={cover}/> : <Img src={staticFile(c.src)} style={cover}/>}
        </div>
      </div>;
    })}
    {label && <Micro x={labelAt.x} y={labelAt.y} o={k(t, at + 1.8, at + 2.5, 0, 1) * (out ? k(t, out[0], out[0] + 0.6, 1, 0, GENTLE) : 1)} align="right">{label}</Micro>}
  </>;
}
