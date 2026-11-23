# Step 05: Re-verify the hard-coded numbers

**Why this step exists:** curves keep moving after a Reel is posted. `{{tokens}}` update themselves, but
numbers quoted about one Reel inside a lesson do not. Format examples: "lost 12% in 8 seconds",
"-22 in second 2", "kept 27% at 0:10". Left alone, they drift until the page quietly says something false.

## Do

1. List every hard-coded per-Reel number in `accounts/<alias>/narrative.json` → `lessons` (evidence, hypothesis and
   advice), and in `verdict_html`. Skip `{{tokens}}`.
2. Recompute each one from the latest capture, `accounts/<alias>/library/<shortcode>/captures.jsonl` (last line with
   `"status": "ok"`). `ret = [v for t, v in capture['retention']['points']]` is the kept share per second (verified
   1-second sampling; if `per_second` is false, use the points' own timestamps and never index by position). Useful definitions:
   - "lost N% of the remaining viewers between a and b" = `round((1 - ret[b] / ret[a]) * 100)`
   - "second-2 loss" = `round((ret[1] - ret[2]) * 100)` points
   - "kept N% at 0:xx" = `round(ret[xx] * 100)`
   - "of the people still there at 0:03, N% made it to 0:30" = `round(ret[30] / ret[3] * 100)`
   - "the other Reels kept a to b%": recompute the range over the settled Reels it refers to
3. If a number moved by **2+ points**, update the text and set `updated` on that lesson. If a change flips
   a comparison (e.g. a "largest" example is no longer the largest), rewrite the sentence.
4. Re-check every **sweeping claim**: "all", "every", "none", "always", "only", "best", "largest", "fastest",
   "lowest". Check it against ALL Reels now on the page (settled and new), and for anything visual, against
   each Reel's `title_strip.jpg`. (A sweeping claim can turn false within days.) Narrow or rewrite any claim that's no longer true.

A short Python one-off is fine for the arithmetic. Don't add a script to the skill for it.

## Write in the notes (`## Step 05`)

A table: lesson · quoted number or sweeping claim · current value or verdict · changed? (yes/no).

## Done when

- [ ] Every hard-coded per-Reel number is checked against the latest capture.
- [ ] Anything that moved 2+ points is updated.
- [ ] Every sweeping claim is still true for every Reel on the page.

**Next:** open `teardown/06-write-rewrite-cards.md`.
