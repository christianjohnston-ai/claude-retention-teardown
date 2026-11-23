# Step 04: Test every lesson against the new evidence

**Why this step exists:** this is the step that makes the page more true over time. Each lesson is a claim
about what keeps this account's viewers. Each new video is a chance to confirm it, to find a clearer example,
or to catch it being wrong. The worst outcome is a lesson that keeps saying the same thing after the data has
turned against it.

## Read

- `accounts/<name>/narrative.json` → `lessons` (each has `id`, `tag`, `status`, `title`, `evidence_html`, `do_html`,
  `cite`).
- Your evidence sheets from step 02 in the notes.

## Do

Make a grid in the notes: one row per lesson × new video. For each cell, decide one of:

- **supports**: name the second and the number that shows it.
- **contradicts**: name the second and the number, and say which part of the lesson it cuts against.
- **no bearing**: the video doesn't test this lesson.

Then update `accounts/<name>/narrative.json`:

1. **Supports:** add the video to the lesson's evidence only if it's a clearer example than one already
   there. A lesson shows **at most 3 examples**, the strongest ones. Replacing a weaker example is fine.
2. **Contradicts:** say so in the lesson's evidence, plainly, with the numbers. Don't bury it, and don't
   explain it away. If the lesson's advice (`do_html`) now overreaches, narrow it.
3. **Status** (`holding` | `new` | `weakening` | `retired`):
   - **Only settled videos (48+ h old) can change a status.** Provisional videos, however many, are written into
     the evidence as counter-examples labeled provisional. They wait for the next runs before they count.
   - `holding`: no clear contradiction from settled videos.
   - `weakening`: 2+ settled videos clearly contradict it.
   - `retired`: most of the evidence now contradicts it. It moves to the bottom of the page and stays
     visible.
   - `new`: a lesson added today.
4. **New lesson:** add one only when a pattern shows in **3+ videos**, the difference is bigger than the noise
   band, and a person could act on it while writing a script. Use the same shape as the others and set
   `since` to today. Fill `cite` as the doctrine block below says.
5. Set `"updated": "<today>"` on every lesson you changed.

On a new account with no lessons yet, write in the notes the patterns you see so far and how many videos show each
(they become lessons at 3+).

Aggregate numbers in lesson text are `{{tokens}}` (`n_videos`, `n_settled`, `n_provisional`, `views_range`,
`p1_loss_range`, `p2_loss_range`, `p3_range`, `p10_range`, `p30_range`, `decay_after_3s`, `median_p3`,
`median_p10`, `updated`). They recompute themselves from settled videos. Use them instead of typing aggregate
numbers. `../PAGE_FORMAT.md` defines each one.

## Judgment for this step

<forbidden_overreads>
- One video is not a trend. A lesson needs 3+ videos, and a status change needs 2+ contradicting SETTLED videos.
- A gap inside the noise band (step 02) is not a difference.
- Views are not a verdict on the hook. Distribution varies, and views are not retention.
- Don't compare finish rates across very different lengths without saying so.
- "Both videos that kept the face on screen held better" is a hypothesis to A/B test. Never call it a rule.
- Numbers from a video under 48 h old are provisional. Say so in the text.
</forbidden_overreads>

<divergence_lines>
- You might credit the editing. Check the curves first: if the visuals already change every few seconds, and the
  seconds Gemini marks as "dead zones" show no extra loss against the median, the lever is the script (first frame,
  sentences one and two, open loops, payoff timing, length), not more graphics. Don't recommend more graphics unless a
  curve shows it.
- You might forecast how a fix will perform. Don't: in the author's own testing, the plain average of the account's
  other curves predicted a new video's curve better than both a Claude predictor and Gemini.
  Recommend, and let the next posted video grade it.
- You might rank seconds by raw loss. Compare against the median at the same second instead (step 02).
</divergence_lines>

<hypotheses_to_test>
Common short-form hypotheses. They are NOT findings about this account. Confirm or contradict them with each new
video before any becomes a lesson here:
- "Here's a mistake, and here's why" loops hold well. "I'll show you how" loops don't.
- Stories and proof/demo beats hold best.
- Step-by-step instructions hold only while a question is still open.
- Everything after the payoff leaks.
- Showing the result first beats promising it.
</hypotheses_to_test>

<doctrine>
A lesson's `cite` says what backs it. If the user keeps a written playbook for short-form video (its path is on the
`Playbook:` line of `accounts/<name>/account_notes.md`), cite its section numbers. Otherwise cite the second and the
number on this page that carry the lesson (for example "0:03 hold, 5 settled videos"). Open the playbook only to find a
cite for a new lesson.
</doctrine>

Voice for anything you write: plain, short, direct sentences. No dash asides, no hype. Quote the creator's
words exactly, as `<q>"…"</q>`, fixing only Whisper's brand typos. Mark a cut inside a quote with "…". Every
claim points at a second, a number, or a cited section.

## Write in the notes (`## Step 04`)

The full grid (lesson × video → verdict + second + number), then a list of the changes you made to
`narrative.json`.

## Done when

- [ ] Every lesson has a verdict for every new video in the grid.
- [ ] Every contradiction is written into that lesson's evidence.
- [ ] Count the videos each lesson's evidence names. At most 3 examples per lesson: a same-topic pair counts as
  one example, and a `{{token}}` range over all videos counts as none. Six named videos is a summary, not a
  lesson. Every changed lesson has `updated` set to today.
- [ ] No claim rests on a gap inside the noise band, and provisional numbers are labeled.
- [ ] No status changed because of provisional videos alone.
- [ ] Every claim about what's on screen was checked in the title strip, not taken from Gemini.

**Next:** open `teardown/05-reverify-numbers.md`.
