# Step 02: Read the evidence

**Why this step exists:** this is where you look before you judge. You'll build one evidence sheet per new
video, plus a short list of existing videos that moved. Steps 04 to 07 decide from these sheets, so the sheets
must hold facts with seconds and numbers, not opinions.

All paths here are inside the account folder, `accounts/<name>/`.

## Read

- `runs/<today>-new.md`: per-second tables of each new video (kept %, points lost next second, the
  median of settled videos, words spoken, screen changes).
- `runs/<today>.json`: the `refreshed` list (views and 0:03 hold, before and after).
- The real frames of each new video: open `library/<id>/title_strip.jpg` as an image. It shows the top half of the
  frame at 0.05 / 0.5 / 1.0 / 2.2 s, left to right, divided by red bars. Use `f0.jpg` / `f2.jpg` for the face at
  the bottom. They're only 220 px wide, too small to judge the title.
- `library/<id>/words.json` (`text` field) if you need the full transcript in one piece.
- `account_notes.md`, if it exists.

## Context you need to read it correctly

<account_truths>
What is true about THIS account (its niche, its usual CTA, its format, how fast the creator speaks, where its views come
from, its settled baseline) lives in `account_notes.md`. Never write it from memory, and never carry it over from
another account.

- If `account_notes.md` exists, read it, and check its baseline against today's `--stats` table. Update a line only
  when the settled data now says something different, and change its date.
- If it does not exist and the account has 3 or more settled videos (48+ h old), write it now from the data, in this
  shape (each line from a source you can name):
  ```
  # Account notes: @<handle>  (written <date>, from <n> settled videos)
  - Niche and audience: <from the transcripts>
  - Usual CTA: <exact words, from the endings>
  - Format: <layout, captions, face on screen or not, from the frames>
  - Speaking pace: <a to b words per second, from words.json>
  - Where views come from: <For You share, from the snapshots' traffic field>
  - Settled baseline: 0:03 hold <p3_range>, 0:10 hold <p10_range>, finish <a to b %>, from the --stats tokens
  - Playbook: <path to the user's written short-form playbook, if they keep one; otherwise "none">
  ```
- If it does not exist and there are fewer than 3 settled videos, write nothing yet. Use only today's `--stats` table.
  The user may also fill in the niche, CTA and playbook lines by hand at any time.
</account_truths>

<data_truths>
- Curves are TikTok Studio's own per-second retention. They're exact for the viewers TikTok has counted
  so far.
- **A video under 48 hours old is provisional.** Its curve still moves as views keep arriving (a young video can more
  than double its views in a day). Label every number from it "provisional".
- Words per second come from Whisper word timestamps. Timing is accurate; brand names are often misspelled
  (seen when this was built: ChatBt=ChatGPT, Anthropik=Anthropic, Cloud=Claude, NAN=n8n, Kroc=Grok, Prop=Prompt).
- Screen changes are Gemini watch notes, present only when a Gemini key is set. They're APPROXIMATE (1 to 2 s off, and
  sometimes wrong about frame 0). Trust the frame images over Gemini's description.
</data_truths>

<noise>
At 0:03 a curve is near 50%. How big a gap has to be before it's real (95%):
- **One video vs the median of settled videos:** about ±16 pts at 40 views, ±10 at 100, ±6 at 300, ±3.5 at 800,
  ±2.5 at 1,500.
- **One video vs another:** about ±8 pts at 300 views each, ±5 at 800, ±3.6 at 1,500.

A gap smaller than that is noise. Write "within noise", never a finding.
</noise>

<how_to_read_a_drop>
Viewers leave fastest at the very start of every video. So judge a second by comparing it with the median
column at the **same second**, not by raw size. A 3-point loss at 0:02 is normal; a 3-point loss at 0:25 is a
big event. Hunt for stretches where the video falls well below the median, and stretches where it holds flat
while the median falls. Then read the words and the screen notes in exactly those seconds.
</how_to_read_a_drop>

## Do: one evidence sheet per new video

Write each sheet in the notes with these fields, and fill every field from the data:

```
### <id> · posted <time> · <age> h · <views> views · <length> s · settled|provisional
- Noise band at this view count: ±<n> pts vs median
- 0:01 / 0:03 / 0:10 / 0:30 kept: <a>/<b>/<c>/<d>   median: <..>   gap at 0:03: <+/- pts> (real | within noise)
- Second-2 loss (0:01→0:02): <pts>   (median: <pts>)
- Frame 0 (from title_strip.jpg): <what is on screen at 0.05 s. Compare panel 1 with panels 2 to 4: if the title text
  changes color or a text box appears later, frame 0 was UNFINISHED. Logo? Face?>
- Frame at 2.2 s (f2.jpg): <is the face still on screen?>
- First sentence (exact words): "<...>"
- When the claim lands: the second the viewer first hears WHAT the video claims or promises (the verb that
  carries it, e.g. "cancel", "are at war", "sucks"), from the word timestamps: 0:0x.x. Product names and
  throat-clearing before it (a product name, or a long list of who the video is for) are wait time. Compare it with
  the other videos' landing times in `words.json`.
- Second sentence (exact words): "<...>"
- Strongest fact in the video (number, name, result) and the second it first appears: "<...>" at 0:xx (kept xx% then)
- Open loops: each promise or question and the second it opens; when (if ever) it is paid off
- Payoff: the second the main promise is delivered, and the % still watching
- Biggest below-median stretch: 0:aa to 0:bb, kept x→y vs median x→y, words: "<...>"
- Best-holding stretch: 0:aa to 0:bb, words: "<...>"
- Length and ending: <seconds>; what happens after the payoff; the CTA (exact words)
- Same topic as an earlier video? <id/name or no>. If yes, put the two openings side by side.
```

Then the **movers** among refreshed videos. List only those where views grew by more than 20% or the 0:03
hold moved by more than its noise band, with before and after numbers.

## Done when

- [ ] Every new video has a full sheet with exact quotes and seconds. Every number is labeled provisional
  if the video is under 48 h old.
- [ ] You opened each title strip yourself and compared panel 1 with panels 2 to 4, rather than trusting Gemini
  (or a 220 px thumbnail) about frame 0.
- [ ] Movers are listed, or the notes say "none beyond noise".
- [ ] `account_notes.md` is read and still true, or written now (3+ settled videos), or the notes say why not yet.

**Next:** open `teardown/03-name-new-videos.md`.
