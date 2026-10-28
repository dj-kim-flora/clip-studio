// Generic canvas UI: cards (nodes), handles, edges, a presence cursor, tooltips, groups, notes and a backdrop. All colours come
// from the brand theme (src/theme.ts); S converts design px to video px on a 1920-wide canvas.
import React from 'react';
import {Easing,Img,interpolate,staticFile,useCurrentFrame,useVideoConfig} from 'remotion';
import {ACCENT, COLORS, FONT_BODY, STYLE, inkA, rgba} from './theme';

export const S = 1.5;
const RADIUS = STYLE.radius * 1.5;   // brand.style.radius is px on a 1920 canvas
/** UI tokens derived from the brand colours (ink-based alphas, so a light brand works as well as a dark one) */
export const UI = {
  canvas: COLORS.background, dot: rgba(COLORS.muted, 0.7), line: rgba(COLORS.muted, 0.16),
  card: COLORS.panel,
  borderRest: COLORS.panelBorder, borderSel: inkA(0.5),
  title: COLORS.muted, titleSel: COLORS.ink, model: rgba(COLORS.muted, 0.7), icon: COLORS.muted, iconSel: COLORS.ink,
  handle: COLORS.muted, handleOn: COLORS.ink, plus: COLORS.muted,
  edge: inkA(0.25), edgeMid: inkA(0.42), edgeSel: inkA(0.75),
  tipBg: COLORS.panel, tipBorder: COLORS.panelBorder, tipText: COLORS.ink,
  groupFill: inkA(0.045), groupBorder: COLORS.panelBorder,
};
// The speaker's presence colour: the brand accent. One value drives every accent (webcam ring, cursor, spoken-word pill,
// focus boxes, live table rows, checklist ticks); change colors.accent in public/brand/brand.json.
export const PRESENCE = COLORS.accent;
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
// motion curves
export const hoverEase = Easing.bezier(0.42, 0, 0.58, 1);     // hover chrome 150 ms
export const popEase = Easing.bezier(0.23, 1, 0.32, 1);       // tooltips 150 ms, dialogs 200 ms
export const chromeEase = Easing.bezier(0.4, 0, 0.2, 1);      // panels 250 ms
export const tw = (f: number, a: number, b: number, x: number, y: number, e = chromeEase) => interpolate(f, [a, b], [x, y], {...clamp, easing: e});

// ------------------------------------------------------------------ canvas
export type BackdropVariant = 'dots' | 'grid' | 'gradient' | 'solid';
/** Full-frame background in the brand's backdrop style (dots | grid | gradient | solid); `variant` overrides brand.style.backdrop. */
export const Backdrop = ({spacing = 34, variant = STYLE.backdrop}: {spacing?: number; variant?: BackdropVariant}) => {
  const base: React.CSSProperties = {position: 'absolute', inset: 0, backgroundColor: UI.canvas};
  if (variant === 'dots') return <div style={{...base, backgroundImage: `radial-gradient(circle, ${UI.dot} 1.05px, transparent 1.55px)`, backgroundSize: `${spacing}px ${spacing}px`, backgroundPosition: `${spacing / 2}px ${spacing / 2}px`}}/>;
  if (variant === 'grid') return <div style={{...base, backgroundImage: `linear-gradient(${UI.line} 1px, transparent 1px), linear-gradient(90deg, ${UI.line} 1px, transparent 1px)`, backgroundSize: `${spacing * 2}px ${spacing * 2}px`}}/>;
  if (variant === 'gradient') return <div style={{...base, backgroundImage: `radial-gradient(ellipse 90% 70% at 50% 35%, ${COLORS.accentFill} 0%, ${COLORS.background} 75%)`}}/>;
  return <div style={base}/>;
};

// ------------------------------------------------------------------ icons (24-unit viewBox unless noted)
const ImageIcon = ({size, color}: {size: number; color: string}) =>
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
    <rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg>;
const DeckIcon = ({size, color}: {size: number; color: string}) =>
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
    <path d="M2 3h20"/><path d="M21 3v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V3"/><path d="m7 21 5-5 5 5"/></svg>;
const TextIcon = ({size, color}: {size: number; color: string}) =>   // text block icon
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
    <path d="M15 18H3"/><path d="M17 6H3"/><path d="M21 12H3"/></svg>;
const PlayIcon = ({size, color}: {size: number; color: string}) =>
  <svg width={size} height={size} viewBox="0 0 12 12"><path d="M3 2L10 6L3 10V2Z" fill={color} stroke={color} strokeWidth={1.5} strokeLinejoin="round"/></svg>;
