---
description: Instagram Reel retention teardown for your own Instagram accounts. Runs the instagram-retention-teardown skill. It pulls each Reel's per-second retention curve (the phone app's numbers) from each account's own signed-in cmux browser profile, analyzes new Reels against the transcript and screen, updates lessons and hook-rewrite cards, and rebuilds one page per account. Read-only on Instagram.
---

# /retention-teardown-instagram

Run the **instagram-retention-teardown** skill. Its home is `~/.claude/skills/instagram-retention-teardown` (a symlink
into the user's clone of the claude-retention-teardown repository, folder `instagram`).

Arguments: `$ARGUMENTS`

| You typed | Run |
|---|---|
| nothing, or `all` | every eligible account |
| `<alias>` or `@handle` | that account |
| `<alias> <reel-url>` | only that Reel of that account (a token-less account also starts tracking it) |
| `<reel-url>` alone | find which token account owns it (its shortcode is in that account's official Reel list), then run that account with `--reel`; if no account has a token, ask the user which account it belongs to |
| `check` | `python3 ~/.claude/skills/instagram-retention-teardown/scraping/account.py check all`, report, stop |
| `login <alias>` | `python3 ~/.claude/skills/instagram-retention-teardown/scraping/account.py login <alias>`, tell the user the surface, stop |

1. Read `~/.claude/skills/instagram-retention-teardown/SKILL.md`.
2. Follow it exactly: `teardown/01-refresh-data.md` for the whole run, then steps 02 to 08 one account at a time, then
   `teardown/09-save-and-report.md` once.

Don't work from memory of earlier runs: the step files carry the rules, and each account's notes file carries what
earlier steps found. The TikTok teardown is a separate command (`/retention-teardown`) and is not touched by this one.
