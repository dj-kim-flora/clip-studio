import React from 'react';
import {Easing,Img,staticFile,useCurrentFrame,useVideoConfig} from 'remotion';
import {Scene} from './schema';
import {Cursor,Tooltip,hoverEase,popEase,tw} from './ui';
import {COLORS,inkA} from './theme';
export type Box={x:number;y:number;w:number;h:number};
export const fit=(aspect:number,b:Box):Box=>{const w=Math.min(b.w,b.h*aspect),h=w/aspect;return {x:b.x+(b.w-w)/2,y:b.y+(b.h-h)/2,w,h};};
// ---------------------------------------------------------------- click-through on real app captures
// Crossfades between 2x captures (hover states captured from the app); camera eases between framings; the presence cursor
// travels to each target. Dialog shots open with a 200 ms pop (opacity + scale .95 -> 1 on the popEase curve).
export function Walk({scene,box,cursorName}:{scene:Scene;box:Box;cursorName?:string}){
 const f=useCurrentFrame(),{fps}=useVideoConfig();const t=f/fps;const W=scene.walk!;const [CW,CH]=W.size;
 const P=fit(16/9,box);const asp=P.w/P.h;
 // camera
 const cams=W.camera;let ci=0;while(ci<cams.length-1&&t>=cams[ci+1].t)ci++;
 const c0=cams[Math.max(0,ci)],c1=cams[Math.min(cams.length-1,ci+1)];
 const dur=c1.dur??0.9;const e=c1===c0?1:tw(f,(c1.t-dur)*fps,c1.t*fps,0,1,Easing.bezier(.45,0,.55,1));
 // each framing becomes an in-bounds view rect first; a move then zooms about the one point both rects agree on,
 // with the width changing geometrically (even perceived zoom speed), so it never snags on the capture's edge
 const rect=(c:{cx:number;cy:number;w:number})=>{let w=Math.min(c.w,CW),h=w/asp;if(h>CH){h=CH;w=h*asp;}return {x:Math.max(0,Math.min(CW-w,c.cx-w/2)),y:Math.max(0,Math.min(CH-h,c.cy-h/2)),w,h};};
 const ra=rect(c0),rb=rect(c1);const k2=t>=c1.t?1:e;
 let cw:number,chh:number,x0:number,y0:number;
 if(Math.abs(rb.w-ra.w)<0.5){cw=ra.w;chh=ra.h;x0=ra.x+(rb.x-ra.x)*k2;y0=ra.y+(rb.y-ra.y)*k2;}
 else{cw=ra.w*Math.pow(rb.w/ra.w,k2);chh=cw/asp;const s=cw/ra.w;
  const fx=(ra.x*rb.w-rb.x*ra.w)/(rb.w-ra.w),fy=(ra.y*rb.h-rb.y*ra.h)/(rb.h-ra.h);
  x0=fx-(fx-ra.x)*s;y0=fy-(fy-ra.y)*s;}
 const sc=P.w/cw;
 const map=(x:number,y:number):[number,number]=>[P.x+(x-x0)*sc,P.y+(y-y0)*sc];
 // shots: current plus the one it is fading from
 const shots=W.shots;let si=0;while(si<shots.length-1&&t>=shots[si+1].from)si++;
 const cur=shots[si],prv=shots[si-1];const fadeS=cur.fade??(cur.pop?0.2:0.15);const k=tw(f,cur.from*fps,(cur.from+fadeS)*fps,0,1,cur.pop?popEase:hoverEase);
 const img=(sh:typeof cur,op:number,pop:number)=>{const st:React.CSSProperties={position:'absolute',left:-x0*sc,top:-y0*sc,width:CW*sc,height:CH*sc,maxWidth:'none',opacity:op};
  if(sh.pop&&pop<1){const [px,py]=map(sh.pop[0]+sh.pop[2]/2,sh.pop[1]+sh.pop[3]/2);st.transformOrigin=`${px-P.x+x0*sc}px ${py-P.y+y0*sc}px`;st.transform=`scale(${0.95+0.05*pop})`;}
  return <Img src={staticFile(sh.src)} style={st}/>;};
 // cursor: arrive at each keyframe at its time, travelling during the preceding d s (default .5); clicks press it
 const cur2=W.cursor.length?W.cursor:[{t:0,x:-1e4,y:-1e4}];const noCursor=!W.cursor.length;const dOf=(k:{d?:number})=>k.d??0.5;let ki=0;while(ki<cur2.length-1&&t>=cur2[ki+1].t-dOf(cur2[ki+1]))ki++;
 const kA=cur2[Math.max(0,ki-1)],kB=cur2[ki];const mv=ki===0?1:tw(f,(kB.t-dOf(kB))*fps,kB.t*fps,0,1,Easing.bezier(.45,0,.55,1));
 const press=(W.clicks||[]).reduce((p,c)=>Math.min(p,t<c+0.06?tw(f,c*fps,(c+0.06)*fps,1,.86,hoverEase):tw(f,(c+0.06)*fps,(c+0.22)*fps,.86,1,hoverEase)),1);
 const [ax,ay]=map(kA.x,kA.y),[bx,by]=map(kB.x,kB.y);const pxy:[number,number]=[ax+(bx-ax)*mv,ay+(by-ay)*mv];
 const curOn=tw(f,(cur2[0].t-0.7)*fps,(cur2[0].t-0.4)*fps,0,1)*tw(f,((W.cursorOut??scene.duration)-0.3)*fps,(W.cursorOut??scene.duration)*fps,1,0);
 const tips=(W.tips||[]).filter(tp=>t>=tp.from&&t<tp.to+0.12);
 return <div style={{position:'absolute',left:P.x,top:P.y,width:P.w,height:P.h,borderRadius:16,overflow:'hidden',background:COLORS.background,boxShadow:`inset 0 0 0 1.5px ${inkA(0.1)}`}}>
  {prv&&k<1&&img(prv,1,1)}
  {img(cur,prv?k:1,k)}
  <div style={{position:'absolute',left:-P.x,top:-P.y,width:1920,height:1080}}>
   {tips.map((tp,i)=>{const [x,y]=map(tp.x,tp.y);return <Tooltip key={i} x={x} y={y} text={tp.text} side={tp.side} t={tw(f,tp.from*fps,(tp.from+0.15)*fps,0,1,popEase)*tw(f,tp.to*fps,(tp.to+0.1)*fps,1,0)}/>;})}
   {!noCursor&&<Cursor x={pxy[0]} y={pxy[1]} opacity={curOn} press={press} name={cursorName}/>}
  </div>
  <div style={{position:'absolute',inset:0,borderRadius:16,boxShadow:`inset 0 0 0 1.5px ${inkA(0.1)}`,pointerEvents:'none'}}/>
 </div>;
}