const POINTER = 'M4.037 4.688a.495.495 0 0 1 .651-.651l16 6.5a.5.5 0 0 1-.063.947l-6.124 1.58a2 2 0 0 0-1.438 1.435l-1.579 6.126a.5.5 0 0 1-.947.063z';
const DASHED = ['M10.1 2.182a10 10 0 0 1 3.8 0', 'M13.9 21.818a10 10 0 0 1-3.8 0', 'M17.609 3.721a10 10 0 0 1 2.69 2.7', 'M2.182 13.9a10 10 0 0 1 0-3.8',
  'M20.279 17.609a10 10 0 0 1-2.7 2.69', 'M21.818 10.1a10 10 0 0 1 0 3.8', 'M3.721 6.391a10 10 0 0 1 2.7-2.69', 'M6.391 20.279a10 10 0 0 1-2.69-2.7'];

// ------------------------------------------------------------------ nodes
// A card (canvas node): rounded panel with a thin inner stroke at rest and a stronger one when selected, no shadow, selection
// snaps. Header: icon, title, and a right-aligned model label in the muted colour.
export type NodeProps = {x: number; y: number; w: number; h: number; kind?: 'image' | 'video' | 'deck' | 'text'; title?: string; model?: string; selected?: boolean; ring?: string; opacity?: number; flowW?: number; headerOpacity?: number; icon?: React.ReactNode; titleRight?: boolean; children?: React.ReactNode};
// flowW: the card's width in canvas px (a standard image card is 384), so the corner radius scales with the zoom it implies.
export function Card({x, y, w, h, kind = 'image', title, model, selected = false, ring, opacity = 1, flowW = 384, headerOpacity = 1, icon, titleRight = false, children}: NodeProps) {
  const r = RADIUS * (w / flowW);
  const fs = 12 * S, lh = 15 * S, mid = y - 12.98 * S;
  const tc = selected ? UI.titleSel : UI.title, ic = selected ? UI.iconSel : UI.icon;
  return <div style={{position: 'absolute', left: 0, top: 0, opacity}}>
    {(title || model) && headerOpacity > 0.001 && <div style={{position: 'absolute', left: x, top: mid - lh / 2, width: w, height: lh, opacity: headerOpacity, display: 'grid', gridTemplateColumns: '1fr auto', columnGap: 12 * S, alignItems: 'center', fontFamily: FONT_BODY, fontSize: fs, lineHeight: `${lh}px`, letterSpacing: -0.32 * S, whiteSpace: 'nowrap'}}>
      <div style={{display: 'flex', alignItems: 'center', minWidth: 0}}>
        <div style={{minWidth: icon ? 0 : 12 * S, height: 12 * S, flexShrink: 0, display: 'grid', placeItems: 'center start'}}>{icon ?? (kind === 'video' ? <PlayIcon size={12 * S} color={ic}/> : kind === 'deck' ? <DeckIcon size={12 * S} color={ic}/> : kind === 'text' ? <TextIcon size={12 * S} color={ic}/> : <ImageIcon size={12 * S} color={ic}/>)}</div>
        {!titleRight && <div style={{marginLeft: 6 * S, color: tc, overflow: 'hidden', textOverflow: 'ellipsis'}}>{title}</div>}
      </div>
      {titleRight ? <div style={{color: tc, textAlign: 'right'}}>{title}</div>
        : model && <div style={{color: UI.model, maxWidth: 120 * S, overflow: 'hidden', textOverflow: 'ellipsis', textAlign: 'right'}}>{model}</div>}
    </div>}
    <div style={{position: 'absolute', left: x, top: y, width: w, height: h, borderRadius: r, overflow: 'hidden', background: UI.card}}>
      {children}
      <div style={{position: 'absolute', inset: 0, borderRadius: r, boxShadow: `inset 0 0 0 ${selected ? 3 : 2}px ${selected ? UI.borderSel : UI.borderRest}`}}/>
      {ring && <div style={{position: 'absolute', inset: 0, borderRadius: r, boxShadow: `inset 0 0 0 3px ${ring}`}}/>}
    </div>
  </div>;
}

