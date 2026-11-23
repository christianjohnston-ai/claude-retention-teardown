# Step 04: Test every lesson against the new evidence

**Why this step exists:** this is the step that makes the page more true over time. Each lesson is a claim about what
keeps THIS account's viewers. Each new Reel can confirm it, give a clearer example, or catch it being wrong. The worst
outcome is a lesson that keeps saying the same thing after the data has turned against it.

## Read

- `accounts/<alias>/narrative.json` → `lessons` (each has `id`, `tag`, `status`, `title`, `evidence_html`,
  `hypothesis_html` (optional), `do_html`, `cite`).
- Your evidence sheets from step 02 in the notes.

## Do

Make a grid in the notes: one row per lesson × new Reel. For each cell, decide one of:

- **supports**: name the second and the number that shows it.
- **contradicts**: name the second and the number, and say which part of the lesson it cuts against.
- **no bearing**: the Reel doesn't test this lesson (including a Reel with no curve, for any lesson about seconds).

Then update `accounts/<alias>/narrative.json`:

1. **Supports:** add the Reel to the lesson's evidence only if it is a clearer example than one already there. At most
   3 examples per lesson, the strongest ones.
2. **Contradicts:** say so in the lesson's evidence, plainly, with the numbers. If the advice (`do_html`) now
   overreaches, narrow it.
3. **Status** (`holding` | `new` | `weakening` | `retired`): only settled Reels (48+ h) can change a status.
   `holding` = no clear contradiction from settled Reels; `weakening` = 2+ settled Reels clearly contradict it;
   `retired` = most of the evidence now contradicts it (it moves to the bottom and stays visible); `new` = added today.
4. **New lesson:** only when a pattern shows in **3+ SETTLED (48 h+) Reels of this account on different topics** (a
   same-topic pair counts once), the difference is bigger than the noise band, and a person could act on it while
   writing a script. Fill `cite` as the doctrine block below says. Set `since` to today.
5. Set `"updated": "<today>"` on every lesson you changed.

**Measured vs explained, in the file itself.** `evidence_html` holds only measured facts: seconds, kept shares, likes,
sources, exact quotes. Anything about WHY goes in `hypothesis_html`, which the page shows under "Possible explanation
(not tested)". A drop that lines up with a sentence or an edit does not prove the sentence or the edit caused it.
`do_html` may act on a hypothesis only if it says it is a test ("try X on the next Reel and see if 0:03 moves").

Aggregate numbers in lesson text are `{{tokens}}` (`n_videos`, `n_settled`, `n_provisional`, `views_range`,
`p1_loss_range`, `p2_loss_range`, `p3_range`, `p10_range`, `p30_range`, `skip_range`, `decay_after_3s`, `median_p3`,
`median_p10`, `updated`). They recompute from settled Reels every build. Use them instead of typing aggregates.
`../PAGE_FORMAT.md` defines each one.

## Judgment for this step

<forbidden_overreads>
- One Reel is not a trend. A lesson needs 3+ Reels; a status change needs 2+ contradicting SETTLED Reels.
- A gap inside the noise band (step 02) is not a difference.
- Views are not a verdict on the hook. Distribution varies, and views are not retention.
- Reels with very different view sources (mostly followers vs mostly Reels tab / Explore) have different audiences.
  Don't build a lesson on a comparison between them without saying so.
- Skip rate and the 0:03 point are counted differently by Instagram; don't treat a gap between them as a finding.
- Don't compare TikTok and Instagram curves as if they were one audience. If the same video ran on both, say "on
  TikTok it held X at 0:03, on Instagram Y", and draw no lesson from one pair.
- "Both Reels that kept the face on screen held better" is a hypothesis to test. Never call it a rule.
- Numbers from a Reel under 48 h old are provisional. Say so.
</forbidden_overreads>

<divergence_lines>
- You might forecast how a fix will perform. Don't: in the author's own testing, the plain average of the account's
  other curves predicted a new video's curve better than both a Claude predictor and Gemini.
  Recommend, and let the next posted Reel grade it.
- You might rank seconds by raw loss. Compare against the median at the same second instead (step 02).
- You might reuse the TikTok page's lessons because the videos look alike. Don't: they are conclusions about a
  different audience on a different app. They can be listed below as things to test, nothing more.
</divergence_lines>

<hypotheses_to_test>
Common short-form hypotheses. NOT findings about this account. If the user also runs the TikTok skill, its lessons
belong in this list too, as things to test. Confirm or contradict them with this account's own Reels before any
becomes a lesson here:
- "Here's a mistake, and here's why" loops hold better than "I'll show you how" loops.
- Stories and proof/demo beats hold best.
- Step-by-step instructions hold only while a question is still open.
- Everything after the payoff leaks.
- Showing the result first beats promising it.
- A finished first frame (full-contrast text, no fade-in) holds better at 0:03.
</hypotheses_to_test>

<doctrine>
A lesson's `cite` says what backs it. If the user keeps a written playbook for short-form video (its path is on the
`Playbook:` line of `accounts/<alias>/account_notes.md`), cite its section numbers. Otherwise cite the second and the
number on this page that carry the lesson (for example "0:03 hold, 4 settled Reels"). Open the playbook only to find a
cite for a new lesson.
</doctrine>

Voice for anything you write: plain, short, direct sentences. No dash asides, no hype. Quote the creator's words
exactly, as `<q>"…"</q>`, fixing only Whisper's brand typos. Mark a cut inside a quote with "…". Every claim points at a
second, a number, or a cited section.

## Write in the notes (`## Step 04`)

The full grid (lesson × Reel → verdict + second + number), then a list of the changes you made to `narrative.json`.
On a new account with no lessons yet, write the patterns you see so far and how many Reels show each (they become
lessons at 3+).

## Done when

- [ ] Every lesson has a verdict for every new Reel in the grid.
- [ ] Every contradiction is written into that lesson's evidence.
- [ ] At most 3 examples per lesson; every changed lesson has `updated` set to today.
- [ ] No claim rests on a gap inside the noise band, and provisional numbers are labeled.
- [ ] No status changed because of provisional Reels alone.
- [ ] Every explanation is in `hypothesis_html`, never in `evidence_html`.
- [ ] Every claim about what's on screen was checked in the title strip, not taken from Gemini.

**Next:** open `teardown/05-reverify-numbers.md`.
