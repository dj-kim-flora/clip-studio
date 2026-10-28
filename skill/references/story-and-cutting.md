# From a long recording to a tight script, and cutting it

A 1 to 2 hour recording holds a couple of minutes of film, or a dozen standalone clips. The job is editorial: find the
arc, keep whole sentences, and cut so it sounds like the speaker at their best without sounding edited. For mining many
clips at once see `clip-farming.md`; the cutting rules below apply to both.

## 1. Read the recording

After `python3 tools/prepare_source.py "<recording>" <sourceId>` (or `tools/fetch_source.py` first, for a link):
- Skim `source/<id>/transcript.txt` (one line per segment with `[h:mm:ss]`).
- Search it with `python3 tools/find.py <id> "phrase" ...`. The transcriber mishears names and jargon: search for what it
  wrote ("Acme" heard as "acne"). Put correct spellings in the brand glossary.
- Look through `source/<id>/sheets/`. Note:
  - where a webcam or speaker bubble sits (for `face.crop`: `[x, y, w, h]` in source pixels);
  - overlay icons inside the bubble to erase (`face.clean`, delogo boxes);
  - which stretches are screen share, slides, or talking head;
  - where the results are.
- Read exact word times for a stretch with `python3 tools/words.py <id> 1:14:05-1:14:30`.
- To see where a word really ends, run `python3 tools/energy.py <id> 2964.9`.

## 2. Find the story

Pick the format first:
- **How-to / explainer:** the promise, then what the thing is, then the principle, then the steps, then the settings that
  matter, a shortcut if there is one, a recap, the sign-off.
- **Case study:** the result first, then the setup, the process in acts, the result again, and what's next.
- **Feature or product demo:** the best output, then the promise, the controls in order, before / after, more outputs.
- **Interview or podcast highlight:** the sharpest claim or question, the answer, one example, the line people will quote.
- **Lecture or talk highlight:** the surprising claim, the reason, one concrete example, the takeaway.

Then outline it as a table before cutting:

| # | Line (source time) | What they say | Beat on screen |
|---|---|---|---|
| 1 | 0:11:30 | "Most pricing pages hide the one number people want..." | the demo's pricing page, full frame |
| 2 | 0:11:43 + 0:12:56 | "...so put the price first... test it for a week" | headline pair over the results |

Rules:
- **Whole sentences from continuous takes**, but never with an "um"/"uh" or a restart in them: cut those out (section 4).
  A jump cut at a measured dip is better than a spoken um; a jump cut mid-word is not, so pick the dip or another take.
- Sentences can come from anywhere in the recording. Keep the claims true to what was shown or said; never splice two
  statements into one that was not said.
- **Open strong: the hook (default).** Before the first body line, one or two of the speaker's strongest lines over the
  recording's best footage (EDL scenes `hook1`, `hook2`; the first body scene gets `padBefore: 0.8` if a title needs a
  hold). **Keep the hook minimal:** only the words that carry the point, no "um"/"uh", no restart, no setup filler, no
  repeated clause. If it reads fine without a sentence, drop the sentence. Aim for 5 to 7 s to the first body word. Pick
  lines that are short, reactive and true to what's on screen. Remove them from the body so no line is heard twice. Skip
  "hello everyone" and setup chatter.
- **Stay on what was asked for.** Leave out other topics shown in the same recording, competitor comparisons, pricing
  talk, off-topic chat Q&A, and swearing, unless the user wants them.
- **End well:**
  - A recap of what was covered, then the speaker's real sign-off.
  - Never end mid-thought or on the last syllable: keep about 1 s of room tone after the final word (`endHold`). The hold
    stops early if the speaker talks again in the source; when the payoff covers the recording anyway, add
    `endHoldForce: true` so the picture holds the full time (the audio is faded out regardless). Check the final word's
    real end by transcribing a tiny window: a word after a short pause ("...better than we *do*") is easy to clip.
- **Target length:** 30 to 60 s by default (`energy.md`); up to 90 s only if every beat earns it; tips under 30 s. A
  longer, calmer cut is editorial mode, for when the user asks. Cut repetition, false starts, tangents and anything that
  is merely context. Keep the funny, the cool and the useful.
- If two stories are possible (a marketing cut versus a how-to), ask which, or make the one that was asked for.

## 3. The cut list (EDL)

