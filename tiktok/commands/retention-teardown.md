---
description: TikTok retention teardown for your own TikTok account. Runs the tiktok-retention-teardown skill. It refreshes every video's per-second retention curve from TikTok Studio through cmux, analyzes new posts, updates the lessons and hook-rewrite cards, and rebuilds the account's page. Read-only on TikTok.
---

# /retention-teardown

Run the **tiktok-retention-teardown** skill. Its home is `~/.claude/skills/tiktok-retention-teardown` (a symlink into
the user's clone of the claude-retention-teardown repository, folder `tiktok`).

Arguments: `$ARGUMENTS`

1. Read `~/.claude/skills/tiktok-retention-teardown/SKILL.md`. If the user named an account
   (`/retention-teardown <name>`), run every step for that account as SKILL.md's "Accounts" section says; with no
   name, run the default account (`account.py list` shows which one that is).
2. Follow it exactly: open `teardown/01-refresh-data.md`, do that step, then open the next step file, one at a
   time, through `teardown/09-save-and-report.md`.

Don't work from memory of earlier runs. The step files carry the rules, and the notes file carries what earlier steps
found.
