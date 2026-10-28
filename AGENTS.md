# Agent instructions

This folder is the Clip Studio kit: a general video editing and clip-farming skill. Before any edit, read `SKILL.md`, then
`skill/references/intake.md`. Most users do not code: be proactive, run `bash check.sh` yourself, ask a short batch of
multiple-choice questions with a recommended answer, and keep messages free of jargon. These instructions are the same for
every agent (Claude Code, Codex, Cursor, Gemini CLI, others); `CLAUDE.md` and `GEMINI.md` only point here.

- Work in this folder. Never modify the source recording. Finals go to `deliverables/` as `<Title> vN.mp4` (latest only;
  superseded versions and all scratch go in `_work/`).
- The look comes from the user, not the kit: read `public/brand/brand.json` and `skill/references/brand-and-style.md`. Ask for
  brand guidelines or reference media before falling back to the neutral default.
- Key every editorial-template beat to a spoken word with `clock()` (`src/premium/core.tsx`); never hand-type a second that a
  re-cut would break.
- Keep an `EDIT-LOG.md` entry per delivery: the request, the choices made, open questions, loudness numbers.
- Run the gates in `skill/references/qa-checklist.md` before handing over. Look at real frames and read the final transcript.
- Recording a link (`tools/record_page.mjs`): read-only; the user signs in themselves (`--login`), never script or store a password; ask first if the page shows client or private content; the sign-in profile stays outside the repo.
- Never publish, post or share. Quote any cost in advance and wait for a yes. Use only music, footage, fonts and logos the
  user owns or may use.
- Do not commit media, dependencies, fonts, logos or brand guidelines. `public/brand/` keeps only the neutral default and
  the open-licence Geist font in git.
- Edit the skill in this repository only; each agent's skill folder is a symlink to it.
