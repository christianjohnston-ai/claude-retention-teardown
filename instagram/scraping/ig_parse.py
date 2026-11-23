"""Parse and normalize one Instagram Reel insights answer (i.instagram.com/graphql_www). No network, no side effects.

Everything here was checked, when this tool was built (2026-10-14), against a real captured answer and against the
phone app's Insights screen for the same Reel. Facts the code relies on:

- The body is a STREAM of top-level JSON objects (11 on the test Reel), served as text/html. The first has
  data["1$ig_reel_insights(...)"]; the rest are incremental parts whose path[0] contains "ig_reel_insights(". The last
  part carries extensions.is_final = true. A stream without it is incomplete.
- Keys that hold floats carry a "1f" prefix ("1fpercentage", "1fvalue"). The raw file keeps them; normalize() strips them.
- UNITS DIFFER FIELD BY FIELD, whatever "format" says, so each field is converted explicitly:
    retention_curve percentage  share 0-1 (the app rounds down: for example 0.6249 in the data shows as 62% on the phone)
    avg_watch_time value        MILLISECONDS although format = DURATION_SECONDS (equals the official API's ms exactly)
    performance_factors value   share 0-1 although format = PERCENTAGE (for example skip 0.5512 = app "55.1%")
    views_sources value         share 0-1
    demographics                age/gender look like shares, country like percents: kept raw only, never converted
- The retention curve was 1 point per second from 0 to the Reel's length. If a Reel ever comes back with other
  spacing, the points are kept exactly as returned and per_second is False (nothing is filled in).
"""
import json, re

# Credit: the request shape and the two Instagram-internal ids below were learned from the ReelCurve v0.4.0 Chrome extension.
# SYNC WARNING: they must match the ids in insights.js; change both together.
METHOD = {'method': 'web graphql_www (page fetch in the account cmux profile)', 'client_doc_id': '34117726176169458716316101',
          'bloks_id': '06d2ce5b718bc1f7b81c5c853dadef374aea8a009110982b5b80ff74164fd5dc'}
COLLECTOR_VERSION = '0.1.0'
ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
SIGNED_URL_KEYS = ('video_url', 'thumbnail_url')

class FormatChanged(Exception):
    """The answer is not the shape we know. collect.py exits 7 and keeps the raw text for diagnosis."""

def media_igid(shortcode):
    """Reel shortcode -> the numeric media id the insights query takes (the shortcode read as base-64 digits)."""
    if not re.fullmatch(r'[A-Za-z0-9_-]{5,40}', shortcode or ''): raise ValueError(f'not a shortcode: {shortcode!r}')
    n = 0
    for c in shortcode: n = n * 64 + ALPHABET.index(c)
    return str(n)

def shortcode_from(x):
    """A Reel URL or a bare shortcode -> shortcode."""
    m = re.search(r'instagram\.com/(?:[A-Za-z0-9._]+/)?(?:reel|reels|p)/([A-Za-z0-9_-]+)', x or '')
    if m: return m.group(1)
    if re.fullmatch(r'[A-Za-z0-9_-]{5,40}', x or ''): return x
    raise ValueError(f'not a Reel URL or shortcode: {x!r}')

def split_stream(text):
    dec, parts, i = json.JSONDecoder(), [], 0
    try:
        while i < len(text):
            while i < len(text) and text[i].isspace(): i += 1
            if i >= len(text): break
            obj, i = dec.raw_decode(text, i)
            parts.append(obj)
    except ValueError as e:
        raise FormatChanged(f'not a JSON stream at char {i}: {e}; starts {text[:120]!r}')
    if not parts: raise FormatChanged('empty answer')
    return parts

