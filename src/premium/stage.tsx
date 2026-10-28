// The stage beside the step column: the product itself. A floating window that settles from a 3D tilt and leans away when
// it leaves, holding either a click-through of crisp UI captures (AppWindow + walk.tsx) or recordings / stills with an eased
// camera and focus boxes (Window + Shot), plus a floating panel for one piece of UI with the presence cursor on it.
import React from 'react';
import {AbsoluteFill, Easing, Img, Loop, OffthreadVideo, Sequence, staticFile, useVideoConfig} from 'remotion';
import type {Scene} from '../schema';
import {Cursor, hoverEase, popEase} from '../ui';
import {COLORS, inkA} from '../theme';
import {Walk} from '../walk';
import {Box, E, GENTLE, WIN, accent, k} from './core';

/** window arrival/departure: settle from a tilt (1.8 s) and lean away (0.9 s) */
const windowTransform = (t: number, inAt: readonly [number, number], outAt: readonly [number, number], box: Box) => {
  const q = k(t, inAt[0], inAt[1], 0, 1, E.out), qo = k(t, outAt[0], outAt[1], 0, 1, GENTLE);
  const ry = -14 * (1 - q) + 8 * qo, rx = 6 * (1 - q), sc = (0.92 + 0.08 * q) * (1 - 0.04 * qo), tx = 60 * (1 - q) + 30 * qo;
  return {q, qo, style: {transform: `perspective(2400px) translateX(${tx}px) rotateY(${ry}deg) rotateX(${rx}deg) scale(${sc})`,
    transformOrigin: `${box.x + box.w / 2}px ${box.y + box.h / 2}px`, opacity: k(t, inAt[0], inAt[0] + 0.45, 0, 1) * (1 - qo)} as React.CSSProperties};
};

/**
 * App click-through on real 2x captures (a Scene with a `walk`: shots crossfading between hover states, an eased camera,
 * the presence cursor travelling to each target and pressing on clicks, tooltips). `start` is the film time of
 * walk time 0. Keep the camera calm: one move at a time with holds (skill/references/motion-language.md).
 */
export function AppWindow({t, walk, start, inAt, outAt, box = WIN, cursorName}:
  {t: number; walk: Scene; start: number; inAt: readonly [number, number]; outAt: readonly [number, number]; box?: Box; cursorName?: string}) {
  const {fps} = useVideoConfig();
  if (t < Math.min(start, inAt[0]) || t > outAt[1] + 0.05) return null;
  const w = windowTransform(t, inAt, outAt, box);
  return <AbsoluteFill style={w.style}>
    <div style={{position: 'absolute', left: box.x, top: box.y, width: box.w, height: box.h, borderRadius: 16, boxShadow: `0 40px 120px rgba(0,0,0,${0.6 * w.q})`}}/>
    <Sequence from={Math.round(start * fps)} layout="none"><Walk scene={walk} box={box} cursorName={cursorName}/></Sequence>
  </AbsoluteFill>;
}

/** A clip that starts playing at film time `at`, one continuous stretch at 1x (loop only if it truly must). */
export function Clip({src, at, start = 0, loop, rate = 1, style}: {src: string; at: number; start?: number; loop?: number; rate?: number; style: React.CSSProperties}) {
  const {fps} = useVideoConfig();
  const v = <OffthreadVideo src={staticFile(src)} muted startFrom={Math.round(start * fps)} playbackRate={rate} style={style}/>;
  return <Sequence from={Math.round(at * fps)} layout="none">{loop ? <Loop durationInFrames={Math.round(loop * fps)} layout="none">{v}</Loop> : v}</Sequence>;
}

/**
 * A shot inside a Window: an image or a recording (e.g. the stream's own screen share, a Codex session, a canvas), shown
 * from `from` to `to` (film time). `cam` keys are [t (film), cx, cy (0..1 of the shot), z (zoom, 1 = fit)] eased on the camera
 * curve; `boxes` are focus boxes (r = [x0, y0, x1, y1] in 0..1 of the shot): the rest of the frame dims and the box takes
 * the accent edge, on the line that talks about it.
 */
