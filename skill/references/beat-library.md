# Beat library

Every beat is a component in `src/premium/`. Import them from `'../premium'` in a film. UI building blocks (`Card`,
`Group`, `Edge`, `Cursor`, `Tooltip`, `Label`, `Note`, `Backdrop`, `Handle`) come from `src/ui.tsx`. Beats take the film
time `t` and times you get from the clock. Nothing is hard-wired to a particular video, and all colours and fonts come
from the active theme (`public/brand/brand.json`).

```ts
const brief = data as unknown as Brief;           // briefs/<slug>.json from tools/build_cut.py
const LEAD = 1.5;                                 // silent cold open before the voice
const c = clock(brief, LEAD);                     // c.wordT(scene, word, nth?)  c.wordEnd(...)  c.sceneAt(id)  c.sceneEnd(id)  c.total
```

`wordT` matches a word by its first letters, ignoring case and punctuation ('acme' finds "Acme's", '25' finds "2.5"), and
**throws** if the word isn't in the scene. A re-cut therefore breaks loudly instead of silently mistiming a beat.

Pick beats by what the speaker is saying. A film uses maybe 6 to 10 of these, never all of them. `firstDraft(brief, {...})`
(`src/films/first-draft.tsx`) wires a sensible default film from an EDL; replace its sections with the beats below.

---

## Openers (pick one)

### Flash open: output first, one hook option
- **What:** beat-length close-ups of the best results from frame 0, each cut landing with a white pop, then pull-outs to
  the full shot under the speaker's hook lines (inputs beside their outputs, with small tags), then the title over a scrim.
- **When:** only when the user picks it, for a striking hi-res result that still reads in close-up. For a feature demo,
  show the feature at full view instead; flashing close-ups that don't show clearly what happens is the failure.
- **Pitfalls:** needs hi-res originals, not video stills; never crop a before/after in portrait: stack both whole. It is
  not shipped as a component: build it in a film file from `Window` shots and `Rise`.

### HookOpen: the default for any recording with strong screen moments
- **What:** 7 to 9 s of the recording's best moments full frame. The first shot dither-reveals from its still (about
  0.85 s) and plays at 1x; later shots hard-cut (0.12 s). The speaker's strongest lines are the hook audio (EDL scenes
  `hook1`, `hook2` before the body). The two-line title card reveals over the last shot on a left scrim, holds into a
  breath, lifts; the footage melts into the backdrop as the first body beat arrives. Bottom scrim for the hook captions.
- **When:** almost always. The payoff moments (a camera move, gameplay, a generated video, the finished product) are the
  hook.