def signal(status, parts_or_text):
    """Instagram integrity signals that must STOP collection for this account. Returns (kind, detail) or None.

    Only error/message fields are inspected (never the metrics), so a label in the data cannot trigger a false stop.
    Kinds and what collect.py does: logged_out -> exit 3; challenge -> pause until the user clears it; rate_limit and
    action_block -> 24 h pause. Code 1675002 is what Instagram answered when signed out (seen 2026-10-14).
    """
    if isinstance(parts_or_text, str):
        blob = parts_or_text[:4000]
    else:
        bits = []
        for p in parts_or_text:
            bits += [json.dumps(p.get('errors') or '')] + [str(p.get(k) or '') for k in ('message', 'error_type', 'error_title', 'status', 'checkpoint_url', 'challenge', 'spam')]
        blob = ' '.join(bits)
    low = blob.lower()
    if '1675002' in low or 'logged out' in low or 'login_required' in low: return ('logged_out', blob[:200])
    if re.search(r'checkpoint_required|challenge_required|checkpoint_url', low): return ('challenge', blob[:200])
    if status == 429 or re.search(r'rate_limit|too many requests|please wait a few minutes', low): return ('rate_limit', blob[:200])
    if re.search(r'feedback_required|sentry_block|"spam":\s*true|\bspam true\b', low): return ('action_block', blob[:200])
    return None

def merge(parts):
    """Merge the stream into one insights dict (keys still raw, 1f prefixes kept). Raises FormatChanged."""
    data, unknown, errors = None, [], []
    for p in parts:
        errors += p.get('errors') or []
        path = p.get('path')
        if not path:
            for k, v in (p.get('data') or {}).items():
                if 'ig_reel_insights(' in k and v: data = dict(v)
        elif len(path) == 1 and 'ig_reel_insights(' in str(path[0]):
            data = {**(data or {}), **(p.get('data') or {})}
        else:
            unknown.append(path)
    final = bool((parts[-1].get('extensions') or {}).get('is_final'))
    return data, {'errors': errors, 'unknown_paths': unknown, 'is_final': final, 'n_parts': len(parts)}

def strip1f(x):
    if isinstance(x, list): return [strip1f(v) for v in x]
    if isinstance(x, dict): return {(k[2:] if k.startswith('1f') else k): strip1f(v) for k, v in x.items()}
    return x

def scrub_signed_urls(x):
    """Raw files keep everything Instagram sent EXCEPT signed CDN links: they expire and do not belong in git."""
    if isinstance(x, list): return [scrub_signed_urls(v) for v in x]
    if isinstance(x, dict): return {k: ('[signed CDN url removed]' if k in SIGNED_URL_KEYS and isinstance(v, str) else scrub_signed_urls(v)) for k, v in x.items()}
    return x

def _metric(d):
    """The {id,label,value,format,formatted_value} objects -> value, or None."""
    return d.get('value') if isinstance(d, dict) else d

