#!/usr/bin/env python3
"""Collect Instagram Reel retention insights for ONE account (run by /retention-teardown-instagram, step 01).

Usage:
  python3 ~/.claude/skills/instagram-retention-teardown/scraping/collect.py --account <alias|@handle|all> [--reel <url|shortcode>]...
                                       [--check] [--skip-gemini] [--max N] [--all-reels]

  --account all   each eligible account in turn, each in its own process; one account's failure never stops the rest
  --reel X        only this Reel (repeatable). An account without an official token has no Reel list: name its Reels
                  here once and later runs keep refreshing them (account.json "reels").
  --skip-gemini   skip the Gemini watch pass (a later run backfills it). Automatic when no GEMINI_API_KEY is set.
  --check         identity only: who is signed in, pin web_pk on the first verified sign-in. Writes nothing else.
  --max N         at most N insights requests this run (default 20). Requests are 10-20 s apart, one at a time.
  --all-reels     also refresh tracked Reels older than 30 days (normally weekly)

Exit codes (the step file tells the analyst what to do with each):
  0 OK · 2 usage, config or cmux failure · 3 NOT_SIGNED_IN · 4 WRONG_ACCOUNT · 5 NOT_OWNED · 6 PAUSED (challenge / rate limit / action
  block, or an earlier pause still active) · 7 FORMAT_CHANGED · 9 another run of this account is in progress

The order of the gates is the safety design:
  lock -> pause -> own surface (--profile ig-<alias>) -> IDENTITY before any write -> official token identity ->
  OWNERSHIP before any insights request -> one request -> stop signals -> save raw + capture -> next Reel.
Nothing is ever written into another account's folder: every path comes from the alias AFTER the identity gate.
"""
import argparse, datetime, fcntl, json, math, os, random, re, statistics, subprocess, sys, time

import account, ig_parse as P, media, net, official

HERE = os.path.dirname(os.path.realpath(__file__))
TODAY = datetime.date.today().isoformat()
NOW = lambda: datetime.datetime.now(datetime.timezone.utc)
SETTLED_H = 48          # same rule as the TikTok skill: aggregates and the median use Reels 48+ h old
GAP_S = (10, 20)        # seconds between insights requests: the pace of a person opening insights, not a crawler
REFRESH_DAYS = 30       # Reels younger than this are refreshed every run; older ones weekly (or with --all-reels)
IN_PAGE_HOSTS = ['www.instagram.com (page, identity)', 'i.instagram.com (insights)']

class Stop(Exception):
    def __init__(self, code, msg): super().__init__(msg); self.code = code; self.msg = msg

def sh(*a, **k): return subprocess.run(list(a), capture_output=True, text=True, **k)

# ---------- cmux ----------
def open_surface(profile):
    """Always a NEW surface in the account's own profile. Never reuse an existing instagram.com tab: the cmux CLI cannot
    tell which profile a tab belongs to (verified 2026-10-14), so a reused tab could belong to another account."""
    args = ['cmux', '--json', 'browser', 'open', 'https://www.instagram.com/', '--profile', profile, '--focus', 'false']
    if os.environ.get('CMUX_WORKSPACE_ID'): args += ['--workspace', os.environ['CMUX_WORKSPACE_ID']]
    r = sh(*args)
    try: s = json.loads(r.stdout)['surface_ref']
    except Exception: raise Stop(2, f'could not open a cmux browser in profile {profile}: {r.stdout[:200]} {r.stderr[:200]}')
    sh('cmux', 'browser', s, 'wait', '--load-state', 'complete', '--timeout', '30')
    time.sleep(3)
    return s

def close_surface(s):
    if s: sh('cmux', 'close-surface', '--surface', s)

def ev(surface, js):
    r = sh('cmux', 'browser', surface, 'eval', '--script', js, timeout=180)
    try: return json.loads(r.stdout.strip())
    # A cmux failure is a tool problem (exit 2), not an Instagram format change (exit 7): the analyst must not go
    # looking for new Instagram ids when the browser surface simply did not answer.
    except Exception: raise Stop(2, f'cmux eval failed on {surface}: {r.stdout[:200]} {r.stderr[:200]}')

