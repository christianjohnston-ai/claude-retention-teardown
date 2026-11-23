#!/usr/bin/env python3
"""Daily TikTok retention refresh for one TikTok account (run by /retention-teardown, step 01).

Usage: python3 ~/.claude/skills/tiktok-retention-teardown/scraping/daily.py [--account <name>] [--check] [--surface surface:N] [--skip-gemini]

--account <name>  which account (see account.py). Without it: the default account (the first one you added).
--check           only verify the sign-in and the signed-in @handle, print the post counts, write nothing.
--skip-gemini     skip the Gemini watch pass (a later run backfills it). Also automatic when no GEMINI_API_KEY is set.

1. Finds (or opens) a cmux browser surface on TikTok Studio in the account's own cmux profile, checks the session is
   signed in, and checks it is signed in as THIS account's @handle. Exit code 3 + "NOT_SIGNED_IN surface:N" means the
   user must sign in inside that surface; exit code 4 + "WRONG_ACCOUNT" means a different account is signed in and
   nothing was written.
2. Lists every post. Non-public posts are recorded and skipped.
3. Every public post: pulls today's retention curve + stats and stores a dated snapshot.
4. Posts never analyzed: downloads the video, grabs frames, transcribes (mlx_whisper, word
   timestamps), runs one Gemini watch pass. Posts too young to have a curve stay "pending".
5. Writes runs/<date>.json and runs/<date>-new.md (per-second tables of newly analyzed videos)
   for the analyst step, then the caller runs build_report.py.

Library layout: accounts/<name>/library/<video_id>/{meta.json, snapshots.jsonl, words.json, gemini.json, f0.jpg, f2.jpg,
title_strip.jpg, video.mp4}
"""
import json, os, re, subprocess, sys, time, datetime, argparse, math, statistics

import account as acct

HERE = os.path.dirname(os.path.realpath(__file__))
SKILL_ROOT = acct.SKILL_ROOT                       # the skill folder (claude-retention-teardown/tiktok in the clone)
# ROOT/LIB/RUNS are the ACCOUNT's data folders (accounts/<name>/...). configure() sets them once --account is known.
# There is no account built into the code, so they stay None until then.
ROOT = LIB = RUNS = None
ACCT = None
STUDIO = 'https://www.tiktok.com/tiktokstudio/analytics'
TODAY = datetime.date.today().isoformat()
# tz_offset = the UTC offset in seconds, read from this Mac's clock, so TikTok Studio buckets the days in your own time
# zone wherever you are.
INSIGHT = ("/aweme/v2/data/insight/?locale=en&aid=1988&app_name=tiktok_creator_center&tz_offset=%d&type_requests="
           % time.localtime().tm_gmtoff)

def scrub(msg):
    """Redact API-key-shaped text from an error string before it is stored in runs/*.json (which step 09 may commit to
    the user's private history repo)."""
    return re.sub(r'(AIza[0-9A-Za-z_-]{10,}|([?&]key=)[^&\s\'"]+)', lambda m: (m.group(2) or '') + '[REDACTED]', str(msg))

def sh(*a, **k):
    return subprocess.run(list(a), capture_output=True, text=True, **k)

def configure(a):
    """Point the data folders at account `a` (a dict from account.load)."""
    global ROOT, LIB, RUNS, ACCT
    ACCT = a; ROOT = a['root']; LIB = os.path.join(ROOT, 'library'); RUNS = os.path.join(ROOT, 'runs')

# ---------- cmux ----------
# Every in-page fetch goes through F(): a Studio tab that sat idle answers the first request(s) with
# "TypeError: Load failed" and then works, so each request retries up to 5 times (2026-10-07).
# Which account a tab is signed in as: TikTok's own account endpoint, same-origin from the tab. Retries like F() below
# because an idle tab answers its first fetch with "Load failed".
WHO_JS = """(async()=>{for(let i=0;i<4;i++){try{const j=await (await fetch('/passport/web/account/info/?aid=1988',{credentials:'include'})).json();
return JSON.stringify({u:(j.data&&j.data.username)||null})}catch(e){await new Promise(r=>setTimeout(r,1500*(i+1)))}}return JSON.stringify({u:null})})()"""

def handle_of(surface):
    """The @handle (no @) the tab is signed in as, or None if signed out or the tab does not answer."""
    try: return ev(surface, WHO_JS).get('u')
    except Exception: return None

