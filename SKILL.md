---
name: clip-studio
description: General video editing and clip-farming for any recording. Turns a long video or audio file (podcast, interview, livestream, webinar, talk, lecture, tutorial, demo, vlog, event) into finished videos - many standalone short clips (clip-farm), one highlight reel or teaser, a cleaned-up full cut, a recap with titles and steps, or quote cards, or a behind-the-scenes reel recorded from a web link (a project canvas, dashboard or page, captured in the background) - in 9:16, 4:5, 1:1 or 16:9, with transcript-led cuts, ums and dead air removed, word-highlight captions, loudness-matched audio and an optional music bed. The look comes from the user's own brand guidelines or reference media (or a clean neutral default). Proactive and built for non-technical users - it sets itself up, finds the file, asks a few multiple-choice questions with a recommended answer, proposes a plan, then delivers. Tool-agnostic: any coding agent that can run a shell (Claude Code, Codex, Cursor, Gemini CLI). Use when someone says "clip this", "cut this down", "make shorts from my podcast", "highlight reel", "trim the ums", "make a teaser", "reformat for Reels/TikTok/Shorts", "add captions", "edit my video", or "make a behind-the-scenes / how-I-made-it reel from this link".
---

# Clip Studio: general video editing and clip-farming

A runnable kit plus playbook. Keep source recordings untouched. Generated files stay in the project:
`source/` (prepared recordings, brand inputs), `cuts/` (edit decision lists), `briefs/`, `public/` (media the renderer
reads), `_work/` (scratch, QA stills, raw renders), `deliverables/` (finals only, latest version of each).

## Be proactive: start here

Most users do not code and do not know video terms. Read `skill/references/intake.md` and follow it:

1. Run `bash check.sh`; if NOT READY run `bash setup.sh`. Find the file or link yourself, prepare and read it.
2. Ask one batch of at most four multiple-choice questions (purpose, where it will be watched, how much, what it should look
   like), each with a recommended default. Skip anything you can infer. "You decide" is a valid answer.
3. Come back with a plan (what you found, what you recommend, one alternative at most), get a go.
4. For a set, make one proof clip and get a yes on the look. Then do everything else without further prompts.
5. Deliver, show the paths, and offer next steps unprompted.

If the request is vague ("edit my video"), show the capability menu in `intake.md` section 6 with your recommendation first.

## Any agent, one source

This folder is both the skill and the kit. `bash setup.sh` links it into `~/.agents/skills`, `~/.claude/skills` and
`~/.codex/skills`; agents without a skills folder open this repository and follow `AGENTS.md`. Resolve the kit root as the
real path of this `SKILL.md`'s folder and run every command from there. Shell, Python, Node and ffmpeg do the work.

## What it can make

Pick the recipe in `skill/references/purposes.md`: clip-farm, highlight or teaser, podcast soundbites, tutorial or demo
cutdown, lecture or webinar recap, full-length clean-up, event or vlog recap, quote cards, reformat of an existing edit, and a **behind-the-scenes reel from a link** (no recording needed: it records a web
page or canvas headlessly; `skill/references/behind-the-scenes.md`).
Formats: 9:16, 4:5, 1:1, 16:9. Ask which; never guess ("vertical" could be 9:16 or 4:5).

## Two templates, one look

- **Clip** (generic composition): video fills the frame (or split / blurred-fill), word-highlight captions, hook line, name
  tag, progress bar, end card, platform safe zones. Fast and consistent: use it for sets. `tools/export_clips.py`.
- **Editorial** (`firstDraft()` + beat library): hook open, stage window beside a step column, speaker tile, captions on
  the stage axis, diagrams, end card. Use it for recaps of demos, tutorials and webinars.

Colours, fonts, logo, backdrop, caption style and end card come from `public/brand/brand.json`
(`skill/references/brand-and-style.md`). Ask for the user's brand guidelines or a reference video first; use the neutral
default only when they have neither, and say so.

## Read first (in this order)

