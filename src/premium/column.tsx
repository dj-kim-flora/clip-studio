// Display type beats: kinetic headlines on key lines, chapter titles, and the editorial step column (label, italic word,
// a note that builds as the speaker says it).
import React from 'react';
import {MUTED_RGB, INK_RGB, inkA} from '../theme';
import {ACCENT, COL, E, GENTLE, INK, NOTE, Micro, Rise, Seg, k, mix} from './core';

/**
 * Kinetic headline: each line rises on its own spoken word (`at`), all leave together at `out` with a soft melt.
 * Two-tone contrast: a grey line ("Not someone else's art.") answered by a white one with the italic word ("Your own work.").
 */
export function Headline({t, lines, out, x = 96, y = 100, size = 100, gap = 110, outDur = 0.9, outEase = GENTLE}:
  {t: number; lines: Array<{text: React.ReactNode; at: number; color?: string; out?: number}>; out?: number; x?: number; y?: number; size?: number; gap?: number; outDur?: number; outEase?: (n: number) => number}) {
  return <>{lines.map((l, i) => <Rise key={i} t={t} at={l.at} out={l.out ?? (out !== undefined ? out + i * 0.08 : undefined)} outDur={outDur} outEase={outEase}
    lines={[l.text]} size={size} x={x} y={y + i * gap} color={l.color ?? INK}/>)}</>;
}

/**
 * Chapter title on the canvas: two big lines (one italic word) and a path in the note voice under them
 * ("ASSETS → STYLES → ADD STYLE → TRAIN"). Rises at `at`, leaves at `out`; keep the stage empty while it is up.
 */
export function Chapter({t, lines, note, at, out, x = 92, y = 130, size = 150, noteX = COL.x, noteSize = 19}:
  {t: number; lines: React.ReactNode[]; note?: string; at: number; out: number; x?: number; y?: number; size?: number; noteX?: number; noteSize?: number}) {
  if (t < at - 0.05 || t > out + 0.8) return null;
  const o = k(t, at + 0.55, at + 1.15, 0, 1) * k(t, out, out + 0.5, 1, 0, E.in);
  return <>
    <Rise t={t} at={at + 0.15} out={out} lines={lines} size={size} x={x} y={y} lh={1.0}/>
    {note && <div style={{position: 'absolute', left: noteX, top: y + lines.length * size + 36, ...NOTE, fontSize: noteSize, whiteSpace: 'nowrap', opacity: o, transform: `translateY(${k(t, at + 0.55, at + 1.35, 12, 0)}px)`}}>{note}</div>}
  </>;
}

/** A small spec table for a step (e.g. training speed per model): rows arrive as they are named, the live one lights in the accent colour. */
export type TableRow = {name: string; value: string; f: number; at: number};
export function StepTable({t, rows, fade}: {t: number; rows: TableRow[]; fade: number}) {
  return <>{rows.map((r, i) => {
    const later = rows.map(x => x.at).filter(a => a > r.at); const nx = later.length ? Math.min(...later) : Infinity;
    const live = k(t, r.at, r.at + 0.3, 0, 1) * (nx < Infinity ? k(t, nx, nx + 0.3, 1, 0) : 1);   // the row being talked about
    const o = k(t, r.at, r.at + 0.5, 0, 1) * fade; const bar = k(t, r.at + 0.1, r.at + 1.0, 0, 1);
    return <div key={i} style={{position: 'relative', height: 42, opacity: o}}>
      <div style={{...NOTE, display: 'flex', justifyContent: 'space-between', color: mix(MUTED_RGB, INK_RGB, live)}}><span>{r.name}</span><span>{r.value}</span></div>
      <div style={{position: 'absolute', left: 0, top: 32, width: '100%', height: 2, borderRadius: 1, background: inkA(0.1)}}/>
      <div style={{position: 'absolute', left: 0, top: 32, width: `${100 * r.f * bar}%`, height: 2, borderRadius: 1, background: mix(MUTED_RGB, [...ACCENT], live)}}/>
    </div>;
  })}</>;
}

/**
 * The step column. Each step: a micro label ("[3] Step" by default), the italic display word (long words go on two lines:
 * the column is 440 px and the stage starts at 560), and notes that build line by line on the words that say them, or a
 * table. A step leaves as the next arrives; the last leaves at `end`. Keep notes to 3–4 lines so they clear the webcam.
 */
export type Step = {at: number; lines: string[]; note?: Seg[]; table?: TableRow[]; label?: string};
export function StepColumn({t, steps, end, label = (i: number) => `[${i + 1}] Step`, col = COL, gap = 0.6, noteSize = 19, microSize = 15, noteGap = 35}:
  {t: number; steps: Step[]; end: number; label?: (i: number) => string; col?: typeof COL; gap?: number; noteSize?: number; microSize?: number; noteGap?: number}) {
  return <>{steps.map((s, i) => {
    const out = steps[i + 1] ? steps[i + 1].at - 0.1 : end;
    const at = s.at + (i > 0 ? gap : 0);   // the next step word rises only once the previous one has fully left (no overlap)
    if (t < at - 0.05 || t > out + 0.8) return null;
    const fade = k(t, out, out + 0.45, 1, 0, E.in);
    const vis = k(t, at, at + 0.5, 0, 1) * fade;
    const lh = s.lines.length > 1 ? 1.0 : 1.04;
    const top = col.word + s.lines.length * col.size * lh + noteGap;
    return <React.Fragment key={i}>
      <Micro x={col.x} y={col.label} o={vis} size={microSize}>{s.label ?? label(i)}</Micro>
      <Rise t={t} at={at + 0.05} out={out} lines={s.lines.map(l => <span style={{fontStyle: 'italic'}}>{l}</span>)} size={col.size} x={col.x - 6} y={col.word} lh={lh}/>
      <div style={{position: 'absolute', left: col.x, top, width: col.w}}>
        {s.note?.map((g, j) => { const a = Math.max(g.at ?? at + 0.3, at + 0.3);
          return <div key={j} style={{...NOTE, fontSize: noteSize, marginBottom: 6, opacity: k(t, a, a + 0.6, 0, 1) * fade, transform: `translateY(${k(t, a, a + 0.8, 12, 0)}px)`}}>{g.t}</div>; })}
        {s.table && <StepTable t={t} rows={s.table} fade={fade}/>}
      </div>
    </React.Fragment>;
  })}</>;
}
