// Remotion entry: loads the brand fonts (public/brand/brand.json), then registers every film in src/films as a composition
// (30 fps, 1920x1080 unless the film sets width/height) and the generic `Clip` composition, whose size and length come from
// its props (calculateMetadata), so one composition renders 9:16, 4:5, 1:1 and 16:9 clips.
import React from 'react';
import {Composition, cancelRender, continueRender, delayRender, registerRoot} from 'remotion';
import type {CalculateMetadataFunction} from 'remotion';
import {FILMS, LOCAL_FILMS} from './films';
import {Clip} from './clip/Clip';
import {CLIP_DEFAULTS, ClipProps, clipFrames} from './clip/types';
import {loadBrandFonts} from './theme';

const fontsReady = delayRender('Loading brand fonts');
loadBrandFonts().then(() => continueRender(fontsReady)).catch(err => cancelRender(err));

const clipMetadata: CalculateMetadataFunction<ClipProps> = ({props}) => ({
  width: Math.round(props.width || 1080), height: Math.round(props.height || 1920), fps: props.fps || 30, durationInFrames: clipFrames({...CLIP_DEFAULTS, ...props}),
});

registerRoot(() => <>
  {[...FILMS, ...LOCAL_FILMS].map(f => <Composition key={f.id} id={f.id} component={f.component} width={f.width ?? 1920} height={f.height ?? 1080} fps={30} durationInFrames={Math.round(f.seconds * 30)}/>)}
  <Composition id="Clip" component={Clip} width={1080} height={1920} fps={30} durationInFrames={clipFrames(CLIP_DEFAULTS)} defaultProps={CLIP_DEFAULTS} calculateMetadata={clipMetadata}/>
</>);
