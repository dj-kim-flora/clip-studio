# Motion language

The look is **editorial and real**: a designed backdrop, restrained type, real footage and real product UI. The pace is
**fast by default** (`energy.md`); the slow, calm timings below are the optional *editorial mode*, and where a value here
conflicts with `energy.md` (holds, hand-off lengths, step `gap`, key-line breath), `energy.md` wins unless the user asked
for slow. Every value below lives in code (`src/premium/core.tsx`, `src/ui.tsx`, `src/theme.ts`); change it there, not per
film.

**Colours, fonts and backdrop come from the active theme** (`public/brand/brand.json`, loaded by `src/theme.ts`):
`colors.*`, `fonts.display`, `fonts.body`, `style.backdrop`, `style.radius`, `style.motion`. This file describes
structure and behaviour; wherever it says "accent", "display face" or "backdrop" it means the theme's values. This file
covers the **editorial template**. The other template, the generic `Clip` composition used for clip-farming, shares the
theme, the caption rules and the curves, but has its own simpler layout (see `beat-library.md`, "Clip composition").

## Canvas

- Editorial template: 1920x1080, 30 fps, `colors.background` behind the backdrop (`Backdrop`, default dots at spacing 24:
  1.05 px dots at 85% grey). Other sizes (4:5, 1:1, 9:16) reflow the same pieces; never crop a before/after, stack both
  whole.
- **The backdrop never moves.** A zooming or panning backdrop shimmers, and the camera never moves the canvas. Motion
  happens in the objects on it.
- A soft vignette sits over everything (`Vignette`).
- Everything fades together into the outro card at the end. The card is screened over the backdrop, so the dots stay.

## Type

| Role | Face | Size | Colour | Notes |
|---|---|---|---|---|
| Chapter title | display | 150 px, line-height 1.0 | ink | two lines, one italic word |
| Step word | display italic | 124 px | ink | one or two lines; over about 440 px wide, two lines |
| Headline | display | 100 px, 110 px line pitch | ink / grey | one italic word; two-tone pairs |
| Checklist title | display | 44 px | ink | the italic word echoes the step word |
| Micro label | body | 15 px, 0.08em, UPPERCASE | muted | "[1] Step", "Example · 6 of 21" |
| Note / subtext | body | 19 px, 0.08em, UPPERCASE, lh 1.5 | light grey | step notes, chapter path, table rows |
| Captions | body 400 | 34 to 40 px, lh 1.18, -0.01em | ink | see Layout |
| UI text | body | the UI component's own specs (`src/ui.tsx`) | | node headers 18 px, badges 18 px 500 |

- There is no fake bold and no silent fallback: if `fonts.display` fails to load, say so (the render shows the fallback
  serif). If the theme has no italic file, skip the italic accent word and use the accent colour on that word instead.
- **One italic accent word** per headline, chosen for meaning: "One simple *plan*.", "Your own *work*.", "Keep *building*."
- **Two-tone contrast:** a grey line answered by an ink one.
- **Every piece of subtext speaks in one voice** (uppercase body face, 15 px labels / 19 px notes). Subtext that doesn't
  match reads as sloppy.
- Labels: no hyphens or dashes; use the middle dot and the arrow. UI labels in Title Case.
- Type arrives with `Rise`: it slides up out of a mask with a 6 px blur that clears as it lands (1.2 s, entrance curve),
  and leaves by lifting 25% of its size with a blur. `style.motion: calm` scales durations up (about 1.5x).
- `style.headlineCase: upper` switches headlines to uppercase and turns off the italic word.

## Colour

- Ink, secondary, tertiary and grey-headline tones come from `colors.ink` and `colors.muted`.
- **`colors.accent` is the only accent** (`ACCENT` / `accent(a)` in `src/theme.ts`). Use it for:
  - the speaker tile's presence ring;
  - the pill on the spoken caption word (25% fill, 1.5 px edge);
  - the same pill on a key word inside a prompt;
  - focus boxes on recordings;
  - the live row of a table;
  - the ticked checklist boxes;
  - the cursor and its name pill;
  - the progress bar in a clip.
