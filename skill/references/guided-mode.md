# Guided mode: the playbook for people who don't code

Most people who ask for a clip, a recap or "a bunch of shorts from my podcast" are not engineers. They hand over a file or
a link. You do the technical work; they make the editorial calls.

## Be proactive: start without being asked twice

1. **Check readiness yourself.** Run `bash check.sh`. If it prints NOT READY, run `bash setup.sh`, fix what it reports
   (install ffmpeg or Node with Homebrew, etc.), and re-check. Don't hand the user a list of commands. If something needs
   their hands (approve a macOS prompt, sign in to a site), say exactly what to click, in one sentence.
2. **Find the recording yourself.** Accept a file path, a file dropped into the chat, a folder ("the newest video in
   Downloads"), a YouTube, Vimeo, Zoom, Loom or Drive link (`python3 tools/fetch_source.py <url-or-path> <source-id>`), or
   an audio-only file. Search likely places before asking where it is. Never modify the original; work on a copy.
3. **Ask a SHORT batch of questions, all at once, only for what you can't infer.** Each question offers concrete options
   and a recommended default. The actual list lives in `intake.md`; don't improvise a longer one. If they say "you
   decide", decide and say what you chose.
4. **Come back with a plan, not a question.** Transcribe, find the strongest material (`energy.md`: lead with the
   funniest, coolest or most useful moment, not the chronological start), and present a short outline in plain English: the
   hook and what it shows, the main points in order, the closing line, the expected length (or, for a clip set, the list
   of picked clips with one line each). Recommend one plan; offer a second only if the recording truly supports two.
   End with "Good to cut this?"
5. **Then do everything else without further prompts:** cut, first draft, render, run the QA gates, show the result.
   Offer a fast preview before the polish pass if the wait will be long.
6. **Offer next steps unprompted:** a shorter cut, a different hook, another aspect ratio, captions only, more clips from
   the same recording, a different look.

## Speak plainly

- No jargon in messages: say "I cut the pauses and the ums", not "split hesitations in the EDL". Say "video file", not
  "master". Explain a technical step in one clause only when it affects them ("this takes about 10 minutes").
- Give time and cost expectations before long or paid steps. Quote USD before spending anything.
- Show, don't describe: open or point to the rendered file and a still or two. Put the output where they can find it
  (`deliverables/`, with the full path; offer to open the folder).
- Take feedback in their words ("it feels rushed", "cut that story", "make it punchier") and translate it yourself.
- When something fails, say what happened in a sentence, what you're doing about it, and only ask if you're truly blocked.

## Versatility: what the recording may be

| Recording | What to do |
|---|---|
| Screen-share demo / tutorial | Stage window plus step column (editorial template), or fill-frame with captions for a clip |
| Webinar or lecture with slides | Treat the slide being discussed as the "product": frame it, pull headline words from slide titles |
| Talking head / fireside chat | No product window: captions, a speaker tile, headline beats and quotes |
| Multi-speaker podcast or panel | Label each speaker; pick self-contained question-and-answer exchanges; split layout only if there is real video of each person |
| Audio-only (podcast, call) | Type-led: captions, quote cards, an audiogram-style card; say up front that it is type-led |
| Vlog / b-roll heavy | Let the picture lead: cut to action, keep ambient sound under the voice, captions small |
| Gameplay | Keep the game full frame, voice-over reactions on top, crop out HUD text that fights the captions |
| Music performance | Never cut mid-phrase; keep the original audio and loudness; captions optional |
| Q&A heavy | Pick the best two or three question-and-answer pairs; cut the rest |
| Multiple recordings | One film per recording unless they ask to combine; prepare each under its own source id |
| Foreign language | Transcribe and caption in that language; say that spelling needs a native check |
| Rough audio or video | Run `tools/audit_audio.py`, repair what you can, tell them honestly what you couldn't |

## Guardrails (always)

- Never edit or delete the original recording. Never publish or share; give them the file and let them post it.
- Never invent claims, results, numbers or quotes. Only use what was said or shown. If a line is ambiguous, leave it out.
- Personal data, third-party faces, unreleased information, pricing talk, and other people's names: ask the owner once if
  you spot any, and leave them out unless the owner says they're fine.
- The recording is the owner's private material. Don't send it, its transcript or its frames anywhere beyond the tools
  the kit already runs, without saying so and getting a yes.
- Copyright: music, film clips and images you did not make are not yours to add. Use what the user supplied or confirmed
  they may use.
- Keep `EDIT-LOG.md` current. A user who comes back next week should be able to say "do the same for my next recording"
  and you can follow the log.

## When a user returns

If `EDIT-LOG.md` has earlier versions, offer to reuse the same look and settings for the new recording, and ask only what
differs (new file, new topic).
