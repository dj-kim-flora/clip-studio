// A first draft for any long recording, straight from its brief, with the approved first-pass defaults built in:
//   - Hook open: the recording's best moments full frame (the first one resolves from dither pixels), the speaker's own strongest lines as the
//     hook audio (EDL scenes whose id starts with "hook"), and the two-line title card resolving over the last hook shot.
//     Without `hook`, it falls back to the pixel open on a hero result.
//   - The stream's own screen on the floating window (synced to the voice, one shot per scene).
//   - The step column from the scenes' `step` / `notes` fields; each step word rises only after the previous one has left.
//   - The webcam node and one-line captions centred on the stage axis under the window (hook captions centred low on
//     the frame); an optional sign-off arc; the outro card.
// It gets a new cut on screen in minutes; the real work is then authoring beats keyed to words (src/films/cs-map example in
// skill/references/beat-library.md).
//
// Brief scene fields it reads (put them in the EDL scenes; the cut builder copies them into the brief):
//   step:  ["Base", "Model"]                       the italic step word, one or two lines
//   notes: [{"t": "Recraft trains in seconds", "word": "recraft"}]   note lines, each arriving on a spoken word
//   cam:   {"cx": 0.6, "cy": 0.45, "z": 1.3}       how to frame the stream in the window for that scene (0..1, zoom)
import React from 'react';
import {AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Brief} from '../schema';
import type {TextSpec} from '../dither';
import {Backdrop} from '../ui';
import {COLORS, FONT_BODY} from '../theme';
import {Arc, CAP_HOOK, CAP_STAGE, Captions, Card, E, FaceNode, GENTLE, HookOpen, OutroCard, PixelOpen, Rise, Step, StepColumn, Vignette, Window, clock, k, streamShot} from '../premium';

type DraftScene = {id: string; kind: string; step?: string[]; notes?: Array<{t: string; word?: string}>; cam?: {cx: number; cy: number; z: number}};
export type DraftOptions = {
  lead?: number; title: TextSpec; music?: string;
  /** hook open: `still` is the first frame of `open` (dithered in); `shots[i]` plays over the i-th "hook…" scene */
  hook?: {open: {src: string; start?: number}; still: string; shots: Array<{src: string; start?: number}>};
  hero?: string;                                                 // pixel-open fallback when there is no hook
  streamSize?: [number, number];                                 // the stream's frame size (webcam crop maths)
  screen?: {cx: number; cy: number; z: number};                 // default framing of the stream in the window
  signoff?: {lines: React.ReactNode[]; cards: Card[]; label?: string};
  /** the title is already on screen at frame 0 (it is the thumbnail) instead of arriving after the hook lines */
  titleFirst?: boolean;
};

export function firstDraft(data: unknown, o: DraftOptions) {
  const brief = data as Brief; const lead = o.lead ?? 1.5; const c = clock(brief, lead);
  const scenes = brief.scenes as unknown as DraftScene[];
  const hooks = scenes.filter(s => s.kind === 'clip' && s.id.startsWith('hook'));
  const clips = scenes.filter(s => s.kind === 'clip' && !s.id.startsWith('hook'));
  const outro = scenes.find(s => s.kind === 'outro');
  const end = outro ? c.sceneAt(outro.id) : c.total;
  const last = clips[clips.length - 1];
  const signAt = o.signoff ? c.sceneAt(last.id) : end;               // the sign-off takes the last scene
  const words = ((brief as unknown as {words?: Array<[string, number, number, string]>}).words || []);
  const firstWord = words.find(w => w[3] === clips[0].id);
  const voice = firstWord ? firstWord[1] + lead : c.sceneAt(clips[0].id);   // the body's first spoken word
  const faceAt = voice - 0.35, titleOut = voice - 0.75;
  const steps: Step[] = clips.filter(s => s.step && s.id !== (o.signoff ? last.id : '')).map((s, i) => ({at: (i === 0 ? voice : c.sceneAt(s.id)) - 0.1, lines: s.step!,
    note: (s.notes || []).map(n => ({t: n.t, at: n.word ? c.wordT(s.id, n.word) - 0.1 : undefined}))}));
  const shotScenes = clips.filter(s => s.id !== (o.signoff ? last.id : ''));
  const shots = shotScenes.map((s, i) => streamShot(brief, lead, i === 0 ? voice : c.sceneAt(s.id), c.sceneEnd(s.id), {cam: [{t: 0, ...(s.cam || o.screen || {cx: 0.5, cy: 0.5, z: 1})}]}));
  const winOut = [signAt - 0.6, signAt + 0.3] as const;
  const hookShots = o.hook ? [{...o.hook.open, at: 0}, ...hooks.map((h, i) => ({src: o.hook!.shots[i]?.src ?? o.hook!.open.src, start: o.hook!.shots[i]?.start, at: c.sceneAt(h.id) - 0.08}))] : [];
  const titleAt = o.titleFirst ? -1.1 : hooks.length ? c.sceneAt(hooks[hooks.length - 1].id) + 0.15 : 0.6;
  return function FirstDraft() {
    const f = useCurrentFrame(), {fps} = useVideoConfig(); const t = f / fps;
    return <AbsoluteFill style={{background: COLORS.background, fontFamily: FONT_BODY, color: COLORS.ink}}>
      {o.music && <Audio src={staticFile(o.music)}/>}
      {brief.voiceover && <Sequence from={Math.round(lead * fps)}><Audio src={staticFile(brief.voiceover.src)}/></Sequence>}
      <AbsoluteFill style={{opacity: k(t, c.total - 0.7, c.total, 1, 0, E.in)}}>
        <Backdrop spacing={24}/>
        {o.hook
          ? <HookOpen t={t} still={o.hook.still} shots={hookShots} title={o.title} titleAt={titleAt} out={titleOut} fade={[voice - 0.7, voice - 0.1]}/>
          : null}
        <AbsoluteFill style={{opacity: k(t, end - 0.75, end - 0.05, 1, 0, GENTLE)}}>
          {!o.hook && o.hero && <PixelOpen t={t} hero={o.hero} title={o.title} out={Math.max(2.6, voice - 0.6)}/>}
          <Window t={t} win={[voice + 0.05, voice + 1.85, winOut[0], winOut[1]]} shots={shots}/>
          <StepColumn t={t} steps={steps} end={signAt - 0.35}/>
          {o.signoff && <>
            {o.signoff.lines.map((ln, i) => <Rise key={i} t={t} at={signAt + 0.2 + i * 0.6} lines={[ln]} size={100} x={96} y={100 + i * 110}/>)}
            <Arc t={t} at={signAt} cards={o.signoff.cards} end={end} label={o.signoff.label}/>
          </>}
          <FaceNode t={t} brief={brief} lead={lead} from={faceAt} streamSize={o.streamSize}/>
          <Captions t={t} brief={brief} lead={lead} from={faceAt} cueFrom={voice - 0.3} center={CAP_STAGE} size={CAP_STAGE.size}/>
        </AbsoluteFill>
        {hooks.length > 0 && <Captions t={t} brief={brief} lead={lead} from={c.sceneAt(hooks[0].id)} until={faceAt} hold={0.3} center={CAP_HOOK} size={CAP_HOOK.size}/>}
        {outro && <OutroCard t={t} at={end}/>}
      </AbsoluteFill>
      <Vignette/>
    </AbsoluteFill>;
  };
}
