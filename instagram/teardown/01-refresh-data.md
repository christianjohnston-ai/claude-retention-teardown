# Step 01: Refresh the data

**Why this step exists:** every judgment later in the run rests on today's curves. If the data is wrong, missing, or
might belong to the wrong account, stop here rather than analyze it.

## Do

1. Decide the accounts for this run (SKILL.md, "Which accounts"). For each one, create
   `accounts/<alias>/runs/<YYYY-MM-DD>-notes.md` (inside the skill folder), starting with
   `# Teardown notes <date> · @<handle>`. If that file already exists (a second run today), never overwrite it: append a
   `## Run <HH:MM>` heading and write under it.
2. Run ONE of:
   ```bash
   python3 ~/.claude/skills/instagram-retention-teardown/scraping/collect.py --account all              # every eligible account, in turn
   python3 ~/.claude/skills/instagram-retention-teardown/scraping/collect.py --account <alias>          # one account
   python3 ~/.claude/skills/instagram-retention-teardown/scraping/collect.py --account <alias> --reel <url>   # one Reel (repeatable)
   ```
   **Run it in the background** (Claude Code: `run_in_background: true`) and wait for the completion notice. It takes about
   75 s per new Reel (20 to 30 min for a first run) and a foreground command is killed after a few minutes. Every Reel is
   saved as it finishes (raw answer, capture, meta, run file, per-second table), so a killed run loses nothing already
   done; do not re-run it blindly, read `runs/<today>.json` first.
   It opens its own cmux tab in the account's profile, proves who is signed in, checks the Reel belongs to that account,
   then asks Instagram for one Reel's insights at a time, 10 to 20 s apart, at most 20 per run. New Reels also get video,
   frames, Whisper and Gemini (a few minutes each). Never run two collects for the same account at once (it refuses
   with exit 9).
3. Handle the outcome, per account:

   | You see | Do |
   |---|---|
   | exit 0 | Continue. |
   | `NO_GEMINI` line | No Gemini key is set, so the watch notes are skipped. Note it; the per-second tables have no screen changes. Everything else is complete. |
   | `NOTHING_TO_COLLECT` | A token-less account with no tracked Reels yet. Ask the user for the Reel URLs to track and run `collect.py --account <alias> --reel <url>` (repeat `--reel` per Reel). |
   | exit 3 `NOT_SIGNED_IN` | That profile has no Instagram session; a sign-in page labeled "Sign in here as @<handle>" was left open. Only ONE sign-in tab may be open at a time (with two open it is easy to sign an account into the wrong profile): if several accounts are signed out, close all but one with `cmux close-surface --surface <surface:N>` (always pass `--surface`; without it cmux closes the focused surface, which may be your own terminal) and do them one by one. Tell the user which surface and which account, end your turn, and when they say done run `account.py check <alias>`; if it prints OK, run `collect.py --account <alias>` once, in the background. A second exit 3 is final for this run. Never type credentials. |
   | exit 4 `WRONG_ACCOUNT` | A different Instagram account is signed in on that profile, or the official token belongs to another account. Nothing was written. Tell the user which account the output names; never edit `account.json` to make it pass. |
   | exit 5 `NOT_OWNED` | The Reel asked for is not in that account's own list. Nothing was requested. Check which account owns it. |
   | exit 6 `PAUSED` | Instagram sent a challenge, rate limit or action block (now or on an earlier run). Collection for that account stopped with no retry. Tell the user the reason line. A challenge needs them to open Instagram in that profile and answer it, then `account.py unpause <alias>`. A rate limit clears itself after 24 h. Do NOT re-run to "try again". |
   | exit 7 `FORMAT_CHANGED` | Instagram's answer is not the shape we know (the raw answer path is in the output). Stop; tell the user; the internal ids may need updating (see `scraping/README.md`). Never guess numbers. |
   | exit 2 | A usage, config or cmux failure (the message says which). Fix it once or report it. |
   | exit 9 | Another collect for this account is running. Wait for it. |
   | `PENDING` lines | A Reel too young for a curve. A later run processes it. |
   | `NO_RETENTION` lines | A Reel 48 h+ old whose answer had no retention curve. It is analyzed on its other metrics only (step 02). |
   | `NOT_AVAILABLE` lines | Instagram refused insights for that Reel (for example not owned). Note it. |
   | `ERRORS` lines | Read them. Gemini down: re-run that account with `--skip-gemini` (a later run backfills). An offline or "cannot find the requested files" error from Whisper: the model was never downloaded (SETUP.md, the Whisper model step). `No module named ...`: the venv from SETUP.md is missing. Never fill a gap with invented data. |

   With `--account all`, one account's failure does not stop the others; handle each account's outcome on its own. The
   process exit code is only 0/1: read the last line, `ALL {"<alias>": 0, "<alias2>": 3, ...}`, and each account's
   `STOPPED <code>` line. A Python traceback for one account is not a bug to patch in a hurry: report its last line and
   never loosen a gate.
4. For each account that collected something, print the numbers lessons cite:
   ```bash
   python3 ~/.claude/skills/instagram-retention-teardown/scraping/build_report.py --account <alias> --stats
   ```

## Write in each account's notes (`## Step 01`)

- The one-line JSON summary for that account (new / refreshed / pending / no_retention / errors / stopped).
- The `--stats` table, pasted as is.
- One line per NEW Reel: shortcode, posted time, age in hours, views, curve yes/no.
- Anything you had to fix or retry, any stop reason, and whether the Gemini pass ran.

## Done when

- [ ] Every account in this run has `runs/<today>.json`, or a stop reason written in its notes.
- [ ] The `--stats` table is in each collecting account's notes.
- [ ] If there were new Reels, `runs/<today>-new.md` exists for that account.

**Next:** open `teardown/02-read-the-evidence.md`. Do steps 02 to 08 for ONE account at a time.
