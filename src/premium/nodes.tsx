// Canvas beats, drawn with the card/group/edge components (ui.tsx): inputs wired into a result that then lift
// into a 3D arc, a prompt node with its key word in the presence pill wired into what it made, and a row of results compared
// in a group with the one being discussed selected.
import React from 'react';
import {AbsoluteFill, Easing, Img, staticFile, useVideoConfig} from 'remotion';
import {UI, Edge, Group, Card, Tooltip, S, edgeCurve, popEase} from '../ui';
import {FONT_BODY, inkA} from '../theme';
import {Box, E, GENTLE, INK, Micro, POP, cover, k, smoothPath, wordBox} from './core';

/** fade + 14 px rise for a node arriving at `at` */
export const NodeIn = ({t, at, children}: {t: number; at: number; children: React.ReactNode}) => {
  const a = k(t, at, at + 0.45, 0, 1, POP); if (a <= 0.001) return null;
  return <div style={{position: 'absolute', inset: 0, opacity: a, transform: `translateY(${(1 - a) * 14}px)`}}>{children}</div>;
};
/** an edge that draws in from `at` (350 ms) and then sends one packet along */
export const edgeFrom = (t: number, at: number, sx: number, sy: number, tx: number, ty: number, fps: number, key: React.Key, width = 2) =>
  t >= at ? <Edge key={key} q={edgeCurve(sx, sy, tx, ty)} since={(t - at) * fps} fps={fps} width={width} color={UI.edgeMid}/> : null;

// the 6-card wave the inputs float into (front/back alternating, rising to the right, turning less as they go right)
export const ARC6 = [
  {cx: 640, cy: 600, h: 236, z: 0, ry: -24, rx: 7},
  {cx: 872, cy: 508, h: 214, z: -90, ry: -20, rx: 6},
  {cx: 1100, cy: 590, h: 240, z: 20, ry: -16, rx: 6},
  {cx: 1330, cy: 466, h: 210, z: -80, ry: -12, rx: 5},
  {cx: 1556, cy: 550, h: 232, z: 10, ry: -8, rx: 5},
  {cx: 1772, cy: 422, h: 200, z: -120, ry: -5, rx: 4},
];

/**
 * Inputs → result → arc. Up to six input images pop into a 2x3 grid inside a labelled group, edges draw from each into a
 * result node (optionally with a tooltip badge), then the graph fades and the inputs lift out of the grid into a 3D arc
 * threaded by a thin line, with a micro label; the arc drifts off at `times.arcOut`. Pairs with PixelOpen's glide:
 * pass the same `result.box` as the open's `glide.to`, and `times.land` = when the glide ends.
 */
