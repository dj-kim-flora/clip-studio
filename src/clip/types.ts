// The brief the generic `Clip` composition renders (briefs/<slug>.clip.json). Everything but width, height, fps, seconds is optional,
// and every optional field may be null.
export type ClipWord = [string, number, number, (string | number)?];   // [word, start s, end s, scene id], times from clip start
export type ClipCue = {start: number; end: number; text: string; words?: ClipWord[] | null};
export type CaptionStyleName = 'none' | 'pill' | 'karaoke' | 'plain' | 'box';
export type ClipProps = {
  kind?: 'clip'; slug?: string; title?: string;
  width: number; height: number; fps: number;
  /** length of the cut in seconds; the end card (outro.seconds) is added after it */
  seconds: number;
  layout?: 'fill' | 'split' | 'blurfill' | null;
  /** split layout: share of the height given to the top video (0.5 = equal, 0.6 = 60/40) */
  splitRatio?: number | null;
  /** paths under public/; video files are silent, the dialogue comes from `voice` */
  video?: string | null; video2?: string | null; voice?: string | null;
  music?: {src: string; volume?: number} | null;
  captions?: ClipCue[] | null;
  captionStyle?: CaptionStyleName | null;
  captionPos?: 'lower' | 'center' | 'upper' | null;
  hook?: {text: string; from?: number; to?: number} | null;
  lowerThird?: {name?: string | null; role?: string | null; from?: number; to?: number} | null;
  progressBar?: boolean | null;
  outro?: {seconds?: number; line?: string | null; handle?: string | null; cta?: string | null} | null;
  safeZone?: 'social' | 'none' | null;
};

export const CLIP_DEFAULTS: ClipProps = {
  kind: 'clip', slug: 'clip', title: 'Clip', width: 1080, height: 1920, fps: 30, seconds: 6, layout: 'fill',
  video: null, video2: null, voice: null, music: null,
  captions: [
    {start: 0.4, end: 2.4, text: 'Captions follow the words you say', words: [['Captions', 0.4, 0.8, 'a'], ['follow', 0.8, 1.2, 'a'], ['the', 1.2, 1.4, 'a'], ['words', 1.4, 1.9, 'a'], ['you', 1.9, 2.1, 'a'], ['say', 2.1, 2.4, 'a']]},
    {start: 2.8, end: 5.4, text: 'in the colours and fonts of your brand'},
  ],
  captionStyle: null, captionPos: 'lower', hook: null, lowerThird: null, progressBar: true, outro: null, safeZone: 'social',
};

/** total frames: the cut plus the end card */
export const clipFrames = (p: Pick<ClipProps, 'fps' | 'seconds' | 'outro'>) =>
  Math.max(1, Math.round((p.seconds + (p.outro ? p.outro.seconds ?? 2.5 : 0)) * p.fps));
