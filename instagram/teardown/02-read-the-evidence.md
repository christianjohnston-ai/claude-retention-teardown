# Step 02: Read the evidence

**Why this step exists:** this is where you look before you judge. Build one evidence sheet per new Reel, plus a short
list of existing Reels that moved. Steps 04 to 07 decide from these sheets, so every sheet keeps what was MEASURED apart
from what MIGHT explain it.

## Read

- `accounts/<alias>/runs/<today>-new.md`: per-second tables of each new Reel (kept, points lost next second, the median
  of settled Reels, likes in that second, words spoken, screen changes), plus view sources and follower split.
- `accounts/<alias>/runs/<today>.json`: the `refreshed` list (views and 0:03 hold, before and after).
- The real frames: open `library/<shortcode>/title_strip.jpg` as an image (top half of the frame at 0.05 / 0.5 / 1.0 /
  2.2 s, divided by red bars). `f0.jpg` / `f2.jpg` for the face. They are only 220 px wide.
- `library/<shortcode>/words.json` (`text`) for the whole transcript; `captures.jsonl` (last line) for every metric.
- `accounts/<alias>/account_notes.md`, if it exists.
- **Reels collected earlier but never analyzed count as NEW here.** Any Reel whose `meta.json` has `analyzed` set but which
  has no entry in `narrative.json` → `names` (an earlier run was cut off, or a single `--reel` collect was done outside a
  teardown) shows up in step 01 as REFRESHED, not NEW. Give it a full sheet, a name and a card like any new Reel. Print
  its table with today's median (read-only):
  `python3 -c "import os,sys; sys.path.insert(0, os.path.expanduser('~/.claude/skills/instagram-retention-teardown/scraping')); import account, collect; a=account.load('<alias>'); c=collect.latest_curves(a); print(collect.per_second_md(a,'<shortcode>',*c['<shortcode>'],collect.account_median(a)))"`

## Context you need to read it correctly

<data_truths verified="when this tool was built, against the phone app">
- The curve is Instagram's own per-second Reel retention, the same numbers the phone app shows. The app ROUNDS DOWN:
  for example, 62.49% in the data shows as 62% on the phone. Quote the data with no decimals rounded up past the app.
- Skip rate is NOT 100 minus the curve at 0:03. The app itself can show, for example, 62% at 0:03 next to a 55% skip
  rate. They are counted differently; never "correct" one with the other.
- Average watch time includes replays, so it can exceed the area under the curve. Do not derive one from the other.
- A Reel under 48 hours old is provisional. Label every number from it "provisional".
- `view_sources` says where views came from (Reels tab, Explore, Feed, Profile…). A Reel fed mostly by followers
  (Feed, Profile, Stories) and one fed by strangers (Reels tab, Explore) have different audiences. Compare curves only
  between Reels with similar sources, or say plainly that the sources differ.
- Likes per second are measured. They show where viewers reacted, not why.
- Whisper timing is accurate; brand names are often misspelled (seen when this was built: ChatBt=ChatGPT,
  Anthropik=Anthropic, Cloud=Claude, NAN=n8n, Kroc=Grok, Prop=Prompt).
- Screen changes are Gemini watch notes, present only when a Gemini key is set: APPROXIMATE (1 to 2 s off, sometimes
  wrong about frame 0). Trust the frames.
</data_truths>

<account_truths>
Write nothing here from memory or from TikTok. What is true about THIS account (its niche, its usual CTA, its format, its
baseline 0:03 hold, where its views come from) is learned from its own settled Reels and kept in
`accounts/<alias>/account_notes.md`. TikTok numbers never transfer.

- If `account_notes.md` exists, read it, and check its baseline against today's `--stats` table. Update a line only when
  the settled data now says something different, and change its date.
