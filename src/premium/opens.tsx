// Openers. Pick one per film (skill/references/beat-library.md): the pixel cold open for a talk with a hero image,
// the hook open for a recording, or a partner lockup for a collaboration piece. All leave before the first beat rises.
import React from 'react';
import {AbsoluteFill, Easing, Img, OffthreadVideo, Sequence, interpolate, staticFile, useVideoConfig} from 'remotion';
import {Dither, TextSpec} from '../dither';
import {BRAND, INK_RGB, brandFile, isVideoFile} from '../theme';
import {Box, E, GENTLE, k, stepped} from './core';

/**
 * The brand logo in a corner: the animated logo (a video, screened over dark) if the brand has one, else the mark or wordmark
 * image, else nothing. `logo` overrides: a file under public/ (video or image), or null for no logo.
 */
export function CornerLogo({logo, style}: {logo?: string | null; style: React.CSSProperties}) {
  const file = logo === undefined ? (BRAND.logo.animated ?? BRAND.logo.mark ?? BRAND.logo.wordmark) : logo;
  if (!file) return null;
  const src = logo === undefined ? brandFile(file) : staticFile(file);
  if (!src) return null;
  return isVideoFile(file)
    ? <OffthreadVideo src={src} muted style={{...style, mixBlendMode: 'screen'}}/>
    : <Img src={src} style={{objectFit: 'contain', objectPosition: 'left center', ...style}}/>;
}
import {Clip} from './stage';

/**
 * Pixel open: the hero image and the title arrive as ordered-dither pixels that switch on outward, burn bright, glow, then
 * sharpen in whole steps into the real thing; the brand logo (if any) sits small in the top-left corner. At `out` the title and
 * logo lift away, then the hero glides into `glide.to` (usually the result node of the first beat) or fades if there is none.
 * The first ~1.5 s is silent (the film's lead); the voice starts as the title leaves.
 */
export function PixelOpen({t, hero, title, out, glide, heroBox = {x: 1090, y: 170, w: 740, h: 740}, titleBox = {x: 96, y: 412, w: 900, h: 260},
  titleAt = 0.6, logo}:
  {t: number; hero: string; title: TextSpec; out: number; glide?: {to: Box; at?: number; dur?: number}; heroBox?: Box; titleBox?: Box; titleAt?: number; logo?: string | null}) {
  const {fps} = useVideoConfig();
  const moveAt = glide?.at ?? out + 0.3, moveEnd = moveAt + (glide?.dur ?? 1.1);
  if (t > (glide ? moveEnd + 0.4 : out + 0.8)) return null;
  const lift = k(t, out, out + 0.45, 0, 1, E.in);
  const mv = glide ? k(t, moveAt, moveEnd, 0, 1, E.inOut) : 0;
  const to = glide?.to ?? heroBox;
  const r = {x: heroBox.x + (to.x - heroBox.x) * mv, y: heroBox.y + (to.y - heroBox.y) * mv, w: heroBox.w + (to.w - heroBox.w) * mv, h: heroBox.h + (to.h - heroBox.h) * mv};
  // hero: cells switch on outward, sharpen in whole steps, fill in solid, then hand over to the sharp image underneath
  const hp = {reveal: k(t, 0.2, 1.6, 0, 1, Easing.linear), block: stepped(t, [[0, 8], [1.1, 6], [1.4, 4], [1.65, 3], [1.85, 2], [2.05, 1]]),
    fill: k(t, 1.55, 2.05, 0, 1, Easing.linear), lift: 1.15 - 0.15 * k(t, 1.6, 2.1, 0, 1), burn: 0.9 * (1 - k(t, 1.4, 1.9, 0, 1)),
    crisp: k(t, 2.05, 2.5, 0, 1, Easing.linear), glow: 0.12 + 0.55 * (1 - k(t, 1.2, 2.3, 0, 1)), gain: 1.1, spread: 0.72};
  const ti = {reveal: k(t, titleAt, titleAt + 1.0, 0, 1, Easing.linear), block: stepped(t, [[0, 5], [1.3, 3], [1.55, 2]]),
    burn: 0.9 * (1 - k(t, 1.3, 1.7, 0, 1)),
    crisp: k(t, 1.7, 2.1, 0, 1, Easing.linear), glow: 0.45 * (1 - k(t, 1.2, 2.0, 0, 1)), ink: INK_RGB, cx: 0, cy: 0.5, spread: 0.6};
  const heroOut = glide ? 1 : 1 - lift;
  return <AbsoluteFill>
    {(glide ? t < moveEnd + 0.35 : true) && <div style={{position: 'absolute', left: r.x, top: r.y, width: r.w, height: r.h, borderRadius: 24 * (r.w / 384), overflow: 'hidden', opacity: heroOut}}>
      <Dither src={hero} x={0} y={0} w={r.w} h={r.h} p={hp}/>
    </div>}
    {lift < 1 && <div style={{position: 'absolute', inset: 0, opacity: 1 - lift, transform: `translateY(${-14 * lift}px)`, filter: lift > 0.01 ? `blur(${3 * lift}px)` : undefined}}>
      <Dither text={title} x={titleBox.x} y={titleBox.y} w={titleBox.w} h={titleBox.h} p={ti}/>
      {logo !== null && <Sequence from={0} durationInFrames={Math.round(out * fps) + 14} layout="none">
        <CornerLogo logo={logo} style={{position: 'absolute', left: 79, top: 60, width: 181, height: 51}}/>
      </Sequence>}
    </div>}
  </AbsoluteFill>;
}

