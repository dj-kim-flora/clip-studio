// Closing beats: a checklist the agent ticks off, and the outro end card.
import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, Sequence, useCurrentFrame, useVideoConfig} from 'remotion';
import {BRAND, COLORS, DISPLAY_WEIGHT, FONT_BODY, MOTION, brandFile, inkA, isVideoFile} from '../theme';
import {Backdrop} from '../ui';
import {DISPLAY, E, INK, Micro, NOTE, POP, Rise, accent, k} from './core';

/**
 * Recap checklist on the stage: rows (display title with one italic word, a note-voice sub) arrive on the words that name
 * them, over hairlines that draw in; at `ticksAt` the boxes fill with the accent colour and tick one after another
 * (e.g. on "have the agent help you out"). Titles that echo the step words tie the recap back to the steps.
 */
export function Checklist({t, items, ticksAt, label, x = 1080, y = 262, pitch = 112, w = 750, labelY = 206, labelAt, stagger = 0.25}:
  {t: number; items: Array<{title: React.ReactNode; sub: string; at: number}>; ticksAt: number; label?: string; x?: number; y?: number; pitch?: number; w?: number;
   labelY?: number; labelAt?: number; stagger?: number}) {
  if (t < Math.min(...items.map(i => i.at)) - 1) return null;
  const la = labelAt ?? Math.min(...items.map(i => i.at)) - 0.2;
  return <>
    {label && <Micro x={x} y={labelY} o={k(t, la, la + 0.5, 0, 1)}>{label}</Micro>}
    {items.map((c, i) => {
      const a = c.at, o = k(t, a, a + 0.6, 0, 1), yy = y + i * pitch;
      const tk = ticksAt + stagger * i, on = k(t, tk, tk + 0.18, 0, 1, POP), draw = k(t, tk + 0.05, tk + 0.35, 0, 1);
      return <React.Fragment key={i}>
        <div style={{position: 'absolute', left: x, top: yy - 18, width: w * k(t, a - 0.1, a + 0.7, 0, 1), height: 1, background: inkA(0.12)}}/>
        <div style={{position: 'absolute', left: x, top: yy, opacity: o, transform: `translateY(${(1 - o) * 12}px)`}}>
          <div style={{position: 'absolute', left: 0, top: 9, width: 30, height: 30, borderRadius: 9, background: `${accent(0.25 * on)}`,
            boxShadow: `inset 0 0 0 1.5px ${inkA(0.28 * (1 - on))}, inset 0 0 0 1.5px ${accent(on)}`}}>
            {draw > 0.001 && <svg width={30} height={30} viewBox="0 0 30 30" style={{position: 'absolute', inset: 0}}>
              <path d="M8.5 15.5l4.2 4.2L21.5 10.5" fill="none" stroke={INK} strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" pathLength={1} strokeDasharray={`${draw} 1`}/>
            </svg>}
          </div>
          <div style={{position: 'absolute', left: 54, top: 0, fontFamily: DISPLAY, fontSize: 44, lineHeight: 1.1, letterSpacing: '-0.02em', color: INK, whiteSpace: 'nowrap'}}>{c.title}</div>
          <div style={{position: 'absolute', left: 56, top: 58, ...NOTE, whiteSpace: 'nowrap'}}>{c.sub}</div>
        </div>
      </React.Fragment>;
    })}
  </>;
}

/**
 * Outro end card over the brand backdrop: the animated logo (if the brand has one), else the wordmark or mark image, then the
 * outro line in display type and the handle under it, and an optional call-to-action pill. Text defaults to brand.outro.
 * Starts at film time `at` and lasts `duration` s (3.2 by default). Sizes are design px on a 1080 canvas, scaled to the frame.
 */
export function OutroCard({t, at, duration = 3.2, line, handle, cta, backdrop = true}:
  {t: number; at: number; duration?: number; line?: string | null; handle?: string | null; cta?: string | null; backdrop?: boolean}) {
  const {fps} = useVideoConfig();
  if (t < at - 0.05 || t > at + duration + 0.05) return null;
  return <Sequence from={Math.round(at * fps)} durationInFrames={Math.max(1, Math.round(duration * fps))} layout="none">
    <OutroCardBody line={line ?? BRAND.outro.line} handle={handle ?? BRAND.outro.handle} cta={cta ?? BRAND.outro.cta} backdrop={backdrop}/>
  </Sequence>;
}

function OutroCardBody({line, handle, cta, backdrop}: {line: string; handle: string; cta: string; backdrop: boolean}) {
  const f = useCurrentFrame(), {fps, width, height} = useVideoConfig();
  const t = f / fps, u = Math.min(width, height) / 1080;
  const fade = k(t, 0, 0.35 * MOTION, 0, 1, E.out);
  const animated = brandFile(BRAND.logo.animated), still = brandFile(BRAND.logo.wordmark ?? BRAND.logo.mark);
  const stillStyle: React.CSSProperties = {height: 150 * u, maxWidth: width * 0.7, objectFit: 'contain', display: 'block'};
  const lines = line ? line.split('\n') : [];
  const size = (BRAND.style.headlineCase === 'upper' ? 84 : 96) * u;
  const text = (s: string) => (BRAND.style.headlineCase === 'upper' ? s.toUpperCase() : s);
  return <AbsoluteFill style={{opacity: fade}}>
    {backdrop && <Backdrop/>}
    <AbsoluteFill style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 36 * u}}>
      {animated && BRAND.logo.animated && isVideoFile(BRAND.logo.animated)
        ? <OffthreadVideo src={animated} muted style={{height: 220 * u, maxWidth: width * 0.8, objectFit: 'contain', mixBlendMode: 'screen'}}/>
        : animated ? <Img src={animated} style={stillStyle}/> : still ? <Img src={still} style={stillStyle}/> : null}
      {lines.length > 0 && <div style={{position: 'relative', width: width * 0.86, height: lines.length * size * 1.1}}>
        <Rise t={t} at={0.25 * MOTION} lines={lines.map(text)} size={size} x={0} y={0} w={width * 0.86} align="center" dur={0.9 * MOTION} lh={1.1} weight={DISPLAY_WEIGHT}/>
      </div>}
      {handle && <div style={{fontFamily: DISPLAY, fontWeight: DISPLAY_WEIGHT, fontSize: 46 * u, color: COLORS.accentInk, letterSpacing: '-0.01em', opacity: k(t, 0.7 * MOTION, 1.2 * MOTION, 0, 1), transform: `translateY(${k(t, 0.7 * MOTION, 1.3 * MOTION, 14, 0) * u}px)`}}>{handle}</div>}
      {cta && <div style={{fontFamily: FONT_BODY, fontWeight: 600, fontSize: 32 * u, color: COLORS.accentInk, padding: `${10 * u}px ${24 * u}px`, borderRadius: 999,
        background: COLORS.accentFill, border: `${1.5 * u}px solid ${accent(0.9)}`, opacity: k(t, 1.0 * MOTION, 1.5 * MOTION, 0, 1)}}>{cta}</div>}
    </AbsoluteFill>
  </AbsoluteFill>;
}
