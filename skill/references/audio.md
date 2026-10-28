# Sound

Two stems, mixed by Remotion and finished by `tools/finish.py`:
- **the voice**, from the recording, built by `tools/build_cut.py`;
- **an optional music bed**, supplied or approved by the user and ducked by `tools/music_bed.py`.

## Voice chain (automatic in build_cut.py)

1. The kept spans, back to back, as 32-bit float. Nothing clips before the gain stages.
2. **Clip gain per span:** 70% of the way to a -33 dBFS speech level, at most +/-5 dB. Long recordings drift: sections can
   sit 11 dB apart. This evens them without flattening the delivery.
3. Highpass 70 Hz, one fixed gain to -20 LUFS, then **one moderate RMS compressor** (2.5:1 at -18 dB, 5/150 ms, makeup
   1). That is about 5 to 6 dB on loud syllables. Heavier settings pull breaths and room tone up with the gain.
4. **One fixed gain to -16 LUFS,** then a limiter run at 192 kHz (true peak -1.5 dBTP, latency-compensated). It sits idle
   most of the time (p95 gain reduction around 2.7 dB).
5. `tools/declick.py`: repairs isolated lip smacks and tongue clicks (sub-millisecond high-frequency spikes) by
   low-passing about 2 ms around each.

The stem is written as 16-bit stereo. Mono to stereo in ffmpeg is -3 dB per channel, so the per-channel peak reads about
-4.5 dBFS while loudness is unchanged.

### The traps that caused audible glitches (don't reintroduce them)

- **`acompressor`'s `makeup` is a linear factor, not dB.** `makeup=6` is +15.6 dB. It drove peaks past full scale, and
  they clipped when written to a 16-bit temp file.
- **`loudnorm ... linear=true` silently falls back to dynamic mode** when the gain would break the true-peak target (look
  for `normalization_type: dynamic` in the pass-2 JSON). Dynamic loudnorm rides quiet moments up by up to 35 dB: pumping,
  breaths and room tone swelling between words, and a +50 dB burst at a phrase start.
- **Single-pass loudnorm** is always dynamic. It pumped a music-only cold open up to speech level.

Rule: measure `input_i`, apply `volume=<target - I>dB`, then limit. The kit's tools all do this.

## Music: only if the user supplied or approved it

- No music by default. Ask once: "Do you have a track you want under this, or should it be voice only?" Offer the
  brand's `music.default` (`public/brand/brand.json`) if one is set.
- Use the user's own file or a track they approved. Royalty-free sourcing and licensing are the user's responsibility:
  say so in one line, and do not use a commercial song you cannot clear.
- Never generate or buy music without approval and a quoted price in USD.
- **One track across a set of clips** unless the user says otherwise, so the set sounds like one series. Ask before
  switching to a different track for any clip.
- Judge a candidate bed by measuring: loudness range (LRA) under about 4 LU means steady with no builds. Check for
  vocals and a clean ending.

### Fitting the bed to the film

- `python3 tools/music_bed.py <music> public/voice/<slug>.wav <LEAD> <film seconds> <name>` writes
  `public/music/<name>-ducked.wav`:
  - a fixed gain to -24 LUFS;
  - 7 dB of duck under speech (attack 0.1 s, release 0.7 s, so it never pumps between words);
  - 2.5 dB fuller during a silent cold open;
  - a fade in over 1.8 s and out over the last 1.2 s.

  Point the film's `<Audio>` (or the clip brief's `music.src`) at it.
- **Land the ending.** Most beds end with a sparse tail that starts on a bar line. Aim for the groove to drop as the
  sign-off finishes, and a hit to land on the outro card.
- **Moving the ending:**
  - Insert or remove whole bars before the tail. Find the bar grid from the kick onsets. Use 4-bar blocks so phrases
    stay intact.
  - Crossfade with ffmpeg `acrossfade` (qsin, 2 bars) at a bar line inside steady groove.
  - Check the new envelope before rendering.
- If the bed is shorter than the film, extend it the same way: a 12-bar loop with a 2-bar crossfade, bar-aligned. For
  short clips, a plain loop with a crossfade under the voice is fine.

## Finishing

```
npx remotion render src/index.tsx <Id> _work/<slug>-raw.mp4 --concurrency=8
python3 tools/finish.py _work/<slug>-raw.mp4 "deliverables/<Title> vN.mp4"      # --target -14.3 --ceiling -2
```

- Output: -14.3 LUFS, true peak under -1.5 dBTP, AudioToolbox AAC 256k (ffmpeg's native aac adds about 2 dB of true-peak
  overshoot). For a platform with its own target, `export_clips.py --platform <id>` picks the loudness from
  `tools/presets.json`; every clip in a set uses the same one.
- `finish.py` reports the limiter's work. With healthy stems the raw mix is about -16.3 LUFS and the limiter does 1.5 dB
  or less. If it does more than about 3 dB, the stems are too hot: fix them instead of pushing.
- Expect roughly: a music-only open about -18 to -22 LUFS, speech sections -13 to -17, the outro card -20 to -30.
