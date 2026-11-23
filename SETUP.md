# Setting up retention-teardown on a new Mac

This is a step-by-step procedure. Claude Code can run it for you one step at a time, and you can read it and do it
yourself. Every step has three parts:

- **Do**: the commands for the step.
- **Check**: a command and the output it should print. A step is done only when its check passes.
- **If it fails**: what to do instead.

Steps marked **YOU DO THIS** need you: installing an app, signing in inside the cmux browser, or pasting a key into a
file. At those, Claude tells you exactly what to do and waits.

This guide assumes the repository is cloned at `~/claude-retention-teardown`. If it is somewhere else, use that path wherever
this guide says `~/claude-retention-teardown`. If you only use TikTok, skip steps 13 to 15; if you only use Instagram, skip steps
11 and 12.

## For Claude Code: how to run this guide

<setup_rules>
- Do one step at a time, in order. Run its Do commands, then its Check. Never start the next step while a Check fails:
  follow "If it fails", and if that does not fix it, stop and tell the user what you saw.
- At a step marked YOU DO THIS: tell the user in plain words exactly what to do (which app, which tab, which field),
  then end your turn and wait until they say done. Then run the Check.
- Never type a password, a 2FA code or an answer to a TikTok or Instagram prompt. Never ask the user to paste a key or
  a token into the chat; they put it into the `.env` file themselves.
- Never print a key, a token, or the contents of any `.env` file. Never run `cmux browser state save` or
  `cmux browser cookies get --all`: both dump the whole cookie jar.
- Never overwrite an existing file or link in `~/.claude/skills` or `~/.claude/commands`. If one is in the way, stop
  and ask.
- Commands that download a lot (steps 7 and 8) can take several minutes: run them in the background and wait.
- When every step is done, tell the user in three lines what was set up, what was skipped, and the command to run first.
</setup_rules>

---

### Step 1: Check the Mac and Claude Code

**Do:** nothing to install. Read the Mac's chip, macOS version and Claude Code version.

**Check:**
```bash
uname -m
sw_vers -productVersion
claude --version
```
Expected: `arm64`; a version of `14.0` or higher; a line ending in `(Claude Code)` (tested with `2.1.302`).

**If it fails:** an Intel Mac (`x86_64`) or macOS older than 14 cannot run this: mlx-whisper (the transcriber) is built
only for Apple silicon, and MLX needs macOS 14 or later. Stop here. If `claude` is not found, install it
with the official command from https://code.claude.com/docs/en/setup:
`curl -fsSL https://claude.ai/install.sh | bash`, then open a new terminal.

---

### Step 2: Claude Code is running inside cmux  (YOU DO THIS if it is not)

**Do:** nothing, if the check passes. The skills drive cmux's built-in browser with the `cmux` command, and that
command only works from inside a cmux terminal.

**Check:**
```bash
echo "${CMUX_WORKSPACE_ID:-not inside cmux}"
cmux --version
```
Expected: an id (anything except `not inside cmux`), then a line starting `cmux ` (tested with `cmux 0.64.22`).