- `colors.accentInk` is accent-coloured text on dark; `colors.accentFill` is the deep tint for pills and panels.
- The accent is never decoration. Keep to the theme: do not add a second accent or a neon colour that is not in it.
- Results, UI and photos keep their real colour. Nothing is tinted.

## Motion

| Curve | Bezier | Use |
|---|---|---|
| entrance | (0.16, 1, 0.3, 1) | things arriving: type, nodes, windows |
| camera | (0.65, 0, 0.35, 1) | camera moves, morphs, gliding a hero into a node |
| exit | (0.7, 0, 0.84, 0) | quick exits (step words swapping) |
| melt | (0.37, 0, 0.63, 1) | slow exits: key lines, acts, windows leaning away |
| pop | (0.23, 1, 0.32, 1) | tooltip / node pop |

- **Calm (editorial mode; in the default fast mode keep the no-wobble rule but cut holds and moves shorter):**
  - One camera move at a time, with holds between.
  - No per-card wobble, no film grain, no flicker, no shaking.
  - One slow push (1.5 to 3.5%) may hold a static composition alive.
- **Hand-off rule:** a beat tied to a line melts (0.6 to 0.9 s) starting just after that line's speech ends, and is gone
  before the next beat rises in the same place. Ghosted overlaps read as sloppy.
- **Step words never overlap.** `StepColumn`'s `gap` (default 0.6 s) holds the next step word until the previous one has
  fully lifted away.
- **Key lines hold:** after a key line, the headline and its visual hold about 0.45 s into the breath, then melt over
  0.9 s. The next chapter rises after them. Snapping away right after a key line reads as an abrupt jump.
- **Windows** settle from a 3D tilt (rotateY -14 degrees, rotateX 6 degrees, scale 0.92, 60 px right) over 1.8 s, and lean
  away (+8 degrees, -4%) over 0.9 s.
- **Pixel-dither reveal:**
  - Ordered 4x4 Bayer dither.
  - Cells switch on outward from the centre, burn brighter as they are born, and glow.
  - They sharpen in whole steps (8, 6, 4, 3, 2, 1 px).
  - The mosaic fills solid, then hands over to the sharp image drawn underneath (no dimming, no fumble).
  - The title does the same in ink, keeping its natural weight.
- **Cursor:** the accent-coloured cursor with a name pill travels 0.4 to 0.85 s between targets and presses on clicks.
  Hover states come from real captures.
- **Clips** on cards and in windows play one continuous stretch at 1x. Avoid all of these, which read as choppy:
  - loops restarting mid-shot;
  - montages cutting every second;
  - 0.92x slow-downs;
  - 25 fps footage in a 30 fps film.

## The hook open (default opener)

- About 7 to 9 s before the first body line. The recording's best moments, **full frame**: the first shot dither-reveals
  (about 0.85 s), later shots hard-cut (0.12 s). Typical order: the most striking screen recording (silent), then one or
  two of the speaker's own strongest lines as the hook audio over the payoff footage.
- The two-line title card (one italic word) reveals over the last hook shot on a left scrim, holds about 0.8 s into a
  breath (`padBefore` on the first body scene), lifts, and the footage melts into the backdrop as the first body beat
  arrives.
- Crop footage so no burned-in UI/HUD text meets the logo or the title; crop recordings to the app's content, then scale
  to 1080p (lanczos plus a light unsharp).
- Keep any screen-blended logo outside every blurred or filtered layer: a screen blend inside a filtered group shows its
  black box.
- A still of a result behind the title reads as boring: motion from the recording wins.

## Layout (editorial, 1920x1080)

