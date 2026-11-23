# The page format

Each account gets one page, `accounts/<name>/retention-teardown.html`, inside its skill folder
(`~/.claude/skills/tiktok-retention-teardown/...` or `~/.claude/skills/instagram-retention-teardown/...`). It is one
static HTML file. `build_report.py` writes it from two kinds of input:

- **Measured data** from the account's `library/`, refreshed by the data script on every run. Nobody writes these by
  hand, and the page never fills a gap with an estimate.
- **Written content** from the account's `narrative.json`: the verdict, lessons, rewrite cards, checklist, update log
  and notes. Claude edits it in steps 03 to 07 of each run; you may edit it too.

This document describes the TikTok page section by section, in the order the template renders them, then the
`narrative.json` schema, the `{{tokens}}`, how a run updates the page, how to rebuild it, and how the Instagram page
differs. Values shown in examples are **format examples written for this document**, not data from any real account.

## Where the measured data comes from

| File (in `accounts/<name>/library/<video_id>/`) | What the page takes from it |
|---|---|
| `meta.json` | posting time (`create_time`, `posted`), length (`duration_s`), the video's link (`url`), a fallback name (`name`, the first words of the transcript), and `analyzed` (a video appears on the page only once it is set) |
| `snapshots.jsonl` | the LAST line only: `ret` (the kept share at each second, 0 to 1), `views`, `avg_watch_s`, `finish_rate`, `likes`, `saves`, `comments`, `shares`, `source` (`realtime` or `history_7d`), `pulled_at`. The number of lines is shown as "Snapshots" |
| `words.json` | word timestamps from Whisper, grouped into the words spoken in each second |
| `gemini.json` | `cut_log`, the screen changes with their second (only when a Gemini key was set) |
| `f0.jpg`, `f2.jpg`, `video.mp4` | the frames at 0.05 s and 2.2 s and the clip, hard-linked into `accounts/<name>/media/` (cmux's browser only reads files inside the page's own folder) |

**Settled vs provisional.** A video is settled when its last snapshot was taken 48 hours or more after it was posted.
Curves move a lot in the first two days, so the median and every aggregate token use only settled videos, unless fewer
than 3 are settled, in which case they use every video.

**The median curve.** For each second, the median of the kept share across the videos above, kept only for seconds that
at least half of those videos (and at least 2) reach.

## The sections, in order

1. **Header.** A small line `@<handle> · <n> TikToks analyzed · updated <date>` (plus `(posted since <date>)` when
   `account.json` has a `since`), the title, one line saying what the page is, and the **verdict**: `verdict_html` from
   `narrative.json`, the first thing you read. On a new account it says there are not enough settled videos yet.

2. **The curves.** One chart with every video's curve in grey (dashed while under 48 hours old), the median in black,
   and the selected video in orange. A toggle switches between the first 15 seconds (with the first two seconds shaded
   and labelled "the cliff") and the full length. Hovering shows, at that second, the selected video's kept share and
   the words spoken then, plus the median and the range across all videos. Under the chart, a table with one row per
   video, newest first: Posted, Video (name, a "provisional" tag with its age, a Watch link), Views, At 1 s, At 3 s,
   At 10 s, At 30 s, Avg watch (seconds out of the length), Finished, Saves. The best value in each column is green.
   Clicking a row selects that video everywhere on the page.

3. **Lessons from your own numbers.** One card per lesson from `narrative.json` → `lessons`, active lessons first and
   retired ones at the bottom: `LESSON <n> · <tag>`, a status pill (holding, new, weakening, retired), `since` and
   `updated` dates, the title, an optional strip of the first frames of the 10 newest videos (when the lesson has
   `"frames": true`), the
   evidence box, the advice line, and the cite. A new account shows "No lessons yet" and the rule that earns one.

4. **Every second, every word, every drop.** Pick a video (buttons, or a dropdown once there are more than 10). The side
   panel shows the clip (when `video.mp4` is on disk), a Watch link, the frames at 0 s and 2.2 s, and the numbers:
   posted, views, length, average watch, finished, likes and saves, comments and shares, the curve's source (with the
   age if provisional), and the number of snapshots. The log has one row per second: the time, a bar of the share
   still watching with a black tick at your median for that second, the words spoken (or "(silence)"), and the screen
   changes. A row is red when 5 or more points were lost in the next second (it says `-<n> next`), and green when the
   next 2 seconds lost no more than 0.4 points ("flat", from 0:04 on). Playing the clip highlights the second being heard.