def find_surface(handle):
    """A tiktok.com tab that is signed in as `handle`, or None.
    SYNC WARNING: this used to return ANY tiktok.com tab. With two accounts that would pull account B's curves into
    account A's library, so a tab only counts if it is signed in as the expected account."""
    t = json.loads(sh('cmux', 'tree', '--all', '--json').stdout)
    hits = []
    def walk(o):
        if isinstance(o, dict):
            if o.get('type') == 'browser' and 'tiktok.com' in (o.get('url') or ''):
                hits.append((o['ref'], o['url']))
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(t)
    hits.sort(key=lambda h: 'tiktokstudio' not in h[1])   # prefer a Studio page
    for ref, _ in hits:
        who = handle_of(ref)
        if who and who.lower() == handle.lower(): return ref
    return None

def open_surface(profile):
    # Every account opens in its own cmux profile (tt-<name>), so that two TikTok logins can be signed in at the same time.
    r = sh('cmux', 'browser', 'open', STUDIO, '--focus', 'false', '--profile', profile)
    m = re.search(r'surface=(surface:\d+)', r.stdout)
    if not m:
        sys.exit(f'Could not open a cmux browser: {r.stdout} {r.stderr}')
    s = m.group(1)
    sh('cmux', 'browser', s, 'wait', '--load-state', 'complete', '--timeout', '30')
    return s

def ev(surface, js):
    r = sh('cmux', 'browser', surface, 'eval', '--script', js)
    out = r.stdout.strip()
    try:
        return json.loads(out)
    except Exception:
        raise RuntimeError(f'eval failed on {surface}: {out[:300]} {r.stderr[:300]}')

LIST_JS = """(async()=>{const F=async(u,o)=>{for(let i=0;i<5;i++){try{return await fetch(u,o)}catch(e){if(i===4)throw e;await new Promise(r=>setTimeout(r,1500*(i+1)))}}};const items=[];let cursor=0,more=true,guard=0;
while(more&&guard<20){guard++;const r=await F('/tiktok/creator/manage/item_list/v1/?aid=1988',{method:'POST',credentials:'include',headers:{'content-type':'application/json'},body:JSON.stringify({cursor,size:50})});
 const j=await r.json(); if(!j.item_list){return JSON.stringify({ok:false,status:j.status_code,msg:j.status_msg});}
 items.push(...j.item_list); more=j.has_more; cursor=j.cursor;}
return JSON.stringify({ok:true,items:items.map(i=>({id:i.item_id,create_time:+i.create_time,desc:i.desc,status:i.status,visibility:i.visibility,play_count:+i.play_count}))});})()"""

def insights_js(vid, types):
    tr = json.dumps([{'insigh_type': t, 'aweme_id': vid} for t in types])
    return ("(async()=>{const F=async(u,o)=>{for(let i=0;i<5;i++){try{return await fetch(u,o)}catch(e){if(i===4)throw e;await new Promise(r=>setTimeout(r,1500*(i+1)))}}};const j=await (await F('%s'+encodeURIComponent(%s),{credentials:'include'})).json();"
            "const o={};for(const k in j){if(j[k]!==null&&!['extra','log_pb'].includes(k))o[k]=j[k];}return JSON.stringify(o);})()") % (INSIGHT, json.dumps(tr))

REALTIME = ['video_retention_rate_realtime', 'video_per_duration_realtime', 'video_finish_rate_realtime',
            'video_view_realtime', 'video_new_follower_realtime', 'video_traffic_source_percent_realtime']
HISTORY = ['video_retention_rate_history_7d', 'video_per_duration', 'video_info']

