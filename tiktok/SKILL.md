---
name: tiktok-retention-teardown
description: Use when running or updating the TikTok retention teardown for one of the user's own TikTok accounts. It pulls per-second retention curves from TikTok Studio through the cmux browser, analyzes new posts (frames, word-timed transcript, optional Gemini watch), tests the written lessons against the new evidence, writes hook-rewrite cards from the creator's own lines, and rebuilds the account's retention-teardown.html page. Activates on retention teardown, TikTok retention, retention curve, update the teardown, /retention-teardown, what did my videos do, which second did viewers leave.
---

# TikTok Retention Teardown

This skill maintains one permanent page per TikTok account, `accounts/<name>/retention-teardown.html`. It shows every
public TikTok of that account: its per-second retention curve lined up with what was said and what was on screen, and
compared with the account's own median at the same second. The user reads the page to learn to write hooks, open loops
and scripts that keep viewers. Each run adds one day of evidence. The page must get more true every run. It must never
get longer for the sake of it.

The skill folder is `~/.claude/skills/tiktok-retention-teardown` (a symlink into the user's clone of the public
claude-retention-teardown repository). Every path below is relative to that folder unless it starts with `~`.

## Accounts

Every account lives in `accounts/<name>/`: `account.json`, `library/`, `runs/`, `narrative.json`, `account_notes.md`
(once written), `retention-teardown.html` and `media/`. Its login lives in its own cmux browser profile (`tt-<name>`), so
several accounts stay signed in at once. There is no account in the code: setup creates the first one with
`python3 ~/.claude/skills/tiktok-retention-teardown/scraping/account.py add <name> <@handle>`, and that first account is
the default. `account.py list` shows them all.

Rules for any run:
- With no account named, scripts use the default account. When the user names one (`/retention-teardown <name>`), add
  `--account <name>` to EVERY script call in the step files (`daily.py`, `build_report.py`, `check_quotes.py`).
- Read and write only `accounts/<name>/...` for the account of this run.
- `daily.py` refuses (exit 4, `WRONG_ACCOUNT`) when the signed-in handle isn't the account's. Never work around that by
  editing `account.json`; the user signs in as the right account instead.
- A new account's lessons and rewrite cards start empty. Never copy another account's: they are conclusions about that
  account's own videos. Step 04 adds a lesson only once 3+ videos show a pattern.

## How to run it: one step file at a time

1. Open `teardown/01-refresh-data.md`. Read only that file, and do exactly what it says.
2. Each step writes its findings to the day's working notes, `accounts/<name>/runs/<YYYY-MM-DD>-notes.md`. Create the
   file in step 01 and append a `## Step N` section per step.
3. Check the step's **Done when** list. Only then open the file named under **Next**.
4. Don't read ahead, and don't skip a step. Later steps rely on what earlier steps wrote in the notes, not on what you
   remember.

| Step | File | What it decides |
|---|---|---|
| 01 | `teardown/01-refresh-data.md` | Pull today's curves; handle sign-in and errors |
| 02 | `teardown/02-read-the-evidence.md` | One evidence sheet per new video, plus the movers |
| 03 | `teardown/03-name-new-videos.md` | Short names for new videos |
| 04 | `teardown/04-test-the-lessons.md` | Does each lesson hold, weaken, or need a new example? |
| 05 | `teardown/05-reverify-numbers.md` | Per-video numbers quoted in lessons that moved |
| 06 | `teardown/06-write-rewrite-cards.md` | A hook-rewrite card per new video, from the creator's own lines |
| 07 | `teardown/07-update-log-and-verdict.md` | Today's update-log entry; does the verdict still hold? |
| 08 | `teardown/08-build-and-check.md` | Build, check quotes, look at the page once |
| 09 | `teardown/09-save-and-report.md` | Save the day (optional private history); tell the user in five lines |

## Rules for every step

<authority_boundary>
- TikTok is READ-ONLY. Never post, edit, delete, comment, reply, change a setting, or click anything that changes the
  account. The scripts only read Studio's own analytics from the signed-in page.
- Never type a password or sign in for the user. If the data script reports NOT_SIGNED_IN, tell the user which cmux
  surface to sign in to, and wait.
- Never read, print or save cookies or session tokens. Never run `cmux browser state save` or `cookies get --all` on
  these profiles: both dump the whole cookie jar.
- Browser = cmux only. The sign-in lives in the account's cmux browser profile; never use another browser or browser
  automation tool for these pages.
- Write only inside this skill folder. Never delete `accounts/<name>/library/`: it's the permanent record.
- Deliver the page as the local HTML file opened in cmux. Never upload or publish it anywhere: it holds the user's
  private analytics.
- Change the written content only through `narrative.json`. Edit the scripts or `scraping/report_template.html` only to
  fix a real bug, and say so in the report.
- Never print the Gemini key or the contents of `.env`.
</authority_boundary>

## What lives where

| Path | What it is |
|---|---|
| `scraping/` | **Part 1, the data and the page.** `README.md` (how the scraping works), `daily.py` (sign-in check, pull, snapshot, process new videos), `build_report.py` (renders the page; `--stats` prints the numbers lessons cite), `report_template.html`, `check_quotes.py`, `account.py` |
| `teardown/` | **Part 2, the analyst process.** One file per step |
| `narrative.json` | The EMPTY starter every new account's `narrative.json` is copied from. Never write an account's content here |
| `accounts/<name>/narrative.json` | The page's written content: names, verdict, lessons, rewrite cards, checklist, update log, notes |
| `accounts/<name>/account_notes.md` | What is true about this account (niche, usual CTA, format, baseline), written from its settled videos (step 02) |
| `accounts/<name>/library/<video_id>/` | Per video: `meta.json`, `snapshots.jsonl` (one per day), `words.json`, `gemini.json`, `f0.jpg`, `f2.jpg`, `title_strip.jpg`, `video.mp4` |
| `accounts/<name>/runs/` | `<date>.json` (what the data script did), `<date>-new.md` (per-second tables of new videos), `<date>-notes.md` (your step notes) |
| `run.sh` | Data-only refresh plus rebuild, with no analysis |
| `.env` | Optional `GEMINI_API_KEY` (gitignored; `.env.example` shows the name) |

The page's format (every section, the `narrative.json` schema, the `{{tokens}}`) is described in `../PAGE_FORMAT.md`.