def ds_cookie(surface):
    """The signed-in user's numeric id. The ONLY cookie this tool reads; sessionid/csrftoken are never read."""
    r = sh('cmux', '--json', 'browser', surface, 'cookies', 'get', '--domain', '.instagram.com', '--name', 'ds_user_id')
    try:
        d = json.loads(r.stdout or '{}'); cs = d.get('cookies', d if isinstance(d, list) else [])
        return next((c['value'] for c in cs if c.get('name') == 'ds_user_id' and c.get('value')), None)
    except Exception: return None

# ---------- pause (per account) ----------
def pause_path(a): return os.path.join(a['root'], 'state', 'pause.json')

def check_pause(a):
    p = pause_path(a)
    if not os.path.exists(p): return
    x = json.load(open(p))
    if x.get('until') and datetime.datetime.fromisoformat(x['until']) <= NOW(): os.remove(p); return
    raise Stop(6, f'PAUSED since {x["at"]}: {x["reason"]} ({x.get("detail", "")[:120]}). '
                  + (f'Clears itself at {x["until"]}.' if x.get('until') else
                     f'The user must clear Instagram\'s prompt in the ig-{a["alias"]} profile, then: account.py unpause {a["alias"]}'))

def set_pause(a, kind, detail):
    # A challenge never clears itself: only the user can answer it. Rate limits and action blocks get 24 h, deliberately
    # long: this runs daily, so waiting a day costs nothing, and pushing could escalate.
    until = None if kind == 'challenge' else (NOW() + datetime.timedelta(hours=24)).isoformat(timespec='seconds')
    json.dump({'reason': kind, 'at': NOW().isoformat(timespec='seconds'), 'until': until, 'detail': net.scrub(detail)[:300]},
              open(pause_path(a), 'w'), indent=1)

def stop_on_signal(a, sig):
    kind, detail = sig
    if kind == 'logged_out': raise Stop(3, f'NOT_SIGNED_IN: Instagram answered as logged out ({net.scrub(detail)[:100]})')
    set_pause(a, kind, detail)
    raise Stop(6, f'PAUSED: Instagram sent a {kind} signal; collection for @{a["handle"]} stopped, no retry. {net.scrub(detail)[:150]}')

# ---------- identity gate ----------
def identity(a, surface, pin=False):
    """Prove which account this tab is signed in as, from the session itself. Raises Stop(3|4|6). Returns the pk."""
    ds = ds_cookie(surface)
    if not ds: raise Stop(3, f'NOT_SIGNED_IN: profile {a["profile"]} has no Instagram session')
    who = ev(surface, open(os.path.join(HERE, 'identity.js')).read())
    if who.get('signal'): stop_on_signal(a, ('challenge' if who['signal'].get('checkpoint') else 'rate_limit', who['signal'].get('message', '')))
    if who.get('status') == 429: stop_on_signal(a, ('rate_limit', 'identity endpoint answered 429'))
    if not who.get('json'):
        raise Stop(3, f'NOT_SIGNED_IN (identity answer was not JSON, status {who.get("status")}: {who.get("prefix") or who.get("error")})')
    if (who.get('username') or '').lower() != a['handle'].lower():
        raise Stop(4, f'WRONG_ACCOUNT: profile {a["profile"]} is signed in as @{who.get("username")}, but account "{a["alias"]}" is @{a["handle"]}. Nothing was written.')
    if who.get('ds_page') != ds:
        raise Stop(4, f'WRONG_ACCOUNT: the page and cmux disagree on ds_user_id ({who.get("ds_page")} vs {ds}). Nothing was written.')
    if a.get('web_pk') and ds != a['web_pk']:
        raise Stop(4, f'WRONG_ACCOUNT: ds_user_id {ds} is not the pinned id {a["web_pk"]} for @{a["handle"]}. Nothing was written.')
    if not a.get('web_pk') and pin:
        account.save_field(a['alias'], 'web_pk', ds); a['web_pk'] = ds
    return ds

def token_identity(a, tok):
    """For token accounts the official token must belong to the same account (a mis-pasted token would mix sources)."""
    m = official.me(tok)
    if m.get('username', '').lower() != a['handle'].lower() or (a.get('graph_user_id') and str(m.get('user_id')) != a['graph_user_id']):
        raise Stop(4, f'WRONG_ACCOUNT: the official token in {a["token_env"]} belongs to @{m.get("username")} ({m.get("user_id")}), not @{a["handle"]}')
    return m

# ---------- library ----------
def rdir(a, sc): return os.path.join(a['root'], 'library', sc)
def load_json(p, d=None):
    try: return json.load(open(p))
    except Exception: return d