def pull_insights(surface, vid):
    rt = ev(surface, insights_js(vid, REALTIME))
    hi = ev(surface, insights_js(vid, HISTORY))
    rl = ((rt.get('video_retention_rate_realtime') or {}).get('value') or {}).get('list') or []
    hl = (hi.get('video_retention_rate_history_7d') or {}).get('value') or []
    src, lst = ('realtime', rl) if rl else ('history_7d', hl)
    ret = [round(p['value'], 4) for p in sorted(lst, key=lambda p: int(p['timestamp']))]
    avg = ((rt.get('video_per_duration_realtime') or {}).get('value') or {}).get('value')
    if avg is None and (hi.get('video_per_duration') or {}).get('value') is not None:
        avg = hi['video_per_duration']['value'] / 1000.0      # history value is in ms
    fin = ((rt.get('video_finish_rate_realtime') or {}).get('value') or {}).get('value')
    vi = hi.get('video_info') or {}
    st = vi.get('statistics') or {}
    traffic = ((rt.get('video_traffic_source_percent_realtime') or {}).get('value')) or None
    video = vi.get('video') or {}
    urls = ((video.get('play_addr') or {}).get('url_list') or []) + ((video.get('download_addr') or {}).get('url_list') or [])
    return {
        'snap': {'date': TODAY, 'pulled_at': datetime.datetime.now().isoformat(timespec='seconds'), 'source': src,
                 'views': st.get('play_count'), 'likes': st.get('digg_count'), 'saves': st.get('collect_count'),
                 'comments': st.get('comment_count'), 'shares': st.get('share_count'),
                 'avg_watch_s': avg, 'finish_rate': fin,
                 'new_followers': ((rt.get('video_new_follower_realtime') or {}).get('value') or {}).get('value'),
                 'traffic': traffic, 'ret': ret},
        'duration_s': (video.get('duration') or 0) / 1000.0, 'desc': vi.get('desc'), 'play_urls': urls,
    }

# ---------- library ----------
def vdir(vid): return os.path.join(LIB, vid)
def load_json(p, d=None):
    try: return json.load(open(p))
    except Exception: return d
def snapshots(vid):
    p = os.path.join(vdir(vid), 'snapshots.jsonl')
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []

def save_snapshot(vid, snap):
    """One snapshot per day (re-running today replaces today's). Fields TikTok stopped
    returning (finish rate after 7 days) carry forward from the last snapshot that had them."""
    snaps = [s for s in snapshots(vid) if s['date'] != snap['date']]
    if snaps:
        last = snaps[-1]
        for k in ('finish_rate', 'avg_watch_s', 'new_followers', 'traffic'):
            if snap.get(k) is None and last.get(k) is not None:
                snap[k] = last[k]; snap.setdefault('carried', []).append(k)
        if not snap['ret'] and last.get('ret'):
            snap['ret'] = last['ret']; snap.setdefault('carried', []).append('ret')
    snaps.append(snap)
    with open(os.path.join(vdir(vid), 'snapshots.jsonl'), 'w') as f:
        for s in snaps: f.write(json.dumps(s) + '\n')
    return snaps

# ---------- processing a new video ----------
def download(vid, urls):
    out = os.path.join(vdir(vid), 'video.mp4')
    if os.path.exists(out) and os.path.getsize(out) > 100000: return out
    for u in urls:
        # https only, on the first request and on every redirect (TikTok's video links redirect between its CDN hosts).
        r = sh('curl', '-sL', '--proto', '=https', '--proto-redir', '=https', '--max-redirs', '5', '-m', '180',
               '-A', 'Mozilla/5.0', '-e', 'https://www.tiktok.com/', '-o', out, '-w', '%{http_code}', u)
        if r.stdout == '200' and os.path.getsize(out) > 100000: return out
    raise RuntimeError('download failed')

def frames(vid):
    v = os.path.join(vdir(vid), 'video.mp4')
    for name, t in (('f0', '0.05'), ('f2', '2.2')):
        sh('ffmpeg', '-loglevel', 'error', '-y', '-ss', t, '-i', v, '-frames:v', '1', '-vf', 'scale=220:-1', '-q:v', '5',
           os.path.join(vdir(vid), name + '.jpg'))
    title_strip(vid)

def title_strip(vid):
    """title_strip.jpg: the top half of the frame at 0.05 / 0.5 / 1.0 / 2.2 s, left to right, large enough to read.
    The 220 px page frames are too small to tell a grey, still-fading title from a finished one (an analyst
    misread it on 2026-10-07). If the title text or its box changes across the strip, frame 0 was unfinished."""
    v = os.path.join(vdir(vid), 'video.mp4'); d = vdir(vid); parts = []
    for i, t in enumerate(('0.05', '0.5', '1.0', '2.2')):
        p = os.path.join(d, f'_ts{i}.jpg')
        sh('ffmpeg', '-loglevel', 'error', '-y', '-ss', t, '-i', v, '-frames:v', '1', '-vf',
           'crop=iw:ih*0.5:0:0,scale=360:-1,pad=iw+8:ih:0:0:red', p)   # red bar = divider; no drawtext in this ffmpeg build
        parts.append(p)
    args = ['ffmpeg', '-loglevel', 'error', '-y']
    for p in parts: args += ['-i', p]
    sh(*args, '-filter_complex', 'hstack=4', '-q:v', '4', os.path.join(d, 'title_strip.jpg'))
    for p in parts:
        if os.path.exists(p): os.remove(p)

