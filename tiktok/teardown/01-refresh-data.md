# Step 01: Refresh the data

**Why this step exists:** every judgment later in the run rests on today's curves. If the data is wrong or
missing, stop here rather than analyze stale numbers.

## Do

1. Create today's notes file `accounts/<name>/runs/<YYYY-MM-DD>-notes.md` (inside the skill folder), starting with
   `# Teardown notes <date>`. If it already exists (a second run today), never overwrite it: append a
   `## Run <HH:MM>` heading and write under it.
2. Run (for an account other than the default, add `--account <name>` here and in every later script call; see
   "Accounts" in SKILL.md):
   ```bash
   python3 ~/.claude/skills/tiktok-retention-teardown/scraping/daily.py
   ```
   Run it in the background (Claude Code: `run_in_background: true`) and wait for the completion notice: a first run
   with many videos takes several minutes per new video (download, Whisper, Gemini), longer than a foreground command
   is allowed to run. It finds the cmux tab on tiktok.com signed in as this account (or opens TikTok Studio in the
   account's own cmux profile), checks the sign-in, snapshots every public post, and fully processes new ones.
3. Handle the outcome:

   | You see | Do |
   |---|---|
   | Exit 4 and `WRONG_ACCOUNT` | A different TikTok account is signed in on that tab. Nothing was written. Tell the user which handle is signed in and which one this run needs; never switch it yourself. |
   | Exit 3 and `NOT_SIGNED_IN surface:N` | Tell the user: "TikTok Studio isn't signed in. Sign in inside cmux surface:N as @<handle>, then tell me." Wait for them, then re-run. Never type credentials. |
   | `would not answer after 3 reloads` | The tab is stuck. Run `cmux browser <surface> reload`, wait 10 s, re-run once. Still stuck: tell the user and stop. |
   | `NO_GEMINI` line | No Gemini key is set, so the watch notes were skipped. Note it; the per-second tables have no screen changes. Everything else is complete. |
   | `PENDING` lines | The post is too young for a curve. Note it; a later run processes it. |
   | `ERRORS` lines | Read them. `No module named mlx_whisper` or `requests`: the venv from SETUP.md is missing or broken; report it. Gemini down: re-run with `--skip-gemini` (a later run backfills). Re-run once. Never invent data to fill a gap. |
   | `SKIPPED` lines | Private or under-review posts. Note them. |

4. Print the numbers the lessons cite:
   ```bash
   python3 ~/.claude/skills/tiktok-retention-teardown/scraping/build_report.py --stats
   ```

## Write in the notes (`## Step 01`)

- The one-line JSON summary the script printed (new / refreshed / pending / skipped / errors).
- The `--stats` table, pasted as-is.
- One line per NEW video: id, posted time, age in hours, views.
- Anything you had to fix or retry, and whether the Gemini pass ran.

## Done when

- [ ] `runs/<today>.json` exists and lists no unresolved errors (or the errors are written down as unresolved).
- [ ] The `--stats` table is in the notes.
- [ ] If there were new videos, `runs/<today>-new.md` exists.

**Next:** open `teardown/02-read-the-evidence.md`.
