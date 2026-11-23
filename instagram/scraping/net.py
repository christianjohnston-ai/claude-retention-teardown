"""Every HTTP request the Python side makes goes through allow(): a hard host allowlist, plus a log of host + path
(never the query string, which can hold a token) that collect.py writes into runs/<date>.json.

Why: a design requirement that analytics and credentials never go anywhere unintended, provable from the run files.
The in-page requests (insights.js, identity.js) only ever call www.instagram.com and i.instagram.com.
"""
import re, urllib.parse

# What each host is for. Adding a host is a deliberate decision: say why here.
ALLOWED = {
    'graph.instagram.com': 'official Instagram API (Reel list, reference metrics) for accounts with a token',
    'generativelanguage.googleapis.com': 'Gemini watch pass: the Reel video file only, never analytics (same as the TikTok skill)',
}
ALLOWED_SUFFIXES = {
    '.cdninstagram.com': 'Reel video download (signed CDN link from the official API or the insights answer)',
    '.fbcdn.net': 'Reel video download (Instagram also serves video from fbcdn)',
}
CONTACTED = []          # [(host, path)] for this process

class Blocked(Exception):
    pass

def allow(url):
    u = urllib.parse.urlsplit(url)
    host = (u.hostname or '').lower()
    if u.scheme != 'https' or not (host in ALLOWED or any(host.endswith(s) for s in ALLOWED_SUFFIXES)):
        raise Blocked(f'blocked request to {u.scheme}://{host} (not on the allowlist in net.py)')
    entry = (host, re.sub(r'/v\d+\.\d+/\d{6,}', '/vN/<id>', u.path)[:80])
    if entry not in CONTACTED: CONTACTED.append(entry)
    return url

def scrub(msg):
    """Remove anything token- or cookie-shaped from text before it is stored (runs/*.json are committed)."""
    s = str(msg)
    s = re.sub(r'(access_token=|key=)[^&\s\'"]+', r'\1[REDACTED]', s)
    s = re.sub(r'\b(IGAA|IGQ|EAA|AIza)[A-Za-z0-9_-]{10,}', '[REDACTED]', s)
    s = re.sub(r'(sessionid|csrftoken|ds_user_id|rur|mid|ig_did)=[^;\s]+', r'\1=[REDACTED]', s)
    s = re.sub(r'(oh|oe|_nc_sid|_nc_ohc)=[^&\s"]+', r'\1=[REDACTED]', s)
    return s