def captures(a, sc):
    p = os.path.join(rdir(a, sc), 'captures.jsonl')
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []

def capture(a, surface, sc, tok, official_id):
    """One insights request for one Reel; saves raw + one capture line. Returns (record, signed video_url or None)."""
    igid = P.media_igid(sc)
    res = ev(surface, open(os.path.join(HERE, 'insights.js')).read().replace('__MEDIA_IGID__', igid))
    if not res.get('ok'): return {'status': 'error', 'error': f'transport: {res.get("error")}'}, None
    status, text = res['status'], res['text']
    try:
        parts = P.split_stream(text)
    except P.FormatChanged as e:
        sig = P.signal(status, text)
        if sig: stop_on_signal(a, sig)
        diag = os.path.join(a['root'], 'state', f'format-{NOW().strftime("%Y%m%dT%H%M%SZ")}.txt')
        open(diag, 'w').write(net.scrub(text[:20000]))
        raise Stop(7, f'FORMAT_CHANGED on {sc}: {e}. Answer kept in {diag} (state/, gitignored).')
    sig = P.signal(status, parts)
    if sig: stop_on_signal(a, sig)
    data, meta = P.merge(parts)
    captured_at = NOW()
    d = rdir(a, sc); os.makedirs(os.path.join(d, 'raw'), exist_ok=True)
    stamp = captured_at.strftime('%Y-%m-%dT%H-%M-%SZ')
    base = {'captured_at': captured_at.isoformat(timespec='seconds'), 'local_date': TODAY, 'account': a['alias'], 'handle': a['handle'],
            'web_pk': a['web_pk'], 'shortcode': sc, 'media_igid': igid, 'url': f'https://www.instagram.com/reel/{sc}/',
            **P.METHOD, 'collector': P.COLLECTOR_VERSION, 'http_status': status}
    raw_rel = f'raw/{stamp}.json'
    # Raw is written FIRST and never overwritten (one file per capture, second-resolution UTC name).
    json.dump({**base, 'parts': P.scrub_signed_urls(parts)}, open(os.path.join(d, raw_rel), 'x'), indent=1)
    if data is None:
        # Instagram answered, but with no insights object. With errors this is "not yours / not available"; without
        # errors it is an unknown shape.
        if meta['errors']:
            rec = {**base, 'raw_file': raw_rel, 'status': 'not_available', 'errors': net.scrub(json.dumps(meta['errors']))[:400]}
            open(os.path.join(d, 'captures.jsonl'), 'a').write(json.dumps(rec) + '\n')
            return rec, None
        raise Stop(7, f'FORMAT_CHANGED on {sc}: no ig_reel_insights object and no errors (raw kept: {raw_rel})')
    if not meta['is_final'] or meta['unknown_paths']:
        raise Stop(7, f'FORMAT_CHANGED on {sc}: is_final={meta["is_final"]}, unknown paths {meta["unknown_paths"][:2]} (raw kept: {raw_rel})')
    try: norm = P.normalize(data)
    except P.FormatChanged as e: raise Stop(7, f'FORMAT_CHANGED on {sc}: {e} (raw kept: {raw_rel})')
    ref, val = None, {}
    if tok and official_id:
        try:
            ref = official.reference(tok, official_id)
            if ref.get('views') and norm.get('views') is not None: val['views_delta_pct'] = round((norm['views'] - ref['views']) / ref['views'] * 100, 2)
            if ref.get('avg_watch_s') and norm.get('avg_watch_s') is not None: val['avg_watch_delta_pct'] = round((norm['avg_watch_s'] - ref['avg_watch_s']) / ref['avg_watch_s'] * 100, 2)
            if ref.get('skip_rate_pct') is not None and norm.get('skip_rate_pct') is not None: val['skip_delta_pts'] = round(norm['skip_rate_pct'] - ref['skip_rate_pct'], 2)
            # Tolerances from the build-time check against the phone app (all were exact; views can move by minutes of new
            # plays between the two reads).
            if abs(val.get('views_delta_pct', 0)) > 3 or abs(val.get('avg_watch_delta_pct', 0)) > 5 or abs(val.get('skip_delta_pts', 0)) > 1:
                norm['flags'].append('official_mismatch')
        except official.OfficialError as e:
            val['official_error'] = str(e)[:200]
    else:
        val['official'] = 'no token for this account: no independent cross-check'
    status_ = 'ok' if norm['retention'] else 'no_retention'
    rec = {**base, 'raw_file': raw_rel, 'status': status_, 'n_parts': meta['n_parts'], **norm, 'official': ref, 'validation': val}
    open(os.path.join(d, 'captures.jsonl'), 'a').write(json.dumps(rec) + '\n')
    return rec, (P.strip1f(data).get('video_url') if isinstance(data, dict) else None)

