# Energy: the bar every film has to clear

**Default stance: fast and high-stimulation. Boring is the only real failure.** A film can be accurate, on-brand and
cleanly cut and still fail if nobody would watch it to the end. This file outranks the "calm / long holds / deliberate"
guidance elsewhere in the kit. That slower style is the **editorial mode**: use it only when the user asks for something
slow, premium or calm.

## The three tests

Ask these of the film, and of every beat in it:

1. **Is it funny?** (a reaction, a fail, an absurd result, a punchy line, a surprising juxtaposition)
2. **Is it cool or pretty?** (a striking result, a satisfying move, a great-looking frame)
3. **Would people care?** (a result they want, a trick they'd use, a "wait, what?" they'd send to a friend)

A beat must pass at least one. Pass none: cut it or replace it with the speaker's most surprising, funniest or most
useful moment. A beat that is merely correct, explanatory, or "needed for context" does not earn its seconds. Explain only
what the viewer needs to want the next beat.

## How that becomes decisions

- **Result first.** Open on the best result, not the setup, in a hook direction agreed with the user before you build it.
  Show it whole and readable: the feature at full view, the output full frame, a flip through the results. Flashing
  extreme close-ups is one option for a striking hi-res result, not a reflex: zooming into random footage reads as noise.
  Show the input beside its output so the viewer sees the cause and effect. Never open on a title card, a still held for
  seconds, a logo, or "so today we're going to...".
- **Length.** Default 30 to 60 s. Up to 90 s only when every beat passes a test. A 2:44 cut of a 77-minute recording is
  too long to be called short; if it runs past a minute, say what you'd cut to get under it. For clip-farming, follow the
  platform max (see `clip-farming.md`).
- **Always moving.** Something changes every 1 to 2 s (a cut, a punch-in, a new card, a word pop). No still held longer
  than about 1 s unless it is the payoff. Prefer moving footage over stills; a still gets a push.
- **No dead air.** Split every hesitation of 0.35 s or more (`python3 tools/split_pauses.py ... --min 0.35`), cut every
  um/uh and restart (check with `tools/find_ums.py`: the transcript hides them), cut the hook down to its payload words
  (no setup filler, no repeated clause), drop throat-clearing ("so", "you know", "I think"). Keep the jokes, the
  reactions ("oh nice, it really did it") and the line that makes the payoff land.
- **Tighter beats.** Step words `gap` about 0.2 s (still never overlapping). Key-line hold about 0.15 s instead of
  0.45 s. Hand-offs 0.3 to 0.5 s, not 0.6 to 0.9 s. Keep the no-overlap rule: fast is not messy.
- **Bigger, punchier type.** Short headlines (2 to 4 words). Captions as large as the layout allows, lit word by word.
  A beat pop (scale 1.0 to 1.06 to 1.0) on the word that matters. Size everything for a phone.
- **One track per set.** If there is music at all, it is a track the user supplied or approved, the same one for every
  clip of a set (see `audio.md`). Never pick or generate a song on your own.
- **End fast.** Land the last line and cut to the outro card. No lingering title, no "thanks for watching" tail unless it
  is funny.
- **Sound hits.** Tiny pops and whooshes on cuts and card arrivals, subtle under the voice.

## Funny, cool, caring: where to look in a transcript

- **Funny:** reactions ("oh my god", laughter), a result that is wrong in an amusing way, a mis-click, a deadpan aside,
  an escalation (small to absurdly big).
- **Cool or pretty:** the finished product, a camera move, a before/after, a result that looks unlike anything they have
  seen.
- **People care:** the thing they could do today in a minute, a number ("5 minutes", "$0"), a mistake they'd have made.

Cut anything that exists only to establish credentials, thank people, read the chat, or walk menus the viewer can see.

## Energy gate (run before delivery)

1. Watch the first 3 seconds with fresh eyes. Would someone scrolling stop? If not, rework the hook before anything else.
2. List every beat and the test it passes (funny, cool, caring). Delete or replace any beat that passes none.
3. Is there a stretch of about 3 s with no change on screen? Add a cut, punch-in or card, or trim it.
4. Is it under 60 s (or have you said why not)? Say what you cut and what you'd cut next.
5. Tell the user in one or two plain sentences ("the hook is the finished dish, then the plating, then the first bite;
   52 seconds"), and offer a still faster version.

Accuracy still wins over energy: never invent a claim, result or quote to make a beat pop. Choose the coolest *real* piece.
