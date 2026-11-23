# Part 1: how the retention scraping works

Read this when the data step fails, when TikTok changes something, or before you edit `daily.py`. A normal
run doesn't need it: step 01 runs the script.

## The source

TikTok Studio, signed in as the account's @handle, inside a **cmux browser surface** opened in that account's own cmux
browser profile (`tt-<name>`). cmux keeps the sign-in in that profile's cookie store, so a tab opened weeks later is
still signed in until TikTok expires the session. Never capture or store passwords, cookies or tokens. The user signs
in themselves when needed.

Studio's own analytics endpoints answer a plain same-origin `fetch` run inside the signed-in page (via
`cmux browser <surface> eval`). These are the requests the Studio page itself makes; no request signing is needed:

| Data | Request |
|---|---|
| Post list | `POST /tiktok/creator/manage/item_list/v1/?aid=1988` with body `{cursor, size}`; page with `has_more` / `cursor` |
| Per-second retention, realtime | `GET /aweme/v2/data/insight/?aid=1988&type_requests=[{insigh_type:"video_retention_rate_realtime",aweme_id}]` returns `value.list[{timestamp(ms), value(0-1)}]` |
| Per-second retention, after ~7 days | same endpoint, `video_retention_rate_history_7d` returns `value[{timestamp, value}]` |
| Average watch time | `video_per_duration_realtime` (seconds), or `video_per_duration` (**milliseconds**) |
| Finish rate | `video_finish_rate_realtime` (may stop after ~7 days; the script carries the last value forward) |
| Views, likes, saves, comments, shares, length, download URLs | `video_info` → `statistics`, `video.duration` (ms), `video.play_addr.url_list` |
| Traffic sources | `video_traffic_source_percent_realtime` |
| Which account the tab is signed in as | `GET /passport/web/account/info/?aid=1988` → `data.username` |

Gotchas, each learned the hard way:
- **Request realtime and history types in separate calls.** Mixing them in one `type_requests` returns nulls.
- **A tab left open overnight (Mac asleep)** answers the first request(s) with `TypeError: Load failed`. Every
  in-page fetch goes through a retry helper (`F()` in `daily.py`), and the post list retries after a reload.
- **Post status:** only `status 102` + `visibility 1` is public. Status 140 / visibility 2 are private or under
  review; they're listed in the run as skipped.
- **A brand-new post has no curve for a few hours.** It's recorded as `pending` and processed on a later run.
- `cmux browser network requests` doesn't work on cmux's WebKit view. To discover endpoints, read
  `performance.getEntriesByType('resource')` and search Studio's JS bundles for `insigh_type` names.
- Finding the surface: `cmux tree --all --json`, then a browser surface whose URL contains `tiktok.com` AND whose
  signed-in username is the account's handle. Surface numbers change when cmux restarts, so look them up every run.
- **Wrong account guard.** A tab only counts if it is signed in as the expected account. Otherwise `daily.py` exits 4
  (`WRONG_ACCOUNT`) before writing anything, so one account's curves can never land in another account's library.

## What the script does with a new post

Run as `python3 ~/.claude/skills/tiktok-retention-teardown/scraping/daily.py [--account <name>] [--surface surface:N] [--skip-gemini]`.
For a new post it:
1. downloads the video (curl with a TikTok referer) to `accounts/<name>/library/<id>/video.mp4`
2. saves real frames at 0.05 s and 2.2 s (`f0.jpg`, `f2.jpg`) and the title strip with ffmpeg
3. transcribes locally with mlx_whisper (`mlx-community/whisper-large-v3-turbo`, word timestamps) to `words.json`.
   Whisper misspells brands (seen when this was built: ChatBt, Anthropik, Cloud for Claude, NAN for n8n, Kroc for
   Grok, Prop for Prompt)
4. if a `GEMINI_API_KEY` is set (environment, or `.env` in the skill folder), runs one Gemini watch pass
   (`gemini-3.1-pro-preview`, falling back to `gemini-2.5-pro`) and saves on-screen changes in seconds to
   `gemini.json`. The video file is uploaded to Google's Gemini API for this; the analytics are not. The key travels
   in the `x-goog-api-key` header, never in a URL. A failure is retried on later runs; with no key the pass is skipped
   and the run prints `NO_GEMINI`.

Every public post gets one dated snapshot per day in `snapshots.jsonl`. A re-run on the same day replaces
that day's snapshot.

## The page

`build_report.py` renders `accounts/<name>/retention-teardown.html` from the latest snapshot of every analyzed video
plus that account's `narrative.json`. Aggregate numbers in the written text are `{{tokens}}`, recomputed each
build from **settled** videos only (48+ hours old). The builder refuses to write if a token is unknown.
Frames and clips are hard-linked into `accounts/<name>/media/` next to the page, because cmux's browser only reads
files inside the page's own folder. `../../PAGE_FORMAT.md` describes every section of the page.

`check_quotes.py` confirms every quoted line in `narrative.json` exists in a transcript.

## Where the Python packages come from

`daily.py` needs `mlx-whisper` and `requests`. Setup installs them into `claude-retention-teardown/.venv` (shared with the
Instagram skill), and `daily.py` re-runs itself inside that venv when it exists (`account.use_venv`), so the step
files can call plain `python3`. `build_report.py`, `check_quotes.py` and `account.py` use only the standard library.
