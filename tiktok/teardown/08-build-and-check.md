# Step 08: Build the page and check it

**Why this step exists:** the page is the deliverable. A misquote, an unknown token or a broken layout
undoes the care taken in steps 02 to 07.

## Do

1. Check the quotes:
   ```bash
   python3 ~/.claude/skills/tiktok-retention-teardown/scraping/check_quotes.py
   ```
   Every `MISS` is a quote that isn't the creator's exact words. Fix it in `accounts/<name>/narrative.json` (use their
   real words, and mark cuts with "…"), then re-run until all quotes are found.
2. Build:
   ```bash
   python3 ~/.claude/skills/tiktok-retention-teardown/scraping/build_report.py
   ```
   If it refuses (unknown `{{token}}`), fix `narrative.json` and rebuild.
3. Show it in cmux:
   - Find a browser surface already showing `retention-teardown.html` (`cmux tree --all --json`), and run
     `cmux browser <surface> reload`.
   - Otherwise run `cmux browser open "file://$HOME/.claude/skills/tiktok-retention-teardown/accounts/<name>/retention-teardown.html" --focus true`.
4. Look once:
   - Run `cmux browser <surface> screenshot --out <a temporary file>` and view the image.
   - Run `cmux browser <surface> errors list`.
   - Check for an empty section, overflowing text, or a missing chart or table.
   - Fix anything broken once, rebuild, and stop. No second round of polish.

If you're running without cmux (e.g. in a test), do steps 1 and 2 only and say so in the notes.

## Write in the notes (`## Step 08`)

The quote-check result (`N/N quotes found`), the build line, the surface the page is on, and what the look
found.

## Done when

- [ ] `check_quotes.py` reports every quote found.
- [ ] The build wrote the page.
- [ ] The page is open or reloaded in cmux, and the screenshot showed nothing broken.

**Next:** open `teardown/09-save-and-report.md`.
