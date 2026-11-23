# How the Instagram collection works

Read this when step 01 fails, when Instagram changes something, or before you edit `collect.py`. A normal run doesn't
need it.

## The source

Instagram's own Reel insights (the data behind the phone app's Insights screen), requested from
`https://i.instagram.com/graphql_www` by ordinary page JavaScript (`insights.js`) running in a `www.instagram.com` tab of
the account's own cmux browser profile (`cmux browser <surface> eval`). No extension, proxy or cookie export:

- i.instagram.com answers `Origin: https://www.instagram.com` with `Access-Control-Allow-Origin: https://www.instagram.com`
  and `Access-Control-Allow-Credentials: true`; the page's CSP allows `*.instagram.com`; www → i is same-site, so WebKit
  sends the session cookies (all measured 2026-10-14).
- The request is a plain GET with `client_doc_id`, variables `{bloksVersioningId, mediaIgid}`, `method=get&format=json`
  plus three `enable_canonical_*` flags. `mediaIgid` = the Reel shortcode decoded as base-64 digits. Where the request
  shape and the two Instagram-internal ids came from is credited in `insights.js`.
- When this tool was built, a capture of a 100 s Reel returned 101 points, one every second, within 1 point of the phone
  app at 0:03 / 0:10 / 0:50 / 1:40 (the app rounds down); views, likes, skip rate and average watch were identical to
  the official API.

## Gates, in order (collect.py)

1. Per-account lock (`state/collect.lock`) and pause (`state/pause.json`).
2. A NEW cmux surface with `--profile ig-<alias>`. Never a reused tab: the cmux CLI cannot tell which profile a tab is
   on, so a reused tab could belong to another account.
3. Identity, before any write: the `ds_user_id` cookie (read with `cookies get --name ds_user_id`, nothing else), the
   page's own `ds_user_id`, and `accounts/edit/web_form_data/` (answers only for the signed-in account) must all agree
   with `account.json` (`handle`, and the `web_pk` pinned on the first verified sign-in). Exit 3 / 4.
4. Token accounts: the official token's `/me` must be the same account. Exit 4.
5. Ownership: for a token account, the Reel's shortcode must be in the account's own official Reel list. Exit 5.
   Accounts without a token have no list: their Reels are named with `--reel` and ownership rests on Instagram (it
   returns insights only to the owner; see "Accounts without a token").
6. One insights request, then 10 to 20 s before the next. Max 20 per run (`--max`).
7. Stop signals (`ig_parse.signal`): logged out (code 1675002) → exit 3; checkpoint/challenge → pause until
   `account.py unpause`; 429 / rate limit / "please wait a few minutes" / feedback_required → 24 h pause. Exit 6, no retry.
8. Save: `raw/<UTC>.json` (every part as received, signed CDN URLs removed, never overwritten), then one line in
   `captures.jsonl` (normalized), then `meta.json`. Every capture is kept; nothing is replaced.

## The answer's shape and units (verified on a real answer; see ig_parse.py)

- A stream of JSON objects served as `text/html`: one initial part plus incremental parts whose `path[0]` contains
  `ig_reel_insights(`; the last has `extensions.is_final: true`.
- Float keys carry a `1f` prefix (`1fpercentage`, `1fvalue`). Raw keeps it; the normalizer strips it.
- Units differ per field: curve = share 0 to 1; `avg_watch_time.value` = **milliseconds** (format says seconds);
  `performance_factors` (skip, share, like, save, repost, comment rates) = shares; `views_sources` = shares;
  demographics mix shares (age, gender) and percents (country), so they stay raw only.
- Also returned: `like_timing.likes_by_timing` per second, `views_over_time` (followers vs non-followers), `follows`,
  `profile_visits`, `followers_views`, `non_followers_views`, benchmarks per rate, signed `video_url`.

## Accounts without a token

No official Reel list, no cross-check, no ownership list. Name each Reel to track once with
`collect.py --account <alias> --reel <url>`; it is added to `account.json` "reels" and refreshed on every later run.
New Reels are not discovered by themselves. To give the account the same guarantees as a token account, set up the
official "Instagram API with Instagram Login" for it (Meta's docs:
https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/; it needs a professional
account), then put its token and Instagram user id in the skill folder's `.env` as `IG_TOKEN_<ALIAS>` and
`IG_USER_ID_<ALIAS>` (see `.env.example`). The token is sent only as an `Authorization: Bearer` header, never in a URL.

## Gotchas

- `current_user/?edit=true` returns HTML on web; `users/<pk>/info/` answered 429. Neither is used.
- Skip rate is not 100 minus curve(0:03), and average watch includes replays. Both are Instagram's definitions.
- A WebKit tab that sat idle answers its first fetch with `TypeError: Load failed`; `insights.js` retries transport
  errors only, never an answer.
- The run file's `hosts` lists every host contacted (in-page and Python). Python requests go through `net.allow()`,
  which refuses anything not on its list.
- Whisper runs offline (`HF_HUB_OFFLINE=1` in `media.py`), so the model must already be in the Hugging Face cache.
  SETUP.md downloads it once.
- `collect.py` needs `mlx-whisper` and `requests` from `claude-retention-teardown/.venv`; it re-runs itself inside that venv
  when the venv exists (`account.use_venv`).

## When Instagram changes something (exit 7)

The answer is kept in `state/format-<UTC>.txt` (or the raw file named in the message). Likely causes: a rotated
`client_doc_id` / `bloksVersioningId`, or a renamed field. Update `insights.js` and `ig_parse.METHOD` together, re-run
`tests/test_ig_parse.py`, capture one Reel, and compare its `captures.jsonl` line with the phone app before trusting
the change. Never guess numbers to fill the gap.