export function GraphToArc({t, inputs, groupLabel, result, tooltip, arcLabel, times}:
  {t: number; inputs: Array<{src: string; aspect: number}>; groupLabel: string; arcLabel?: string;
   result: {src: string; title: string; model?: string; box?: Box; selected?: readonly [number, number]};
   tooltip?: {text: string; at: number; until: number};
   times: {from: number; inputs: number; edges: number; land: number; graphOut: readonly [number, number]; toArc: number; arcOut: readonly [number, number]}}) {
  const {fps} = useVideoConfig();
  if (t < times.from - 0.05 || t > times.arcOut[1] + 0.05) return null;
  const OUT = result.box ?? {x: 1110, y: 196, w: 480, h: 480};
  const cells = inputs.map((n, i) => ({...n, x: 520 + (i % 2) * 168, y: 190 + Math.floor(i / 2) * 176, w: 136, h: 136}));
  const kz = OUT.w / 384;
  const graph = k(t, times.graphOut[0], times.graphOut[1], 1, 0, E.in);
  const nodeIn = k(t, times.land, times.land + 0.3, 0, 1);
  const head = k(t, times.land + 0.05, times.land + 0.45, 0, 1);
  const push = 1 + 0.035 * k(t, times.toArc + 1.8, times.arcOut[1], 0, 1, Easing.linear);   // one slow push on the whole arc, no wobble
  const nodes = cells.map((n, i) => {
    const a = k(t, times.inputs + i * 0.09, times.inputs + i * 0.09 + 0.3, 0, 1, POP);
    const arc = ARC6[i]; const aw = arc.h * n.aspect, ah = arc.h;
    const ta = times.toArc + i * 0.12; const q = k(t, ta, ta + 1.8, 0, 1, E.inOut);
    const cx = 960 + (arc.cx - 960) * push, cy = 540 + (arc.cy - 540) * push;
    const leave = k(t, times.arcOut[0] + i * 0.05, times.arcOut[0] + i * 0.05 + 0.85, 0, 1, GENTLE);
    return {n, a, q, leave, x: n.x + (cx - aw * push / 2 - n.x) * q, y: n.y + (cy - ah * push / 2 - n.y) * q + leave * 40, w: n.w + (aw * push - n.w) * q, h: n.h + (ah * push - n.h) * q,
      z: arc.z * q, ry: arc.ry * q, rx: arc.rx * q, rad: 24 * (n.w / 384) * (1 - q) + 6 * q};
  });
  const rows = Math.ceil(cells.length / 2);
  const g0 = {x: 520 - 22, y: 190 - 22, x1: 520 + 168 + 136 + 22, y1: 190 + (rows - 1) * 176 + 136 + 22};
  const groupO = k(t, times.inputs + 0.3, times.inputs + 0.85, 0, 1) * graph;   // the frame settles once the pictures are in
  const lineDraw = k(t, times.toArc + 1.5, times.toArc + 2.9, 0, 1, E.inOut) * k(t, times.arcOut[0], times.arcOut[0] + 0.8, 1, 0, GENTLE);
  const centres = ARC6.slice(0, cells.length).map(a => [960 + (a.cx - 960) * push, 540 + (a.cy - 540) * push] as [number, number]);
  const sel = result.selected ?? [times.edges + 1.0, times.graphOut[0]];
  return <AbsoluteFill>
    {groupO > 0.001 && <Group x={g0.x} y={g0.y} w={g0.x1 - g0.x} h={g0.y1 - g0.y} zoom={136 / 384} label={groupLabel} opacity={groupO}/>}
    {t >= times.edges && graph > 0.001 && <svg width={1920} height={1080} style={{position: 'absolute', inset: 0, overflow: 'visible', opacity: graph}}>
      {cells.map((n, i) => { const kk = n.w / 384; const sx = n.x + n.w + 28 * kk, sy = n.y + n.h / 2; const tx = OUT.x - 24 * kz, ty = OUT.y + OUT.h / 2;
        const since = (t - times.edges - i * 0.12) * fps; if (since < 0) return null;
        return <Edge key={i} q={edgeCurve(sx, sy, tx, ty)} since={since} fps={fps} width={2} color={UI.edgeMid}/>; })}
    </svg>}
    {lineDraw > 0.001 && <svg width={1920} height={1080} style={{position: 'absolute', inset: 0}}>
      <path d={smoothPath([[430, 760], ...centres, [1990, 330]])} fill="none" stroke={inkA(0.28)} strokeWidth={1.4} pathLength={1} strokeDasharray={`${lineDraw} 1`}/>
    </svg>}
    {nodes.map((n, i) => n.a > 0.001 && n.leave < 0.999 && <div key={i} style={{position: 'absolute', inset: 0, perspective: 1700, perspectiveOrigin: '50% 45%'}}>
      <div style={{position: 'absolute', left: n.x, top: n.y, width: n.w, height: n.h, borderRadius: n.rad, overflow: 'hidden', background: UI.card, opacity: n.a * (1 - n.leave),
        transform: `translateZ(${n.z}px) rotateY(${n.ry}deg) rotateX(${n.rx}deg)`, boxShadow: n.q > 0.5 ? `0 30px 80px rgba(0,0,0,${0.55 * n.q})` : `inset 0 0 0 2px ${inkA(0.05)}`}}>
        <Img src={staticFile(n.n.src)} style={cover}/>
      </div></div>)}
    {graph > 0.001 && nodeIn > 0.001 && <Card x={OUT.x} y={OUT.y} w={OUT.w} h={OUT.h} title={result.title} model={result.model} selected={t > sel[0] && t < sel[1]} opacity={graph * nodeIn} headerOpacity={head}>
      <Img src={staticFile(result.src)} style={cover}/>
    </Card>}
    {tooltip && graph > 0.001 && <Tooltip x={OUT.x + OUT.w - 34} y={OUT.y - 34} text={tooltip.text} t={k(t, tooltip.at, tooltip.at + 0.15, 0, 1, POP) * k(t, tooltip.until - 0.15, tooltip.until, 1, 0)}/>}
    {arcLabel && <Micro x={1772} y={740} o={k(t, times.toArc + 2.0, times.toArc + 2.8, 0, 1) * k(t, times.arcOut[0], times.arcOut[0] + 0.7, 1, 0, GENTLE)} align="right">{arcLabel}</Micro>}
  </AbsoluteFill>;
}

/**
 * A prompt in a text card with its key phrase in the presence pill (the same pill as the spoken caption word), wired
 * into the image it made, with a micro caption under the result. `zoom` scales the little graph so a 14 px prompt reads
 * at video size (text card body: 12 px padding, 14 / 1.4 at 350).
 */
