# Brand and style: the look comes from the user

The kit has no built-in brand. Every colour, font, logo and end card comes from `public/brand/brand.json`. With nothing
supplied it uses a clean neutral default (dark background, off-white text, calm blue accent, Geist type, dotted
backdrop). Always ask for the user's own look first (`intake.md`, Q4), then fill `brand.json`.

## The file

`public/brand/brand.json` (neutral default in `brand.default.json`). Fields: `name`, `source` (`default`, `guidelines`
or `reference-media`), `colors` (`background`, `ink`, `muted`, `accent`, `accentInk`, `accentFill`, `panel`,
`panelBorder`), `fonts.display` and `fonts.body` (family, files in `public/brand/`, fallback), `logo` (`mark`,
`wordmark`, `animated`), `style` (`backdrop`: dots, grid, gradient or solid; `radius`; `captionStyle`: pill, karaoke,
plain or box; `headlineCase`: sentence or upper; `motion`: calm or punchy), `outro` (`line`, `handle`, `cta`),
`glossary` (names and terms spelled correctly), `music.default`, `notes`.

## Path A: brand guidelines (PDF, link, hex codes, font names, logo files)

1. Ask for what they have; any of these is enough: primary and secondary colours, fonts, a logo file, a one-line tone.
2. Read the PDF or page. Pull out: colours, typefaces, logo rules (clear space, colours on dark/light, minimum size),
   tone of voice, anything forbidden ("never use red", "never stretch the logo").
3. Map to the file:
   - Brand background if dark; otherwise a near-black or the brand's darkest colour. Videos read best on dark or very
     light backgrounds; if the brand is light, set `background` light and `ink` dark.
   - `accent`: the brand's main bright colour; `accentInk`: a lighter tint of it for text on dark; `accentFill`: a deep
     tint for pills and panels.
   - `fonts.display` for headlines (the brand's headline face), `fonts.body` for labels and captions.
   - Logo: use the supplied transparent PNG, SVG or a short transparent video. Never redraw, recolour or stretch it.
   - `glossary`: product names, people, jargon, so captions spell them right.
   - `notes`: the do and don't rules, legal lines.
4. Quick fill from values: `python3 tools/brand_from_media.py --from-hex "#0B0B10,#F4F1EA,#FF5A36" --font "Inter" --logo logo.png`.
5. Check contrast (below), then confirm with the user (below).

## Path B: reference media (a video or images whose look they like)

1. Put the files in `source/brand/`. Run `python3 tools/brand_from_media.py source/brand/<file-or-folder>`. It samples
   frames, proposes a palette, writes a draft `brand.json` and a swatch image at `_work/brand/palette.png`.
2. Look at the frames yourself. Describe, in plain words, what you see that the palette cannot capture: how fast the
   cuts are, caption style (one word at a time, a highlighted word, a boxed line), text position, type feel (rounded,
   condensed, serif), backdrop (flat, grain, gradient), motion feel (snappy or slow).
3. Translate to `style`: snappy → `motion: punchy`; slow and airy → `calm`; highlighted word → `pill` or `karaoke`;
   one boxed line → `box`; plain white → `plain`; flat colour → `solid`; gradient → `gradient`.
4. Fonts cannot be identified reliably from a picture. Name the closest free match (Inter, DM Sans, Space Grotesk,
   Playfair Display, Bebas Neue are common free faces), say it is an approximation, and ask if they have the real font file.
5. Reference media from another creator or company is inspiration, not permission: take palette and pacing, never their
   logo, name or distinctive trademark look.

## Path C: nothing supplied

Use the neutral default. Say so in one line ("I'll use a clean neutral look; send guidelines or a video you like any
time and I'll restyle it"). Offer a choice of accent colour from three swatches if they want a touch of personality.

## Fonts and licences

- Geist ships with the kit (open licence). Other fonts: the user supplies the file (`.otf`, `.ttf`, `.woff2`) and puts it in
  `public/brand/`. List it under `fonts.*.files`. Rendering text into a video normally needs only a licence for
  commercial or desktop use: ask the user to confirm they hold one.
- Never commit or share font files, logos or guidelines outside the user's team. They stay in `public/brand/` (ignored
  by git) and `source/brand/`.
- A missing font file never crashes a render: the kit warns and uses the fallback. Mention it to the user.

## Contrast and legibility checks (do these every time)

- Body text on background: contrast at least 4.5:1. Accent used for text: at least 3:1 (use `accentInk` if the accent is too dark).
- The active caption word must be distinguishable from inactive words at a glance (accent pill or colour change).
- Test on one real frame: a bright part of the footage under the caption. If it is hard to read, add the scrim (a soft
  dark gradient behind captions) rather than shrinking the type.
- Captions never smaller than about 4% of the frame height on a phone-sized video.

## Confirm in plain words, with a picture

Before the batch: render one still or proof clip and say, for example: "Dark background, off-white text, an orange accent
for the highlighted word, Inter for type, your logo on the end card. Right look?" Wait for yes. After that, do not ask again.

## Saving and reusing a look

`brand.json` plus the files in `public/brand/` are the saved look. For another project, keep the same files. Log in
`EDIT-LOG.md`: which `brand.json` source, any approximations (fonts), who approved.

## Things to never do

- Invent a logo, mascot or slogan. Never put a brand name on screen that the user did not provide.
- Use a neon or high-chroma colour as the accent unless the brand actually is that colour: it reads as generic "creator"
  styling. Pick the supplied brand colour or a calm default.
- Apply someone else's brand to the user's footage without the user saying they have the right to.
