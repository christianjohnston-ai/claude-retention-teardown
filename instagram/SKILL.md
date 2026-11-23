---
name: instagram-retention-teardown
description: Instagram Reel retention teardown for the user's own Instagram accounts, run by /retention-teardown-instagram. Pulls each Reel's per-second retention curve (the one the phone app shows), likes per second, view sources and follower split from Instagram's own Reel insights through each account's own signed-in cmux browser profile, optionally cross-checks against the official API, transcribes and watches each new Reel, tests the lessons, writes hook-rewrite cards and rebuilds one page per account. Read-only on Instagram. Use for "instagram retention", "reel retention", "teardown my reels", "why did this reel drop", "/retention-teardown-instagram".
---

# Instagram Retention Teardown

The Instagram sister of the TikTok teardown (skill `tiktok-retention-teardown`). It keeps one page per account,
`accounts/<alias>/retention-teardown.html`: every Reel's per-second retention curve lined up with what was said, what was
on screen and where likes landed, compared with the account's own median at the same second. Each run adds one day of
evidence. The page must get more true every run, never longer for its own sake.

The skill folder is `~/.claude/skills/instagram-retention-teardown` (a symlink into the user's clone of the public
claude-retention-teardown repository). Every path below is relative to that folder unless it starts with `~`.

## Accounts

`python3 ~/.claude/skills/instagram-retention-teardown/scraping/account.py show` prints every account's live config
(alias, handle, profile, pinned user id, whether an official token is present, pause). Setup creates the first account
with `account.py add <alias> <@handle>`. Each account has its own cmux browser profile, `ig-<alias>`, so the logins never
share cookies. One Instagram account per profile: never "Switch accounts" inside one.

Reel insights exist only for professional (Creator or Business) accounts. An account without an official token has no
Reel list: its Reels are tracked once named with `--reel <url>` (they are kept in `account.json` "reels"), and new Reels
are not found by themselves. With a token (`IG_TOKEN_<ALIAS>` in `.env`), new Reels are found automatically and every
capture is cross-checked against the official API.

## Which accounts this run covers

- `/retention-teardown-instagram` or `... all` → every eligible account.
- `... <alias|@handle>` → that account. `... <alias> <reel-url>` → only that Reel (and, for a token-less account, it is
  added to the tracked list).
- `... check` → `account.py check all` (identity only), then stop.
- `... login <alias>` → `account.py login <alias>`, tell the user which surface to sign in on, then stop.

## How to run it: one step file at a time

1. Open `teardown/01-refresh-data.md`. Read only that file and do exactly what it says (it collects for every account
   in the run at once).
2. Then do steps 02 to 08 for ONE account, finishing its step 08 before starting the next account's step 02. Each step
   appends a `## Step N` section to that account's `accounts/<alias>/runs/<YYYY-MM-DD>-notes.md`.
3. Step 09 once at the end, for all accounts in the run.
4. Check each step's **Done when** list before opening the file under **Next**. Don't read ahead, and don't skip.

| Step | File | What it decides |
|---|---|---|
| 01 | `teardown/01-refresh-data.md` | Collect; handle sign-in, wrong account, pauses, format changes |
| 02 | `teardown/02-read-the-evidence.md` | One evidence sheet per new Reel (measured kept apart from explanations), plus the movers |
| 03 | `teardown/03-name-new-videos.md` | Short names for new Reels |
| 04 | `teardown/04-test-the-lessons.md` | Does each lesson hold, weaken, or need a new example? |
| 05 | `teardown/05-reverify-numbers.md` | Per-Reel numbers quoted in lessons that moved |
| 06 | `teardown/06-write-rewrite-cards.md` | A hook-rewrite card per new Reel, from the creator's own lines |
| 07 | `teardown/07-update-log-and-verdict.md` | Today's update-log entry; does the verdict still hold? |
| 08 | `teardown/08-build-and-check.md` | Build, check quotes, look at the page once |
| 09 | `teardown/09-save-and-report.md` | Save the day (optional private history); tell the user in five lines per account |

## Rules for every step

<authority_boundary>
- Instagram is READ-ONLY. Never post, edit, delete, comment, reply, change a setting, or click anything that changes an
  account. The collector only reads insights of the signed-in account's own Reels.
- Never type a password, a code or an answer to an Instagram prompt for the user. On NOT_SIGNED_IN or a challenge, tell
  them which surface to use, and wait.
- Never work around a stop: WRONG_ACCOUNT (exit 4) means sign in correctly, never edit `account.json`; PAUSED (exit 6)
  means wait or let the user clear the prompt, never re-run to try again.
- Never read, print or save session cookies or tokens. No `cmux browser state save`, no `cookies get --all` on these
  profiles (both dump the whole jar). The only cookie the tool reads is `ds_user_id` (a numeric id).
- Browser = cmux only, each account in its own `ig-<alias>` profile.
- Write only inside this skill folder. Never delete `accounts/<alias>/library/`: raw answers and captures are the
  permanent record, append-only.
- Never copy lessons, rewrite cards or verdicts between accounts or from TikTok. They are earned from each account's Reels.
- Deliver pages as local HTML opened in cmux. Never upload or publish them anywhere: they hold private analytics.
- Change written content only through `narrative.json`. Edit scripts only to fix a real bug, and say so in the report.
- Never print the Gemini key, an Instagram token, or the contents of `.env`.
</authority_boundary>

## What lives where

| Path | What it is |
|---|---|
| `scraping/collect.py` | The collector: lock, pause, own surface, identity gate, ownership gate, one request at a time, raw + capture saves, media for new Reels. Exit codes in its header |
| `scraping/account.py` | Aliases, profiles, `show` / `login` / `check` / `unpause` / `add`, `.env` reading |
| `scraping/insights.js`, `identity.js` | The two in-page scripts (insights request; signed-in username) |
| `scraping/ig_parse.py` | Parse, merge, units per field, stop signals |
| `scraping/official.py`, `net.py` | Optional official API (Reel list, cross-check); host allowlist + secret scrubbing for every Python request |
| `scraping/media.py` | Video, frames, title strip, Whisper, Gemini (forked from the TikTok skill) |
| `scraping/build_report.py`, `report_template.html`, `check_quotes.py` | The page (`--stats` prints the numbers lessons cite) and the quote check |
| `scraping/README.md` | How the collection works, its gotchas, and what to do when Instagram changes something |
| `narrative.json` | The EMPTY starter every new account's `narrative.json` is copied from. Never write an account's content here |
| `accounts/<alias>/` | `account.json`, `narrative.json`, `account_notes.md` (once written, step 02), `retention-teardown.html`, `library/<shortcode>/{meta.json, raw/<UTC>.json, captures.jsonl, words.json, gemini.json, f0.jpg, f2.jpg, title_strip.jpg, video.mp4}`, `runs/`, `state/` |
| `teardown/` | The analyst steps |
| `tests/test_ig_parse.py` | Parser tests that need no private data |
| `.env` | Optional `GEMINI_API_KEY`, `IG_TOKEN_<ALIAS>`, `IG_USER_ID_<ALIAS>` (gitignored; `.env.example` shows the names) |

The page's format (every section, the `narrative.json` schema, the `{{tokens}}`) is described in `../PAGE_FORMAT.md`.