export function PromptToResult({t, at, out, prompt, highlightAt, result, resultAt, caption, nodeTitle = 'Prompt', zoom = 1.15,
  txt = {x: 596, y: 480, w: 470, h: 200}, res = {x: 1244, y: 236, w: 540, h: 540}}:
  {t: number; at: number; out: readonly [number, number]; prompt: {before?: string; highlight: string; after?: string}; highlightAt: number;
   result: {src: string; title: string; model?: string}; resultAt: number; caption?: string; nodeTitle?: string; zoom?: number; txt?: Box; res?: Box}) {
  const {fps} = useVideoConfig();
  if (t < at || t > out[1] + 0.05) return null;
  const TZ = zoom * S;
  const o = k(t, out[0], out[1], 0, 1, GENTLE);
  const txtIn = k(t, at + 0.45, at + 1.05, 0, 1);
  const boxOn = k(t, highlightAt - 0.05, highlightAt + 0.1, 0, 1, popEase);
  const resIn = k(t, resultAt + 0.3, resultAt + 0.8, 0, 1);
  const sx = txt.x + txt.w + 18, sy = txt.y + txt.h / 2, tx = res.x - 16, ty = res.y + res.h / 2;   // small gaps, as in the canvas act
  return <AbsoluteFill style={{opacity: 1 - o, transform: `translateY(${o * 24}px)`}}>
    {t >= resultAt && <svg width={1920} height={1080} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
      <Edge q={edgeCurve(sx, sy, tx, ty)} since={(t - resultAt) * fps} fps={fps} width={2} color={UI.edgeMid}/>
    </svg>}
    <div style={{position: 'absolute', inset: 0, opacity: txtIn, transform: `translateY(${(1 - txtIn) * 14}px)`}}>
      <Card x={txt.x} y={txt.y} w={txt.w} h={txt.h} kind="text" title={nodeTitle} flowW={txt.w / TZ}>
        <div style={{position: 'absolute', left: 12 * TZ, top: 12 * TZ, right: 12 * TZ, fontFamily: FONT_BODY, fontSize: 14 * TZ, lineHeight: 1.4, fontWeight: 350, color: INK}}>
          {prompt.before}<span style={wordBox(boxOn, '0px 5px 2px', 7)}>{prompt.highlight}</span>{prompt.after}
        </div>
      </Card>
    </div>
    <div style={{position: 'absolute', inset: 0, opacity: resIn, transform: `translateY(${(1 - resIn) * 14}px)`}}>
      <Card x={res.x} y={res.y} w={res.w} h={res.h} title={result.title} model={result.model} flowW={res.w / TZ}>
        <Img src={staticFile(result.src)} style={cover}/>
      </Card>
    </div>
    {caption && <Micro x={res.x} y={res.y + res.h + 24} o={k(t, resultAt + 0.9, resultAt + 1.5, 0, 1)}>{caption}</Micro>}
  </AbsoluteFill>;
}

/**
 * Results side by side in a labelled group (same prompt and seed, different settings). `selections` say which one is
 * being talked about and when: it takes the selection edge while the others step back to 45%.
 */
export function CompareRow({t, at, out, items, groupLabel, selections, x, y = 372, size = 276, gap = 30}:
  {t: number; at: number; out: readonly [number, number]; items: Array<{src: string; title: string; model?: string}>; groupLabel: string;
   selections: Array<{index: number; from: number; to?: number}>; x?: number; y?: number; size?: number; gap?: number}) {
  if (t < at || t > out[1] + 0.05) return null;
  const o = k(t, out[0], out[1], 0, 1, GENTLE);
  const total = items.length * size + (items.length - 1) * gap, x0 = x ?? 560 + (1260 - total) / 2;   // centred on the stage
  const first = Math.min(...selections.map(s => s.from));
  const focus = k(t, first, first + 0.35, 0, 1, GENTLE);
  const mine = items.map((_, i) => Math.max(0, ...selections.filter(s => s.index === i).map(s =>
    k(t, s.from, s.from + 0.35, 0, 1, GENTLE) * (s.to !== undefined ? k(t, s.to, s.to + 0.35, 1, 0, GENTLE) : 1))));
  const sel = selections.filter(s => t >= s.from && (s.to === undefined || t < s.to)).map(s => s.index).pop() ?? -1;
  return <AbsoluteFill style={{opacity: 1 - o, transform: `translateY(${o * 24}px)`}}>
    <Group x={x0 - 24} y={y - 50} w={total + 48} h={size + 74} zoom={size / 384} label={groupLabel} opacity={k(t, at + 0.45, at + 1.0, 0, 1)}/>
    {items.map((n, i) => { const a = k(t, at + 0.1 + i * 0.1, at + 0.6 + i * 0.1, 0, 1);
      return <div key={i} style={{position: 'absolute', inset: 0, opacity: a * (1 - 0.55 * Math.max(0, focus - mine[i])), transform: `translateY(${(1 - a) * 14}px)`}}>
        <Card x={x0 + i * (size + gap)} y={y} w={size} h={size} title={n.title} model={n.model} selected={sel === i}>
          <Img src={staticFile(n.src)} style={cover}/>
        </Card>
      </div>; })}
  </AbsoluteFill>;
}
