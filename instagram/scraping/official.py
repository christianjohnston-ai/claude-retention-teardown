"""The official Instagram API (graph.instagram.com, "Instagram API with Instagram Login"). OPTIONAL.

Used for two things only, and only for accounts with a token (IG_TOKEN_<ALIAS> in the environment or the skill .env):
1. The account's own Reel list (shortcode, permalink, timestamp, media_url). This is the ownership gate: a Reel is only
   requested from the insights endpoint if its shortcode is in this list.
2. Reference metrics per Reel (views, reach, average watch time, skip rate, likes, saves, shares, comments), stored
   next to each capture as an independent cross-check. When this tool was built they matched the insights answer exactly.

Without a token the per-second curve still works; only the Reel list (so new Reels are found automatically) and the
cross-check are missing. Setting one up: see Meta's docs,
https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/ (a professional account).

Token handling: read from the environment or the skill .env by account.token(), sent as an Authorization: Bearer header
(never as ?access_token=, because a URL can end up in an error message), never printed or stored.
"""
import datetime, json, urllib.request, urllib.parse, urllib.error

import net

G = 'https://graph.instagram.com/v23.0'
REF_METRICS = 'views,reach,ig_reels_avg_watch_time,reels_skip_rate,likes,saved,shares,comments'

class OfficialError(Exception):
    pass

def get(tok, path, **q):
    url = path if path.startswith('http') else G + path + ('?' + urllib.parse.urlencode(q) if q else '')
    req = urllib.request.Request(net.allow(url), headers={'Authorization': 'Bearer ' + tok})
    try:
        return json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as e:
        try: msg = (json.loads(e.read() or b'{}').get('error') or {}).get('message')
        except Exception: msg = None
        raise OfficialError(net.scrub(f'HTTP {e.code}: {msg}'))
    except Exception as e:
        raise OfficialError(net.scrub(f'{type(e).__name__}: {e}'))

def me(tok):
    return get(tok, '/me', fields='user_id,username,account_type')

def reels(tok, since=None, limit_pages=10):
    """The account's own REELS, newest first: [{id, shortcode, permalink, timestamp, created_ts, caption}]."""
    out, r = [], get(tok, '/me/media', fields='id,shortcode,permalink,timestamp,media_product_type,caption', limit=50)
    cut = datetime.datetime.strptime(since, '%Y-%m-%d').replace(tzinfo=datetime.timezone.utc).timestamp() if since else None
    for _ in range(limit_pages):
        stop = False
        for m in r.get('data', []):
            ts = datetime.datetime.strptime(m['timestamp'], '%Y-%m-%dT%H:%M:%S%z').timestamp()
            if cut and ts < cut: stop = True; continue
            if m.get('media_product_type') == 'REELS':
                out.append({'id': m['id'], 'shortcode': m['shortcode'], 'permalink': m.get('permalink'), 'timestamp': m['timestamp'],
                            'created_ts': ts, 'caption': (m.get('caption') or '')[:300]})
        nxt = (r.get('paging') or {}).get('next')
        if stop or not nxt or not r.get('data'): break
        r = get(tok, nxt)
    return out

def media_url(tok, media_id):
    return get(tok, f'/{media_id}', fields='media_url').get('media_url')

def reference(tok, media_id):
    d = get(tok, f'/{media_id}/insights', metric=REF_METRICS)
    v = {x['name']: x['values'][0]['value'] for x in d.get('data', [])}
    return {'pulled_at': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
            'views': v.get('views'), 'reach': v.get('reach'),
            'avg_watch_s': round(v['ig_reels_avg_watch_time'] / 1000.0, 3) if v.get('ig_reels_avg_watch_time') is not None else None,
            'skip_rate_pct': v.get('reels_skip_rate'), 'likes': v.get('likes'), 'saves': v.get('saved'),
            'shares': v.get('shares'), 'comments': v.get('comments')}