1. `skill/references/intake.md` (how to start and what to ask), `purposes.md` (the recipe), `guided-mode.md` (non-technical playbook)
2. `skill/references/energy.md`: the bar. Funny, striking, or something people would care about. Boring is the only failure.
3. `skill/references/story-and-cutting.md`, `audio.md`, `qa-checklist.md`
4. For clip sets: `clip-farming.md`. For the look: `brand-and-style.md`.
5. For the editorial template only: `style-dna.md`, `motion-language.md`, `beat-library.md`, and `src/films/first-draft.tsx`.

## Pipeline

1. `python3 tools/prepare_source.py "<file>" <source-id>` (links: `tools/fetch_source.py "<url>" <source-id>` first). It writes
   `source/<id>/` with analysis audio, transcript with word times, contact sheets. Search with `tools/find.py`.
2. Decide the cuts. Clip-farm: `tools/farm.py <source-id> ...` then read `_work/farm/<id>/candidates.md` and pick with
   judgment. Other purposes: outline source lines into beats. Write `cuts/<slug>.edl.json` (template: `cuts/_template.edl.json`,
   clip template: `cuts/_template-clip.edl.json`). Cut only inside measured pauses; keep whole sentences; remove ums and
   restarts (`tools/split_pauses.py`, `tools/find_ums.py`). Never invent claims.
3. `python3 tools/build_cut.py cuts/<slug>.edl.json` builds the stringout, the leveled voice, and the brief with captions.
   Then `tools/audit_audio.py`; fix lost words, slivers, clicks.
4. Look: confirm `public/brand/brand.json`. Reframe and render:
   - Clip: `python3 tools/export_clips.py <slug>...` (or `--all`; `--platform reels|tiktok|shorts|linkedin|x|youtube`).
   - Editorial: build with `firstDraft(brief, {...})` then `npx remotion render src/index.tsx <Id> _work/<slug>-raw.mp4`
     and `python3 tools/finish.py _work/<slug>-raw.mp4 "deliverables/<Title> v1.mp4"`.
5. Music only if the user supplied or approved a track; duck it with `tools/music_bed.py`. Otherwise none.
6. Run the gates in `skill/references/qa-checklist.md` on real frames and the final transcript. Log in `EDIT-LOG.md`.

## Defaults (apply without waiting for review)

- Energy first: 30 to 60 s for a highlight (up to 90 if every beat earns it); 20 to 60 s per clip; the point lands in the first 2 s.
- Start on the voice: no more than about 0.5 s of picture before the first word. The hook is the point in as few words as possible.
- Captions on unless declined: one or two short lines, breaks at sentence and comma boundaries, never on weak words, inside the safe zone.
- Show the thing being named, fully in frame. No line heard twice. Same look, captions, end card and loudness across a set.
- Loudness: one fixed gain to the platform target (default -14 LUFS integrated, true peak under -1 dB), never single-pass loudnorm.

## Guardrails (always)

- Never modify or delete the original recording. Never publish, post, upload or share; hand over the files.
- Never invent quotes, numbers, results or claims. Use only what was said or shown.
- Recording a link: read-only, signed in by the user themselves (never script a login), and ask the owner before showing client or private content.
- Personal data, private numbers, unreleased plans, other people's faces or names: ask the owner once before including.
- Only use music, footage, fonts and logos the user owns or has the right to use. Quote any cost first and wait for a yes.
- Keep `EDIT-LOG.md` current so "do the same for my next recording" works.

## References

- `skill/references/intake.md`: the proactive start: legwork, question batch, plan, proof, next steps
- `skill/references/purposes.md`: recipes per purpose and platform
- `skill/references/clip-farming.md`: many clips from one recording, end to end
- `skill/references/behind-the-scenes.md`: a reel recorded from a page or canvas link: sign-in, tour file, record, reel
- `skill/references/brand-and-style.md`: getting the look from guidelines or reference media
- `skill/references/guided-mode.md`: non-technical playbook, versatility table, guardrails
- `skill/references/energy.md`, `story-and-cutting.md`, `audio.md`, `qa-checklist.md`, `lessons.md`
- `skill/references/style-dna.md`, `motion-language.md`, `beat-library.md`, `examples.md`: the editorial template
