# Clip-farming: many good short clips from one long recording

Use for podcasts, interviews, livestreams, webinars, talks, panels, long tutorials. The aim is a set of clips that each
work with no context, look like one series, and are ready to post.

## Pipeline

1. **Prepare.** `python3 tools/prepare_source.py <file> <source-id>` (or `fetch_source.py` for a link first). Read
   `source/<id>/transcript.txt` and the contact sheets: topics, speakers, screen-share stretches, quality problems.
2. **Mine candidates.** `python3 tools/farm.py <source-id> --min 20 --max 60 --top 20 [--topic "pricing"]`. It writes
   `_work/farm/<id>/candidates.md` and `candidates.json`: ranked windows snapped to sentence boundaries with a score and
   plain reasons. It finds likely moments; it does not understand meaning. You do.
3. **Judge.** Read `candidates.md` and the transcript around each. Keep a candidate only if all are true:
   - **Stands alone:** a stranger understands it without the rest of the recording (no "as I said earlier", no unexplained
     "that", "it", "they" in the first sentence; if a clause of setup fixes it, widen the window by that clause).
   - **One idea** with a payoff: a claim and its proof, a question and its answer, a story with an ending, a surprise,
     a joke that lands, a strong opinion, a useful step.
   - **Strong first line** (it can become the hook) and a **clean last word** (a full sentence, not a trailing thought).
   - **Safe:** no personal data, private business numbers, unreleased plans, slurs or defamation, third parties who did not
     agree (see Guardrails in `guided-mode.md`). Ask the owner once if unsure.
   - **Different from the others:** no two clips making the same point.
   Adjust start and end by hand when a better boundary exists (`tools/find.py` searches the transcript).
4. **Show the shortlist** in plain English (see `intake.md` section 3): number, time, length, a one-line description, why
   it works. Recommend your top picks (default: top 8 to 12) and let the user pick numbers, add, or say "you choose".
5. **Emit cuts.** `python3 tools/farm.py <source-id> --emit-edls --pick 1,3,5,8 --prefix <show>` writes
   `cuts/<show>-NN.edl.json`. Add, per clip: `title`, a `hook` line (the speaker's own strongest words, or a short
   on-screen line that is true to what is said), and name tag info if known. Then split hesitations
   (`split_pauses.py`) and check ums (`find_ums.py`) per `story-and-cutting.md`.
6. **Look.** Make sure `public/brand/brand.json` is right (`brand-and-style.md`). Pick the layout per clip: `fill` for one
   camera or a centred speaker, `split` for two people or screen plus speaker, `blurfill` when the source is wide and must
   not be cropped.
7. **Proof clip.** Export one clip (`python3 tools/export_clips.py <show>-01`), show a still and the file, get a yes on the
   look. Change the look once, here.
8. **Batch.** `python3 tools/export_clips.py --all --platform reels` (or the platform the user named). It builds the cut,
   reframes, renders, levels loudness, and writes the `.mp4`, `.srt` and thumbnail to `deliverables/`.
9. **QA the set** with `qa-checklist.md` (clip-farm section): open real frames from each clip, read each clip's final
   transcript, check every first two seconds and last second, check loudness is within 1 LU across the set.
10. **Hand over.** Give the folder path, a table (file, length, one-line description), and the next-step menu. Update
    `EDIT-LOG.md`: source, picks, look, platform, loudness numbers.

## Writing hooks and titles

- A hook is the point in as few words as possible, in the speaker's own voice if possible. Trim stammers and setup
  ("so basically what I wanted to say is").
- On-screen hook text must be true to what is said. No invented numbers, no clickbait the clip does not pay off.
- Titles (file names and optional posting text) are plain and specific: "Why most pricing pages fail", not "You won't
  believe this". Unique per clip. No dates or version numbers in titles.

## Series consistency

Same brand theme, caption style, end card text, loudness and safe zones across the set. Numbered file names keep order
(`<Title> v1.mp4`; the tools handle versions and keep only the latest in `deliverables/`). If the user wants variety
(different hook styles), vary the hook, not the look.

## Rules of thumb

- Fewer, better clips beat many weak ones. If only six clear the bar, deliver six and say why.
- Prefer moments with a visible change (gesture, laugh, screen result) for the first second.
- Do not stretch a clip past its point to hit a length target. 18 s that lands beats 45 s that drifts.
- Overlapping source moments: one clip per moment, unless the user asks for a short and a long version.
- Rights: you only edit what the user owns or has permission to use. Do not add music, footage or other people's clips
  without permission.
