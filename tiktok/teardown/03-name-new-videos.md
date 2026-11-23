# Step 03: Name the new videos

**Why this step exists:** the page uses names everywhere (table, chart, explorer, lessons, rewrite cards). A
good name lets the user recognise a video at a glance.

## Do

For each new video, write a 2 to 5 word name built from its hook line or topic, in the style of the existing
names in `accounts/<name>/narrative.json` → `names`. Format examples (illustrations of the style, not real videos):
"Three pricing mistakes", "Settings warning", "Morning routine re-post".

- Fix Whisper's brand typos in names (seen when this was built: ChatBt→ChatGPT, Cloud→Claude, NAN→n8n, Kroc→Grok,
  Anthropik→Anthropic).
- If the video repeats an earlier topic, say so in the name ("... re-post").
- Never put a verdict in a name ("bad hook", "flop").

Add each to `accounts/<name>/narrative.json` → `names` as `"<video_id>": "<name>"`.

## Write in the notes (`## Step 03`)

`<id> → <name>` for each new video.

## Done when

- [ ] Every new video has a name in `narrative.json`.

**Next:** open `teardown/04-test-the-lessons.md`.
