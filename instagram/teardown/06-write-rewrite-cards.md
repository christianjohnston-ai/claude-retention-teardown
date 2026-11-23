# Step 06: Write a hook-rewrite card for each new Reel

**Why this step exists:** lessons say what to change; a rewrite card shows it on a Reel the user already
made, using their own words. The cards are where they actually learn to write a better opening.

## Read

- Your evidence sheets (step 02): first and second sentence, strongest fact and when it appears, open loops,
  frames.
- The full transcript, `accounts/<alias>/library/<shortcode>/words.json` → `text`.
- Existing cards in `accounts/<alias>/narrative.json` → `rewrites` (or the TikTok page's cards, for format only: never
  copy their content), to match their format and level.
- The TikTok page, if the same video was posted there.

## The rules

<why_their_words>
A rewrite only helps if the creator can say it naturally, and a line written by an AI puts words in their mouth (it also
tends to sound engineered, and natural phrasing held better in the author's own testing). So a card is built from
lines they actually said in that Reel, moved and trimmed. Anything new must be clearly new. Never add a factual claim
they didn't make: no invented numbers, results or features.
</why_their_words>

Each card is `accounts/<alias>/narrative.json` → `rewrites["<shortcode>"] = {was, now, meta[]}`:

- `was`: their actual first line, exactly as said, struck through: `<s>"…"</s>`. If the hook should stay,
  write `Keep: "…"`.
- `now`: a new first line, or first two lines. Tension first: a conflict, a threat, a mistake, or a result
  the viewer wants. Their strongest fact (a number, a name, a surprise) goes in sentence one or two, because
  the best line usually arrives after most viewers have left (check this against the curve: it is the pattern the
  evidence sheet's "strongest fact" line measures). Build it from their words.
- `meta`: 2 to 4 lines, each starting with a bold label:
  - Always: `<b>Frame 0:</b>` a finished visual of the result or the stakes, taken from ONE moment that already
    exists in that Reel (name that second, and check it in the frames or Gemini notes). Use full-contrast
    text, not a logo or title card. If you want elements from two different seconds together, say plainly
    that it's a new composite to build. Never describe it as if it already exists.
  - Then `<b>Super hook:</b>` (or `<b>Text:</b>`): one line of theirs that gives the reason to stay. Quote it
    exactly and mark it `(your line from 0:xx)`, adding `trimmed` if you cut words and marking the cut
    with "…".
  - `<b>Loop held:</b>` the piece of information withheld until later, named.
  - Optional: `<b>Cut:</b>` or `<b>Length:</b>`, plus a link to a full plan if the user keeps one (links are relative
    to `accounts/<alias>/`, where the page lives).

Before you finish, check every quoted line against the transcript yourself. Step 08 runs a checker that
fails the build on a misquote.

## Write in the notes (`## Step 06`)

For each card: which transcript lines (with seconds) you built `now` and the super hook from.

## Done when

- [ ] Every new Reel with a curve has a card (a Reel with no curve gets one only if its sheet supports it).
- [ ] Every quoted line is their exact words, cuts are marked with "…", and there are no invented facts.
- [ ] Frame 0 names a visual that exists at one second of the Reel, or is clearly labeled a new composite.

**Next:** open `teardown/07-update-log-and-verdict.md`.
