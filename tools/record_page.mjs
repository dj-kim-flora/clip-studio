#!/usr/bin/env node
// Record a web page or canvas app from its URL as a video, in the background (headless Chrome, your desktop is not used).
//
//   node tools/record_page.mjs --login <url>                    one-time: open a window to sign in (never scripted)
//   node tools/record_page.mjs --snapshot <url> <slug>          screenshot + list of what is on the page, to plan a tour
//   node tools/record_page.mjs <url> <slug> [--tour auto|none|file.json] [--seconds 30] [--size 1600x900] [--scale 2]
//        [--fps 30] [--wait 5] [--hide "css,selectors"] [--clean] [--cursor] [--headed] [--profile DIR]
//
// Writes source/<slug>/capture.mp4 (silent, constant frame rate), capture.json (url, title, beats with times) and preview.png.
// Read-only by design: the only input sent is mouse move, mouse wheel, and a drag that starts on an empty spot of the page
// (to pan a canvas). No clicks on controls, no typing, no sign-in. The sign-in lives in a separate Chrome profile
// (default ~/.clip-studio/chrome-profile, outside the repository), created by --login.
//
// A tour file is {"steps":[{"label":"Overview","do":"hold","seconds":2}, {"do":"zoom","by":-2,"seconds":2},
//   {"label":"The prompt","do":"pan","dx":-500,"dy":0,"seconds":3}, {"do":"hover","text":"Generate"}, {"do":"scroll","dy":800,"seconds":3}]}
//   do: hold (seconds) | zoom (by: + in, - out; at: [fx,fy] of the viewport; ctrl+wheel) | pan (dx,dy in px; content follows the pointer)
//       | scroll (dy,dx: plain wheel, for ordinary pages) | hover (text: a visible label, or at: [x,y]) | speed is set per label with "speed": 2.
//   A step with "label" starts a new beat; the reel shows the label and times the beat.
import {spawn} from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const sleep = ms => new Promise(r => setTimeout(r, ms));
const die = (msg, code = 1) => { console.error(msg); process.exit(code); };