def normalize(raw_data):
    """Raw merged insights -> the normalized fields stored in captures.jsonl. Missing stays None and is listed in
    `missing`; nothing is ever turned into 0 or filled in."""
    d = strip1f(raw_data)
    out, missing, flags = {}, [], []

    curve = ((d.get('retention') or {}).get('retention_curve')) or []
    pts = [[p.get('timestamp_seconds'), p.get('percentage')] for p in curve]
    pts = [[float(t), float(v)] for t, v in pts if t is not None and v is not None]
    if pts:
        vals = [v for _, v in pts]
        if max(vals) <= 1.0: units = 'share 0-1'
        elif max(vals) <= 100.0:
            # Never seen; if Instagram switches to percent, convert and say so rather than guess silently.
            pts = [[t, v / 100.0] for t, v in pts]; units = 'percent 0-100, converted to share'; flags.append('curve_units_converted')
        else:
            raise FormatChanged(f'retention values out of range (max {max(vals)})')
        ts = [t for t, _ in pts]
        steps = sorted({round(b - a, 3) for a, b in zip(ts, ts[1:])})
        per_second = ts[0] == 0 and steps == [1.0]
        if not all(b > a for a, b in zip(ts, ts[1:])): flags.append('curve_timestamps_not_rising')
        rises = [t for (t, v), (_, v0) in zip(pts[1:], pts) if v > v0 + 1e-9]
        if rises: flags.append('curve_rises_at_' + ','.join(f'{t:g}s' for t in rises[:5]))
        if not per_second: flags.append('curve_not_per_second')
        out['retention'] = {'points': pts, 'units': units, 'n': len(pts), 'steps_s': steps, 'first_s': ts[0], 'last_s': ts[-1], 'per_second': per_second}
    else:
        out['retention'] = None; missing.append('retention')

    lt = d.get('like_timing') or {}
    likes = [[x.get('seconds'), x.get('like_count')] for x in (lt.get('likes_by_timing') or []) if x.get('seconds') is not None]
    out['like_timing'] = likes or None
    out['like_timing_total'] = lt.get('total_likes')
    if not likes: missing.append('like_timing')

    aw = _metric(d.get('avg_watch_time'))
    out['avg_watch_s'] = round(aw / 1000.0, 3) if isinstance(aw, (int, float)) else None    # ms -> s, see module doc
    if out['avg_watch_s'] is None: missing.append('avg_watch_time')

    out['views'] = d.get('total_views')
    out['reach'] = _metric(d.get('viewers_or_reach'))
    for k in ('likes', 'comments', 'saves', 'shares', 'reposts', 'follows', 'profile_visits', 'followers_views', 'non_followers_views'):
        out[k] = d.get(k)
        if d.get(k) is None: missing.append(k)
    # PLACEHOLDER ZEROS: on a Reel Instagram has not computed yet (seen on a Reel a few minutes old:
    # is_media_recently_created = true, empty curve, avg watch "--"), EVERY rate arrives as exactly 0 ("0.0%", even skip
    # rate, which is impossible with real viewers). Without a curve, a rate of exactly 0 is "not computed", not a
    # measurement: it is stored as None, listed in `missing`, and flagged. The raw file keeps Instagram's 0.
    not_computed = not out['retention']
    out['recently_created'] = d.get('is_media_recently_created')
    if out['recently_created']: flags.append('recently_created')
    pf, zeroed = {}, []
    for f in d.get('performance_factors') or []:
        b = f.get('benchmark') or {}
        share = f.get('value')
        if not_computed and share == 0: share = None; zeroed.append(f.get('id'))
        pf[f.get('id')] = {'label': f.get('label'), 'share': share, 'shown': f.get('formatted_value'),
                           'benchmark_share': b.get('value'), 'vs_benchmark': b.get('comparison'), 'sentiment': b.get('sentiment')}
    if zeroed: flags.append('placeholder_zero_rates_treated_as_missing')
    out['rates'] = pf or None
    out['skip_rate_pct'] = round(pf['reels_skip_rate']['share'] * 100, 2) if pf.get('reels_skip_rate') and isinstance(pf['reels_skip_rate']['share'], (int, float)) else None
    if out['skip_rate_pct'] is None: missing.append('skip_rate')
    out['view_sources'] = [[s.get('label'), s.get('value')] for s in (d.get('views_sources') or [])] or None
    if not out['view_sources']: missing.append('view_sources')
    vot = d.get('views_over_time') or {}
    out['media_created_at'] = vot.get('media_created_at')
    dem = d.get('demographics') or {}
    out['demographics_status'] = dem.get('status')
    if dem.get('status') != 'AVAILABLE': missing.append('demographics')
    out['is_collab'] = d.get('is_collab'); out['media_id'] = d.get('media_id')
    out['has_video_url'] = bool(d.get('video_url'))
    out['missing'] = missing; out['flags'] = flags
    return out

def at(points, t):
    """Kept share at second t from MEASURED points only: the exact point, or None. Never interpolates."""
    for pt, v in points:
        if abs(pt - t) < 1e-6: return v
    return None