// ------------------------------------------------------------------ handles, geometry in canvas px x card scale
// Ring r10 in a 24 quad. Optional input: CircleDashed (stroke 1.5); connected: centre dot r3.84. Output: ring + plus (arms 4, stroke 2).
// Revealed with a 150 ms slide of 28 flow px out from behind the card plus fade.
export function Handle({cx, cy, scale, kind, reveal, connected = false, label}: {cx: number; cy: number; scale: number; kind: 'in' | 'out'; reveal: number; connected?: boolean; label?: string}) {
  if (reveal <= 0.001) return null;
  const k = scale;                      // video px per flow px
  const slide = (1 - reveal) * 28 * k * (kind === 'in' ? 1 : -1);
  const x = cx + slide, size = 24 * k, col = reveal > 0.99 ? UI.handleOn : UI.handle;
  return <g opacity={reveal} transform={`translate(${x - size / 2} ${cy - size / 2}) scale(${size / 24})`}>
    {kind === 'out'
      ? <><circle cx={12} cy={12} r={10} fill={UI.canvas} stroke={UI.plus} strokeWidth={2}/><path d="M12 8v8M8 12h8" stroke={UI.plus} strokeWidth={2} strokeLinecap="round"/></>
      : <>{connected ? <circle cx={12} cy={12} r={10} fill={UI.canvas} stroke={col} strokeWidth={2}/> : <g fill="none" stroke={col} strokeWidth={1.5} strokeLinecap="round">{DASHED.map((d, i) => <path key={i} d={d}/>)}</g>}
          {connected && <circle cx={12} cy={12} r={3.84} fill={col}/>}</>}
    {label && kind === 'in' && <text x={-4} y={12} textAnchor="end" dominantBaseline="central" fill={UI.handleOn} fontFamily={FONT_BODY} fontWeight={500} fontSize={12 * S / (size / 24)} letterSpacing={-0.12}>{label}</text>}
  </g>;
}

