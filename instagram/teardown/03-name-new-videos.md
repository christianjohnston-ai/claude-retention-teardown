# Step 03: Name the new Reels

**Why this step exists:** the page uses names everywhere (table, chart, explorer, lessons, rewrite cards). A
good name lets the user recognise a Reel at a glance.

## Do

For each new Reel, write a 2 to 5 word name built from its hook line or topic, in the style of the existing
names in `accounts/<alias>/narrative.json` → `names` (or of the TikTok page's names for the same creator, if this
account has none yet). Format examples (illustrations of the style, not real videos): "Three pricing mistakes",
"Settings warning", "Morning routine re-post".

- Fix Whisper's brand typos in names (seen when this was built: ChatBt→ChatGPT, Cloud→Claude, NAN→n8n, Kroc→Grok,
  Anthropik→Anthropic).
- If the Reel repeats an earlier topic, say so in the name ("... re-post").
- Never put a verdict in a name ("bad hook", "flop").

Add each to `accounts/<alias>/narrative.json` → `names` as `"<shortcode>": "<name>"`.

## Write in the notes (`## Step 03`)

`<shortcode> → <name>` for each new Reel.

## Done when

- [ ] Every new Reel has a name in `accounts/<alias>/narrative.json`.

**Next:** open `teardown/04-test-the-lessons.md`.
