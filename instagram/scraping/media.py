"""Video, frames, transcript and Gemini watch pass for one Reel. Forked from the TikTok skill's daily.py.

SYNC WARNING: forked from ../../tiktok/scraping/daily.py (functions download, frames, title_strip, transcribe, gemini).
Copied instead of imported so the TikTok workflow can change without breaking this one (and vice versa). If a fix
lands there (a Whisper setting, a Gemini timeout, a title-strip change), port it here.
Differences: functions take the Reel folder as an argument; downloads go through net.allow(); the Gemini prompt says
"Reel"; the curl referer is instagram.com.

Every artifact here matches the TikTok library layout so the analyst steps read them the same way:
video.mp4 (gitignored), f0.jpg (0.05 s), f2.jpg (2.2 s), title_strip.jpg (top half at 0.05/0.5/1.0/2.2 s),
words.json (mlx_whisper word timestamps), gemini.json (one watch pass).
"""
import json, os, subprocess, time

import account, net

def sh(*a, **k):
    return subprocess.run(list(a), capture_output=True, text=True, **k)

MAX_HOPS = 5

def fetch(u, out):
    """Download one URL to `out` and return curl's HTTP status. Redirects are followed BY HAND: each hop's Location goes
    through net.allow() before it is requested. WHY not `curl -L`: -L follows a redirect to any host, which would let a
    signed link that redirects (or a tampered answer) send the request outside the allowlist in net.py. https only."""
    for _ in range(MAX_HOPS + 1):
        net.allow(u)
        r = sh('curl', '-s', '--proto', '=https', '-m', '180', '-A', 'Mozilla/5.0', '-e', 'https://www.instagram.com/',
               '-o', out, '-w', '%{http_code} %{redirect_url}', u)
        code, _, nxt = r.stdout.strip().partition(' ')
        if code.startswith('3') and nxt:
            u = nxt
            continue
        return code
    return 'too many redirects'

def download(d, urls):
    out = os.path.join(d, 'video.mp4')
    if os.path.exists(out) and os.path.getsize(out) > 100000: return out
    for u in [u for u in urls if u]:
        try:
            code = fetch(u, out)
        except net.Blocked:
            continue  # this link (or one of its redirects) leaves the allowlist: try the next link, never follow it
        if code == '200' and os.path.exists(out) and os.path.getsize(out) > 100000: return out
    raise RuntimeError('download failed (no working video link)')

def duration(d):
    r = sh('ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', os.path.join(d, 'video.mp4'))
    try: return round(float(json.loads(r.stdout)['format']['duration']), 2)
    except Exception: return None

def frames(d):
    v = os.path.join(d, 'video.mp4')
    for name, t in (('f0', '0.05'), ('f2', '2.2')):
        sh('ffmpeg', '-loglevel', 'error', '-y', '-ss', t, '-i', v, '-frames:v', '1', '-vf', 'scale=220:-1', '-q:v', '5', os.path.join(d, name + '.jpg'))
    title_strip(d)

def title_strip(d):
    """title_strip.jpg: the top half of the frame at 0.05 / 0.5 / 1.0 / 2.2 s, left to right, large enough to read.
    The 220 px frames are too small to tell a still-fading title from a finished one (TikTok lesson, 2026-10-07)."""
    v = os.path.join(d, 'video.mp4'); parts = []
    for i, t in enumerate(('0.05', '0.5', '1.0', '2.2')):
        p = os.path.join(d, f'_ts{i}.jpg')
        sh('ffmpeg', '-loglevel', 'error', '-y', '-ss', t, '-i', v, '-frames:v', '1', '-vf', 'crop=iw:ih*0.5:0:0,scale=360:-1,pad=iw+8:ih:0:0:red', p)
        parts.append(p)
    args = ['ffmpeg', '-loglevel', 'error', '-y']
    for p in parts: args += ['-i', p]
    sh(*args, '-filter_complex', 'hstack=4', '-q:v', '4', os.path.join(d, 'title_strip.jpg'))
    for p in parts:
        if os.path.exists(p): os.remove(p)

