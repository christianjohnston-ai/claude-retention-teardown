# Step 07: Update log, verdict and notes

**Why this step exists:** the update log is the page's memory. It tells the user (and the next run) what
changed and why. The verdict at the top is the first thing they read, so it must still be true.

## Do

1. Append today's entry to `accounts/<alias>/narrative.json` → `changelog`: `{"date": "<today>", "note": "…"}`. Always
   add one, even on a quiet day ("No new posts. No curve moved beyond noise."). In this order, include:
   - new Reels, by name, with age and views, and whether they're provisional (and any without a curve, and why)
   - lesson changes: which lesson, what changed, and the evidence in one clause each
   - the biggest movement in an existing Reel, with before → after numbers (and "within noise" if it is)
   - pending, no-curve or not-available Reels, any stop (paused, wrong account, format change), and whether the
     Gemini pass was skipped
   - any script fix you made
   Keep it to 4 to 7 sentences, in the same plain voice.
2. Set `accounts/<alias>/narrative.json` → `updated` to today.
3. Re-read `verdict_html`. Does it still describe what the settled data says? If a lesson was weakened or
   retired, or the main pattern changed, rewrite it. Otherwise leave it alone. On a new account, keep the starter
   verdict until 3 Reels are settled.
4. Re-read `notes` (the "How to read this" paragraphs). Update only what's no longer true.

## Write in the notes (`## Step 07`)

The changelog entry as written, and "verdict unchanged" or the new verdict.

## Done when

- [ ] Today's changelog entry exists and `updated` = today.
- [ ] The verdict matches the current evidence.

**Next:** open `teardown/08-build-and-check.md`.