- If it does not exist and the account has 3 or more settled Reels (48+ h old), write it now from the data, in this shape
  (each line from a source you can name):
  ```
  # Account notes: @<handle>  (written <date>, from <n> settled Reels)
  - Niche and audience: <from the transcripts>
  - Usual CTA: <exact words, from the endings>
  - Format: <layout, captions, face on screen or not, from the frames>
  - Where views come from: <top sources and the non-follower share, from the captures>
  - Settled baseline: 0:03 hold <p3_range>, 0:10 hold <p10_range>, skip rate <skip_range>, from the --stats tokens
  - Playbook: <path to the user's written short-form playbook, if they keep one; otherwise "none">
  ```
- If it does not exist and there are fewer than 3 settled Reels, write nothing yet. The user may also fill in the niche,
  CTA and playbook lines by hand at any time.
</account_truths>

<noise>
At 0:03 a curve is near 50%. How big a gap has to be before it is real (95%):
- **One Reel vs the median of settled Reels:** about ±16 pts at 40 views, ±10 at 100, ±6 at 300, ±3.5 at 800, ±2.5 at 1,500.
- **One Reel vs another:** about ±8 pts at 300 views each, ±5 at 800, ±3.6 at 1,500.
A gap smaller than that is noise. Write "within noise", never a finding.
</noise>

<how_to_read_a_drop>
Viewers leave fastest at the very start of every Reel. Judge a second by comparing it with the median column at the
same second, not by raw size. Hunt for stretches well below the median, and stretches that hold flat while the median
falls. Then read the words, the screen notes and the likes in exactly those seconds.
</how_to_read_a_drop>

## Do: one evidence sheet per new Reel

```
### <shortcode> · posted <time> · <age> h · <views> views · <length> s · settled|provisional
Sources: <top two view sources with %> · non-follower views <n%> · follows <n> · skip rate <n%>

MEASURED
- Noise band at this view count: ±<n> pts vs median
- 0:01 / 0:03 / 0:10 / 0:30 kept: <a>/<b>/<c>/<d>   median: <..>   gap at 0:03: <+/- pts> (real | within noise)
- Second-2 loss (0:01→0:02): <pts>   (median: <pts>)
- Frame 0 (from title_strip.jpg): <what is on screen at 0.05 s; finished or still animating? logo? face?>
- Frame at 2.2 s (f2.jpg): <face still on screen?>
- First sentence (exact words): "<...>"
- When the claim lands: the second the viewer first hears WHAT the Reel claims or promises, from word timestamps: 0:0x.x
- Second sentence (exact words): "<...>"
- Strongest fact (number, name, result) and the second it first appears: "<...>" at 0:xx (kept xx% then)
- Open loops: each promise or question and the second it opens; when (if ever) it is paid off
- Payoff: the second the main promise is delivered, and the % still watching
- Biggest below-median stretch: 0:aa to 0:bb, kept x→y vs median x→y, words: "<...>"
- Best-holding stretch: 0:aa to 0:bb, words: "<...>"
- Like peaks: the seconds with the most likes, and what was said or shown there
- Length and ending: <seconds>; what happens after the payoff; the CTA (exact words)
- Same topic as an earlier Reel (this account), or the same video posted on TikTok? <id or no>

POSSIBLE EXPLANATIONS (not tested)
- <one line per hypothesis: "the drop at 0:aa to 0:bb lines up with <words/visual>; it may be because …">
  Each names the measured second it refers to. None of them is a finding until a later Reel tests it.
```

No curve (`NO_RETENTION`): write the sheet with what exists (views, sources, skip rate, average watch, likes per
second, frames, transcript) and a first line saying the curve is missing and why. Make no claim about where viewers left.

Then the **movers** among refreshed Reels: only those whose views grew more than 20% or whose 0:03 hold moved by more
than its noise band, with before and after numbers.

## Done when

- [ ] Every new Reel has a full sheet with exact quotes and seconds, MEASURED kept apart from POSSIBLE EXPLANATIONS.
- [ ] Every number from a Reel under 48 h is labeled provisional.
- [ ] You opened each title strip yourself rather than trusting Gemini about frame 0.
- [ ] Movers are listed, or the notes say "none beyond noise".
- [ ] `account_notes.md` is read and still true, or written now (3+ settled Reels), or the notes say why not yet.

**Next:** open `teardown/03-name-new-videos.md`.
