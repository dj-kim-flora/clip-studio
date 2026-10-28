// The speaker on screen: their webcam as a video card (bottom left) and their words beside it as a pinned label. Only for streams where someone talks on camera; a narration-only film (a voiceover case study) has neither.
import React from 'react';
import {Img, OffthreadVideo, Sequence, interpolate, staticFile, useVideoConfig} from 'remotion';
import {BRAND, COLORS, FONT_BODY, brandFile, inkA, rgba} from '../theme';
import type {Brief, CaptionCue} from '../schema';
import {Card, PRESENCE} from '../ui';
import {CAP, FACE, GENTLE, INK, k, wordBox} from './core';

/**
 * Webcam node. brief.face = {src (the stringout the cut builder wrote), crop [x, y, w, h] of the webcam in the stream frame,
 * name}. The header carries the brand mark (13 px) where the card-type icon would be, when the brand has one, and the card
 * wears the presence ring in the accent colour (PRESENCE).
 */
export function FaceNode({t, brief, lead, from, streamSize = [1280, 720], box = FACE}:
  {t: number; brief: Brief; lead: number; from: number; streamSize?: [number, number]; box?: {x: number; y: number; s: number}}) {
  const {fps} = useVideoConfig();
  if (!brief.face) return null;
  const o = k(t, from + 0.05, from + 0.45, 0, 1);
  if (o <= 0.001) return null;
  const c = brief.face.crop; const kk = box.s / c[2];
  const mark = brandFile(BRAND.logo.mark);
  const icon = mark ? <Img src={mark} style={{width: 13, height: 13, display: 'block', objectFit: 'contain', transform: 'translateY(-0.5px)'}}/> : <span/>;   // no brand mark: no icon
  return <Card x={box.x} y={box.y} w={box.s} h={box.s} kind="video" title={brief.face.name} selected ring={PRESENCE} opacity={o} icon={icon}>
    <Sequence from={Math.round(lead * fps)} layout="none">
      <OffthreadVideo src={staticFile(brief.face.src)} muted style={{position: 'absolute', left: -c[0] * kk, top: -c[1] * kk, width: streamSize[0] * kk, height: streamSize[1] * kk, maxWidth: 'none'}}/>
    </Sequence>
  </Card>;
}

/**
 * Captions beside the webcam, bottom-aligned with it, styled as a pinned label (with the pin dot toward the card).
 * The word being said sits in the accent presence pill and hands over word to word with a short crossfade. Through a pause
 * shorter than `hold` the last line stays up (no blinking between lines); after a longer one it melts away.
 */
export function Captions({t, brief, lead, from, until = Infinity, hold = 1.6, x = CAP.x, bottom = CAP.bottom, plain = false, center, size = 34, cueFrom}:
  {t: number; brief: Brief; lead: number; from: number; until?: number; hold?: number; x?: number; bottom?: number; plain?: boolean;
   /** centred one-line mode: the line sits on an axis (cx), vertically centred on cy, within width w */
   center?: {cx: number; cy: number; w: number}; size?: number; cueFrom?: number}) {
  const tb = t - lead; const cues = (brief.captions || []).filter(c => cueFrom === undefined || c.start + lead >= cueFrom);
  if (t < from || t >= until || !cues.length) return null;
  let i = cues.findIndex(c => tb >= c.start && tb < c.end); let a = 1;
  if (i < 0) {
    let p = -1; cues.forEach((c, j) => { if (c.end <= tb) p = j; });
    if (p < 0) return null;
    const next = cues[p + 1];
    if (!(next && next.start - cues[p].end <= hold)) a = k(tb, cues[p].end + 0.25, cues[p].end + 0.6, 1, 0, GENTLE);
    if (a <= 0.001) return null;
    i = p;
  } else if (!(i > 0 && cues[i].start - cues[i - 1].end <= hold)) a = k(tb, cues[i].start, cues[i].start + 0.12, 0, 1);
  const cue: CaptionCue = cues[i];
  const ws = cue.words && cue.words.length ? cue.words : cue.text.split('\n').flatMap((ln, li) => ln.split(' ').map(w => [w, cue.start, cue.end, li] as [string, number, number, number]));
  const lines: React.ReactNode[][] = [];
  ws.forEach(([w, s, e, li], j) => {
    const next = ws[j + 1];
    const until = next ? next[1] : Math.max(e, s + 0.3);
    const on = interpolate(tb, [s - 0.02, s + 0.05], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) * interpolate(tb, [until, until + 0.08], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
    (lines[li] = lines[li] || []).push(<span key={j} style={wordBox(on)}>{w}</span>);
  });
  const text = {color: INK, fontFamily: FONT_BODY, fontSize: size, lineHeight: 1.18, fontWeight: 400, letterSpacing: '-0.01em', opacity: a} as React.CSSProperties;
  if (center) return <div style={{position: 'absolute', left: center.cx - center.w / 2, top: center.cy, width: center.w, transform: 'translateY(-50%)',
    display: 'flex', justifyContent: 'center', pointerEvents: 'none'}}>
    <div style={{...text, textAlign: 'center', whiteSpace: 'nowrap', textShadow: '0 2px 16px rgba(0,0,0,0.85)'}}>
      {lines.map((ln, j) => <div key={j}>{ln}</div>)}
    </div>
  </div>;
  return <div style={{position: 'absolute', left: x, top: 0, height: bottom, width: 1000, display: 'flex', alignItems: 'flex-end', pointerEvents: 'none'}}>
    <div style={{position: 'relative', padding: '10px 14px', borderRadius: 12, ...text, textAlign: 'left',
      ...(plain ? {textShadow: '0 2px 14px rgba(0,0,0,0.85)'} : {background: rgba(COLORS.panel, 0.9), border: `1.5px solid ${inkA(0.28)}`, backdropFilter: 'blur(16px)'})}}>
      {/* pin dot: a pinned label shows a small dot at its attachment point, here toward the speaker's card */}
      {!plain && <div style={{position: 'absolute', left: -19, top: '50%', width: 6, height: 6, marginTop: -3, borderRadius: 3, background: COLORS.ink}}/>}
      {lines.map((ln, j) => <div key={j} style={{whiteSpace: 'nowrap'}}>{ln}</div>)}
    </div>
  </div>;
}