- **Knobs:** `still` (first frame of shot 1), `shots: [{src, at, start}]` (shot 1's `at` is ignored), `title`, `titleAt`
  (last hook scene + 0.15), `out` (first body word - 0.75), `fade` ([first body word - 0.7, - 0.1]), `titleBox`,
  `ditherEnd`. `firstDraft(brief, {hook: {open, still, shots}, title})` wires all of it from the EDL.
- **Captions:** `<Captions center={CAP_HOOK} size={CAP_HOOK.size} from={hook1} until={faceAt} hold={0.3}/>`.
- **Pitfalls:**
  - Crop every shot to the app's content and below any burned-in HUD/UI text (it collides with the logo). Check the
    top-left 640x200 of each shot's frames.
  - Hook lines are **removed from the body** so nothing plays twice.
  - Keep any logo outside blurred layers (black-box bug).

### PixelOpen: a talk whose payoff is one still result (no strong motion)
- **What:** the hero image and the two-line title (one italic word) reveal as dither pixels, with the brand logo mark small
  in the top-left if the theme has one. At `out` the title lifts away and the hero glides into the first beat's result
  node (`glide.to`).
- **When:** a how-to or explainer with one image that sums up the payoff.
- **Knobs:**
  - `hero` (square-ish works best, 740 px box);
  - `title` (`{lines: [[{t:'How to Build'}], [{t:'a '}, {t:'Funnel', italic: true}, {t:' in a Day'}]], size: 110}`);
  - `out` (about 3.25 s: the voice starts right after);
  - `glide`.
- **Keying:** the first 1.5 s is silent (LEAD) plus the intro scene. The voice starts as the title leaves.
- **Variations:** no glide (the hero fades), a different hero per film, a title on one line, `logo={null}`.
- **Pitfalls:** the hero must be the film's own result. A striking unrelated picture is wrong.

### Lockup: partner or collaboration pieces
- **What:** two or more logos rise out of a blur one by one, centred. An optional `grow` layer is revealed radially. It
  melts at `out`.
- **When:** case studies with a partner.
- **Knobs:** `parts: [{src, h, grow?}]`, `out: [a, b]`, `gap`.

### Arc first
Open on the arc of finished pieces (see Arc) under a two-line headline. This works when the results are the hook.

---

## Display type

### Headline: kinetic key lines
- **What:** lines rise on their own words; all leave together with a slow melt.
- **When:** the two or three lines that carry the argument ("One simple *plan*.", "Not someone else's idea." /
  "*Your own work.*").
- **Knobs:** `lines: [{text, at, color?}]`, `out`, `outDur` (0.9), `outEase` (GENTLE), `x/y/size/gap`.
- **Keying:**
  - `at` = `c.wordT(scene, firstWord) - 0.1` to `0.2`.
  - `out` = `c.wordEnd(scene, lastWord) + 0.45` for a key line (hold into the breath).
- **Pitfalls:** two lines max on screen. Grey then ink for contrast pairs.

### Chapter: a new section
- **What:** a 150 px two-line title plus its path in the note voice ("SETTINGS → PRICING → PLANS → SAVE").
- **When:** the moment the film moves from "why" to "how", or into a new act. At most two chapters in a 2-minute film.
- **Keying:** it rises about 1.05 s after the previous key line ends and holds about 2.3 s. The stage stays empty until it
  has gone. The window arrives 0.7 s after it leaves.

### StepColumn: the spine of a how-to
- **What:** "[N] STEP" micro label, the italic step word (the UI's own name for the thing: "Settings", "Export", "Add
  Rule", "Base Model", "Strength"), and notes that build line by line on the words that say them. It can carry a
  `StepTable` instead of notes.
- **When:** for a sequence of actions or settings. It sits beside whatever the stage shows.
- **Knobs:** `steps: [{at, lines: ['Base', 'Model'], note: [{t, at?}], table?: [{name, value, f, at}], label?}]`, `end`,
  `label(i)` (e.g. `i => 'Setting'`).
- **Keying:**
  - A step's `at` = when the speaker reaches it (the click in the UI, or the scene start).
  - Each note `at` = `c.wordT(scene, word) - 0.1`.
  - A step leaves when the next arrives; the last leaves at `end`.
- **Hand-off:** `gap` (default 0.6 s): the next step word rises only after the previous one has fully left. Never set it
  to 0 on a new film.
- **Pitfalls:**
  - Words wider than about 440 px go on two lines ("Add / Rule"), or the word runs under the window.
  - Keep notes to 3 to 4 lines so they clear the speaker tile header.
  - No dashes in labels.

### StepTable: numbers the speaker compares
- **What:** rows of `NAME ......... VALUE` with thin bars (log scale for times). Rows appear as they are named, and the one
  being talked about lights in the accent.
- **When:** speeds, prices, sizes ("Plan A 5 minutes, Plan B about 10 minutes, Plan C a few hours").

---

## Stage beats

### AppWindow: a click-through on crisp UI captures
- **What:** a floating window holding a `walk` scene: 2x captures of each UI state and hover state crossfading, an eased
  camera, the cursor travelling to targets and pressing on clicks, and tooltips.
- **When:** the steps happen in an app you can capture cleanly (read-only capture, never your own signed-in session
  unless the owner agreed).
- **Knobs:** `walk` (Scene with `walk: {size, shots, camera, cursor, clicks, tips}`), `start` (film time of walk t=0),
  `inAt`, `outAt`.
- **Keying:** walk times are scene-local seconds. Put every click on the word that names it. After a re-cut, carry them
  with `tools/retime_edl.py`.
- **Pitfalls:**
  - The camera does one move at a time with holds. Moves are zooms about a fixed point (no kinks at the capture's edges).
  - The cursor never teleports (travel 0.4 s or more).
  - Continuous walks: when two scenes show the same UI, concatenate their walks instead of cutting between them.

### Window + Shot: recordings and stills with a camera and focus boxes
- **What:** a floating window of shots (images or clips) that crossfade. Each shot has eased camera keys
  (`cam: [{t, cx, cy, z}]`, 0..1 of the shot, z = zoom). **Focus boxes** dim the rest of the frame and put the accent edge
  on the thing being talked about.
- **When:**
  - Anything recorded: the recording's own screen share, a coding session, a scroll, an event video.
  - **`streamShot(brief, LEAD, from, to, {cam})`** plays the cut's own stringout in sync with the voice. It is the
    universal stage for any recording; frame out a webcam bubble with `cam`.
- **Knobs:** `win: [in0, in1, out0, out1]`, `shots`, `children` (overlays such as a report card pinned to the window).
- **Keying:** move the camera and switch focus boxes on the words ("through the API" zooms to the API line).
- **Pitfalls:** a camera move that isn't motivated by a word is noise. Hold instead. Focus boxes appear on the word and
  leave after about 1 to 1.5 s.

### FloatingPanel: one piece of real UI
- **What:** a crop of a capture (e.g. a menu) on a floating card. The cursor glides to a row and a hover highlight lights
  it.
- **When:** a single control or menu the speaker names.
- **Knobs:** `src`, `size` (image px), `at`, `scale`, `inAt/outAt`, `cursor: {from, to, arrive}`, `hover: {rect, at}`
  (rect and cursor points are in image px).

---

## Node-graph beats (cards, groups, edges)

### GraphToArc: inputs → result → arc
- **What:** up to six input images pop into a 2x3 grid in a labelled `Group`. `Edge`s draw into a result `Card` (with an
  optional `Tooltip` badge). Then the graph fades and the inputs float up into a 3D arc threaded by a thin line, with a
  micro label, and drift off.
- **When:** explaining what goes in and what comes out (reference photos → model → result; ingredients → dish).
- **Keying:** edges on the verb ("what the model *learned*"), the tooltip on the noun, the arc on the next line.

### PromptToResult: a prompt and what it made
- **What:** a text card with the key phrase in the accent pill, wired into the result image card, with a micro caption.
- **When:** trigger words, prompt structure, a specific instruction, a query and its answer.
- **Keying:**
  - The pill lights on the spoken word.
  - The result arrives on the payoff word.

### CompareRow: the same thing, different settings
- **What:** 3 to 5 results in a labelled group ("Same Input"). The one being discussed takes the selection edge and the
  rest step back to 45%.
- **When:** strength, versions, tools, before/after.
- **Keying:** selection windows on the words ("strength to *four*", then "something like *2.5*").

### NodeIn / edgeFrom: build your own graph
For graphs that don't fit the above:
- rebuild the real graph from its original assets, at full resolution;
- `NodeIn` pops a card in;
- `edgeFrom` draws an edge on a word.

---

## Closers

### Arc: finished pieces on a 3D wave
- **What:** cards rise in depth one after another, a thin line draws through them, one slow push, a micro label, and they
  drift off.
- **Slots:** `ARC6` is six mid-size cards. `ARC5` is five bigger cards with measured margins.
- **Cards:** stills or continuous clips (`{src, kind: 'vid', aspect, start}`). Far cards paint first.
- **When:** the sign-off ("Build it once. Keep *going*."), or as the opener's "world".
- **Pitfalls:**
  - Check margins on the rendered frame.
  - No looping or montage clips.
  - Clamp very wide pieces (aspect at most 1.5, width at most 500).

### Checklist: the recap that ticks
- **What:** rows (a 44 px title with the step word in italic, and a note-voice sub) arrive on the words that name them. At
  `ticksAt` the boxes fill with the accent and tick one after another.
- **When:** the recap ("you don't have to think through every setting").

### OutroCard
The brand's end card (logo, one line and handle from `brand.outro`) screened over the backdrop, about 3.2 s, after
everything has faded. Skip it if `brand.outro` is empty and the user didn't ask. If there is music, its last hit should
land on it.

---

## The speaker

### FaceNode + Captions
- `FaceNode` is a themed speaker tile (presence ring in the accent, optional logo mark before the name). Use it only when
  someone talks on camera. `brief.face = {src, crop, name}`; the crop is the speaker bubble in the source frame.
- Both appear as the cold open hands over (about LEAD + the intro scene).
- The tile plays the stringout in sync.
- Captions come from the brief's cues (rebuilt from the EDL scripts by `tools/postbrief.py`, which `build_cut.py` runs).
  Word timings put the pill on the word being said.
- **Default placement:** `<Captions center={CAP_STAGE} size={CAP_STAGE.size} from={faceAt} cueFrom={firstBodyWord - 0.3}/>`:
  one line centred on the stage axis in the band under the window. `cueFrom` keeps hook cues out of the body captions.
- Pass `streamSize` to `FaceNode` when the source isn't 1280x720, and `cursorName={brief.cursorName}` to `AppWindow` /
  `FloatingPanel`.
- Fix transcription with the EDL's `captionFixes` and the brand glossary.

---

## Clip composition (the other template)

`Clip` is a generic, brand-themed composition for standalone short clips (clip-farming). It is not a film you author per
beat: you give it a brief and it renders. Briefs are written by `tools/make_clip_brief.py` as `briefs/<slug>.clip.json`;
`tools/export_clips.py` runs the whole batch. Render one by hand:

```
npx remotion render src/index.tsx Clip _work/<slug>-raw.mp4 --props=briefs/<slug>.clip.json
```

It takes width, height and duration from the brief (`seconds` plus the outro's seconds), so one composition serves 9:16,
4:5, 1:1 and 16:9. What the brief controls:

- **Layout:** `fill` (one video fills the frame), `split` (content video on top, speaker video below; needs `video2`),
  `blurfill` (the video fitted over a blurred copy of itself, for a source whose shape doesn't match the target).
- **Captions:** burned-in, word-timed, in the style from `captionStyle` or `brand.style.captionStyle` (`pill`,
  `karaoke`, `plain`, `box`, or `none`), at `captionPos` (`lower`, `center`, `upper`). Same break rules as the editorial
  template: by sentence and comma, never on a weak word.
- **Hook:** an optional big opening line over the first seconds.
- **Lower third:** an optional name and role card.
- **Progress bar:** an optional thin accent bar across the clip.
- **Outro:** an optional end card from `brand.outro`.
- **Safe zones:** `safeZone: social` keeps the top 12% and bottom 22% clear of captions and type, for platform UI.

The video in a clip brief is silent, already cut and reframed to the target size; the cut, leveled dialogue is the
separate `voice` file. For the exact prop names and defaults, read the brief type in `src/schema.ts` and the composition
source (`src/index.tsx` and the files it imports) rather than guessing. See `clip-farming.md` for picking and exporting
clips.

---

## Recipes (how beats combine)

| Film type | A typical spine |
|---|---|
| Product demo recap (editorial) | HookOpen (screen recording → best line → payoff line + title) → StepColumn beside Window of recording clips → Chapter → AppWindow or Window with focus boxes on each control as it's named → CompareRow (before / after) → Headline pair over Arc of real outputs → OutroCard |
| How-to or tutorial | PixelOpen → GraphToArc (what it is) → Headline pair (the principle) → Chapter → StepColumn beside AppWindow → PromptToResult / CompareRow for settings → Checklist → Arc sign-off → OutroCard |
| Case study | Lockup → Arc of results under a two-line headline → Chapter → StepColumn beside Window shots with focus boxes → node graphs from the original assets → Arc again → OutroCard |
| Lecture or talk highlight | HookOpen of the sharpest claim → Window of the slide being discussed with focus boxes → Headline (the takeaway) → OutroCard |
| Quick tip (under 45 s) | Headline (the tip) → one stage beat (Window or PromptToResult) → one line of notes → OutroCard |
| Clip-farm short | `Clip` with `fill` or `split`, captions, a hook line, optional outro; no authoring per beat |