// ------------------------------------------------------------------ edges
export const edgeCurve = (sx: number, sy: number, tx: number, ty: number) => { const d = tx - sx; const off = d >= 0 ? 0.5 * d : 6.25 * Math.sqrt(-d); return [sx, sy, sx + off, sy, tx - off, ty, tx, ty]; };
const at = (q: number[], t: number): [number, number] => { const m = 1 - t; return [m * m * m * q[0] + 3 * m * m * t * q[2] + 3 * m * t * t * q[4] + t * t * t * q[6], m * m * m * q[1] + 3 * m * m * t * q[3] + 3 * m * t * t * q[5] + t * t * t * q[7]]; };
const samples = (q: number[], n = 64) => Array.from({length: n + 1}, (_, i) => at(q, i / n));
// Draw-in: 350 ms, p = 1-(1-x)^2 along the curve parameter. Selected edges: 2px at 75% white (scaled for video legibility).
export function Edge({q, since, fps, width = 2.5, color = UI.edgeSel, packetScale = 1, drag = false}: {q: number[]; since: number; fps: number; width?: number; color?: string; packetScale?: number; drag?: boolean}) {
  const x = Math.min(1, Math.max(0, since / (0.35 * fps))), p = 1 - (1 - x) * (1 - x);
  const pts = samples(q, 64); const cut = Math.max(1, Math.round(64 * p));
  const d = 'M' + pts.slice(0, cut + 1).map(([a, b]) => `${a.toFixed(1)} ${b.toFixed(1)}`).join(' L');
  if (drag) return <path d={d} fill="none" stroke={COLORS.ink} strokeWidth={2} strokeDasharray="8 16" strokeDashoffset={-since / fps * 40} strokeLinecap="round"/>;
  // one running packet after the edge lands: R = min(50, len/3), solid to 0.4R, 0.25 at R, 600 flow px/s
  const lens = [0]; for (let i = 1; i < pts.length; i++) lens.push(lens[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  const L = lens[lens.length - 1], R = Math.min(50 * packetScale, L / 3);
  const tp = (since - 0.35 * fps) / fps, c = -1.4 * R + tp * 600 * packetScale;
  const segs: React.ReactNode[] = [];
  if (p >= 1 && c < L + 1.4 * R && tp >= 0) for (let i = 1; i < pts.length; i++) {
    const m = (lens[i] + lens[i - 1]) / 2, dist = Math.abs(m - c);
    const a = dist <= 0.4 * R ? 1 : dist <= R ? 1 - 0.75 * (dist - 0.4 * R) / (0.6 * R) : 0;
    if (a > 0) segs.push(<line key={i} x1={pts[i - 1][0]} y1={pts[i - 1][1]} x2={pts[i][0]} y2={pts[i][1]} stroke={COLORS.ink} strokeOpacity={a} strokeWidth={width + 0.5} strokeLinecap="round"/>);
  }
  return <g><path d={d} fill="none" stroke={color} strokeWidth={width} strokeLinecap="round"/>{segs}</g>;
}

// ------------------------------------------------------------------ presence cursor
// A pointer in the user's colour (16px, fill + stroke) with a name pill 16px down/right: radius 8, border in the colour, colour
// at 25% fill, colour text, 4x8 padding, 16px blur.
// press < 1 briefly shrinks the pointer about its tip on a click.
export function Cursor({x, y, color = PRESENCE, name = 'You', opacity = 1, press = 1}: {x: number; y: number; color?: string; name?: string; opacity?: number; press?: number}) {
  const sz = 16 * S, u = sz / 24;
  return <div style={{position: 'absolute', left: x - 4.037 * u, top: y - 4.688 * u, opacity, pointerEvents: 'none', transform: `scale(${press})`, transformOrigin: `${4.037 * u}px ${4.688 * u}px`}}>
    <svg width={sz} height={sz} viewBox="0 0 24 24"><path d={POINTER} fill={color} stroke={color} strokeWidth={2} strokeLinejoin="round"/></svg>
    <div style={{position: 'absolute', left: 16 * S, top: 16 * S, padding: `${4 * S}px ${8 * S}px`, borderRadius: 8 * S, border: `${1.5}px solid ${color}`, background: rgba(color, 0.25), color, fontFamily: FONT_BODY, fontSize: 12 * S, lineHeight: `${16.5 * S}px`, whiteSpace: 'nowrap', backdropFilter: 'blur(16px)'}}>{name}</div>
  </div>;
}

// ------------------------------------------------------------------ tooltip: in 150 ms, opacity + scale .95 -> 1
export const BADGE: React.CSSProperties = {padding: `${4 * S}px ${8 * S}px`, borderRadius: 8 * S, border: `1.5px solid ${UI.tipBorder}`, background: UI.tipBg, color: UI.tipText, fontFamily: FONT_BODY, fontSize: 12 * S, lineHeight: 1.375, fontWeight: 500, whiteSpace: 'nowrap'};
export function Tooltip({x, y, text, t, side = 'top'}: {x: number; y: number; text: string; t: number; side?: 'top' | 'right' | 'left' | 'bottom'}) {
  if (t <= 0.001) return null;
  const tr = side === 'top' ? 'translate(-50%, calc(-100% - 6px))' : side === 'bottom' ? 'translate(-50%, 6px)' : side === 'right' ? 'translate(10px, -50%)' : 'translate(calc(-100% - 10px), -50%)';
  return <div style={{position: 'absolute', left: x, top: y, transform: `${tr} scale(${0.95 + 0.05 * t})`, opacity: t, pointerEvents: 'none', ...BADGE}}>{text}</div>;
}

// ------------------------------------------------------------------ text label, outline mode
export function Label({x, y, text, color = COLORS.ink, selected = 0, size = 14}: {x: number; y: number; text: string; color?: string; selected?: number; size?: number}) {
  return <div style={{position: 'absolute', left: x, top: y, padding: `${4 * S}px ${8 * S}px`, borderRadius: 8 * S, border: `1px solid ${inkA(0.3 * selected)}`, background: inkA(0.08 * selected), color, fontFamily: FONT_BODY, fontSize: size * S, lineHeight: 1.4, fontWeight: 350, whiteSpace: 'nowrap'}}>{text}</div>;
}

// ------------------------------------------------------------------ group
// Frame: rounded panel with a faint fill and a thin inset border. Header badge: screen-constant, bottom-left on the frame's top
// edge lifted 4px; radius 8, border, 4x8 padding, 12 / 1.375 at 500.
export function Group({x, y, w, h, label, zoom, opacity = 1}: {x: number; y: number; w: number; h: number; label?: string; zoom: number; opacity?: number}) {
  const r = RADIUS * zoom;
  return <div style={{position: 'absolute', left: 0, top: 0, opacity}}>
    <div style={{position: 'absolute', left: x, top: y, width: w, height: h, borderRadius: r, background: UI.groupFill, boxShadow: `inset 0 0 0 1.5px ${UI.groupBorder}`}}/>
    {label && <div style={{position: 'absolute', left: x, top: y - 4 * S, transform: 'translateY(-100%)', ...BADGE}}>{label}</div>}
  </div>;
}
export const GROUP_HEADER_H = (12 * 1.375 + 8) * S + 3 + 4 * S;   // badge height + lift

// ------------------------------------------------------------------ note: a text label with an accent fill
// The accent at 80% behind dark text; rounded, 4x8 padding, 14 / 1.4 at 350, backdrop blur. zoom = canvas zoom (the note scales with it).
export function Note({x, y, w, lines, zoom = 1, color = ACCENT.join(' '), opacity = 1}: {x: number; y: number; w?: number; lines: string[]; zoom?: number; color?: string; opacity?: number}) {
  const k = zoom * S;
  return <div style={{position: 'absolute', left: x, top: y, width: w, boxSizing: 'border-box', padding: `${4 * k}px ${8 * k}px`, borderRadius: 8 * k, background: `rgb(${color} / 0.8)`, backdropFilter: 'blur(12px)', color: COLORS.background, fontFamily: FONT_BODY, fontSize: 14 * k, lineHeight: 1.4, fontWeight: 350, opacity}}>
    {lines.map((l, i) => <div key={i} style={{whiteSpace: 'nowrap'}}>{l}</div>)}
  </div>;
}
