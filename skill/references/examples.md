# What a finished set looks like

Three worked examples, described in words. **These are descriptions, not shipped files**: the kit ships no finished films.
Use them to calibrate what "done" means, then build the user's own from their recording and their theme.

## 1. A 45 s product-demo recap (editorial template)

- **Source:** a 40-minute screen-share demo of a SaaS analytics tool, presenter on a webcam bubble.
- **Purpose and format:** a recap for the product's social feed; 16:9 (the user chose it), 45 s.
- **Structure, beat by beat:**
  1. 0 to 7 s, hook: the finished dashboard full frame, silent, then the presenter's line "this report used to take me a
     day" over the one-click export; title card in the theme's display face with one italic word.
  2. 7 to 14 s, step 1 "Connect": step column beside a window playing the recording's own screen, a focus box on the
     data-source button as it is named.
  3. 14 to 26 s, steps 2 and 3 "Filter" and "Share": the step word swaps (never overlapping), notes build on the words,
     the cursor presses each click on the spoken word.
  4. 26 to 36 s, a before/after comparison row: the old spreadsheet beside the new dashboard, whole and uncropped.
  5. 36 to 42 s, the presenter's real sign-off line, with about 1 s of room tone after the last word.
  6. 42 to 45 s, outro card: logo, line and handle from the brand file.
- **What made it work:** result first; every on-screen label literally true to the demo; no line heard twice (the hook
  lines were removed from the body); ums and restarts cut; one-line captions centred under the window, the spoken word in
  the accent pill; loudness -14.3 LUFS; no music because the user had none to offer.

## 2. A 12-clip clip-farm from a 90-minute podcast

- **Source:** a two-host video podcast episode, 90 minutes, both hosts on camera.
- **Purpose and format:** standalone shorts for several platforms; 9:16, each 25 to 55 s, under the platform maximum.
- **Structure:**
  1. `farm.py` mined candidates; the agent read the ranked list and picked 12 that each hold one complete idea
     (a question, the answer, one example), spread across the episode, none overlapping.
  2. Each clip starts on a full sentence and opens on its strongest claim (a hook line over the first 2 s), then runs the
     exchange with ums, restarts and long pauses cut.
  3. Layout `split` for exchanges where both hosts are on camera, `fill` (tracked on the speaker) for monologues.
  4. Burned-in captions in the lower third, inside the safe zone, the spoken word in the accent pill; a lower third with
     the speaker's name on the first clip of each guest; a thin progress bar; a short outro card.
  5. `export_clips.py` built them all with the platform's loudness, titles that differ from each other, and a thumbnail
     frame per clip.
- **What made it work:** each clip stands alone with no missing context; the first 2 s earn the swipe; one loudness and
  one look across the whole set so it reads as a series; the user approved the list of 12 (one line each) before anything
  rendered; nothing was posted by the agent.

## 3. A 60 s lecture highlight

- **Source:** a 70-minute university lecture with slides, one lecturer, a fixed camera at the back of the room.
- **Purpose and format:** a shareable highlight for the course page; 16:9, 60 s.
- **Structure:**
  1. 0 to 6 s, hook: the lecturer's most surprising sentence ("most of what you remember is reconstructed, not stored")
     over the slide that shows it, full frame.
  2. 6 to 40 s, the reasoning in three beats, each a whole sentence or two from the lecture, with the relevant slide in a
     window and a focus box on the diagram being described (the whole diagram in frame, never a crop of it).
  3. 40 to 55 s, one concrete example from the Q&A, kept because it was funny, captions in the lecturer's own words
     (spelling of technical terms from the glossary).
  4. 55 to 60 s, the takeaway line and a plain title card with the course name.
- **What made it work:** it kept the lecturer's real words and never added a claim; slides were shown whole, sized for a
  phone; room noise was held low with the fixed-gain voice chain rather than aggressive denoising; the final transcript
  was read end to end before delivery.
