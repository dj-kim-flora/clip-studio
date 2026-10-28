# Purposes: pick the recipe

Each purpose is a default recipe. Start from it, change what the user asked to change, and say what you chose. "Template"
is which renderer carries the look: **Clip** is the generic composition (video fills the frame, captions, hook, name tag,
progress bar, end card; fast, ideal for sets). **Editorial** is the richer template (`firstDraft()` + the beat library:
hook open, stage window beside a step column, speaker tile, captions on the stage axis, end card). Both are themed by
`public/brand/brand.json`.

| Purpose | Length | Format default | Template | Structure | Captions | Tools |
|---|---|---|---|---|---|---|
| **Clip-farm** (many shorts from one long recording) | 20 to 60 s each, 8 to 12 clips | 9:16 | Clip | Each clip stands alone: hook line first, one idea, payoff, clean last word | word highlight, lower third of frame | `farm.py`, `build_cut.py`, `export_clips.py` |
| **Highlight reel / teaser** | 30 to 60 s (up to 90 s) | 16:9 master, 9:16 or 4:5 on request | Editorial or Clip | Hook from the strongest moment, 3 to 5 beats, closing line; best moment first, not chronological | one line, centred | `find.py`, `build_cut.py`, `firstDraft()` |
| **Podcast / interview soundbites** | 15 to 45 s each | 9:16 or 1:1 | Clip (`split` layout when two cameras) | Question (optional), the answer's best 20 to 40 s, name tag on first seconds | word highlight | `farm.py`, `reframe.py --mode split` |
| **Tutorial / demo cutdown** | 45 to 90 s | 16:9 and 4:5 | Editorial | Result first, then numbered steps beside the real screen, one note per step, recap line | one line under the screen | `firstDraft()`, `strips.py` |
| **Lecture / webinar recap** | 60 to 90 s | 16:9 | Editorial | Claim in the first sentence, 3 key points over the slide being discussed, takeaway | one line | `find.py`, `firstDraft()` |
| **Full-length clean-up** (remove ums, dead air, mistakes) | same as source, minus 10 to 30% | same as source | none (cut only) | Keep whole sentences; cut only inside measured pauses | optional burned or `.srt` | `split_pauses.py`, `find_ums.py`, `build_cut.py`, `finish.py` |
| **Event / vlog recap** | 30 to 90 s | 9:16 or 16:9 | Clip | Most striking visual first, quick cuts keyed to music or speech, location or name tags | minimal or none | `reframe.py`, `music_bed.py` |
| **Quote / audiogram cards** | 10 to 30 s | 1:1 or 9:16 | Clip (hook text large, still image or waveform behind) | One quotable line, speaker name, brand end card | word highlight | `farm.py`, `build_cut.py` |
| **Behind-the-scenes reel from a link** (a web page or canvas, no recording needed) | 20 to 45 s | 9:16 or 4:5 recorded in that shape, or 16:9 | Clip | Overview, 4 to 7 labelled steps in build order, end on the result; hook line "Behind the scenes" | step labels, plain | `record_page.mjs`, `make_reel.py` (`behind-the-scenes.md`) |
| **Reformat an existing edit** | same | requested ratio | Clip (no re-cut) | Reframe, add captions and safe zones | as requested | `reframe.py`, `export_clips.py` |

## Defaults that apply to every purpose

- Energy first (`energy.md`): the point lands in the first 2 seconds; something changes every 1 to 2 seconds; no dead air;
  every beat is funny, striking, or something the viewer would care about. If it is none, cut it.
- Keep the speaker's own voice and the real picture. Never invent claims, numbers, results or quotes.
- Whole sentences. Cut only on measured silence. Remove ums and restarts (`story-and-cutting.md`).
- Captions on unless the user says no (most feeds play muted). Captions stay inside the platform safe zone.
- One loudness for the whole set (`audio.md`). Music only if the user supplied or approved a track.
- A set of clips shares one look, one caption style, one end card, one loudness.
- Ask before: publishing or sharing anything, spending money, using someone else's music, footage or brand.

## Platform quick sheet (also in `tools/presets.json`)

| Platform | Ratio | Typical max | Notes |
|---|---|---|---|
| TikTok, Reels, Shorts | 9:16 | 60 to 90 s | Keep top 12% and bottom 22% free of text; first 2 s must hook |
| Instagram / LinkedIn feed | 4:5 | 60 to 90 s | Sound off by default: captions matter most |
| Square | 1:1 | 60 s | Works in most feeds and chat apps |
| X | 16:9 or 1:1 | 140 s | Short and silent-friendly |
| YouTube, website | 16:9 | any | Title card and chapters fine; slower pacing allowed if it earns it |

"Vertical" is ambiguous: ask whether they mean 9:16 (phone feeds) or 4:5 (feed posts). Do not guess.

## Mixed requests

A user often wants two things ("a highlight reel and some clips for Reels"). Make them separate deliverables with separate
names; reuse the same cut where possible. Do not combine a highlight and a clip set into one film.