export type Cam = {t: number; cx: number; cy: number; z: number};
export type FocusBox = {from: number; to: number; r: [number, number, number, number]};
export type Shot = {from: number; to: number; src: string; kind: 'img' | 'vid'; aspect: number; start?: number; cam?: Cam[]; boxes?: FocusBox[]};
const camAt = (keys: Cam[], t: number) => {
  if (t <= keys[0].t) return keys[0];
  const i = keys.findIndex((c, j) => j < keys.length - 1 && t >= c.t && t < keys[j + 1].t); if (i < 0) return keys[keys.length - 1];
  const a = keys[i], b = keys[i + 1], u = E.inOut((t - a.t) / (b.t - a.t));
  return {t, cx: a.cx + (b.cx - a.cx) * u, cy: a.cy + (b.cy - a.cy) * u, z: Math.exp(Math.log(a.z) + (Math.log(b.z) - Math.log(a.z)) * u)};
};
function ShotView({s, t, o, box}: {s: Shot; t: number; o: number; box: Box}) {
  const pw = box.w, ph = box.h, A = s.aspect;
  const W0 = A > pw / ph ? ph * A : pw, H0 = A > pw / ph ? ph : pw / A;
  const cam = camAt(s.cam && s.cam.length ? s.cam : [{t: 0, cx: 0.5, cy: 0.5, z: 1}], t);
  const z = cam.z * (1 + 0.02 * k(t, s.from, s.to, 0, 1, Easing.linear)), w = W0 * z, h = H0 * z;   // a 2% drift keeps stills alive
  const left = Math.min(0, Math.max(pw - w, pw / 2 - cam.cx * w)), top = Math.min(0, Math.max(ph - h, ph / 2 - cam.cy * h));
  const st: React.CSSProperties = {position: 'absolute', left, top, width: w, height: h, objectFit: 'fill', maxWidth: 'none'};
  return <div style={{position: 'absolute', inset: 0, opacity: o}}>
    {s.kind === 'vid' ? <Clip src={s.src} at={s.from} start={s.start} style={st}/> : <Img src={staticFile(s.src)} style={st}/>}
    {(s.boxes || []).map((b, i) => {
      if (t < b.from || t >= b.to + 0.4) return null;
      const al = Math.min(k(t, b.from, b.from + 0.35, 0, 1, popEase), k(t, b.to, b.to + 0.35, 1, 0, GENTLE)); const pad = 10;
      return <div key={i} style={{position: 'absolute', left: left + b.r[0] * w - pad, top: top + b.r[1] * h - pad, width: (b.r[2] - b.r[0]) * w + 2 * pad, height: (b.r[3] - b.r[1]) * h + 2 * pad,
        borderRadius: 12, boxShadow: `0 0 0 4000px rgba(0,0,0,${0.46 * al})`, transform: `scale(${1.03 - 0.03 * al})`}}>
        <div style={{position: 'absolute', inset: 0, borderRadius: 12, background: `${accent(0.1 * al)}`, boxShadow: `inset 0 0 0 1.5px ${accent(al)}`}}/>
      </div>;
    })}
  </div>;
}
/** Floating window of shots. win = [in0, in1, out0, out1]. Shots crossfade (0.6 s) into each other. */
export function Window({t, win, shots, box = WIN, children}: {t: number; win: readonly [number, number, number, number]; shots: Shot[]; box?: Box; children?: React.ReactNode}) {
  const [in0, in1, out0, out1] = win;
  if (t < in0 - 0.05 || t > out1 + 0.05) return null;
  const w = windowTransform(t, [in0, in1], [out0, out1], box);
  return <AbsoluteFill style={w.style}>
    <div style={{position: 'absolute', left: box.x, top: box.y, width: box.w, height: box.h, borderRadius: 16, overflow: 'hidden', background: COLORS.background, boxShadow: `0 40px 120px rgba(0,0,0,${0.6 * w.q})`}}>
      {shots.map((s, i) => { if (t < s.from - 0.05 || t > s.to + 0.7) return null;
        const o = Math.min(i === 0 ? 1 : k(t, s.from, s.from + 0.6, 0, 1, GENTLE), 1);
        return <ShotView key={i} s={s} t={t} o={o} box={box}/>; })}
      <div style={{position: 'absolute', inset: 0, borderRadius: 16, boxShadow: `inset 0 0 0 1.5px ${inkA(0.1)}`, pointerEvents: 'none'}}/>
    </div>
    {children}
  </AbsoluteFill>;
}