```
 x 92/98                     560                                                        1800
 ┌──────────────────────────┬──────────────────────────────────────────────────────────┐ y 146
 │ [1] STEP        (206)    │                                                          │
 │ Italic word     (232)    │     STAGE: floating window 1240x697 / node graphs /      │
 │ word 2 (if long)         │     panel / arc                                          │
 │ NOTE LINES ...           │                                                          │
 │ (440 px wide, <= ~650)   │                                                          │ y 843
 ├──────────────┐           └──────────────────────────────────────────────────────────┘
 │ Name         │ y 700
 │  speaker tile│  • one-line caption centred on the stage axis x 1180, y ~ 922 (window bottom to tile bottom)
 │  300x300     │
 └──────────────┘ y 1000
```

- **Column:**
  - Micro label at y 206, display word at 232, note 35 px under the word block. The column is 440 px wide.
  - Nothing in it may cross x 560 (the stage).
  - Notes must end above the speaker tile header (y about 660): keep to 3 to 4 lines.
- **Stage:** x 560 to 1830, y about 150 to 850. Centre graphs vertically in the free stage.
- **Speaker tile (`FaceNode`):**
  - (96, 700), 300 px, an optional logo mark (13 px) before the name, sitting on the baseline.
  - The accent presence ring.
  - The name stays left-aligned.
- **Captions (default):**
  - **One straight line, centred on the stage axis** (x = 1180, the window's centre), vertically centred in the band
    between the window's bottom edge (y 843.5) and the tile's bottom (y 1000): `CAP_STAGE` in `core.tsx`.
  - Body face 40 px, no box, a soft text shadow; the spoken word sits in the accent pill (or accent colour for
    `captionStyle: karaoke`, plain for `plain`).
  - Lines up to about 55 characters (`captionChars: 46` plus slack), so a full line spans roughly the window's width: the
    caption reads as part of the stage. A short left-aligned line beside the tile leaves most of the band empty and
    aligns with nothing.
  - Breaks per sentence by `tools/postbrief.py`: commas are good breaks, never end a line on a weak word (and, the,
    from...), no one-word widows, very short sentences join the next line.
  - The same position holds when no window is up (chapter, sign-off arc).
  - A line holds through pauses under 1.6 s, and fades after longer ones.
  - Hook captions (over full-frame footage): centred on the frame at y 968, 46 px, over a soft bottom scrim (`CAP_HOOK`);
    they fade 0.3 s after the line and never carry into the body (`until` / `cueFrom`).
- **Arcs:**
  - Keep at least 170 to 200 px from the frame's sides; check the rendered bounding box.
  - Busy full-frame pictures go in the back slots, pieces with type in front.
  - Far cards paint first.
- **Chapter titles** own the whole canvas while up. The stage stays empty and the window arrives only after the title
  has left.
- **Safe zones** apply to vertical and square outputs: keep captions and key type out of the top 12% and bottom 22%
  (platform UI), and size type for a phone.

## UI fidelity (`src/ui.tsx`)

Cards, groups, edges, tooltips, labels and the cursor are rebuilt from the real product's look, themed by `style.radius`
and the colours. Details that read as polish:

- **Cards (nodes):** dark panel (`colors.panel`), radius from the theme, a 1 px 5% inner edge at rest, 2 px 50% accent when
  selected. Header above the card: icon 18 px, title in muted (ink when selected), model right-aligned and dimmer.
- **Groups:** a 4.5% white fill, a 1.5 px 11% edge, and a label badge on the top-left edge.
- **Badges and tooltips (one design):** panel fill, 1.5 px 11% edge, radius 12 px, ink 18 px 500.
- **Edges:** draw in over 350 ms, then one packet runs along. Use 42% white on video.
- **Text cards** (prompts): 12 px padding, body 14/1.4 at 350. Scale a small graph up (zoom about 1.15) so prompts read at
  video size.
- **Cursor:** a pointer 24 px in the accent colour, with a name pill 16 px down-right.
- Match the real product where the video shows it: if the product uses Title Case labels and one badge style, so do you.