def transcribe(vid):
    out = os.path.join(vdir(vid), 'words.json')
    if os.path.exists(out): return
    import mlx_whisper
    r = mlx_whisper.transcribe(os.path.join(vdir(vid), 'video.mp4'), path_or_hf_repo='mlx-community/whisper-large-v3-turbo',
                               word_timestamps=True, language='en', condition_on_previous_text=False,
                               hallucination_silence_threshold=0.5)
    w = [{'w': x['word'].strip(), 's': round(x['start'], 2), 'e': round(x['end'], 2)} for s in r['segments'] for x in s.get('words', [])]
    json.dump({'text': r['text'].strip(), 'words': w}, open(out, 'w'))

GEMINI_PROMPT = """You are a short-form video retention analyst. Watch this TikTok carefully (video AND audio). Return JSON only.
ALL timestamps are plain numbers of SECONDS from the start (e.g. 67.5), never minutes:seconds.
{"first_frame":"exact description of frame 0: framing, what is on screen, on-screen text verbatim, whether text is fully visible or still animating in",
 "hook_visuals_0_to_5s":[{"t":"0-1","visual":"...","onscreen_text":"verbatim or null","motion_or_cut":"..."}],
 "cut_log":[{"t":12.5,"what_changes":"..."}],
 "layout":"...","on_screen_text_overview":"...","energy_delivery":"...",
 "payoff_visible_by":"seconds at which the viewer first SEES the promised thing, or null",
 "dead_zones":[{"start":10.0,"end":15.0,"why":"..."}]}
hook_visuals_0_to_5s has one entry per second for 0-5 s. cut_log lists every visual change for the WHOLE video and must not go past the video's length."""

# Gemini calls never follow redirects. WHY: the API key travels in the x-goog-api-key header, and requests keeps
# custom headers when it follows a redirect to another host, so a redirect could hand the key to that host.
def _post(*a, **k):
    import requests  # imported here, like the watch pass, so a run without Gemini never needs it
    return requests.post(*a, allow_redirects=False, **k)

def _get(*a, **k):
    import requests
    return requests.get(*a, allow_redirects=False, **k)

def gemini(vid, duration_s):
    out = os.path.join(vdir(vid), 'gemini.json')
    if os.path.exists(out): return 'cached'
    import requests
    # The key comes from the environment or the skill folder's .env (gitignored), never from the account folder:
    # one key serves every account. main() skips this pass when there is no key, so a missing key never fails a video.
    key = acct.env_value('GEMINI_API_KEY')
    if not key: raise RuntimeError('no GEMINI_API_KEY (set it in the environment or in the skill folder .env)')
    f = os.path.join(vdir(vid), 'video.mp4'); sz = os.path.getsize(f)
    # Every request has a timeout: on 2026-10-14 a first pull of 13 videos sat 32 minutes at 13 s of CPU on one of these
    # calls (no timeout = blocks forever). With a timeout the hang raises, is recorded in run["errors"], and the run moves
    # on; the video is retried on the next run.
    # SECURITY: the API key goes in the x-goog-api-key header, never in the URL. A requests timeout/connection error
    # prints the full URL, run["errors"] stores that text, and runs/*.json may be committed (step 09).
    H = {'x-goog-api-key': key}
    r = _post('https://generativelanguage.googleapis.com/upload/v1beta/files',
                      headers={**H, 'X-Goog-Upload-Protocol': 'resumable', 'X-Goog-Upload-Command': 'start',
                               'X-Goog-Upload-Header-Content-Length': str(sz), 'X-Goog-Upload-Header-Content-Type': 'video/mp4',
                               'Content-Type': 'application/json'}, json={'file': {'display_name': vid}}, timeout=60)
    fi = _post(r.headers['X-Goog-Upload-URL'], headers={**H, 'X-Goog-Upload-Offset': '0', 'X-Goog-Upload-Command': 'upload, finalize'},
                       data=open(f, 'rb').read(), timeout=300).json()['file']
    for _ in range(90):
        if fi['state'] == 'ACTIVE': break
        time.sleep(4); fi = _get(f"https://generativelanguage.googleapis.com/v1beta/{fi['name']}", headers=H, timeout=60).json()
    prompt = GEMINI_PROMPT + f"\nThis video is {duration_s:.1f} seconds long."
    for model in ('gemini-3.1-pro-preview', 'gemini-2.5-pro'):
        g = _post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent', headers=H,
                          json={'contents': [{'parts': [{'file_data': {'mime_type': 'video/mp4', 'file_uri': fi['uri']}}, {'text': prompt}]}],
                                'generationConfig': {'response_mime_type': 'application/json', 'temperature': 0.2}}, timeout=600).json()
        if 'candidates' in g:
            a = json.loads(g['candidates'][0]['content']['parts'][-1]['text'])
            if isinstance(a, list):                       # seen 2026-10-14: the answer is [ {...} ], not {...}
                a = next((x for x in a if isinstance(x, dict)), None)
                if a is None: raise RuntimeError('gemini returned a list with no object in it')
            a['cut_log'] = [c for c in a.get('cut_log', []) if isinstance(c.get('t'), (int, float)) and c['t'] <= duration_s + 0.5]
            json.dump({'model': model, 'analysis': a}, open(out, 'w'), indent=1)
            return model
    raise RuntimeError(f'gemini failed: {scrub(g)[:300]}')

