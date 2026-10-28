# Intake: how to start, what to ask, what to offer

The user may have never edited a video. Your job is to make every decision easy: do the legwork first, then ask a short
batch of multiple-choice questions, each with a recommended default, then come back with a plan. Never open with "What do
you want to do?" and never ask something you could find out yourself.

## 1. Do this before asking anything

1. Run `bash check.sh`; if it says NOT READY run `bash setup.sh`, then check again. Say nothing unless the user must act.
2. Find the recording. If they give a link to a web page, canvas or project instead of a video and want it shown ("how I made
   it", walkthrough), follow `behind-the-scenes.md` (record the page; ask first whether it is theirs to show). Accept a path, a dropped file, "the newest video in Downloads", a folder, an audio-only file, or a
   link (`python3 tools/fetch_source.py "<link or path>" <source-id>`). Never modify the original.
3. Prepare it: `python3 tools/prepare_source.py <file> <source-id>` (audio, transcript, contact sheets). Tell the user how
   long it will take ("about 5 minutes for a 90 minute recording") if it is more than a minute.
4. Read the transcript and look at two or three contact sheets. Work out: what it is (podcast, webinar, screen demo, talk,
   vlog, interview, gameplay, event), who speaks, whether there is a screen share, the language, the audio quality.
5. Look in `public/brand/` and `source/brand/`. If a real `brand.json` (`source` is not `default`) exists, the look is
   already decided: reuse it and say so.
6. Check `EDIT-LOG.md`. If earlier versions exist, offer "same style as last time?" and only ask what is different.

## 2. The question batch (ask all at once, at most four, skip what you can infer)

Use the harness's multiple-choice question tool when it has one; otherwise a numbered list. Each question: plain words,
two to four options, one marked **(recommended)**, and "something else" always allowed. Lead with what you found.

**Q1. What is this for?** (purpose; see `purposes.md`)
1. Pull many short clips from it (clip-farm) **(recommended for recordings over 20 minutes)**
2. One short highlight video or teaser
3. A trimmed, cleaned-up version of the whole thing (remove ums and dead air)
4. A recap with titles, steps and captions (tutorial, demo, webinar)
5. Quote or soundbite cards for a podcast or interview
6. A behind-the-scenes reel from a link (a project canvas, dashboard or page; no recording needed): see `behind-the-scenes.md`
7. Something else (describe it)

**Q2. Where will people watch it?** (sets the shape; never assume)
1. Phone feeds: TikTok, Reels, Shorts (9:16 tall)
2. Instagram or LinkedIn feed (4:5)
3. Square (1:1)
4. YouTube or a website (16:9 wide)
5. More than one (say which; each is its own export)

**Q3. How much?** Depends on Q1. Clip-farm: how many clips and how long each (recommend 8 to 12 clips of 30 to 60 s, or
fewer if the recording is short). Highlight or recap: 30 s, 60 s **(recommended)**, 90 s. Say "short and fast wins".

**Q4. What should it look like?** (see `brand-and-style.md`)
1. I have brand guidelines (PDF, link, colours, fonts, logo): send them
2. I have a video or images whose look I like: send them
3. Clean neutral look, no branding **(recommended if they have neither)**
4. Just captions, nothing else on the picture

Optional, only when it matters and cannot be inferred: speaker names and roles for name tags; anything that must be in or
left out (a person, a number, a customer, an off-the-record part); a call to action or handle for the end card; a music
track they want (never choose one for them; see `audio.md`).

If they answer "you decide", decide, state what you chose in one line, and go.

## 3. Come back with a plan, not a question

After they answer, read the transcript properly and present, in plain English, in under 15 lines:

- **What I found:** one sentence ("Your podcast has about 14 moments that work on their own").
- **The plan:** the shortlist (clip-farm: ranked list with timestamps, length, a one-line description each; highlight:
  a beat outline of hook, points, closing line, expected length), the format, the look, the captions style.
- **My recommendation** in one line and **one or two alternatives** only if the recording truly supports them.
- **A clear go:** "Good to start?" or pick numbers.

For hooks, offer directions instead of defaulting: the speaker's own strongest line over the picture; the finished result
shown whole; a text hook line on screen; a quick flip through the best moments. Do not default to flashing and
zooming into footage the viewer cannot place.

## 4. Proof first, then the batch

For more than one clip, make one **proof clip** first, show a still and the file, and ask: "Is this the look? (yes / change
something)". Fix the look once, then run the whole set with no more questions. For a single film, deliver a quick first
draft before the polish pass if the wait will be long.

## 5. After delivering: offer next steps unprompted

Show where the files are (full path, offer to open the folder), then offer two or three that fit what you made:
- a shorter or longer cut; a different hook; a version without captions or without the speaker;
- the same set in another format (4:5, 1:1, 16:9);
- more clips from the same recording (the next ten-best list);
- a posting pack: a title and a caption text for each clip (text only; you never post);
- a teaser that stitches the best three clips; a quote card; a thumbnail alternative;
- saving the look so the next recording matches ("same as this one").

## 6. When the request is vague

If the user only says "edit my video" or "make something from this", do steps 1 to 4 of section 1 anyway, then show this
menu in plain words, with your recommendation first:

> I can: **pull the best short clips** out of a long recording; **make one highlight or teaser**; **clean up and trim** the
> whole thing; **make a recap with titles and captions**; **turn quotes into cards**; or **reformat** a finished video for
> another platform. From what I heard, I'd start with: <recommendation and why>. Want that?

## 7. Style of every message

- Plain words. "I removed the pauses and ums", not "split hesitations in the EDL". "Video file", not "master".
- Give time and cost expectations before long or paid steps. Quote a price before anything that costs money, and ask.
- Show, don't describe: a still, the file, a path. Take feedback in their words ("punchier", "that part is boring") and
  translate it yourself.
- On failure: one sentence on what happened, what you are doing about it, and ask only if truly blocked.