**If it fails (YOU DO THIS):**
1. Install cmux (macOS 14 or later), either way, both from the official project (https://github.com/manaflow-ai/cmux):
   - Download https://github.com/manaflow-ai/cmux/releases/latest/download/cmux-macos.dmg, open it, and drag cmux into
     Applications. Or, if you have Homebrew: `brew tap manaflow-ai/cmux` then `brew install --cask cmux`.
2. Open cmux. If macOS asks whether to open an app from an identified developer, click Open.
3. In a cmux terminal, run `claude`, and paste: `Continue ~/claude-retention-teardown/SETUP.md from step 2.`

---

### Step 3: Homebrew  (YOU DO THIS if it is missing)

**Do:** nothing, if the check passes.

**Check:**
```bash
brew --version
```
Expected: a line starting `Homebrew `.

**If it fails (YOU DO THIS):** Homebrew's installer asks for your Mac password, so run it yourself in a cmux terminal
tab (not through Claude). The official command, from https://brew.sh:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
When it finishes, run the "Next steps" lines it prints (they add `brew` to your PATH), open a new terminal tab, and
tell Claude you are done.

---

### Step 4: ffmpeg

**Do:**
```bash
brew install ffmpeg
```
(Source: https://formulae.brew.sh/formula/ffmpeg. It cuts the frames and reads each video's length.)

**Check:**
```bash
ffmpeg -version | head -1
ffprobe -version | head -1
```
Expected: lines starting `ffmpeg version ` and `ffprobe version ` (tested with 9.0.2).

**If it fails:** run `brew doctor`, fix what it reports, and install again.

---

### Step 5: Python 3.10 or newer

**Do:** nothing, if the check prints `True`.

**Check:**
```bash
python3 -c 'import sys; print(sys.version_info >= (3, 10))'
```
Expected: `True`.

**If it fails (prints `False`):** the Python that comes with macOS is too old for mlx-whisper (MLX needs 3.10 or newer).
Install Homebrew's Python 3.13 formula (https://formulae.brew.sh/formula/python%403.13). The version sits in the
variable `V` so it is written in one place; the install command is the one on that formula page:
```bash
V=3.13; brew install "python@$V" && "python$V" --version
```
Expected: `Python 3.13.` and a number. Use `python3.13` instead of `python3` in step 7 only. Everything else keeps
calling `python3`: the scripts switch to the step 7 environment by themselves. (Pick 3.13 rather than Homebrew's newest
Python: mlx-whisper depends on PyTorch and numba, which often publish wheels for a new Python version some time
after it ships.)

---

### Step 6: The code is in place

**Do:** nothing, if the check passes (the line you pasted cloned it).

**Check:**
```bash
ls ~/claude-retention-teardown/tiktok/SKILL.md ~/claude-retention-teardown/instagram/SKILL.md
```
Expected: both paths printed, no "No such file".

**If it fails:**
```bash
git clone https://github.com/christianjohnston-ai/claude-retention-teardown.git ~/claude-retention-teardown
```
If the folder exists but is old: `git -C ~/claude-retention-teardown pull`. If `git` is missing, macOS offers to install the
Command Line Tools (YOU DO THIS: run `xcode-select --install` and accept), then try again.

---

### Step 7: The Python packages, in their own environment

**Do:** create one virtual environment shared by both skills and install `mlx-whisper` (the transcriber, PyPI name
`mlx-whisper`, https://pypi.org/project/mlx-whisper/) and `requests` (for the optional Gemini pass). Use `python3.13`
in the second line if step 5 needed it.
```bash
cd ~/claude-retention-teardown
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install mlx-whisper requests
```
This downloads a lot (mlx-whisper brings in PyTorch) and can take several minutes; run it in the background. `.venv/`
is gitignored.
Why a venv: Homebrew's Python refuses `pip install` outside one, and it keeps these packages away from everything else.

**Check:**
```bash
~/claude-retention-teardown/.venv/bin/python -c "import mlx_whisper, requests; print('ok')"
```
Expected: `ok`.

**If it fails:** if the error says the Python version is too old, delete the environment
(`rm -rf ~/claude-retention-teardown/.venv`), do step 5's fix, and redo this step with `python3.13`. If pip
reports no matching distribution for `mlx`, check step 1 again (Apple silicon, macOS 14+).

---

### Step 8: The Whisper model

**Do:** download the transcription model once (about 1.6 GB, into `~/.cache/huggingface`). Run it in the background.
```bash
~/claude-retention-teardown/.venv/bin/python -c "from huggingface_hub import snapshot_download; print(snapshot_download('mlx-community/whisper-large-v3-turbo'))"
```
Why now: the Instagram collector runs Whisper offline, so during a run it contacts only Instagram's and Meta's servers
(and Google's Gemini API, if you add a key). The model must already be on the Mac.

**Check:**
```bash
ls ~/.cache/huggingface/hub/models--mlx-community--whisper-large-v3-turbo/snapshots/*/weights.safetensors
```
Expected: one path ending in `weights.safetensors`.

**If it fails:** run the Do command again (it resumes). Check free disk space with `df -h ~`.

---

### Step 9: Link the skills and commands into Claude Code

**Do:** first look for anything already in the way:
```bash
mkdir -p ~/.claude/skills ~/.claude/commands
ls -ld ~/.claude/skills/tiktok-retention-teardown ~/.claude/skills/instagram-retention-teardown \
       ~/.claude/commands/retention-teardown.md ~/.claude/commands/retention-teardown-instagram.md 2>&1
```
Every line should say "No such file or directory". If one exists and is not already a link into
`~/claude-retention-teardown`, stop and ask the user. Then link the platforms they use:
```bash
ln -s ~/claude-retention-teardown/tiktok ~/.claude/skills/tiktok-retention-teardown
ln -s ~/claude-retention-teardown/tiktok/commands/retention-teardown.md ~/.claude/commands/retention-teardown.md
ln -s ~/claude-retention-teardown/instagram ~/.claude/skills/instagram-retention-teardown
ln -s ~/claude-retention-teardown/instagram/commands/retention-teardown-instagram.md ~/.claude/commands/retention-teardown-instagram.md
```

**Check:**
```bash
python3 ~/.claude/skills/tiktok-retention-teardown/scraping/account.py list
python3 ~/.claude/skills/instagram-retention-teardown/scraping/account.py show
```
Expected: `No TikTok account yet. Create one with: ...` and `No Instagram account yet. Create one with: ...`.
(This also proves the links work and that the scripts run.)

**If it fails:** `No such file`: a link points to the wrong place; check it with `readlink` and recreate it. Claude
Code reads new skills and commands when a session starts: if `/retention-teardown` is not offered later, start a new
session.

---

### Step 10: Gemini key (optional)  (YOU DO THIS)

**Do:** ask the user whether they want the Gemini watch notes (what changes on screen, second by second). Each new
video file is then uploaded to Google's Gemini API; the analytics are not. Without a key, everything else works and
each run says the watch notes were skipped. If they want it:
```bash
cp -n ~/claude-retention-teardown/tiktok/.env.example ~/claude-retention-teardown/tiktok/.env
cp -n ~/claude-retention-teardown/instagram/.env.example ~/claude-retention-teardown/instagram/.env
```
YOU DO THIS: create a key at https://aistudio.google.com/apikey. Open each `.env` you use (for example
`open -e ~/claude-retention-teardown/tiktok/.env`), paste the key right after `GEMINI_API_KEY=` on that line,
and save. Do not paste the key into the chat. (Setting `GEMINI_API_KEY` in your shell profile works too.)

**Check** (prints a count, never the key):
```bash
grep -c '^GEMINI_API_KEY=.' ~/claude-retention-teardown/tiktok/.env
grep -c '^GEMINI_API_KEY=.' ~/claude-retention-teardown/instagram/.env
```
Expected: `1` for each file the user filled in.

**If it fails:** `0` means the line is still empty or has a space before the `=`. Ask the user to fix it in the editor.
Skipping this step is fine.

---

### Step 11: Your TikTok account

**Do:** ask the user for their TikTok @handle and a short name for the account (lowercase; `main` is fine). Then:
```bash
python3 ~/.claude/skills/tiktok-retention-teardown/scraping/account.py add main @their_handle
python3 ~/.claude/skills/tiktok-retention-teardown/scraping/build_report.py
```
`add` creates `accounts/main/` (gitignored) and a cmux browser profile called `tt-main`, where this account's sign-in
will live. The first account added is the default. `build_report.py` renders the empty page, offline.

**Check:**
```bash
python3 ~/.claude/skills/tiktok-retention-teardown/scraping/account.py list
```
Expected: `main  @their_handle  profile tt-main  (default)`. The build line before it said
`wrote .../accounts/main/retention-teardown.html · 0 videos`.

**If it fails:** if `add` said the cmux profile was NOT created, you are outside cmux: go back to step 2, then run
`cmux browser profiles add tt-main`. A back catalog of many videos takes minutes per video on the first run; to track
only recent posts, set `"since": "YYYY-MM-DD"` in `accounts/main/account.json`.

---

### Step 12: Sign in to TikTok inside cmux  (YOU DO THIS)

**Do:**
```bash
python3 ~/.claude/skills/tiktok-retention-teardown/scraping/daily.py --check
```
The first time, it opens TikTok Studio in the `tt-main` profile and prints `NOT_SIGNED_IN surface:N ...` (exit 3).
YOU DO THIS: in cmux, find that browser tab (it is in your current workspace), and sign in to TikTok there as
@their_handle. Use only this account in this profile. Then tell Claude you are done.

**Check:** run the same command again.
Expected: `OK account "main" @their_handle is signed in on surface:N: <n> public posts, <n> private or under review. Nothing was written.`

**If it fails:** `WRONG_ACCOUNT`: a different TikTok account is signed in on that tab; sign out there and sign in as
the right one. `would not answer after 3 reloads`: run `cmux browser surface:N reload`, wait 10 seconds, check again.

---

### Step 13: Your Instagram account

**Do:** Reel insights exist only for professional (Creator or Business) Instagram accounts; confirm the user's account
is one. Ask for the @handle and a short alias (`main` is fine). Then:
```bash
python3 ~/.claude/skills/instagram-retention-teardown/scraping/account.py add main @their_handle
python3 ~/.claude/skills/instagram-retention-teardown/scraping/build_report.py --account main
```
`add` creates `accounts/main/` (gitignored) and a cmux browser profile called `ig-main`.

**Check:**
```bash
python3 ~/.claude/skills/instagram-retention-teardown/scraping/account.py show main
```
Expected: JSON with `"handle": "their_handle"`, `"profile": "ig-main"` and `"token_present": false`. The build line
said `wrote .../accounts/main/retention-teardown.html · 0 Reels drawn, 0 without a per-second curve`.

**If it fails:** if the cmux profile was NOT created, go back to step 2, then run `cmux browser profiles add ig-main`.

---

### Step 14: Sign in to Instagram inside cmux  (YOU DO THIS)

**Do:**
```bash
python3 ~/.claude/skills/instagram-retention-teardown/scraping/account.py login main
```
It opens Instagram's sign-in page in the `ig-main` profile, with an orange banner saying which account belongs there.
YOU DO THIS: sign in there as @their_handle (password, 2FA, and "Save login info"). Never use "Switch accounts" inside
this profile. Then tell Claude you are done.

**Check:**
```bash
python3 ~/.claude/skills/instagram-retention-teardown/scraping/account.py check main
```
Expected: `OK main @their_handle signed in on surface:N (profile ig-main), ds_user_id <a number>; no official token. Nothing else was written.`

**If it fails:** exit 3 (`NOT_SIGNED_IN`): the sign-in did not finish; do it again in the bannered tab. Exit 4
(`WRONG_ACCOUNT`): another account is signed in to that profile; sign it out there and sign in as the right one. Exit 6
(`PAUSED`): Instagram showed a challenge; answer it in that tab, then run `account.py unpause main` and check again.

---

### Step 15: Which Reels to track (and the optional official token)  (YOU DO THIS)

**Do:** without the official Instagram API, the collector has no list of the account's Reels, so you name the ones to
track once; every later run refreshes them. YOU DO THIS: send Claude the links of the Reels you want analyzed (start
with your last 5 to 10). Claude then collects them, in the background (about 75 seconds per Reel, at most 20 per run;
this is the first real request to Instagram):
```bash
python3 ~/.claude/skills/instagram-retention-teardown/scraping/collect.py --account main --reel <url> --reel <url>
```
Each named Reel is saved to `account.json` "reels" and refreshed on every later run. New Reels you post later are added
the same way (`/retention-teardown-instagram main <reel-url>`). If the collector stops with an exit code, the table in
`~/.claude/skills/instagram-retention-teardown/teardown/01-refresh-data.md` says what to do.

Optional, instead: with the official "Instagram API with Instagram Login" set up for this account (Meta's docs:
https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/), the collector finds new
Reels by itself and cross-checks views, watch time and skip rate. YOU DO THIS: put the token and the account's
Instagram user id into `~/claude-retention-teardown/instagram/.env` as `IG_TOKEN_MAIN=` and `IG_USER_ID_MAIN=`
(see `.env.example`; the names follow the alias in capitals).

**Check:** for the Reel links:
```bash
python3 ~/.claude/skills/instagram-retention-teardown/scraping/account.py show main
```
Expected: the `"reels"` list holds the shortcodes of the links (the part after `/reel/`), and the collector's JSON
summary line showed `"new"` greater than 0 (or `PENDING` lines, for Reels too young to have a curve). For a token:
```bash
python3 ~/.claude/skills/instagram-retention-teardown/scraping/account.py show main | grep token_present
python3 ~/.claude/skills/instagram-retention-teardown/scraping/account.py check main
```
Expected: `"token_present": true`, and the check line ends with `; official token matches. Nothing else was written.`

**If it fails:** `WRONG_ACCOUNT ... the official token ... belongs to`: the token is for another account; replace it.

---

### Step 16: The first run

**Do:** start a new Claude Code session in a cmux terminal (so the new commands are loaded), then run the platforms you
set up:
- TikTok: `/retention-teardown`
- Instagram: `/retention-teardown-instagram`. The Reels collected in step 15 are analyzed as new in its step 02.

The first TikTok run takes several minutes per video (download, frames, Whisper, Gemini). Claude follows the nine step
files and ends with a five-line report.

**Check:**
```bash
ls -la ~/.claude/skills/tiktok-retention-teardown/accounts/main/retention-teardown.html ~/.claude/skills/instagram-retention-teardown/accounts/main/retention-teardown.html
```
Expected: the page file of each platform you ran, with today's date, and the page open in a cmux browser tab.

**If it fails:** read the step 01 table in the skill's `teardown/01-refresh-data.md`: every exit code and message the
collectors print is listed there with what to do.

---

### Step 17: A private history of your runs (optional)

**Do:** your data is never committed to the claude-retention-teardown clone (`accounts/` is gitignored). If you want a dated
history of what the curves and lessons said each day, make each account folder its own git repository. Never push it
to a public repository: it holds your analytics.
```bash
cd ~/claude-retention-teardown/tiktok/accounts/main && git init && printf 'media/\n*.mp4\n' > .gitignore && cd -
cd ~/claude-retention-teardown/instagram/accounts/main && git init && printf 'media/\nstate/\n*.mp4\n' > .gitignore && cd -
```
Step 09 of each run then commits that folder.

**Check:**
```bash
git -C ~/claude-retention-teardown/tiktok/accounts/main status --short | head -5
```
Expected: a few lines of untracked files (`??`), and no error.

**If it fails:** `not a git repository`: the `git init` did not run in that folder; run it again there.

---

## Later

- **Update:** `git -C ~/claude-retention-teardown pull`. Your `accounts/` folders and `.env` files are gitignored, so an update
  never touches them.
- **Never run `git clean -x` (or `-X`) in the clone.** It deletes every ignored file, which means every `accounts/`
  folder (your whole history of curves, transcripts and pages) and your `.env` keys.
- **Another account:** `account.py add <name> <@handle>` again, sign it in (steps 12 or 14), then
  `/retention-teardown <name>` or `/retention-teardown-instagram <alias>`.
- **Uninstall:** remove the four links from step 9 (`rm ~/.claude/skills/tiktok-retention-teardown` and so on). Your
  data stays in the `accounts/` folders until you delete them yourself. The cmux profiles (`tt-...`, `ig-...`) can be
  removed with `cmux browser profiles delete <name>`.
