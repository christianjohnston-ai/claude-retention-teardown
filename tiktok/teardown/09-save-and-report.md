# Step 09: Save the day and tell the user

**Why this step exists:** a dated record of what the curves and lessons said each day lets the user see how the
lessons changed. The report is the only part they may read in the terminal, so it must be short.

## Do

1. Save the day, only if the user keeps a private history. Their data never goes into the claude-retention-teardown clone:
   `accounts/` is gitignored there, so it cannot reach the public repository by accident. Never change that, and
   never `git add` anything in the clone for a run.
   - If `accounts/<name>/` is its own git repository (the user ran `git init` there once; SETUP.md, last step),
     commit only that folder:
     ```bash
     cd ~/.claude/skills/tiktok-retention-teardown/accounts/<name>
     # Only the paths a run owns, never `git add -A`: media/ holds hard-linked copies of the library files.
     git add account.json narrative.json library runs retention-teardown.html
     [ -f account_notes.md ] && git add account_notes.md
     git status --short    # anything staged outside those paths? unstage it
     git commit -m "Teardown <YYYY-MM-DD>: <n> new, <one-line headline>"
     git push              # only if the user set a remote; say so in the report if it fails
     cd -
     ```
     That repository's `.gitignore` (SETUP.md writes it) keeps `media/` and the large `*.mp4` files out.
   - Otherwise skip this. Everything is already saved on disk.
2. Tell the user, in **five lines at most**:
   - what's new (videos analyzed, by name; say "provisional" if under 48 h)
   - the biggest movement in an existing video
   - any lesson that changed status or got a counter-example, and why
   - anything pending, skipped or broken (including a skipped Gemini pass or a failed push)
   - where the page is: the cmux surface, and the file
     `~/.claude/skills/tiktok-retention-teardown/accounts/<name>/retention-teardown.html`

   Don't repeat the page.

## Done when

- [ ] The day is committed to the user's private history repository, or there is none and nothing was committed.
- [ ] The user has the five-line report.

This is the last step.