# ---------- analyst tables ----------
def latest_curves(a):
    out = {}
    lib = os.path.join(a['root'], 'library')
    for sc in os.listdir(lib) if os.path.isdir(lib) else []:
        m = load_json(os.path.join(lib, sc, 'meta.json'), {}) or {}
        caps = [c for c in captures(a, sc) if c.get('status') == 'ok' and (c.get('retention') or {}).get('per_second')]
        if m.get('analyzed') and caps: out[sc] = (m, caps[-1])
    return out

def is_settled(m, c):
    if not m.get('created_ts'): return False
    return (datetime.datetime.fromisoformat(c['captured_at']).timestamp() - m['created_ts']) >= SETTLED_H * 3600

def account_median(a):
    cur = latest_curves(a)
    keep = [(m, c) for m, c in cur.values() if is_settled(m, c)]
    use = keep if len(keep) >= 3 else list(cur.values())
    curves = [[v for _, v in c['retention']['points']] for _, c in use]
    n = max((len(c) for c in curves), default=0); med = []
    for t in range(n):
        vals = [c[t] for c in curves if t < len(c)]
        med.append(statistics.median(vals) if len(vals) >= 3 else None)
    return med

def per_second_md(a, sc, m, c, med):
    W = (load_json(os.path.join(rdir(a, sc), 'words.json'), {}) or {}).get('words', [])
    G = ((load_json(os.path.join(rdir(a, sc), 'gemini.json'), {}) or {}).get('analysis')) or {}
    evs = {}
    for x in G.get('cut_log', []):
        if isinstance(x.get('t'), (int, float)): evs.setdefault(int(math.floor(x['t'])), []).append(x.get('what_changes', ''))
    likes = {int(s): n for s, n in (c.get('like_timing') or [])}
    pts = c['retention']['points']
    L = [f"\n## {m.get('name') or sc}  ·  {sc}",
         f"posted {m.get('posted')} · {c.get('views')} views · {m.get('duration_s')} s · avg watch {c.get('avg_watch_s')} s · skip rate {c.get('skip_rate_pct')}% · "
         f"follows {c.get('follows')} · saves {c.get('saves')} · non-follower views {c.get('non_followers_views')} of {c.get('views')}",
         f"View sources: {', '.join(f'{l} {v * 100:.1f}%' for l, v in (c.get('view_sources') or []))}",
         f"First frame (Gemini, approximate): {G.get('first_frame')}",
         "| s | kept | lost next s | account median | likes in this s | words | screen changes |", "|---|---|---|---|---|---|---|"]
    for i, (t, v) in enumerate(pts):
        nxt = pts[i + 1][1] if i + 1 < len(pts) else v
        ti = int(t); words = ' '.join(w['w'] for w in W if ti <= w['s'] < ti + 1)
        md = f"{med[ti] * 100:.0f}%" if ti < len(med) and med[ti] is not None else ''
        L.append(f"| {ti} | {v * 100:.1f}% | {(v - nxt) * 100:.1f} | {md} | {likes.get(ti, '')} | {words} | {' · '.join(evs.get(ti, []))} |")
    return '\n'.join(L)

