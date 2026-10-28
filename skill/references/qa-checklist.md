# QA gates

Every version passes these before anyone sees it. "It rendered" proves the code runs; it doesn't prove the film is good.
Look at real frames and read the real transcript. Sections marked (editorial) apply to the editorial template; sections
marked (clip) apply to the generic `Clip` composition and clip-farm sets. Everything else applies to both.

## Before rendering

- [ ] `python3 tools/build_cut.py cuts/<slug>.edl.json` has no `NO PAUSE FOUND` you haven't checked, and the verify pass
      flags only mishearings.
- [ ] `python3 tools/audit_audio.py cuts/<slug>.edl.json` shows: 0 pauses over 0.45 s, 0 slivers, 0 clicks, alignment
      N/N, stem about -16 LUFS. Every flag was listened to.
- [ ] Stills of the key moments: `node scripts/stills.mjs <Id> _work/qa <sec> <sec> ...` (SCALE=0.5 is enough for
      layout). Check:
  - type is the theme's display font (`fonts.display`), not a serif fallback (a fallback means the font file is missing);
  - colours come from the active theme (accent, ink, background), nothing off-palette;
  - captions: one line (editorial) or at most two (clip), breaks by sentence and comma, no line ending on a weak word,
    the spoken word highlighted, inside the safe zone (below);
  - (editorial) notes clear the speaker tile, nothing crosses into the stage from the step column, captions centred on
    the stage axis, step words never overlap (check a still 0.3 s after each step change);
  - (editorial) hook shots full frame, with no burned-in UI text near the logo or under the title;
  - when the speaker names a thing on screen, the whole thing is in frame, with a focus box.

## After rendering

- [ ] **Transition strips** at every hand-off: `python3 tools/strips.py _work/<raw>.mp4 <t0> 0.3` (8 frames). Check:
  - no ghosting (a beat still melting while the next rises in the same place);
  - chapter titles gone before the window arrives;
  - key lines holding into their breath and then melting, not snapping;
  - windows settling, not popping.
- [ ] **Glitch scan:** look at one frame every 0.25 s (or run `tools/glitch_scan.py <video>`; it must print
      `none`). A single green or shifted frame is a decode error in the render, not in the cut; it does not reproduce, so
      re-render.
- [ ] **Margins:** nothing within about 150 px of the sides of a 1920 wide frame (scale for other sizes) except
      full-bleed backgrounds. Measure the bounding box of non-background pixels (PIL `ImageChops.difference` against the
      empty backdrop, then `getbbox()`).
- [ ] **Motion:** one camera move at a time; no card wobble, flicker or grain; clips continuous at 1x (no loop restarts,
      no montage cuts); the backdrop never moves.
  - **Frame rates:** every clip is 30 fps. Frame-blend 24/25 fps sources:
    `ffmpeg -i in.mp4 -vf "minterpolate=fps=30:mi_mode=blend" out.mp4`. A choppy low-fps screen recording (under about
    20 fps) reads better as a sharp still with a slow push.
- [ ] **Copy:** every label and number is literally true to the source; prompts and quotes shown on screen are the real
      ones; names are spelled as the owner spells them (see the glossary in `public/brand/brand.json`).
- [ ] **Sound:**
  - `python3 tools/finish.py ...` lands -14.3 LUFS (or the platform target), true peak under -1.5 dBTP, limiter p95 at
    most about 3 dB.
  - Section loudness is roughly: music-only open -18 to -22, speech -13 to -17.
  - If there is music, it ducks under speech and its ending lands with the sign-off or outro card.
- [ ] **No repeats:** no line is heard twice (hook lines are cut from the body).
- [ ] **Words:** transcribe the finished file and read it end to end (Whisper may invent a phrase over a music-only open;
      check the voice stem before chasing it):
  ```
  ffmpeg -i "<final>.mp4" -vn -ac 1 -ar 16000 _work/f.wav
  tools/transcribe _work/f.wav _work/f.json
  ```
  Every line is there; no stray "um" or "uh" at the joins you cut; no fragments ("but", "that") where a join grabbed the
  start of a filler. The first word of the hook and the last word of the sign-off are whole.
- [ ] **Ums and restarts:** `python3 tools/find_ums.py "<final>.mp4"` prints `none` (a flag marked "over silence" is
      Whisper inventing an "Um," before a first word: ignore it). The plain transcript cannot show this: it drops ums.
- [ ] **Hook is minimal:** every sentence of the hook carries the point; no setup filler, no repeated clause, no stammer;
      the first body word lands within about 7 s.
- [ ] **Ending:** the real sign-off with about 1 s of room tone after the last word; everything fades together; the film
      fades out in its last 0.7 s.

## Clip-farm checks (clip)

Run these on every clip of a set, then once across the set.

- [ ] **Stands alone:** a stranger understands it with no missing context ("as I said earlier", "that one" with no
      referent, a name never introduced). If a clip needs a setup line, extend the start or drop the clip.
- [ ] **Starts on a full sentence:** the first word is the start of a sentence, not "and", "so", "but" mid-thought.
- [ ] **First 2 s earn the swipe:** a claim, a question, a result or movement, not a greeting or a pause.
- [ ] **Ends clean:** the last sentence is finished, with about 0.5 to 1 s of room tone, and it closes the thought.
- [ ] **Captions inside the safe zone** for the target platform (`safeZone: social` keeps the top 12% and bottom 22%
      clear; check on a real frame at the platform's size).
- [ ] **No clip over the platform max** (`tools/presets.json`, `maxSeconds`).
- [ ] **Thumbnail frame** is not a blink, a mid-word mouth or a transition; it shows the speaker or result clearly.
- [ ] **File names and titles are unique** across the set and in `deliverables/`.
- [ ] **One loudness across the set:** every clip lands within about 0.5 LU of the same target.
- [ ] **No overlap:** two clips do not share the same sentences unless the user asked for variants.

## Delivery

- [ ] File name: `<Title> vN.mp4` at the chosen size (1920x1080, 1080x1920, 1080x1350 or 1080x1080), 30 fps, H.264, AAC.
      Keep the raw render in `_work/`.
- [ ] `EDIT-LOG.md` entry: what was asked, what changed, what's still open, the loudness numbers.
- [ ] Nothing published or shared unless asked. Costs quoted in USD before any paid step.

## Energy gate (before every delivery; see `energy.md`)

- The first 3 s would stop a scroll (result first, something already moving).
- Every beat passes at least one test: funny, cool/pretty, or people would care. Anything else is cut.
- No stretch of about 3 s with nothing changing on screen; no still held past about 1 s unless it is the payoff.
- Length is under 60 s (or the platform max), or the reply says why not and what would be cut next.
