# Style DNA: the film, the pipeline in depth, and what never varies

This kit turns a long recording into short films. It has **two templates**:

- **Editorial template** (this file, `motion-language.md`, `beat-library.md`): a short, designed film with a hook open, a
  stage (window or node graphs), a step column, a speaker tile, one-line captions and an outro card. Authored per film from
  the shared beat library, so two films feel related but never identical.
- **`Clip` composition** (generic, used for clip-farming): one cut and reframed video, burned-in captions, optional hook
  line, lower third, progress bar and outro card, sized for 9:16, 4:5, 1:1 or 16:9. See `clip-farming.md` and the
  "Clip composition" section of `beat-library.md`.

**Colours and fonts are not fixed.** Everything below that mentions an accent, a display face or a backdrop means the
active brand theme in `public/brand/brand.json`: `colors.accent`, `colors.accentInk`, `colors.accentFill`,
`fonts.display`, `fonts.body`, `style.backdrop`. With no brand supplied the neutral default theme is used. See
`brand-and-style.md` for how a theme is made.

The runnable kit is the repository root (two levels up from this file: the "kit root"). If you only have this markdown,
find or ask for the whole `clip-studio` folder: the renderer, beats and tools live there.

## Read before you start

| When | Read |
|---|---|
| Always, first | `intake.md` (what to ask) and `purposes.md` (what each kind of output needs) |
| The look | `motion-language.md`: type, backdrop, colour, curves, layout, hand-offs |
| Choosing beats | `beat-library.md`: every beat, when to use it, its knobs |
| Picking the story and cutting | `story-and-cutting.md` (and `clip-farming.md` for many clips) |
| Sound | `audio.md`: voice chain, music, ducking, finishing, the traps |
| Before handing over | `qa-checklist.md`: the gates every version passes |
| Taste | `lessons.md`: one-line rules learned from many review rounds |

## The pipeline

Work in the kit root. Keep an `EDIT-LOG.md` entry per version: feedback, changes, open questions.

1. **Setup (once).** `bash setup.sh`, then `bash check.sh` (prints READY).
2. **Prepare the source.** `python3 tools/prepare_source.py "<recording>" <sourceId>` writes `source/<sourceId>/`: the
   analysis audio, an on-device transcript with word timings plus a readable `transcript.txt`, contact sheets, and
   `info.json`. Read the transcript and look at the sheets. Find any speaker bubble (for `face.crop`), the screen-share
   stretches, and the results worth showing. For a link, run `tools/fetch_source.py` first.
3. **Find the story.** Pick the format and outline it as a table: line they say, beat on screen. Use
   `python3 tools/find.py <sourceId> "phrase"` to locate lines. Build from whole sentences in continuous takes, open on
   the payoff or the promise, end on a recap plus the speaker's real sign-off. If the story choice is genuinely uncertain,
   show the outline before cutting.
4. **Cut list.** Write `cuts/<slug>.edl.json` from `cuts/_template.edl.json`, one scene per story beat, spans in source
   seconds. Run `python3 tools/build_cut.py cuts/<slug>.edl.json`: it snaps cuts into real pauses, balances each join to
   about 0.3 s, builds the voice stem (per-clip gain, gentle compression, fixed gain to -16 LUFS, limiter, click repair),
   writes the stringout and `briefs/<slug>.json` (captions and per-word timings), then re-transcribes the result to check
   no words were lost. Run `python3 tools/audit_audio.py cuts/<slug>.edl.json`, fix what it flags, rebuild. After changing
   spans, carry timed fields across with `python3 tools/retime_edl.py <old brief> <new brief> <edl>`.
5. **First draft.** For the editorial template add a film file `export const MyFilm = firstDraft(brief, {hero, title, ...})`
   (`src/films/first-draft.tsx`) and register it in `src/films/index.ts`. It gives the open, the recording's own screen on
   the window (synced to the voice), the step column from the scenes' `step`/`notes`, the speaker tile, captions and the
   outro. For a clip, use `tools/make_clip_brief.py` instead. Render stills:
   `node scripts/stills.mjs <Id> _work/qa 5 20 40 ...`.
6. **Author the beats** (editorial). Replace draft sections with real beats from `src/premium/`: node graphs, UI captures,
   comparisons, a checklist, a results arc. Key **every** in/out to a spoken word with the clock:
   ```ts
   const c = clock(brief, LEAD);
   c.wordT('scene', 'word')
   c.wordEnd(...)
   c.sceneAt(...)
   ```
   Never hand-type a second that a re-cut would break.