/**
 * One piece of real UI (a crop of a capture, e.g. a menu) on a floating card, with the presence cursor
 * gliding to a target and a hover highlight appearing on a row. Coordinates in `cursor` and `hover.rect` are in the
 * image's own pixels; `scale` maps them to screen.
 */
export function FloatingPanel({t, src, size, at, scale = 0.9, inAt, outAt, cursor, hover, cursorName}:
  {t: number; src: string; size: [number, number]; at: {x: number; y: number}; scale?: number; inAt: readonly [number, number]; outAt: readonly [number, number];
   cursor?: {from: [number, number]; to: [number, number]; arrive: number; travel?: number; show?: number}; hover?: {rect: [number, number, number, number]; at: number; radius?: number}; cursorName?: string}) {
  if (t < inAt[0] - 0.05 || t > outAt[1] + 0.05) return null;
  const box = {x: at.x, y: at.y, w: size[0] * scale, h: size[1] * scale};
  const w = windowTransform(t, inAt, outAt, box);
  const mv = cursor ? k(t, cursor.arrive - (cursor.travel ?? 1.0), cursor.arrive, 0, 1, Easing.bezier(0.45, 0, 0.55, 1)) : 0;
  const hov = hover ? k(t, hover.at, hover.at + 0.15, 0, 1, hoverEase) : 0;
  return <AbsoluteFill style={w.style}>
    <div style={{position: 'absolute', left: box.x, top: box.y, width: box.w, height: box.h, borderRadius: 16, overflow: 'hidden', background: COLORS.background, boxShadow: `0 40px 120px rgba(0,0,0,${0.6 * w.q})`}}>
      <Img src={staticFile(src)} style={{width: '100%', height: '100%', display: 'block'}}/>
      {hover && <div style={{position: 'absolute', left: hover.rect[0] * scale, top: hover.rect[1] * scale, width: hover.rect[2] * scale, height: hover.rect[3] * scale, borderRadius: hover.radius ?? 11, background: inkA(0.07 * hov)}}/>}
      <div style={{position: 'absolute', inset: 0, borderRadius: 16, boxShadow: `inset 0 0 0 1.5px ${inkA(0.1)}`}}/>
    </div>
    {cursor && <Cursor x={box.x + (cursor.from[0] + (cursor.to[0] - cursor.from[0]) * mv) * scale} y={box.y + (cursor.from[1] + (cursor.to[1] - cursor.from[1]) * mv) * scale}
      opacity={k(t, cursor.show ?? inAt[0] + 0.6, (cursor.show ?? inAt[0] + 0.6) + 0.3, 0, 1)} name={cursorName}/>}
  </AbsoluteFill>;
}

/**
 * The stream's own screen, in sync with the voice: a Shot that plays the cut's stringout (brief.face.src, written by the
 * cut builder: the kept spans back to back, aligned with the voice) from film time `from` to `to`. Frame it with `cam`
 * (e.g. {cx: 0.62, cy: 0.45, z: 1.3} to crop the webcam bubble out) and point at things with focus `boxes`.
 */
export const streamShot = (brief: {face?: {src: string}}, lead: number, from: number, to: number, extra: Partial<Shot> = {}, aspect = 16 / 9): Shot =>
  ({src: brief.face!.src, kind: 'vid', aspect, from, to, start: Math.max(0, from - lead), ...extra});