/**
 * Partner lockup (brand × partner): parts rise out of a blur one after another, centred; a `grow` layer (e.g. a logo's rays)
 * is revealed radially from `origin` (0..1 of the part). Holds under the first words and melts at out[0]..out[1].
 */
export type LockupPart = {src: string; h: number; grow?: {src: string; origin: [number, number]}};
export function Lockup({t, parts, out, gap = 56}: {t: number; parts: LockupPart[]; out: readonly [number, number]; gap?: number}) {
  if (t > out[1] + 0.05) return null;
  const f = t * 30, o = k(t, out[0], out[1], 0, 1, E.in);
  const ease = Easing.bezier(0.22, 1, 0.36, 1);
  const c = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
  return <AbsoluteFill style={{display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: 1 - o, transform: `translateY(${-14 * o}px)`, filter: o > 0.01 ? `blur(${4 * o}px)` : undefined}}>
    <div style={{display: 'flex', alignItems: 'center', gap}}>
      {parts.map((l, i) => { const at = 3 + i * 8, p = interpolate(f, [at, at + 13], [0, 1], {...c, easing: ease});
        const r = l.grow ? interpolate(f, [at + 4, at + 40], [0, 104], {...c, easing: ease}) : 0;
        const mask = l.grow ? `radial-gradient(circle at ${l.grow.origin[0] * 100}% ${l.grow.origin[1] * 100}%, #000 ${r - 4}%, transparent ${r}%)` : '';
        return <div key={i} style={{position: 'relative', height: l.h, flexShrink: 0}}>
          <Img src={staticFile(l.src)} style={{height: l.h, width: 'auto', display: 'block', opacity: p, transform: `translateY(${(1 - p) * 16}px)`, filter: `blur(${(1 - p) * 9}px)`}}/>
          {l.grow && <Img src={staticFile(l.grow.src)} style={{position: 'absolute', inset: 0, width: '100%', height: '100%', WebkitMaskImage: mask, maskImage: mask} as React.CSSProperties}/>}
        </div>; })}
    </div>
  </AbsoluteFill>;
}

/**
 * Hook open (the default opener): the recording's best moments full frame, with the speaker's own strongest
 * lines as the hook's audio. The first shot resolves from full-frame dither pixels from its still (quick, ~0.85 s) and plays
 * at 1x; each later shot hard-cuts (0.12 s) in at its `at`. The two-line title card resolves from dither pixels over a left scrim at `titleAt`
 * and lifts at `out`; everything melts into the grid over `fade`. A soft bottom scrim sits under the hook captions (render
 * them with <Captions center={CAP_HOOK} …/>). The logo sits outside every filtered layer (a screen blend inside a
 * filtered group shows its black box). Crop footage so no burned-in UI/HUD text meets the logo or the title.
 */