def transcribe(d):
    out = os.path.join(d, 'words.json')
    if os.path.exists(out): return
    # OFFLINE ON PURPOSE: mlx_whisper resolves the model through huggingface_hub, which contacted huggingface.co on every
    # run even though the model is cached (~/.cache/huggingface/hub/models--mlx-community--whisper-large-v3-turbo, about
    # 1.6 GB of weights), seen with lsof in an acceptance test, 2026-10-14. Only metadata, but not an approved host
    # (net.py). So the model must already be downloaded: SETUP.md does it once. If the cache is ever deleted this
    # raises; download the model again by hand (SETUP.md), outside a teardown run.
    os.environ['HF_HUB_OFFLINE'] = '1'
    import mlx_whisper
    r = mlx_whisper.transcribe(os.path.join(d, 'video.mp4'), path_or_hf_repo='mlx-community/whisper-large-v3-turbo',
                               word_timestamps=True, language='en', condition_on_previous_text=False, hallucination_silence_threshold=0.5)
    w = [{'w': x['word'].strip(), 's': round(x['start'], 2), 'e': round(x['end'], 2)} for s in r['segments'] for x in s.get('words', [])]
    json.dump({'text': r['text'].strip(), 'words': w}, open(out, 'w'))

GEMINI_PROMPT = """You are a short-form video retention analyst. Watch this Instagram Reel carefully (video AND audio). Return JSON only.
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

def gemini(d, duration_s):
    out = os.path.join(d, 'gemini.json')
    if os.path.exists(out): return 'cached'
    import requests
    # From the environment or the skill folder's .env (gitignored). collect.main() skips this pass when there is no key.
    key = account.env_value('GEMINI_API_KEY')
    if not key: raise RuntimeError('no GEMINI_API_KEY (set it in the environment or in the skill folder .env)')
    f = os.path.join(d, 'video.mp4'); sz = os.path.getsize(f)
    # SECURITY: key in the x-goog-api-key header, never in the URL (a timeout error prints the URL; runs/*.json may be committed).
    # Every request has a timeout: a call without one hung for 32 minutes on 2026-10-14 (TikTok skill).
    H = {'x-goog-api-key': key}
    base = 'https://generativelanguage.googleapis.com'
    r = _post(net.allow(base + '/upload/v1beta/files'),
                      headers={**H, 'X-Goog-Upload-Protocol': 'resumable', 'X-Goog-Upload-Command': 'start',
                               'X-Goog-Upload-Header-Content-Length': str(sz), 'X-Goog-Upload-Header-Content-Type': 'video/mp4',
                               'Content-Type': 'application/json'}, json={'file': {'display_name': os.path.basename(d)}}, timeout=60)
    fi = _post(net.allow(r.headers['X-Goog-Upload-URL']), headers={**H, 'X-Goog-Upload-Offset': '0', 'X-Goog-Upload-Command': 'upload, finalize'},
                       data=open(f, 'rb').read(), timeout=300).json()['file']
    for _ in range(90):
        if fi['state'] == 'ACTIVE': break
        time.sleep(4); fi = _get(net.allow(f"{base}/v1beta/{fi['name']}"), headers=H, timeout=60).json()
    prompt = GEMINI_PROMPT + (f"\nThis video is {duration_s:.1f} seconds long." if duration_s else '')
    for model in ('gemini-3.1-pro-preview', 'gemini-2.5-pro'):
        g = _post(net.allow(f'{base}/v1beta/models/{model}:generateContent'), headers=H,
                          json={'contents': [{'parts': [{'file_data': {'mime_type': 'video/mp4', 'file_uri': fi['uri']}}, {'text': prompt}]}],
                                'generationConfig': {'response_mime_type': 'application/json', 'temperature': 0.2}}, timeout=600).json()
        if 'candidates' in g:
            a = json.loads(g['candidates'][0]['content']['parts'][-1]['text'])
            if isinstance(a, list):                       # seen 2026-10-14 on TikTok: the answer is [ {...} ], not {...}
                a = next((x for x in a if isinstance(x, dict)), None)
                if a is None: raise RuntimeError('gemini returned a list with no object in it')
            if duration_s:
                a['cut_log'] = [c for c in a.get('cut_log', []) if isinstance(c.get('t'), (int, float)) and c['t'] <= duration_s + 0.5]
            json.dump({'model': model, 'analysis': a}, open(out, 'w'), indent=1)
            return model
    raise RuntimeError(net.scrub(f'gemini failed: {str(g)[:300]}'))