def default_name(vid):
    w = load_json(os.path.join(vdir(vid), 'words.json'), {}).get('text', '')
    first = re.split(r'(?<=[.!?])\s', w.strip())[0] if w else ''
    words = first.split()
    return (' '.join(words[:7]) + ('…' if len(words) > 7 else '')).strip() or vid

def per_second_md(vid, meta, snap, median):
    W = load_json(os.path.join(vdir(vid), 'words.json'), {}).get('words', [])
    G = (load_json(os.path.join(vdir(vid), 'gemini.json'), {}) or {}).get('analysis', {})
    ev_ = {}
    for c in G.get('cut_log', []):
        ev_.setdefault(int(math.floor(c['t'])), []).append(c['what_changes'])
    R = snap['ret']
    L = [f"\n## {meta['name']}  ·  {vid}",
         f"posted {meta['posted']} · {snap['views']} views · {meta['duration_s']:.0f} s · avg watch {snap['avg_watch_s']} s · finished {fmt_pct(snap['finish_rate'])} · saves {snap['saves']} · source {snap['source']}",
         f"First frame (Gemini): {G.get('first_frame')}",
         "| s | kept | lost next s | account median | words | screen changes |", "|---|---|---|---|---|---|"]
    for t, r in enumerate(R):
        nxt = R[t + 1] if t + 1 < len(R) else r
        words = ' '.join(w['w'] for w in W if t <= w['s'] < t + 1)
        med = f"{median[t] * 100:.0f}%" if t < len(median) and median[t] is not None else ''
        L.append(f"| {t} | {r * 100:.0f}% | {(r - nxt) * 100:.0f} | {med} | {words} | {' · '.join(ev_.get(t, []))} |")
    return '\n'.join(L)

def fmt_pct(x): return '-' if x is None else f'{x * 100:.1f}%'