5. **Your hooks, rewritten.** One card per entry in `narrative.json` → `rewrites`, newest video first: the video's name
   and Watch link, the original first line (`was`, struck through, or `Keep: "…"`), the new opening (`now`), and the
   labelled notes (`meta`: Frame 0, Super hook, Loop held, and optionally Cut or Length).

6. **The script checklist.** `narrative.json` → `checklist`, as a numbered list. It starts empty: these are your own
   questions to ask before you hit record. No step of a run writes them.

7. **What changed, run by run.** `narrative.json` → `changelog`, newest first: the date and a 4 to 7 sentence note.

8. **How to read this.** `narrative.json` → `notes`, one paragraph each (sample size, where the numbers come from, how
   to refresh).

The page remembers the selected video in your browser (`localStorage`, key `rt-sel`) and loads its fonts from Google
Fonts; without a connection it falls back to system fonts.

## narrative.json

One file per account (`accounts/<name>/narrative.json`). Each new account starts as a copy of the skill's empty
`narrative.json`. Every string field that ends in `_html` (and `title`, the `rewrites` fields, the checklist, the
changelog notes and the notes) is inserted as HTML, and may contain `{{tokens}}`.

| Field | Type | What it is | Written by |
|---|---|---|---|
| `updated` | string, `YYYY-MM-DD` | the date of the last run that changed the content; shown in the header and as `{{updated}}` | step 07 |
| `names` | object: video id → string | a 2 to 5 word name per video, used everywhere on the page | step 03 |
| `verdict_html` | HTML string | the verdict under the title | step 07 |
| `lessons` | array of lesson objects (below) | the lessons | steps 04 and 05 |
| `rewrites` | object: video id → rewrite object (below) | the hook-rewrite cards | step 06 |
| `checklist` | array of HTML strings | your pre-record questions | you |
| `changelog` | array of `{"date": "YYYY-MM-DD", "note": "..."}` | the update log | step 07, one entry per run |
| `notes` | array of HTML strings | the "How to read this" paragraphs | step 07 (only what became untrue) |

A **lesson** object:

| Field | Type | Format example |
|---|---|---|
| `id` | string, short and unique; the card's anchor is `#lesson-<id>` | `"open-question"` |
| `tag` | string shown after `LESSON <n> ·` | `"OPEN QUESTION"` |
| `status` | `"holding"`, `"new"`, `"weakening"` or `"retired"` | `"holding"` |
| `since` | `YYYY-MM-DD`, the day the lesson was added | `"2026-01-05"` |
| `updated` | `YYYY-MM-DD`, optional, the last day it changed | `"2026-01-12"` |
| `title` | the claim, one sentence | `"A question left open holds viewers through the middle"` |
| `frames` | optional `true`: show the strip of first frames | `true` |
| `evidence_html` | the measured facts, at most 3 examples, with seconds and numbers; quotes as `<q>"…"</q>` | `"<b>Example:</b> kept 52% at 0:03 vs a median of {{median_p3}}."` |
| `do_html` | the advice, something a person can act on while writing | `"<b>Do:</b> ask the question in the first sentence and answer it last."` |
| `cite` | what backs it: a section of your playbook, or the second and the number | `"0:03 hold, 4 settled videos"` |

A **rewrite** object (key = the video id):

| Field | Type | Format example |
|---|---|---|
| `was` | the original first line, exact, struck through; or `Keep: "…"` | `"<s>\"So today I want to talk about…\"</s>"` |
| `now` | the new first line or two, built from the creator's own words | `"\"Your best line is at 0:24. Nobody hears it.\""` |
| `meta` | array of 2 to 4 HTML lines, each starting with a bold label | `["<b>Frame 0:</b> the result at 0:18, full-contrast text.", "<b>Super hook:</b> \"…\" (your line from 0:24)", "<b>Loop held:</b> which setting it was"]` |
| `label` | optional; the card's title when the video is not on the page | `"Deleted video"` |

`check_quotes.py` checks every `<q>"…"</q>` in lessons, every quoted line in `was`, and every quoted line in a `meta`
entry marked `(your line …)` against the transcripts, ignoring case, spacing and punctuation. A quote with `…` is
checked piece by piece (pieces of 3 or more words). Any miss fails the check, and step 08 does not build until it passes.

## The {{tokens}}