`cuts/<slug>.edl.json`, from `cuts/_template.edl.json`:
- `slug`: names every output: `briefs/<slug>.json`, `public/voice/<slug>.wav`, `public/media/<slug>/stringout.mp4`.
- `source`: the recording's path. `sourceId`: its analysis folder in `source/`.
- `brief.face`: `{crop, name, clean}` for the speaker tile. Leave it out for narration-only films.
- `captionFixes`: `[regex, replacement]` pairs applied to captions (a mis-heard name fixed, a leading "Also " dropped when
  it wasn't really said). Glossary spellings from `brand.json` are applied automatically.
- `captionChars`: the maximum characters per caption line (38 for 16:9; fewer for 9:16).
- `scenes`: one per story beat, in order:
  - `{"id": "intro", "kind": "intro", "duration": 2.4}`: the silent stretch a cold open plays over.
  - `{"id": "...", "kind": "clip", "spans": [[a, b], ...], "script": "the exact words", ...}`: spans are source seconds.
    `script` is what should be heard, and the builder's verify pass checks every word of 3+ letters against a fresh
    transcript of the result.
  - `{"id": "outro", "kind": "outro", "duration": 3.2}`: the outro card.
  - Any other field on a scene is copied into the brief for the film to use (`step`, `notes`, `cam`, `walk`, `steps`,
    `inserts`, `pills`, `pointers`...).

Span modes: `[a, b]` lets the builder snap both ends into the nearest real pause. `[a, b, "exact-in" | "exact-out" |
"exact"]` pins an end:
- where two spans run straight through;
- where a cut must sit in a tiny gap (a 40 ms silence between two words);
- inside a silence you measured yourself, so the join-balancing can't borrow a faint murmur back as "quiet".

`padBefore` (seconds) holds the first frame silently before a scene. Rarely right: prefer real room tone.

## 4. Cutting rules

- **Tighten hesitations on the first pass:** after writing spans, run `python3 tools/split_pauses.py cuts/<slug>.edl.json`.
  It splits every span at each internal silence of 0.55 s or more so the builder closes it to the 0.3 s join. (Split
  points must differ: an out equal to the next in reads as one continuous take and removes nothing.) Recordings made
  while dictating or thinking aloud are full of these.
- **Transcriber timing:** the Whisper fallback stretches word stamps across silences by up to about 1 s. When a cut lands
  `NO PAUSE FOUND`, map real silences (-64 dB runs) and re-transcribe a short window around the spot; don't trust the
  long-form stamps. The verify pass often drops the first word of a very short isolated scene: confirm in the final
  transcript before "fixing" it.
- Every cut lives **inside a measured pause**. Soft consonants and word tails sit at -55 to -62 dB and room tone near -80,
  so the builder calls -64 dB a pause, waits for tails to settle below -68, and keeps 0.12 s before speech and 0.15 s
  after. Never cut mid-word.
- Each join gets about **0.3 s** of silence in total (`balance_join` borrows real pause from either side).
- **Ums, uhs and restarts: cut every one, in every scene, hooks first.** None may survive in the film.
  - **Find them.** The default transcribers drop disfluencies, so the transcript and `build_cut.py`'s verify pass look
    clean while the audio still says "scene by scene? *um*". Run `python3 tools/find_ums.py public/voice/<slug>.wav` (it
    forces Whisper with a prompt that writes ums out and flags "um"/"uh" and a phrase said twice) after every build, and on
    the finished mp4 before delivery. Its flags are times to check, not verdicts: Whisper also invents an "Um," over
    silence in front of a first word (the tool marks those "over silence").
  - **Where they hide.** Three places a first pass keeps missing:
    1. a faint murmur just after the last word of a span ("scene?" then -48 dB of "mm"): end the span at the dip between
       the word and the murmur, not at the next pause;
    2. glued to the start of the next word ("uh" then "the only proper way"): start the span at the dip after the vowel;
    3. in front of a word inside a span ("out of, uh, the front face"): split the span there and drop the uh.
  - **How to cut one.** Read a 10 ms envelope of the source (`tools/energy.py`) around the flagged time. An um is a
    steady 0.2 to 0.4 s vowel or nasal level (-35 to -48 dB), with a dip of a few dB where the real word starts. Pin the
    span end or start to that dip with `exact-in` / `exact-out`. Confirm by transcribing a short window that starts at
    the new in point: the um should be gone and the word whole. The cut costs a jump on camera; it is still the right
    trade.
  - **Restarts.** "It's not... it's not the tool's problem" keeps one "It's not": take whichever is fluent and splice at
    a dip (the first one when it is short and clean), never the drawn-out one with a 0.4 s hole before "not".
  - After the cut, the join should still sound like a comma, about 0.1 to 0.3 s; closer than that and words run together.
- **Trim hesitations over about 0.45 s** (fast mode: over about 0.35 s, `split_pauses.py --min 0.35`) to the 0.3 s join.
  Leave natural 0.3 to 0.4 s phrase pauses alone.
- **After a key line, about 0.45 s** of breath is right in editorial mode (fast mode: about 0.15 s). Much longer feels
  like dead air; much shorter feels like "it cuts too quickly". The visual melt carries the moment, not silence.
- Each internal cut is also a jump on camera. Only cut where it buys real time (a hesitation, a repeated phrase), not
  0.1 s.
- **Re-cutting:** keep the previous brief, rebuild, then run
  `python3 tools/retime_edl.py <old brief> <new brief> cuts/<slug>.edl.json`. It moves every scene-local time (walk
  camera, cursor, shots, clicks, steps, pointers, inserts, pills) through source time. Anything that fell inside a removed
  stretch lands on the join: re-spread those by hand. Also re-cut every other file that plays in film time (a separate
  speaker video, for example), then check sync on frames, not words.

## 5. Build, check, iterate

```
python3 tools/build_cut.py cuts/<slug>.edl.json          # --no-media for a quick timing pass without rendering audio/video
python3 tools/audit_audio.py cuts/<slug>.edl.json
```

- `NO PAUSE FOUND` means a cut fell back to the quietest frame. Move the span end into a real pause or pin it.
- The verify pass flags words it didn't hear. Most are mishearings (names, numbers: "4" for "forward"). A real miss means
  a span clipped a word.
- The audit flags pauses over 0.45 s, slivers at cuts (an um fragment), clicks, dropouts and misaligned spans. Listen to
  each one; fix it and rebuild.
