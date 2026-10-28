// The clip-farm workhorse: one short vertical (or square, 4:5, 16:9) clip from a cut video, its dialogue, word-timed captions,
// an opening hook line, a lower third, a progress bar and an end card. Everything is driven by the brief (see ./types.ts)
// and the brand theme; all sizes are designed on a 1080 px short side and scaled to the frame.
// Render: npx remotion render src/index.tsx Clip _work/<slug>-raw.mp4 --props=briefs/<slug>.clip.json
import React from 'react';
import {AbsoluteFill, Audio, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {COLORS, DISPLAY_WEIGHT, FONT_BODY, FONT_DISPLAY, MOTION, STYLE, accent, rgba} from '../theme';
import {Backdrop} from '../ui';
import {E, GENTLE, Rise, k} from '../premium/core';
import {OutroCard} from '../premium/closers';
import {Captions} from './captions';
import {measure, wrap, zones, Zones} from './layout';
import {CLIP_DEFAULTS, ClipProps} from './types';

const fill: React.CSSProperties = {position: 'absolute', left: 0, top: 0, width: '100%', height: '100%', objectFit: 'cover', display: 'block'};
const Vid = ({src, style}: {src: string; style: React.CSSProperties}) => <OffthreadVideo src={staticFile(src)} muted style={style}/>;

/** the picture: one video filling the frame, two stacked, or one fitted over a blurred copy of itself */
function Picture({p, z}: {p: ClipProps; z: Zones}) {
  const layout = p.layout ?? 'fill';
  if (!p.video) return <Backdrop variant={STYLE.backdrop === 'solid' ? 'gradient' : STYLE.backdrop}/>;
  if (layout === 'split') {
    const ratio = Math.min(0.8, Math.max(0.2, p.splitRatio ?? 0.5));
    const topH = Math.round(z.h * ratio);
    return <AbsoluteFill style={{background: COLORS.background}}>
      <div style={{position: 'absolute', left: 0, top: 0, width: z.w, height: topH, overflow: 'hidden'}}><Vid src={p.video} style={fill}/></div>
      <div style={{position: 'absolute', left: 0, top: topH, width: z.w, height: z.h - topH, overflow: 'hidden'}}>
        {p.video2 ? <Vid src={p.video2} style={fill}/> : <Backdrop variant="gradient"/>}
      </div>
      <div style={{position: 'absolute', left: 0, top: topH - 3 * z.u, width: z.w, height: 6 * z.u, background: COLORS.accent}}/>
    </AbsoluteFill>;
  }
  if (layout === 'blurfill') {
    return <AbsoluteFill style={{background: COLORS.background}}>
      <div style={{position: 'absolute', inset: 0, overflow: 'hidden'}}>
        <Vid src={p.video} style={{...fill, transform: 'scale(1.3)', filter: `blur(${36 * z.u}px) brightness(0.55) saturate(1.1)`}}/>
      </div>
      <Vid src={p.video} style={{...fill, objectFit: 'contain'}}/>
    </AbsoluteFill>;
  }
  return <Vid src={p.video} style={fill}/>;
}

/** the opening line: big display type rising into the upper part of the frame, leaving at hook.to */
function Hook({t, hook, pos, z}: {t: number; hook: NonNullable<ClipProps['hook']>; pos: string; z: Zones}) {
  const text = (hook.text || '').trim();
  const from = hook.from ?? 0, to = hook.to ?? from + 2.4;
  if (!text || t < from - 0.05 || t > to + 0.1) return null;
  const upper = STYLE.headlineCase === 'upper';
  const words = (upper ? text.toUpperCase() : text).split(/\s+/);
  const maxW = z.w - 2 * z.side;
  let size = 108 * z.u, lines: string[][] = [];
  for (; size >= 52 * z.u; size -= 4 * z.u) {
    lines = wrap(words, maxW, s => measure(s, size, FONT_DISPLAY, DISPLAY_WEIGHT));
    const widest = Math.max(...lines.map(l => measure(l.join(' '), size, FONT_DISPLAY, DISPLAY_WEIGHT)));
    if (lines.length <= 4 && widest <= maxW) break;
  }
  const lh = 1.08, blockH = lines.length * size * lh;
  const centre = pos === 'upper' ? z.h * 0.5 : z.h * 0.3;
  const y = Math.max(z.top + 24 * z.u, centre - blockH / 2);
  const outAt = Math.max(from + 0.9, to - 0.45);
  const scrim = k(t, from, from + 0.3, 0, 1) * k(t, outAt, to, 1, 0, GENTLE);
  return <>
    <AbsoluteFill style={{pointerEvents: 'none', opacity: scrim, background: `linear-gradient(180deg, ${rgba(COLORS.background, 0.7)} 0%, ${rgba(COLORS.background, 0.45)} ${Math.round((y + blockH + 60 * z.u) / z.h * 100)}%, transparent ${Math.round((y + blockH + 260 * z.u) / z.h * 100)}%)`}}/>
    <Rise t={t} at={from + 0.05} out={outAt} outDur={Math.max(0.2, to - outAt)} lines={lines.map(l => l.join(' '))} size={size} x={z.side} y={y} w={maxW}
      align="center" lh={lh} dur={0.8 * MOTION} stagger={0.09 * MOTION} weight={DISPLAY_WEIGHT} shadow={`0 ${3 * z.u}px ${26 * z.u}px rgba(0,0,0,0.55)`}/>
  </>;
}

/** name and role on a small panel with an accent bar, sliding in from the left */
function LowerThird({t, lt, bottom, z}: {t: number; lt: NonNullable<ClipProps['lowerThird']>; bottom: number; z: Zones}) {
  const name = (lt.name ?? '').trim(), role = (lt.role ?? '').trim();
  const from = lt.from ?? 1, to = lt.to ?? from + 4;
  if ((!name && !role) || t < from - 0.05 || t > to + 0.1) return null;
  const p = k(t, from, from + 0.5 * MOTION, 0, 1, E.out) * k(t, to - 0.4, to, 1, 0, GENTLE);
  const inn = k(t, from, from + 0.5 * MOTION, 0, 1, E.out);
  const u = z.u;
  return <div style={{position: 'absolute', left: z.side, bottom: z.h - bottom, opacity: p, transform: `translateX(${(1 - inn) * -40 * u}px)`,
    display: 'flex', alignItems: 'stretch', gap: 18 * u, padding: `${16 * u}px ${28 * u}px ${18 * u}px ${20 * u}px`, borderRadius: STYLE.radius * u * 0.8,
    background: rgba(COLORS.background, 0.62), backdropFilter: `blur(${12 * u}px)`, maxWidth: z.w - 2 * z.side}}>
    <div style={{width: 8 * u, borderRadius: 4 * u, background: COLORS.accent, transform: `scaleY(${inn})`, transformOrigin: 'bottom'}}/>
    <div style={{fontFamily: FONT_BODY}}>
      {name && <div style={{fontSize: 44 * u, fontWeight: 700, lineHeight: 1.15, color: COLORS.ink, letterSpacing: '-0.01em'}}>{name}</div>}
      {role && <div style={{fontSize: 30 * u, fontWeight: 500, lineHeight: 1.3, color: COLORS.accentInk, marginTop: name ? 2 * u : 0}}>{role}</div>}
    </div>
  </div>;
}

export const Clip: React.FC<ClipProps> = props => {
  const p: ClipProps = {...CLIP_DEFAULTS, ...props};
  const frame = useCurrentFrame(), {fps, width, height} = useVideoConfig();
  const t = frame / fps;
  const z = zones(width, height, p.safeZone);
  const seconds = Math.max(0.1, p.seconds);
  const outro = p.outro ? {seconds: p.outro.seconds ?? 2.5, ...p.outro} : null;
  const total = seconds + (outro?.seconds ?? 0);
  const capStyle = p.captionStyle ?? STYLE.captionStyle;
  const capPos = p.captionPos ?? 'lower';
  const cues = p.captions ?? [];
  const barY = z.bottom - 10 * z.u;
  const bodyFade = outro ? k(t, seconds - 0.25, seconds, 1, 0, GENTLE) : 1;
  const music = p.music && p.music.src ? p.music : null;
  const musicVol = (f: number) => (music?.volume ?? 1) * interpolate(f / fps, [total - 0.6, total], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  // the lower third sits just above the captions (or at the bottom edge of the safe area when captions are elsewhere)
  const ltBottom = capPos === 'lower' ? z.bottom - 64 * z.u - 160 * z.u - 24 * z.u : z.bottom - 40 * z.u;
  return <AbsoluteFill style={{background: COLORS.background, fontFamily: FONT_BODY, color: COLORS.ink}}>
    <Sequence from={0} durationInFrames={Math.max(1, Math.round(seconds * fps))} layout="none">
      {p.voice && <Audio src={staticFile(p.voice)}/>}
    </Sequence>
    {music && <Audio src={staticFile(music.src)} volume={musicVol}/>}
    <AbsoluteFill style={{opacity: bodyFade}}>
      <Picture p={p} z={z}/>
      {capStyle !== 'none' && cues.length > 0 && <AbsoluteFill style={{pointerEvents: 'none', background: 'linear-gradient(0deg, rgba(0,0,0,0.42) 0%, rgba(0,0,0,0) 38%)'}}/>}
      {p.hook && <Hook t={t} hook={p.hook} pos={capPos} z={z}/>}
      {p.lowerThird && <LowerThird t={t} lt={p.lowerThird} bottom={ltBottom} z={z}/>}
      {capStyle !== 'none' && cues.length > 0 && <Captions t={t} cues={cues} style={capStyle} pos={capPos} z={z}/>}
      {p.progressBar && <div style={{position: 'absolute', left: z.side, width: z.w - 2 * z.side, top: barY, height: 8 * z.u, borderRadius: 4 * z.u, background: rgba(COLORS.ink, 0.2), overflow: 'hidden'}}>
        <div style={{width: `${Math.min(1, t / seconds) * 100}%`, height: '100%', borderRadius: 4 * z.u, background: COLORS.accent, boxShadow: `0 0 ${12 * z.u}px ${accent(0.5)}`}}/>
      </div>}
    </AbsoluteFill>
    {outro && <OutroCard t={t} at={seconds} duration={outro.seconds} line={outro.line} handle={outro.handle}/>}
  </AbsoluteFill>;
};