# ---------- main ----------
def collect(a, args):
    run = {'date': TODAY, 'started_at': NOW().isoformat(timespec='seconds'), 'account': a['alias'], 'handle': a['handle'],
           'profile': a['profile'], 'surface': None, 'new': [], 'refreshed': [], 'pending': [], 'no_retention': [], 'not_available': [],
           'skipped': [], 'errors': [], 'stopped': None, 'requests': 0}
    os.makedirs(os.path.join(a['root'], 'runs'), exist_ok=True); os.makedirs(os.path.join(a['root'], 'library'), exist_ok=True)
    surface = None; code = 0
    hhmmss = datetime.datetime.now().strftime('%H%M%S')
    rp = os.path.join(a['root'], 'runs', f'{TODAY}.json')
    np_ = os.path.join(a['root'], 'runs', f'{TODAY}-new.md')
    rotated = []    # non-empty once an earlier same-day run file has been moved aside by THIS run

    # INCREMENTAL WRITES (found in review when this was built): a run takes ~75 s per new Reel and can be killed
    # (a 10-minute tool timeout, a closed laptop). meta.json marks a Reel "analyzed" as soon as it is done, so if the run
    # file and the per-second tables were only written at the end, a killed run lost those tables for good: the next run
    # sees the Reels as already analyzed. So both are written after EVERY Reel.
    def write_run():
        if not rotated:
            if os.path.exists(rp):   # keep an earlier same-day run instead of overwriting it
                os.rename(rp, os.path.join(a['root'], 'runs', f'{TODAY}-{hhmmss}-earlier.json'))
            rotated.append(True)
        run['updated_at'] = NOW().isoformat(timespec='seconds')
        run['hosts'] = IN_PAGE_HOSTS + [f'{h}{p}' for h, p in net.CONTACTED]
        json.dump(run, open(rp, 'w'), indent=1)

    def append_new_md(n):
        # APPEND-ONLY: never rewrite this file (step 02 reads every section written today, from every run).
        existed = os.path.exists(np_)
        md = [] if existed else [
            f'# New Reels analyzed {TODAY} · @{a["handle"]}\n',
            'Columns: kept = share still watching at that second (measured, Instagram rounds down in the app); '
            'lost next s = points lost during the next second; account median = median of settled (48+ h) Reels at that second; '
            'likes in this s = likes given at that second of the Reel.']
        cur = latest_curves(a)
        if n['id'] in cur: md.append(per_second_md(a, n['id'], *cur[n['id']], account_median(a)))
        else: md.append(f"\n## {n['name']} · {n['id']}\nNo retention curve in Instagram's answer; analyze only the other metrics.")
        with open(np_, 'a') as f: f.write(('\n' if existed else '') + '\n'.join(md))

    try:
        check_pause(a)
        surface = open_surface(a['profile']); run['surface'] = surface
        identity(a, surface, pin=True)
        tok = account.token(a)
        if tok: token_identity(a, tok)
        if args.check:
            print(f'OK {a["alias"]} @{a["handle"]} signed in on {surface} (profile {a["profile"]}), ds_user_id {a["web_pk"]}'
                  + ('; official token matches' if tok else '; no official token') + '. Nothing else was written.')
            return 0
        # ----- which Reels -----
        wanted = [P.shortcode_from(x) for x in (args.reel or [])]
        explicit = bool(wanted)    # named on the command line; a no-token account's tracked list follows the daily refresh rules
        own = {}
        if tok:
            for r in official.reels(tok, None if wanted else a.get('since')): own[r['shortcode']] = r
        elif not wanted:
            # No token = no official Reel list. Such an account tracks the Reels named in account.json "reels" (shortcodes
            # added by hand or by a --reel run). With none, it is a clean "nothing to collect", not a failure, so the daily
            # `--account all` does not report a token-less account as broken every day (its new Reels are never
            # discovered automatically).
            wanted = list(a.get('reels') or [])
            if not wanted:
                print(f'NOTHING_TO_COLLECT @{a["handle"]}: no official token and no tracked Reels in account.json "reels". '
                      f'Run with --reel <url> to add one.')
                return 0
        if wanted and tok:
            stranger = [sc for sc in wanted if sc not in own]
            if stranger: raise Stop(5, f'NOT_OWNED: {", ".join(stranger)} is not in @{a["handle"]}\'s own Reel list. No insights request was sent.')
        todo = wanted or list(own)
        if not tok and args.reel:
            # Remember Reels named for a no-token account so later daily runs refresh them (see the no-token branch above).
            known = list(a.get('reels') or [])
            add = [sc for sc in wanted if sc not in known]
            if add: account.save_field(a['alias'], 'reels', known + add); a['reels'] = known + add
        def priority(sc):
            caps = captures(a, sc)
            if not caps: return (0, 0)
            last = datetime.datetime.fromisoformat(caps[-1]['captured_at'])
            age_d = (NOW().timestamp() - (own.get(sc, {}).get('created_ts') or 0)) / 86400
            if not explicit and not args.all_reels and age_d > REFRESH_DAYS and (NOW() - last).days < 7: return None   # old + recently seen
            if (NOW() - last).total_seconds() < 3600: return None if not explicit else (1, last.timestamp())          # captured within the hour
            return (1, last.timestamp())
        queue = sorted([sc for sc in todo if priority(sc) is not None], key=priority)
        run['skipped'] = [sc for sc in todo if priority(sc) is None]
        for i, sc in enumerate(queue):
            if run['requests'] >= args.max:
                run['skipped'] += queue[i:]; break
            if run['requests']: time.sleep(random.uniform(*GAP_S))
            d = rdir(a, sc); os.makedirs(d, exist_ok=True)
            mp = os.path.join(d, 'meta.json'); m = load_json(mp, {}) or {}
            run['requests'] += 1
            rec, video_url = capture(a, surface, sc, tok, own.get(sc, {}).get('id'))
            if rec['status'] == 'error':
                run['errors'].append({'id': sc, 'step': 'insights', 'error': net.scrub(rec['error'])[:300]}); write_run(); continue
            if rec['status'] == 'not_available':
                run['not_available'].append({'id': sc, 'why': rec.get('errors')}); write_run(); continue
            o = own.get(sc, {})
            created = o.get('created_ts') or rec.get('media_created_at')
            m.update({'shortcode': sc, 'media_igid': rec['media_igid'], 'official_media_id': o.get('id') or m.get('official_media_id'),
                      'url': o.get('permalink') or rec['url'], 'created_ts': created,
                      'posted': datetime.datetime.fromtimestamp(created).strftime('%Y-%m-%d %H:%M') if created else m.get('posted'),
                      'caption': o.get('caption', m.get('caption'))})
            m.setdefault('first_seen', TODAY)
            age_h = (NOW().timestamp() - created) / 3600 if created else None
            if rec['status'] == 'no_retention':
                (run['pending'] if (age_h is not None and age_h < SETTLED_H) else run['no_retention']).append(
                    {'id': sc, 'age_h': round(age_h) if age_h else None, 'missing': rec['missing']})
            if m.get('analyzed'):
                prev = [c for c in captures(a, sc) if c.get('status') == 'ok'][-2:-1]
                p3 = lambda c: P.at(c['retention']['points'], 3) if c and c.get('retention') else None
                run['refreshed'].append({'id': sc, 'views': rec.get('views'), 'views_prev': prev[0].get('views') if prev else None,
                                         'p3': p3(rec), 'p3_prev': p3(prev[0]) if prev else None})
            elif rec['status'] == 'ok' or (rec['status'] == 'no_retention' and age_h is not None and age_h >= SETTLED_H):
                try:
                    urls = []
                    if tok and m.get('official_media_id'): urls.append(official.media_url(tok, m['official_media_id']))
                    urls.append(video_url)
                    media.download(d, urls); m['duration_s'] = media.duration(d); media.frames(d); media.transcribe(d)
                    m['gemini'] = 'skipped' if args.skip_gemini else media.gemini(d, m['duration_s'])
                    m['analyzed'] = TODAY
                    w = (load_json(os.path.join(d, 'words.json'), {}) or {}).get('text', '')
                    first = (re.split(r'(?<=[.!?])\s', w.strip())[0] if w else '').split()
                    m.setdefault('name', (' '.join(first[:7]) + ('…' if len(first) > 7 else '')) or sc)
                    run['new'].append({'id': sc, 'name': m['name'], 'views': rec.get('views'), 'curve': rec['status'] == 'ok'})
                except Exception as e:
                    run['errors'].append({'id': sc, 'step': 'process', 'error': net.scrub(e)[:300]})
            # A Reel analyzed earlier with --skip-gemini (or whose Gemini call failed) gets its watch pass on a later run.
            if m.get('analyzed') and m.get('gemini') == 'skipped' and not args.skip_gemini and os.path.exists(os.path.join(d, 'video.mp4')):
                try: m['gemini'] = media.gemini(d, m.get('duration_s'))
                except Exception as e: run['errors'].append({'id': sc, 'step': 'gemini backfill', 'error': net.scrub(e)[:300]})
            json.dump(m, open(mp, 'w'), indent=1)       # saved after EVERY Reel: a later failure cannot erase this one
            if run['new'] and run['new'][-1]['id'] == sc: append_new_md(run['new'][-1])
            write_run()
    except Stop as e:
        run['stopped'] = {'code': e.code, 'reason': net.scrub(e.msg)}; code = e.code
        if e.code == 3 and surface:
            sh('cmux', 'browser', surface, 'navigate', 'https://www.instagram.com/accounts/login/')
            account.label_tab(surface, a)    # never leave an unlabeled sign-in tab (see account.label_tab)
    finally:
        run['finished_at'] = NOW().isoformat(timespec='seconds')
        run['hosts'] = IN_PAGE_HOSTS + [f'{h}{p}' for h, p in net.CONTACTED]
        if not args.check and (run['requests'] or run['stopped']):
            if not run['requests']:
                # Stopped before asking Instagram anything (wrong account, not owned, paused...): record it on its own so
                # it never displaces the day's real run file, which step 01 reads (bug found in acceptance, 2026-10-14).
                json.dump(run, open(os.path.join(a['root'], 'runs', f'{TODAY}-{hhmmss}-stopped.json'), 'w'), indent=1)
            else:
                write_run()    # final state (finished_at, stopped, hosts); per-Reel tables were already appended as they finished
        if code != 3: close_surface(surface)
    if not args.check or code:
        summary = {k: (v if k in ('date', 'account', 'surface', 'requests', 'stopped') else len(v)) for k, v in run.items() if k not in ('started_at', 'finished_at', 'updated_at', 'hosts', 'handle', 'profile')}
        print(json.dumps(summary))
        for k in ('new', 'pending', 'no_retention', 'not_available', 'skipped', 'errors'):
            for x in run[k]: print(k.upper(), json.dumps(x)[:220])
        for x in run['refreshed']: print('REFRESHED', x['id'], f"views {x['views_prev']}→{x['views']}", f"3s {x['p3_prev']}→{x['p3']}")
        if run['stopped']: print('STOPPED', run['stopped']['code'], run['stopped']['reason'])
    return code