def account_median(ids):
    # settled videos only (48+ h old at their last snapshot), matching build_report.py
    def settled(i):
        m = load_json(os.path.join(vdir(i), 'meta.json'), {}) or {}; s = snapshots(i)
        if not s or not s[-1]['ret'] or not m.get('create_time'): return False
        return (datetime.datetime.fromisoformat(s[-1]['pulled_at']) - datetime.datetime.fromtimestamp(m['create_time'])).total_seconds() >= 48 * 3600
    keep = [i for i in ids if settled(i)]
    curves = [snapshots(i)[-1]['ret'] for i in (keep if len(keep) >= 3 else ids) if snapshots(i) and snapshots(i)[-1]['ret']]
    n = max((len(c) for c in curves), default=0)
    med = []
    for t in range(n):
        vals = [c[t] for c in curves if t < len(c)]
        med.append(statistics.median(vals) if len(vals) >= 3 else None)
    return med

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--surface'); ap.add_argument('--skip-gemini', action='store_true')
    ap.add_argument('--account'); ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    configure(acct.load(a.account))
    if not a.check:
        acct.use_venv()          # mlx-whisper and requests live in claude-retention-teardown/.venv (see account.use_venv)
    # Gemini is optional. Without a key the run skips the watch pass for every video and says so; the per-second
    # table then has no "screen changes" column content. Adding a key later backfills it on the next run.
    no_key = not a.skip_gemini and not a.check and not acct.env_value('GEMINI_API_KEY')
    if no_key: a.skip_gemini = True

    surface = a.surface or find_surface(ACCT['handle']) or open_surface(ACCT['profile'])
    # A tab left open overnight (Mac asleep) can answer every fetch with "Load failed" until it is
    # reloaded, and needs a few seconds after load before Studio's requests work again (2026-10-07).
    L = None
    for attempt in range(3):
        try:
            L = ev(surface, LIST_JS); break
        except RuntimeError as e:
            print(f'list attempt {attempt + 1} failed ({str(e)[:80]}); reloading {surface}', file=sys.stderr)
            sh('cmux', 'browser', surface, 'navigate', STUDIO) if attempt else sh('cmux', 'browser', surface, 'reload')
            sh('cmux', 'browser', surface, 'wait', '--load-state', 'complete', '--timeout', '30')
            time.sleep(6 + 4 * attempt)
    if L is None:
        sys.exit(f'TikTok Studio in {surface} would not answer after 3 reloads. Check the tab, then re-run.')
    if not L.get('ok'):
        print(f'NOT_SIGNED_IN {surface} (status {L.get("status")}: {L.get("msg")}) - sign in as @{ACCT["handle"]}'
              f' inside cmux browser profile "{ACCT["profile"]}"')
        sh('cmux', 'browser', surface, 'navigate', STUDIO)
        sys.exit(3)

    # Signed in is not enough: it must be THIS account. Checked before anything is written, because a wrong-account
    # run would silently put another account's videos into this account's library and page.
    who = handle_of(surface)
    if not who or who.lower() != ACCT['handle'].lower():
        print(f'WRONG_ACCOUNT {surface} is signed in as {"@" + who if who else "an account I could not read"}, but account '
              f'"{ACCT["name"]}" is @{ACCT["handle"]}. Nothing was written. Sign in as @{ACCT["handle"]} in this tab, then re-run.')
        sys.exit(4)
    if a.check:
        n_pub = sum(1 for i in L['items'] if i['status'] == 102 and i['visibility'] == 1)
        in_win = n_pub
        if ACCT.get('since'):
            cut = datetime.datetime.strptime(ACCT['since'], '%Y-%m-%d').timestamp()
            in_win = sum(1 for i in L['items'] if i['status'] == 102 and i['visibility'] == 1 and i['create_time'] >= cut)
        print(f'OK account "{ACCT["name"]}" @{who} is signed in on {surface}: {n_pub} public posts, {len(L["items"]) - n_pub} private or under review'
              + (f'; {in_win} posted since {ACCT["since"]} (the tracked window)' if ACCT.get('since') else '') + '. Nothing was written.')
        sys.exit(0)
    os.makedirs(LIB, exist_ok=True); os.makedirs(RUNS, exist_ok=True)

    run = {'date': TODAY, 'account': ACCT['name'], 'surface': surface, 'new': [], 'refreshed': [], 'pending': [], 'skipped': [], 'errors': []}
    if no_key: run['gemini'] = 'skipped: no GEMINI_API_KEY set, so no watch notes this run'
    elif a.skip_gemini: run['gemini'] = 'skipped: --skip-gemini'

    public = [i for i in L['items'] if i['status'] == 102 and i['visibility'] == 1]
    # Window: posts older than account.json's `since` are not tracked (counted, not listed as skipped, so a back
    # catalog of dozens of posts does not flood the run summary). Posts already in the library stay tracked.
    n_before_window = 0
    non_public = [i for i in L['items'] if i not in public]    # taken BEFORE the window filter below
    if ACCT.get('since'):
        cut = datetime.datetime.strptime(ACCT['since'], '%Y-%m-%d').timestamp()
        keep = [i for i in public if i['create_time'] >= cut or os.path.exists(os.path.join(vdir(i['id']), 'meta.json'))]
        n_before_window = len(public) - len(keep); public = keep
    run['before_window'] = n_before_window
    run['skipped'] = [{'id': i['id'], 'status': i['status'], 'visibility': i['visibility'], 'desc': (i['desc'] or '')[:60]}
                      for i in non_public]

    for it in sorted(public, key=lambda i: i['create_time']):
        vid = it['id']; os.makedirs(vdir(vid), exist_ok=True)
        meta_p = os.path.join(vdir(vid), 'meta.json')
        meta = load_json(meta_p, {}) or {}
        try:
            d = pull_insights(surface, vid)
        except Exception as e:
            run['errors'].append({'id': vid, 'step': 'insights', 'error': scrub(e)[:300]}); continue
        meta.update({'id': vid, 'desc': it['desc'], 'create_time': it['create_time'],
                     'posted': datetime.datetime.fromtimestamp(it['create_time']).strftime('%Y-%m-%d %H:%M'),
                     'duration_s': d['duration_s'] or meta.get('duration_s', 0),
                     'url': f'https://www.tiktok.com/@{ACCT["handle"]}/video/{vid}'})
        meta.setdefault('first_seen', TODAY)
        if not d['snap']['ret'] and not snapshots(vid):
            run['pending'].append({'id': vid, 'why': 'no retention curve yet (TikTok fills it in a few hours after posting)'})
            json.dump(meta, open(meta_p, 'w'), indent=1); continue
        snaps = save_snapshot(vid, d['snap'])
        if meta.get('analyzed') and not a.skip_gemini and not os.path.exists(os.path.join(vdir(vid), 'gemini.json')):
            try:
                meta['gemini'] = gemini(vid, meta['duration_s']); run.setdefault('gemini_backfilled', []).append(vid)
            except Exception as e:
                run['errors'].append({'id': vid, 'step': 'gemini backfill', 'error': scrub(e)[:300]})
        if meta.get('analyzed'):
            prev = snaps[-2] if len(snaps) > 1 else None
            run['refreshed'].append({'id': vid, 'views': d['snap']['views'], 'views_prev': prev and prev['views'],
                                     'p3': d['snap']['ret'][3] if len(d['snap']['ret']) > 3 else None,
                                     'p3_prev': prev and len(prev['ret']) > 3 and prev['ret'][3]})
        else:
            try:
                download(vid, d['play_urls']); frames(vid); transcribe(vid)
                g = 'skipped' if a.skip_gemini else gemini(vid, meta['duration_s'])
                meta['analyzed'] = TODAY; meta.setdefault('name', default_name(vid)); meta['gemini'] = g
                run['new'].append({'id': vid, 'name': meta['name'], 'views': d['snap']['views']})
            except Exception as e:
                run['errors'].append({'id': vid, 'step': 'process', 'error': scrub(e)[:300]})
        json.dump(meta, open(meta_p, 'w'), indent=1)

    ids = [m for m in os.listdir(LIB) if (load_json(os.path.join(LIB, m, 'meta.json'), {}) or {}).get('analyzed')]
    med = account_median(ids)
    md = [f'# New videos analyzed {TODAY}\n', 'Columns: kept = % still watching at that second; lost next s = points lost during the next second; account median = median of settled (48+ h old) videos at that second.']
    for n in run['new']:
        md.append(per_second_md(n['id'], load_json(os.path.join(vdir(n['id']), 'meta.json')), snapshots(n['id'])[-1], med))
    open(os.path.join(RUNS, f'{TODAY}-new.md'), 'w').write('\n'.join(md))
    json.dump(run, open(os.path.join(RUNS, f'{TODAY}.json'), 'w'), indent=1)
    print(json.dumps({k: (v if k in ('date', 'account', 'surface', 'before_window', 'gemini') else len(v)) for k, v in run.items()}))
    if no_key: print('NO_GEMINI no GEMINI_API_KEY set: the watch notes (screen changes) were skipped. Add the key to the skill folder .env to get them; the next run backfills.')
    for k in ('new', 'pending', 'skipped', 'errors'):
        for x in run[k]: print(k.upper(), json.dumps(x)[:200])
    for x in run['refreshed']:
        print('REFRESHED', x['id'], f"views {x['views_prev']}→{x['views']}", f"3s {x['p3_prev']}→{x['p3']}")

if __name__ == '__main__':
    main()