7. **Music** (only if the user supplied or approved a track; see `audio.md`). Run
   `python3 tools/music_bed.py <music> public/voice/<slug>.wav <LEAD> <film seconds> <name>`.
8. **Render, finish, audit, deliver.** `npx remotion render src/index.tsx <Id> _work/<slug>-raw.mp4 --concurrency=8`, then
   `python3 tools/finish.py _work/<slug>-raw.mp4 "deliverables/<Title> vN.mp4"` (-14.3 LUFS, true peak under -1.5). For a
   batch of clips use `tools/export_clips.py`. Run every gate in `qa-checklist.md`, then send the file in the size the user
   chose (never assume one).

## Non-negotiables (the style's DNA)

- **Type:**
  - The theme's display face (`fonts.display`) for display type, with **one italic accent word** per headline when the
    face has an italic. Everything else is the theme's body face.
  - Labels are 15 px uppercase muted grey. Notes and subtext are 19 px uppercase light grey with 0.08em tracking.
  - No hyphens or dashes in labels. Title case in UI labels.
- **Canvas:**
  - The theme's backdrop (`style.backdrop`: dots, grid, gradient or solid) behind every scene. It never zooms or pans.
  - Background and ink from the theme (`colors.background`, `colors.ink`).
  - `colors.accent` is the one accent: the presence ring, the spoken-word pill, focus boxes, live table rows, ticks.
    Never decoration.
- **Motion:**
  - One camera move at a time, with holds in editorial mode; fast cuts in the default energy mode.
  - No wobble, no grain, no flicker, no zooming backdrop.
  - Curves: entrance (0.16,1,0.3,1), camera (0.65,0,0.35,1), exit (0.7,0,0.84,0), melt (0.37,0,0.63,1).
- **Hand-offs:**
  - A beat melts away after its line ends and is gone before the next beat rises in the same place. No ghosting.
  - A key line holds into its breath and melts. Never snap away right after it.
- **Real material:**
  - Real captures of the product or the recording's own screen. Never invent results.
  - Rebuild UI and node graphs from the actual assets (`src/ui.tsx`).
- **Speaker:**
  - When someone talks on camera, their video is a themed speaker tile (`FaceNode`), bottom left: 300 px, the presence
    ring, an optional logo mark before the name.
  - Their words are one straight line, centred on the stage axis under the window, with the spoken word in the accent
    pill.
  - Narration-only films have neither.
- **Sound:**
  - One fixed gain, never adaptive leveling.
  - Cuts inside real pauses, with about 0.3 s of breath.
  - Ums removed only where they sit in silence.
  - Music (if any) ducks under speech and ends with the film.
- **Ending:** a recap of what was covered, the speaker's real sign-off, then the outro card (`OutroCard`: logo, line and
  handle from `brand.outro`) over the backdrop. No outro card if `brand.outro` is empty and the user did not ask.

## First-pass defaults

Hook open with the speaker's best lines (removed from the body) · one-line stage-centred captions · step words that never
overlap · the whole named thing in frame · footage cropped clear of HUD text · hesitations of 0.55 s or more split before
the first build (`tools/split_pauses.py`) · captions rebuilt from the verified scripts (`tools/postbrief.py`, run by
`build_cut.py`). See `lessons.md`.

## Variability: what changes from film to film

Choose per film; don't copy a previous one:
- **The opener:** the hook open (the recording's best moments full frame, the speaker's best lines, a title card); a
  partner lockup for partner pieces; a pixel-dither open only when the payoff is a single still.
- **The stage:** UI captures with the presence cursor; the recording's own screen with a camera and focus boxes; node
  graphs rebuilt from the product; floating panels.
- **Which beats and how many:** steps can be 3 to 8; a spec table, a prompt-to-result, a comparison row or a checklist
  only where the words call for them.
- **The words:** which word in each headline is italic, and the two-tone pairs.
- **Pacing:** follows the speaker, never a fixed grid of seconds.

Never vary the non-negotiables above.

## House rules

- Ask only for what you can't find: missing story facts, which results to show, access to assets. Show the outline first
  when the story choice is genuinely open.
- Quote the USD cost of anything paid before spending. Never show unreleased product or model names on screen.
- Don't publish, post or share unless asked.
- Keep the source recording untouched. Every build writes new files; versions go in `deliverables/` with `vN` names (only
  the latest stays; older ones move to `_work/superseded/`).
- Fonts and logos belong to their owners: check the licence before shipping a font file with a shared copy of the kit.
- A rendered frame proves the code runs, not that the film is good. Look at stills and strips of every transition, and
  read the final transcript before calling a version done.
