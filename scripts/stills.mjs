// Render QA stills of a composition: node scripts/stills.mjs <CompositionId> <outDir> <seconds…> [--props <file.json>]
// SCALE=0.5 by default (SCALE=1 for full size). With --props the JSON is passed as the composition's input props, e.g. a clip brief:
//   node scripts/stills.mjs Clip _work/stills 1 3 7 --props briefs/<slug>.clip.json
import {bundle} from '@remotion/bundler';
import {renderStill, selectComposition} from '@remotion/renderer';
import path from 'node:path';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
let propsFile = null;
const pi = args.indexOf('--props');
if (pi >= 0) { propsFile = args[pi + 1]; args.splice(pi, 2); }
const [id, outDir, ...secs] = args;
if (!id || !outDir || !secs.length) { console.error('usage: node scripts/stills.mjs <CompositionId> <outDir> <seconds…> [--props <file.json>]'); process.exit(1); }
let inputProps = {};
if (propsFile) {
  if (!fs.existsSync(propsFile)) { console.error(`props file not found: ${propsFile}`); process.exit(1); }
  try { inputProps = JSON.parse(fs.readFileSync(propsFile, 'utf8')); } catch (e) { console.error(`props file is not valid JSON: ${propsFile} (${e.message})`); process.exit(1); }
}
fs.mkdirSync(outDir, {recursive: true});
const serveUrl = await bundle({entryPoint: path.join(root, 'src/index.tsx'), publicDir: path.join(root, 'public')});
const composition = await selectComposition({serveUrl, id, inputProps});
const tag = propsFile ? path.basename(propsFile).replace(/\.json$/, '').replace(/\.clip$/, '') + '-' : '';
for (const s of secs) {
  const frame = Math.min(composition.durationInFrames - 1, Math.round(Number(s) * composition.fps));
  const output = path.join(outDir, `${tag}${id}-${String(s).replace('.', '_')}s.png`);
  await renderStill({serveUrl, composition, frame, output, inputProps, scale: Number(process.env.SCALE || 0.5)});
  console.log(output);
}