export type HookShot = {src: string; at: number; start?: number};   // the first shot's `at` is ignored: it starts as the dither resolves
export function HookOpen({t, still, shots, title, titleAt, out, fade, titleBox = {x: 96, y: 372, w: 900, h: 272}, ditherEnd = 0.85, logo}:
  {t: number; still: string; shots: HookShot[]; title: TextSpec; titleAt: number; out: number; fade: readonly [number, number];
   titleBox?: Box; ditherEnd?: number; logo?: string | null}) {
  const {fps} = useVideoConfig();
  if (t > fade[1] + 0.05) return null;
  const full = {position: 'absolute', inset: 0, width: 1920, height: 1080, objectFit: 'cover'} as React.CSSProperties;
  const d = ditherEnd;
  const hp = {reveal: k(t, 0.05, d * 0.6, 0, 1, Easing.linear), block: stepped(t, [[0, 12], [d * 0.33, 8], [d * 0.47, 6], [d * 0.59, 4], [d * 0.68, 3], [d * 0.78, 2], [d * 0.87, 1]]),
    fill: k(t, d * 0.5, d * 0.8, 0, 1, Easing.linear), lift: 1.15 - 0.15 * k(t, d * 0.59, d * 0.92, 0, 1), burn: 0.9 * (1 - k(t, d * 0.45, d * 0.78, 0, 1)),
    crisp: k(t, d * 0.85, d, 0, 1, Easing.linear), glow: 0.12 + 0.5 * (1 - k(t, d * 0.35, d, 0, 1)), gain: 1.1, spread: 0.72};
  const a = titleAt;
  const ti = {reveal: k(t, a, a + 0.6, 0, 1, Easing.linear), block: stepped(t, [[0, 5], [a + 0.4, 3], [a + 0.55, 2]]), burn: 0.9 * (1 - k(t, a + 0.4, a + 0.75, 0, 1)),
    crisp: k(t, a + 0.7, a + 1.0, 0, 1, Easing.linear), glow: 0.45 * (1 - k(t, a + 0.4, a + 1.0, 0, 1)), ink: INK_RGB, cx: 0, cy: 0.5, spread: 0.6};
  const lift = k(t, out, out + 0.45, 0, 1, E.in);
  const all = shots.map((s, i) => i === 0 ? {...s, at: d} : s);   // the first shot takes over from the dither
  return <AbsoluteFill style={{opacity: k(t, fade[0], fade[1], 1, 0, GENTLE)}}>
    {all.map((s, i) => { const nx = all[i + 1]?.at ?? fade[1] + 0.1;
      if (t < s.at - 0.05 || t > nx + 0.2) return null;
      return <div key={i} style={{position: 'absolute', inset: 0, opacity: i === 0 ? 1 : k(t, s.at, s.at + 0.12, 0, 1, GENTLE)}}>
        <Clip src={s.src} at={s.at} start={s.start ?? 0} style={full}/></div>; })}
    {t < d + 0.05 && <Dither src={still} x={0} y={0} w={1920} h={1080} p={hp}/>}
    <div style={{position: 'absolute', inset: 0, opacity: k(t, (shots[1]?.at ?? d) - 0.2, (shots[1]?.at ?? d) + 0.3, 0, 1),
      background: 'linear-gradient(0deg, rgba(0,0,0,0.62) 0%, rgba(0,0,0,0.25) 16%, rgba(0,0,0,0) 30%)'}}/>
    <div style={{position: 'absolute', inset: 0, opacity: k(t, a - 0.2, a + 0.4, 0, 1) * (1 - lift * 0.6),
      background: 'linear-gradient(90deg, rgba(0,0,0,0.78) 0%, rgba(0,0,0,0.5) 34%, rgba(0,0,0,0) 62%)'}}/>
    {t >= a && lift < 1 && <div style={{position: 'absolute', inset: 0, opacity: 1 - lift, transform: `translateY(${-14 * lift}px)`, filter: lift > 0.01 ? `blur(${3 * lift}px)` : undefined}}>
      <Dither text={title} x={titleBox.x} y={titleBox.y} w={titleBox.w} h={titleBox.h} p={ti}/>
    </div>}
    {logo !== null && <Sequence from={0} durationInFrames={Math.round((out + 0.5) * fps)} layout="none">
      <CornerLogo logo={logo} style={{position: 'absolute', left: 79, top: 60, width: 181, height: 51, opacity: 1 - lift}}/>
    </Sequence>}
  </AbsoluteFill>;
}
