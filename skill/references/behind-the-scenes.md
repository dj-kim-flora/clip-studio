# Behind-the-scenes reel: record a page or canvas from its link

Use when the user gives a **link** to something on the web (a project canvas, a dashboard, a design file, a docs page, a
product page, a site) and wants a "how it was made", walkthrough or quick reel of it. There is no recording to start from:
the tool records the page itself, in the background (headless Chrome), so the user's screen, mouse and windows are not
touched. Works on any site; best on canvas apps (nodes you pan and zoom across) and long pages.

```
link ──► record_page.mjs (headless Chrome, scripted camera tour) ──► source/<name>/capture.mp4 + capture.json (labelled beats)
      ──► make_reel.py (speed up, cut, step labels as captions) ──► export_clips.py ──► deliverables/
```

## 1. Before recording (ask first, all in one batch)

- **Is it theirs to show?** Client names, unreleased work, other people's names or faces, prompts, prices or keys visible on
  the page: ask the owner once. Hide what must not show with `--hide "css,selectors"` (and `--clean`), or leave it out of the tour.
- **Format** (9:16, 4:5, 1:1, 16:9; "vertical" is ambiguous, ask), **length** (recommend 30 s; up to 60), **what story**
  (recommend: overview first, 4 to 6 steps in the order the work happened, end on the result). Music only if they supply it.
- **The look** comes from `public/brand/brand.json` as for every other purpose (`brand-and-style.md`).

## 2. One-time sign-in (only if the page needs it)

Never type, store or script a password. Run `node tools/record_page.mjs --login "<link>"`; a Chrome window opens, the user
signs in themselves and closes it. The sign-in lives in `~/.clip-studio/chrome-profile` (outside the project, never
committed). If a recording stops with "asks for a sign-in" (exit code 3), repeat this. The profile cannot be used while that
window is still open.

## 3. Look, then plan the tour

`node tools/record_page.mjs --snapshot "<link>" <name> --clean` prints the page title, whether it is a canvas or a page, the
visible nodes or headings with their positions, and writes `source/<name>/preview.png`. Read the screenshot and the list, then
write `_work/<name>-tour.json`. Make it a story, not a sweep:

```json
{"steps": [
  {"label": "Start from reference photos", "do": "hold", "seconds": 2},
  {"do": "hover", "text": "Reference photos", "seconds": 1.5},
  {"label": "Build the character sheet", "do": "pan", "dx": -450, "dy": 0, "seconds": 3},
  {"label": "Zoom out for the whole flow", "do": "zoom", "by": -2, "seconds": 2.5},
  {"label": "End on the result", "do": "pan", "dx": -900, "dy": 0, "seconds": 3},
  {"do": "hold", "seconds": 1.5}
]}
```

| `do` | Fields | What it does |
|---|---|---|
| `hold` | `seconds` | stand still (let the viewer read) |
| `zoom` | `by` (+ in, - out), `at` [fx, fy] 0..1, `seconds` | ctrl + wheel zoom around a point |
| `pan` | `dx`, `dy` (px), `seconds` | drag the canvas from an empty spot; the content follows the pointer |
| `scroll` | `dy`, `dx`, `seconds` | plain wheel, for ordinary pages |
| `hover` | `text` or `at` [x, y], `seconds` | glide the pointer to a visible label |

A step with a `label` starts a new **beat**; the label becomes the on-screen caption and `"speed": 2` on it forces that beat's
speed. Labels: two to six plain words naming what happens ("Pick the style"), never the tool's jargon. 4 to 7 beats, 3 to 5 s
each when recorded. `--tour auto` makes a generic tour (overview, zoom in, a serpentine pan; for a page, scroll with headings as
labels): fine for a first look, but write a real tour for anything shipped.

## 4. Record

```sh
node tools/record_page.mjs "<link>" <name> --tour _work/<name>-tour.json --clean --cursor
```

- Records in real time (a 25 s tour takes about 30 s). `--size 1600x900 --scale 2` is the default (3200x1800 picture).
- **Phone formats: record in the reel's own shape**, `--size 900x1600` for 9:16 or `--size 1080x1350` for 4:5. The reel then
  fills the frame with no blur bars. A wide recording in a tall reel is shown whole over a blurred copy of itself, which is
  small and hard to read.
- `--cursor` draws a pointer so hovers read; `--hide "sel,sel"` removes toasts, presence cursors and app chrome;
  `--wait 8` gives a slow page longer to load; `--headed` shows the window (it must stay uncovered).
- Look at four or five frames (`ffmpeg -ss 5 -i source/<name>/capture.mp4 -frames:v 1 _work/f.png`). Reject and fix: a login
  page, a spinner, an empty canvas, an error toast, anything private, a pan that did not move (see limits).

## 5. Make the reel

```sh
python3 tools/make_reel.py <name> --title "How I made it" --seconds 30 --formats reels,widescreen --export
```

It sets one shared speed-up so the beats fit `--seconds` (no beat shorter than `--min-beat`, default 1.6 s), cuts them together,
shows each label as a caption (plain style: step labels are not speech), adds the hook ("Behind the scenes", change with
`--hook`), and with `--export` renders and finishes every format into `deliverables/` with `.srt` and thumbnail. Several formats
get their own slug and title suffix so the versions do not replace each other. Options for the other purposes carry over
(`--music file`, `--outro`, `--caption-pos`, `--name`). No music means a silent file (the loudness step leaves silence alone).
Then run `qa-checklist.md` on real frames.

## Rules and limits

- **Read-only.** The tool only moves the pointer, turns the wheel, and drags from an empty spot of the page (never from a node,
  button, link, input or menu). It never clicks controls, types, submits or signs in. Still, tell the user it ran, and prefer
  a copy or a view-only account for anything precious.
- **Be honest about what it shows.** It records the project as it is now, driven by a tour. Call it a walkthrough; do not
  present it as the original build, its time or its cost.
- **Pan is a drag.** Apps that pan on drag (most canvases) work. If a pan does not move the canvas, use `scroll` steps (some
  apps pan on wheel) or `zoom` instead; ask the user how the app moves rather than clicking around.
- **Canvases using WebGL or video** may need `--headed` (window uncovered) to paint. Video nodes play only if the page plays them.
- Needs Google Chrome (or another Chromium browser: set `CHROME`), Node 22+, and ffmpeg (all from `bash setup.sh`).
- The sign-in profile holds credentials: never copy it, zip it, or put it in the project.
- Tested end to end on a local test canvas, headless (pan, zoom, hover, hidden overlays, 9:16 and 16:9 exports). Not yet tried
  against a real signed-in service: treat the first real recording as the proof and check its frames.