def lock(a):
    os.makedirs(os.path.join(a['root'], 'state'), exist_ok=True)
    f = open(os.path.join(a['root'], 'state', 'collect.lock'), 'w')
    try: fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError: print(f'BUSY: another collect run for "{a["alias"]}" holds the lock'); sys.exit(9)
    return f

def check_cli(name):
    """account.py check <alias|all>: identity only, for every named account."""
    worst = 0
    for al in (account.aliases() if name == 'all' else [account.resolve(name)]):
        a = account.load(al); _l = lock(a)
        code = collect(a, argparse.Namespace(check=True, reel=None, skip_gemini=True, max=0, all_reels=False))
        worst = max(worst, code)
    return worst

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--account', required=True); ap.add_argument('--reel', action='append')
    ap.add_argument('--check', action='store_true'); ap.add_argument('--skip-gemini', action='store_true')
    ap.add_argument('--max', type=int, default=20); ap.add_argument('--all-reels', action='store_true')
    args = ap.parse_args()
    if not args.check:
        account.use_venv()       # mlx-whisper and requests live in claude-retention-teardown/.venv (see account.use_venv)
    # Gemini is optional. Without a key every Reel skips the watch pass and the run says so (NO_GEMINI); adding a key
    # later backfills it on the next run (the 'skipped' marker in meta.json, see collect()).
    if not args.skip_gemini and not args.check and not account.env_value('GEMINI_API_KEY'):
        args.skip_gemini = True
        print('NO_GEMINI no GEMINI_API_KEY set: the watch notes (screen changes) are skipped this run. Add the key to the '
              'skill folder .env to get them; the next run backfills.', flush=True)
    if args.account == 'all':
        if args.reel: sys.exit('--reel needs one account, not "all"')
        if not account.aliases(): sys.exit(f'No Instagram account yet. Create the first one with: {account.ADD_HINT}')
        codes = {}
        for al in account.aliases():
            if account.load(al).get('eligible') is False:
                print(f'== {al}: not eligible (no Reel insights for this account), skipped'); codes[al] = 'ineligible'; continue
            print(f'== {al}', flush=True)
            # One process per account: nothing in memory carries from one account to the next.
            r = subprocess.run([sys.executable, os.path.abspath(__file__), '--account', al] + (['--check'] if args.check else [])
                               + (['--skip-gemini'] if args.skip_gemini else []) + ['--max', str(args.max)] + (['--all-reels'] if args.all_reels else []))
            codes[al] = r.returncode
        print('ALL', json.dumps(codes))
        sys.exit(0 if all(c in (0, 'ineligible') for c in codes.values()) else 1)
    a = account.load(args.account)
    _l = lock(a)
    sys.exit(collect(a, args))

if __name__ == '__main__':
    main()