Aggregate numbers in written text are tokens, recomputed on every build so they never go stale. An unknown token stops
the build with an error. Ranges read `a to b` (or one value when they are equal) and `n/a` when there is no data yet.

| Token | Value |
|---|---|
| `{{n_videos}}` | how many videos are on the page |
| `{{n_settled}}` | how many videos the aggregates use (the settled ones, or every video while fewer than 3 are settled) |
| `{{n_provisional}}` | `n_videos` minus `n_settled` |
| `{{views_range}}` | lowest to highest views, over every video on the page |
| `{{p1_loss_range}}` | share lost by 0:01, in % |
| `{{p2_loss_range}}` | points lost between 0:01 and 0:02 |
| `{{p3_range}}`, `{{p10_range}}`, `{{p30_range}}` | share still watching at 0:03, 0:10 and 0:30, in % |
| `{{decay_after_3s}}` | average points lost per second from 0:03 to the end (videos longer than 5 s) |
| `{{median_p3}}`, `{{median_p10}}` | the median curve at 0:03 and 0:10 |
| `{{updated}}` | `narrative.json` → `updated`, or today if it is empty |

`build_report.py --stats` prints every video's key seconds and the current value of every token; step 01 pastes it
into the day's notes so lessons cite real numbers.

## How a run updates the page

| Step | What changes |
|---|---|
| 01 | the data script adds a snapshot to every public video and fully processes new ones (`library/`), and writes `runs/<date>.json` and `runs/<date>-new.md` |
| 02 | nothing on the page; evidence sheets go into `runs/<date>-notes.md`, and `account_notes.md` is written or checked |
| 03 | `names` |
| 04 | `lessons` (evidence, advice, status, new lessons) |
| 05 | per-video numbers quoted inside `lessons` and `verdict_html` that moved 2 or more points; sweeping claims that became false |
| 06 | `rewrites` |
| 07 | `changelog`, `updated`, and `verdict_html` / `notes` if they are no longer true |
| 08 | `check_quotes.py`, then `build_report.py` writes the page, which is opened or reloaded in cmux |

## Rebuilding the page by hand

```bash
python3 ~/.claude/skills/tiktok-retention-teardown/scraping/check_quotes.py [--account <name>]
python3 ~/.claude/skills/tiktok-retention-teardown/scraping/build_report.py [--account <name>]
```
The build only reads `library/` and `narrative.json`, makes no network request, and prints
`wrote <path> · <n> videos`. Open the file in cmux:
`cmux browser open "file://$HOME/.claude/skills/tiktok-retention-teardown/accounts/<name>/retention-teardown.html"`.
For Instagram, use the `instagram-retention-teardown` paths; `--account <alias>` is required there.

## How the Instagram page differs

Same sections, template, schema and settled rule, with these differences:

- **Data source.** The last line of `library/<shortcode>/captures.jsonl` instead of a snapshot: `retention.points`
  (pairs of second and kept share), `views`, `avg_watch_s`, `skip_rate_pct`, `likes`, `saves`, `comments`, `shares`,
  `follows`, `profile_visits`, `non_followers_views`, `view_sources` and `like_timing`. `meta.json` holds `created_ts`,
  `posted`, `duration_s` and `url`.
- **Only measured seconds are drawn.** A Reel is drawn only when Instagram returned a point at every second from 0.
  Reels without a curve (too young, refused, or none returned) are listed under the table with the reason. Nothing is
  filled in or interpolated.
- **Header and chart.** The header says `Instagram · <n> Reels analyzed`; the chart's heading is "Every Reel, second by
  second", and there is no "cliff" band.
- **Table.** Finished is replaced by **Skip rate** (lowest is best) and **Follows**.
- **Explorer.** Each row shows the kept share with one decimal, and `♥ <n>` when likes landed in that second. The side
  panel adds follows and profile visits, the non-follower share of views, and the top view sources; "Curve" shows the
  number of measured points, and "Captures" replaces "Snapshots".
- **Lessons** may carry `hypothesis_html`, shown under "Possible explanation (not tested)", visibly apart from the
  measured evidence. Explanations go there, never in `evidence_html`.
- **One more token:** `{{skip_range}}`, the skip rate range in %. `{{n_settled}}` and `{{n_provisional}}` count Reels
  48 hours old or more, and younger, exactly (the aggregates themselves still use every Reel while fewer than 3 are
  settled).
- Instagram's app rounds down: for example, 62.49% in the data shows as 62% on the phone, so the page can read up to a point higher.
