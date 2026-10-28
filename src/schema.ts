export type Crop = [number, number, number, number];
export type Media = {src:string; type:'video'|'image'; startSeconds?:number; playbackRate?:number; fit?:'contain'|'cover'; aspect?:number; mute?:boolean; crop?:Crop; cropTo?:Crop; srcSize?:[number,number]};
export type Insert = {src:string; aspect:number; from:number; until?:number; caption?:string; hl?:[number,number]; title?:string; model?:string; sel?:[number,number][]};
export type Highlight = {box:Crop; from:number; to:number};
export type Pill = {text:string; sub?:string; from:number; until?:number};
export type Link = {from:number; to:number; target:{kind:'panel'|'insert'|'pill'; index?:number; x:number; y:number}; label?:string; glide?:boolean; under?:boolean};
export type Pointer = {from:number; to:number; x:number; y:number; label?:string; tx?:number; ty?:number; side?:'top'|'right'|'left'|'bottom'};
export type WalkShot = {src:string; from:number; fade?:number; pop?:[number,number,number,number]};
export type Walk = {size:[number,number]; shots:WalkShot[]; camera:{t:number; cx:number; cy:number; w:number; dur?:number}[]; cursor:{t:number; x:number; y:number; d?:number}[]; clicks?:number[]; cursorOut?:number; tips?:{from:number; to:number; x:number; y:number; text:string; side?:'top'|'right'|'left'|'bottom'}[]};
export type Scene = {id:string; kind:'prompt'|'response'|'media'|'hero'|'outro'|'clip'|'intro'; duration:number; heading?:string; subtitle?:string; text?:string; result?:string; status?:string; completedStatus?:string; footer?:string; evidence?:string; media?:Media; typingSeconds?:number; typingStart?:number; clickSeconds?:number; caption?:string;
  // livestream clip additions (see EDIT-LOG.md)
  at?:number; face?:boolean; panel?:boolean; fadeOut?:number; links?:Link[]; steps?:{text:string; from:number}[]; walk?:Walk; pointers?:Pointer[]; node?:{title?:string; model?:string; sel?:[number,number][]; kind?:'image'|'video'|'deck'; flowW?:number}; group?:string; noteZoom?:number; noteWidth?:number; screen?:boolean; tall?:boolean; insertLayout?:'grid'|'sequence'; cols?:number; insertAspect?:number; logo?:boolean; label?:string; inserts?:Insert[]; highlights?:Highlight[]; pills?:Pill[]};
export type CaptionCue = {start:number; end:number; text:string; words?:[string,number,number,number][]};
export type Brief = {title:string; slug:string; demo:boolean; fps:30; modelLabel?:string; cursorName?:string; sound:boolean; outro?:string; logos?:Array<{src:string; label:string; invert?:boolean}>; voiceover?:{src:string; voice:string}; captions?:CaptionCue[]; face?:{src:string; crop:Crop; name?:string}; lockup?:{logos:string[]; separator:string; accent:string}; scenes:Scene[]};
