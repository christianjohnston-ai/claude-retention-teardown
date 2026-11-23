# Step 09: Save the day and tell the user

**Why this step exists:** a dated record of what the curves and lessons said each day lets the user see how the lessons
changed. The report is the only part they may read in the terminal, so it must be short. Run this step ONCE per run,
after steps 02 to 08 are done for every account in it.

## Do

1. Save the day, only if the user keeps a private history. Their data never goes into the claude-retention-teardown clone:
   `accounts/` is gitignored there, so it cannot reach the public repository by accident. Never change that, and never
   `git add` anything in the clone for a run.
   - For each account in this run whose `accounts/<alias>/` is its own git repository (the user ran `git init` there
     once; SETUP.md, last step), commit only the paths a run owns:
     ```bash
     cd ~/.claude/skills/instagram-retention-teardown/accounts/<alias>
     # Never `git add -A`: media/ holds hard-linked copies, state/ holds locks, pauses and format-change dumps.
     git add account.json narrative.json library runs retention-teardown.html
     [ -f account_notes.md ] && git add account_notes.md
     git status --short            # anything staged outside those paths? unstage it
     # Confirm no session or token text is staged (raw answers keep everything Instagram sent except signed links):
     # A real gate: if secret-shaped text is staged, stop here and commit nothing.
     if git diff --cached | grep -E -i -q 'sessionid=|csrftoken=|access_token=|IGAA[A-Za-z0-9]|EAA[A-Za-z0-9]{20}'; then
       echo "STOP: secret-shaped text staged"; git reset -q; cd -; exit 1
     fi
     git commit -m "Instagram teardown <YYYY-MM-DD>: <n> new, <one-line headline>"
     git push                      # only if the user set a remote; say so in the report if it fails
     cd -
     ```
     If the check prints STOP, unstage everything, commit nothing, and tell the user which file matched.
     That repository's `.gitignore` (SETUP.md writes it) keeps `media/`, `state/` and the large `*.mp4` files out.
   - Otherwise skip this. Everything is already saved on disk.
2. Tell the user, in **five lines at most per account** (an account that only had a stop gets one line):
   - what's new (Reels analyzed, by name; "provisional" if under 48 h; "no curve" where Instagram gave none)
   - the biggest movement in an existing Reel
   - any lesson that changed status or got a counter-example, and why
   - anything pending, paused, wrong-account or broken (including a skipped Gemini pass or a failed push)
   - where the page is: the cmux surface, and the file
     `~/.claude/skills/instagram-retention-teardown/accounts/<alias>/retention-teardown.html`

   Don't repeat the page.

## Done when

- [ ] The day is committed to each account's private history repository with no secret-shaped text staged, or there is
  none and nothing was committed.
- [ ] The user has the short report.

This is the last step.
