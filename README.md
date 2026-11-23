# retention-teardown

Two Claude Code skills that read your short-form videos' retention the way an editor would, every time you run them.

- **`/retention-teardown`** for TikTok, and **`/retention-teardown-instagram`** for Instagram Reels.
- Each run pulls the per-second retention curve the phone app shows for every video (the share of viewers still
  watching at 0:01, 0:02, 0:03 and so on), lines every second up with the words you said (a local Whisper transcript)
  and what was on screen (real frames, plus an optional Gemini watch pass), and compares each second with your own
  account's median at that same second.
- It finds where viewers leave, writes a hook-rewrite card for each new video built only from lines you actually said
  in it, and re-tests its written lessons against every new video. A lesson needs the same pattern in 3 or more
  videos, bigger than the noise, and only videos 48 hours or older can change a lesson's status.
- Everything lands in one local page per account, `retention-teardown.html`, that gets more true each run.

Read this before you install:

- **Unofficial.** Not affiliated with, endorsed by or supported by TikTok, Instagram, Meta, Anthropic or Manaflow (the
  makers of cmux).
- **It reads YOUR OWN analytics from YOUR OWN signed-in browser tab**, through the same requests TikTok Studio's and
  Instagram's own pages make. It never asks for or stores your password and never reads your session cookies (the
  Instagram side reads one cookie, your numeric user id, to prove which account is signed in).
- **Read-only.** It never posts, edits, deletes, comments, likes or changes a setting. On Instagram it asks for one
  Reel's insights at a time, 10 to 20 seconds apart, at most 20 per run, and stops collecting for that account on any
  challenge or rate limit (for 24 hours, or until you clear Instagram's prompt yourself).
- **Any app update can break it.** TikTok and Instagram can change these internal requests at any time. When Instagram's
  answer changes shape, the collector stops with a clear message instead of guessing numbers.
- **macOS on Apple silicon only** (macOS 14 or later). Transcription uses mlx-whisper, which runs only on Apple silicon.
- **Tested with** macOS 15.7.3, cmux 0.64.22, Claude Code 2.1.302, Python 3.10.4, ffmpeg 9.0.2 and mlx-whisper 0.4.3.
  The two skills run on one Mac with those versions. This public copy was checked offline (every script compiles,
  starts and renders an empty page; the parser tests pass); it has not yet been run end to end on anyone else's Mac.

## What you get

One page per account, opened inside cmux. From top to bottom: a one-paragraph verdict; every video's curve on one
chart with your median drawn through them and a table of the key seconds; the lessons, each with its evidence, its
advice and its status (holding, new, weakening, retired); a second-by-second explorer where every row is one second
(how many viewers were left, your median at that second, the words, what changed on screen); hook-rewrite cards built
from your own lines; your own pre-record checklist; and an update log of what changed on each run.

A new account starts empty and honest: no lessons until 3 videos are 48 hours old. The full description of every
section and of the `narrative.json` file behind it is in [PAGE_FORMAT.md](PAGE_FORMAT.md).

## Requirements

- A Mac with Apple silicon and macOS 14 or later.
- [cmux](https://cmux.com), the macOS terminal with a built-in browser. Claude Code must run inside a cmux terminal,
  because the skills drive cmux's browser, where you stay signed in to TikTok and Instagram.
- [Claude Code](https://code.claude.com/docs/en/setup), on a plan that includes it.
- Homebrew, ffmpeg and Python 3.10 or newer. Setup installs what is missing.
- About 1.6 GB of disk for the Whisper model, plus the Python packages (mlx-whisper brings in PyTorch).
- A TikTok account with analytics in TikTok Studio, and/or a professional (Creator or Business) Instagram account:
  Instagram shows Reel insights only to those.
- Optional: a Gemini API key, for the notes on what changes on screen each second. Without one, everything else works
  and each run says the watch notes were skipped.

## Set it up

Open cmux, start `claude` in a cmux terminal, and paste this one line:

```text
Clone https://github.com/christianjohnston-ai/claude-retention-teardown into ~/claude-retention-teardown (git pull if it is already there), then read ~/claude-retention-teardown/SETUP.md and follow it one step at a time, stopping at every step marked YOU DO THIS until I say done.
```

Claude Code then works through [SETUP.md](SETUP.md): it checks your Mac, installs ffmpeg, Python packages and the
Whisper model, links the two skills into `~/.claude/skills`, and creates your first account. It stops and waits for
you at the few steps only you can do: installing an app, signing in inside the cmux browser, and (if you want the
Gemini notes) pasting a key into a file. You can also read SETUP.md and do every step yourself.

Then, in a new Claude Code session inside cmux, run `/retention-teardown` or `/retention-teardown-instagram`.

## Where your data goes

| What | Where |
|---|---|
| Retention curves, stats, post lists | Read from TikTok's and Instagram's own servers, by your own signed-in tab |
| Video files | Downloaded from TikTok's and Instagram's video servers to your Mac |
| Transcripts | Made on your Mac by Whisper |
| Gemini watch pass (optional) | Each new video file is uploaded to Google's Gemini API. Your analytics are not |
| Instagram official API (optional) | graph.instagram.com, with your own token, for the Reel list and a cross-check |
| The page | A local file. Opening it loads its fonts from Google Fonts |

Everything a run writes stays in `accounts/` inside each skill folder, which is gitignored, so it cannot reach this
public repository by accident. Keys and tokens go in a gitignored `.env` file; the scripts never print them. On TikTok
runs, Whisper's model loader may check huggingface.co for model updates; the Instagram collector runs Whisper offline.

## The two skills

| Folder | Skill | Command |
|---|---|---|
| [tiktok/](tiktok/) | `tiktok-retention-teardown` | `/retention-teardown [account]` |
| [instagram/](instagram/) | `instagram-retention-teardown` | `/retention-teardown-instagram [alias] [reel-url]`, `... check`, `... login <alias>` |

Each skill is a `SKILL.md` plus nine step files (`teardown/01` to `09`) that Claude reads one at a time, so every run
follows the same discipline: refresh the data, read the evidence, name new videos, test every lesson, re-verify every
quoted number, write rewrite cards, update the log, build and check the page, report in five lines. The scripts are in
each skill's `scraping/` folder, with a README on how the collection works and what to do when an app changes.

## Disclaimer

You are responsible for using your own accounts within TikTok's, Instagram's and Google's terms. This only works with
accounts you own and sign in to yourself. It is provided as is, without warranty of any kind; see the repository's
[LICENSE](LICENSE).