// ---------- arguments ----------
const argv = process.argv.slice(2);
const flags = new Set(['--login', '--snapshot', '--clean', '--cursor', '--headed', '--help']);
const opt = {}; const pos = [];
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a.startsWith('--')) { if (flags.has(a)) opt[a.slice(2)] = true; else opt[a.slice(2)] = argv[++i]; } else pos.push(a);
}
if (opt.help || !pos.length) die(fs.readFileSync(fileURLToPath(import.meta.url), 'utf8').split('\n').filter(l => l.startsWith('//')).map(l => l.slice(3)).join('\n'), opt.help ? 0 : 2);
if (typeof WebSocket === 'undefined') die('This needs Node 22 or newer (it uses the built-in WebSocket). Update Node, then try again.');
const url = pos[0], slug = pos[1];
if (!/^https?:\/\//.test(url)) die('Give the page address starting with https:// .');
const profile = path.resolve((opt.profile || '~/.clip-studio/chrome-profile').replace(/^~/, os.homedir()));
const [VW, VH] = (opt.size || '1600x900').split('x').map(Number);
const SCALE = Number(opt.scale || 2), FPS = Number(opt.fps || 30), SETTLE = Number(opt.wait || 5);
if (!(VW > 200 && VH > 200 && SCALE >= 1 && FPS >= 10)) die('Check --size (like 1600x900), --scale (1 to 3) and --fps.');

const chromePath = [process.env.CHROME, '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Chromium.app/Contents/MacOS/Chromium', '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser']
  .find(p => p && fs.existsSync(p));
if (!chromePath) die('I could not find Google Chrome. Install it from google.com/chrome (or set CHROME to a Chromium-based browser), then try again.');
fs.mkdirSync(profile, {recursive: true});

// ---------- one-time sign-in ----------
if (opt.login) {
  const child = spawn(chromePath, [`--user-data-dir=${profile}`, '--no-first-run', '--no-default-browser-check', url], {detached: true, stdio: 'ignore'});
  child.unref();
  console.log(`A Chrome window opened. Sign in there yourself, check that you can see the page, then CLOSE that window.\nYour sign-in is kept in ${profile} (outside the project, never committed). You only do this once.`);
  process.exit(0);
}
if (!slug) die('Name the recording (a short label like  my-canvas ) after the address.', 2);
const outDir = path.join(ROOT, 'source', slug);
fs.mkdirSync(outDir, {recursive: true});

// ---------- Chrome over the DevTools protocol ----------
const port = 9400 + Math.floor(Math.random() * 500);
const chrome = spawn(chromePath, [
  ...(opt.headed ? [] : ['--headless=new']), `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  `--window-size=${VW},${VH}`, '--hide-scrollbars', '--mute-audio', '--no-first-run', '--no-default-browser-check',
  '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows', 'about:blank',
], {stdio: 'ignore'});
let chromeGone = false; chrome.on('exit', () => { chromeGone = true; });
const finish = async code => { try { ws?.close(); } catch {} chrome.kill(); await sleep(300); process.exit(code); };
let list;
for (let i = 0; i < 60 && !list; i++) {
  if (chromeGone) die(`Chrome closed straight away. If a Chrome window that uses the clip-studio sign-in is still open, close it and try again. (${profile})`);
  try { list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(); } catch { await sleep(250); }
}
if (!list) { chrome.kill(); die('Chrome did not start in time.'); }
const target = list.find(t => t.type === 'page');
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((ok, err) => { ws.onopen = ok; ws.onerror = () => err(new Error('could not connect to Chrome')); });
let nid = 0; const pending = new Map(); const listeners = [];
ws.onmessage = e => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { const {ok, err} = pending.get(m.id); pending.delete(m.id); m.error ? err(new Error(m.error.message)) : ok(m.result); return; }
  for (const l of listeners) l(m);
};
const send = (method, params = {}) => new Promise((ok, err) => { const id = ++nid; pending.set(id, {ok, err}); ws.send(JSON.stringify({id, method, params})); });
const evaluate = async expr => {
  const r = await send('Runtime.evaluate', {expression: expr, awaitPromise: true, returnByValue: true});
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || 'page script failed');
  return r.result.value;
};
listeners.push(m => { if (m.method === 'Page.javascriptDialogOpening') send('Page.handleJavaScriptDialog', {accept: false}).catch(() => {}); });

await send('Page.enable'); await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', {width: VW, height: VH, deviceScaleFactor: SCALE, mobile: false});
const loaded = new Promise(r => { listeners.push(m => { if (m.method === 'Page.loadEventFired') r(); }); setTimeout(r, 45000); });
await send('Page.navigate', {url});
await loaded;
await sleep(SETTLE * 1000);

// not signed in? stop, never try to sign in
const state = await evaluate(`({href: location.href, title: document.title, password: !!document.querySelector('input[type=password]'), body: (document.body?.innerText || '').length})`);
if (state.password || /\/(log-?in|sign-?in|sign-?up|auth)\b/i.test(new URL(state.href).pathname)) {
  console.error(`This page asks for a sign-in (${state.href}).\nRun  node tools/record_page.mjs --login "${url}"  once, sign in yourself in the window that opens, close it, then record again.`);
  await finish(3);
}

// ---------- page tidy-up ----------
const hide = [...(opt.clean ? ['.react-flow__minimap', '.react-flow__controls', '.react-flow__attribution', '[class*="toast" i]', '[class*="Toastify" i]', '[class*="cookie" i]'] : []),
  ...(opt.hide ? opt.hide.split(',').map(s => s.trim()).filter(Boolean) : [])];
await evaluate(`(()=>{const s=document.createElement('style');s.textContent=${JSON.stringify((hide.length ? hide.join(',') + '{display:none!important}' : '') + '::-webkit-scrollbar{display:none}')};document.head.appendChild(s);
  ${opt.cursor ? `const c=document.createElement('div');c.style.cssText='position:fixed;left:0;top:0;width:22px;height:22px;z-index:2147483647;pointer-events:none;transition:none;transform:translate(-100px,-100px)';
  c.innerHTML='<svg viewBox="0 0 24 24" width="22" height="22"><path d="M3 2l7 18 2.5-7.5L20 10z" fill="#fff" stroke="#000" stroke-width="1.5" stroke-linejoin="round"/></svg>';document.body.appendChild(c);
  addEventListener('mousemove',e=>{c.style.transform='translate('+e.clientX+'px,'+e.clientY+'px)'},true);` : ''}return 1})()`);
const kind = await evaluate(`document.querySelector('.react-flow, .react-flow__renderer') ? 'canvas' : 'page'`);

// ---------- what is on the page (for planning a tour) ----------
const inventory = await evaluate(`(()=>{
  const vis = el => { const r = el.getBoundingClientRect(); return r.width > 4 && r.height > 4 && r.bottom > 0 && r.right > 0 && r.top < innerHeight && r.left < innerWidth; };
  const clean = t => (t || '').replace(/\\s+/g, ' ').trim().slice(0, 60);
  const nodes = [...document.querySelectorAll('.react-flow__node')].filter(vis).slice(0, 40)
    .map(n => { const r = n.getBoundingClientRect(); return {text: clean(n.innerText), x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2)}; });
  const heads = [...document.querySelectorAll('h1,h2,h3')].filter(el => clean(el.innerText)).slice(0, 40).map(h => ({text: clean(h.innerText), top: Math.round(h.getBoundingClientRect().top + scrollY)}));
  return {nodes, headings: heads, pageHeight: document.documentElement.scrollHeight};
})()`);
const preview = path.join(outDir, 'preview.png');
fs.writeFileSync(preview, Buffer.from((await send('Page.captureScreenshot', {format: 'png'})).data, 'base64'));
if (opt.snapshot) {
  console.log(JSON.stringify({title: state.title, kind, viewport: [VW, VH], preview: path.relative(ROOT, preview), ...inventory}, null, 1));
  await finish(0);
}

// ---------- input helpers (read-only: move, wheel, drag on empty spots) ----------
const ease = t => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
let mouse = [VW / 2, VH / 2];
const mouseEvt = (type, x, y, extra = {}) => send('Input.dispatchMouseEvent', {type, x, y, ...extra});
async function glide(x, y, seconds) {
  const [x0, y0] = mouse, n = Math.max(1, Math.round(seconds * 60));
  for (let i = 1; i <= n; i++) { const e = ease(i / n); await mouseEvt('mouseMoved', x0 + (x - x0) * e, y0 + (y - y0) * e); await sleep(1000 / 60); }
  mouse = [x, y];
}
async function wheel(dx, dy, seconds, modifiers = 0, at = mouse) {
  const n = Math.max(1, Math.round(seconds * 60)); let prev = 0;
  for (let i = 1; i <= n; i++) {
    const e = ease(i / n);
    await mouseEvt('mouseWheel', at[0], at[1], {deltaX: dx * (e - prev), deltaY: dy * (e - prev), modifiers}); prev = e;
    await sleep(1000 / 60);
  }
}
const emptySpot = (cx, cy) => evaluate(`(()=>{
  const bad = 'a,button,input,textarea,select,[role=button],[contenteditable],.react-flow__node,.react-flow__controls,.react-flow__minimap,.react-flow__edge,.react-flow__handle,.react-flow__panel,header,nav,aside';
  const pts = []; for (let r = 0; r < 1; r += 0.08) for (let a = 0; a < 6.3; a += 0.6) pts.push([${cx} + Math.cos(a) * r * ${VW} * 0.4, ${cy} + Math.sin(a) * r * ${VH} * 0.4]);
  for (const [x, y] of pts) { if (x < 30 || y < 30 || x > ${VW} - 30 || y > ${VH} - 30) continue; const el = document.elementFromPoint(x, y); if (el && !el.closest(bad)) return [x, y]; }
  return null; })()`);
async function dragBy(dx, dy, seconds) {
  // a drag moves the content with the pointer; long pans are split into several grabs
  const maxX = VW * 0.55, maxY = VH * 0.55, parts = Math.max(1, Math.ceil(Math.max(Math.abs(dx) / maxX, Math.abs(dy) / maxY)));
  for (let p = 0; p < parts; p++) {
    const sx = dx / parts, sy = dy / parts;
    const spot = await emptySpot(VW / 2 - sx / 2, VH / 2 - sy / 2);
    if (!spot) { console.error('  note: no empty spot to grab the canvas, skipped a pan'); return; }
    let [x0, y0] = spot; x0 = Math.min(Math.max(x0, 40 + Math.max(0, -sx)), VW - 40 - Math.max(0, sx)); y0 = Math.min(Math.max(y0, 40 + Math.max(0, -sy)), VH - 40 - Math.max(0, sy));
    await glide(x0, y0, 0.25);
    await mouseEvt('mousePressed', x0, y0, {button: 'left', buttons: 1, clickCount: 1});
    const n = Math.max(2, Math.round(seconds / parts * 60));
    for (let i = 1; i <= n; i++) { const e = ease(i / n); await mouseEvt('mouseMoved', x0 + sx * e, y0 + sy * e, {button: 'left', buttons: 1}); await sleep(1000 / 60); }
    await mouseEvt('mouseReleased', x0 + sx, y0 + sy, {button: 'left', buttons: 0, clickCount: 1});
    mouse = [x0 + sx, y0 + sy]; await sleep(120);
  }
}
async function hoverText(text) {
  const pt = await evaluate(`(()=>{const t=${JSON.stringify(text.toLowerCase())};let best=null;
    for (const el of document.querySelectorAll('body *')) { if (el.children.length > 3) continue; const s=(el.innerText||'').trim().toLowerCase(); if (!s || !s.includes(t) || s.length > t.length + 40) continue;
      const r=el.getBoundingClientRect(); if (r.width<4||r.height<4||r.bottom<0||r.right<0||r.top>innerHeight||r.left>innerWidth) continue; if (!best || s.length < best.len) best={len:s.length,x:r.x+r.width/2,y:r.y+r.height/2}; }
    return best && [best.x, best.y]; })()`);
  return pt;
}

// ---------- the tour ----------
function autoTour() {
  const steps = [{label: 'Overview', do: 'hold', seconds: 2.5}];
  if (kind === 'canvas') {
    steps.push({label: 'Zoom in', do: 'zoom', by: 2, seconds: 2.5}, {do: 'hold', seconds: 1.5});
    const legs = [[-0.55, 0], [-0.55, 0], [0, 0.45], [0.55, 0], [0.55, 0]];
    legs.forEach(([fx, fy], i) => steps.push({label: i === 0 ? 'Follow the flow' : null, do: 'pan', dx: fx * VW, dy: fy * VH, seconds: 2.8}, {do: 'hold', seconds: 1.2}));
  } else {
    const total = Math.min(inventory.pageHeight, VH * 8), seconds = Number(opt.seconds || 24);
    const chunks = Math.max(1, Math.min(8, Math.round((total - VH) / (VH * 0.8))));
    for (let i = 0; i < chunks; i++) {
      const y = (i + 1) * (total - VH) / chunks, head = [...inventory.headings].reverse().find(h => h.top <= y + VH * 0.4);
      steps.push({label: head ? head.text : null, do: 'scroll', dy: (total - VH) / chunks, seconds: Math.max(1.5, (seconds - 2.5) / chunks - 1)}, {do: 'hold', seconds: 1});
    }
  }
  return steps;
}
let steps;
if (!opt.tour || opt.tour === 'auto') steps = autoTour();
else if (opt.tour === 'none') steps = [{label: 'Page', do: 'hold', seconds: Number(opt.seconds || 8)}];
else {
  try { steps = JSON.parse(fs.readFileSync(path.resolve(opt.tour), 'utf8')).steps; } catch (e) { await finish(die('I could not read that tour file: ' + e.message)); }
  if (!Array.isArray(steps) || !steps.length) die('The tour file needs a "steps" list.');
}

// ---------- recording: screencast frames -> constant frame rate -> ffmpeg ----------
const OW = Math.round(VW * SCALE / 2) * 2, OH = Math.round(VH * SCALE / 2) * 2;
const mp4 = path.join(outDir, 'capture.mp4');
const {FF} = await new Promise(r => { const p = spawn('python3', ['-c', 'import sys,json;sys.path.insert(0,"tools");import ff;print(json.dumps({"FF":ff.FF}))'], {cwd: ROOT}); let o = ''; p.stdout.on('data', d => o += d); p.on('close', () => r(JSON.parse(o || '{"FF":"ffmpeg"}'))); });
const enc = spawn(FF, ['-hide_banner', '-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
  '-vf', `scale=${OW}:${OH}:flags=lanczos`, '-c:v', 'libx264', '-crf', '16', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-r', String(FPS), '-movflags', '+faststart', mp4], {stdio: ['pipe', 'inherit', 'inherit']});
enc.stdin.on('error', () => {});
let last = Buffer.from((await send('Page.captureScreenshot', {format: 'jpeg', quality: 92})).data, 'base64');
listeners.push(m => {
  if (m.method === 'Page.screencastFrame') { last = Buffer.from(m.params.data, 'base64'); send('Page.screencastFrameAck', {sessionId: m.params.sessionId}).catch(() => {}); }
});
await send('Page.startScreencast', {format: 'jpeg', quality: 92, maxWidth: OW, maxHeight: OH, everyNthFrame: 1});
const t0 = performance.now(); const now = () => (performance.now() - t0) / 1000;
let written = 0, recording = true;
const writer = (async () => {
  while (recording) {
    const due = Math.floor(now() * FPS) - written;
    for (let i = 0; i < due; i++) { if (!enc.stdin.write(last)) await new Promise(r => enc.stdin.once('drain', r)); written++; }
    await sleep(8);
  }
})();

const beats = [];
await sleep(600);                                     // first frames of the page before anything moves
for (const s of steps) {
  const t = now();
  if (s.label !== undefined && s.label !== null) { if (beats.length) beats.at(-1).t1 = t; beats.push({label: String(s.label), t0: t, t1: null, speed: s.speed ?? null}); }
  else if (!beats.length) beats.push({label: null, t0: t, t1: null, speed: null});
  const sec = Number(s.seconds ?? 2);
  switch (s.do) {
    case 'hold': case 'wait': await sleep(sec * 1000); break;
    case 'zoom': { const at = s.at ? [s.at[0] * VW, s.at[1] * VH] : [VW / 2, VH / 2]; await glide(at[0], at[1], 0.3); await wheel(0, -(Number(s.by ?? 1)) * 100, sec, 2, at); break; }
    case 'pan': await dragBy(Number(s.dx || 0), Number(s.dy || 0), sec); break;
    case 'scroll': await glide(VW * 0.62, VH * 0.5, 0.2); await wheel(Number(s.dx || 0), Number(s.dy || 0), sec); break;
    case 'hover': { const pt = s.at ? [s.at[0], s.at[1]] : await hoverText(String(s.text || '')); if (pt) await glide(pt[0], pt[1], Math.min(sec, 1.2)); else console.error(`  note: no visible "${s.text}" to hover`); await sleep(Math.max(0, sec - 1.2) * 1000); break; }
    default: console.error(`  note: unknown step "${s.do}" skipped`);
  }
}
await sleep(700);
const seconds = now();
if (beats.length) beats.at(-1).t1 = seconds;
recording = false; await writer;
await send('Page.stopScreencast').catch(() => {});
enc.stdin.end(); await new Promise(r => enc.on('close', r));
fs.writeFileSync(path.join(outDir, 'capture.json'), JSON.stringify({
  url: url.replace(/[?#].*$/, ''), title: state.title, kind, recordedAt: new Date().toISOString(), viewport: {w: VW, h: VH, scale: SCALE}, fps: FPS,
  size: [OW, OH], seconds: Math.round(seconds * 100) / 100, hidden: hide, beats: beats.map(b => ({...b, t0: +b.t0.toFixed(2), t1: +b.t1.toFixed(2)})),
}, null, 1));
console.log(`Recorded ${seconds.toFixed(1)} s of ${kind} "${state.title}" at ${OW}x${OH}: ${path.relative(ROOT, mp4)}  (${beats.filter(b => b.label).length} labelled beats)`);
await finish(0);
