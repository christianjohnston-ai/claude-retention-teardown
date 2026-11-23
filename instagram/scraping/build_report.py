#!/usr/bin/env python3
"""Rebuild accounts/<alias>/retention-teardown.html from that account's library + narrative.json.

Usage: python3 ~/.claude/skills/instagram-retention-teardown/scraping/build_report.py --account <alias|@handle>          # write the page
       python3 ~/.claude/skills/instagram-retention-teardown/scraping/build_report.py --account <alias> --stats  # print the numbers lessons cite

Forked from ../../tiktok/scraping/build_report.py. Same {{tokens}}, same settled rule (48 h),
same narrative.json schema, plus:
- Data comes from the LATEST capture in library/<shortcode>/captures.jsonl (every capture is kept; the page shows the newest).
- Only Reels whose curve Instagram returned at every second from 0 are drawn (sampling verified 2026-10-14). A Reel
  without a curve, or with any other spacing, is listed under the chart with the reason, never filled in or interpolated.
- A lesson may carry `hypothesis_html`: rendered under "Possible explanation (not tested)", visibly apart from the
  measured evidence. A drop that lines up with a sentence does not prove the sentence caused it.
"""
import datetime, html, json, math, os, re, shutil, statistics, sys

import account

HERE = os.path.dirname(os.path.realpath(__file__))
SETTLED_H = 48
if '--help' in sys.argv or '-h' in sys.argv:
    print(__doc__); sys.exit(0)

def arg(name):
    a = sys.argv
    for i, x in enumerate(a):
        if x == name and i + 1 < len(a): return a[i + 1]
        if x.startswith(name + '='): return x.split('=', 1)[1]
    return None

A = account.load(arg('--account') or sys.exit('--account <alias> is required'))
ROOT = A['root']; LIB = os.path.join(ROOT, 'library')
OUT = os.path.join(ROOT, 'retention-teardown.html')
MEDIA = os.path.join(ROOT, 'media')          # hard links to library frames/videos (gitignored)
NARR = os.path.join(ROOT, 'narrative.json')

def load(p, d=None):
    try: return json.load(open(p))
    except Exception: return d

def media(sc, name):
    """Page-relative path to library/<sc>/<name>, hard-linked into media/. cmux's browser only reads files inside the
    page's own folder, so ../library paths do not load there (TikTok skill, same reason)."""
    src = os.path.join(LIB, sc, name)
    if not os.path.exists(src): return None
    dst = os.path.join(MEDIA, sc, name)
    if not (os.path.exists(dst) and os.path.samefile(src, dst)):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.lexists(dst): os.remove(dst)
        try: os.link(src, dst)
        except OSError: shutil.copy2(src, dst)
    return f'media/{sc}/{name}'

def reels(names):
    """(drawn, not_drawn). drawn = Reels with a per-second curve in their latest capture."""
    out, nc = [], []
    for sc in sorted(os.listdir(LIB)) if os.path.isdir(LIB) else []:
        m = load(os.path.join(LIB, sc, 'meta.json'), {}) or {}
        cp = os.path.join(LIB, sc, 'captures.jsonl')
        if not os.path.exists(cp): continue
        caps = [json.loads(l) for l in open(cp)]
        c = caps[-1]
        name = names.get(sc) or m.get('name') or sc
        if not m.get('analyzed'):
            # A Reel captured but never analyzed has no curve yet (Instagram had none, or it was refused). It must still
            # appear on the page with the reason: a silently missing Reel reads as "there is nothing to see" (acceptance
            # A4, 2026-10-14: a minutes-old Reel was left off the page entirely).
            if c.get('status') in ('no_retention', 'not_available'):
                age = (datetime.datetime.fromisoformat(c['captured_at']).timestamp() - m['created_ts']) / 3600 if m.get('created_ts') else None
                why = ('Instagram refused insights for it' if c.get('status') == 'not_available' else
                       f'pending: Instagram had no curve yet ({age:.0f} h after posting); a later run collects it' if age is not None and age < SETTLED_H else
                       'Instagram returned no retention curve')
                nc.append({'id': sc, 'name': name, 'url': m.get('url') or f'https://www.instagram.com/reel/{sc}/', 'why': why,
                           'views': c.get('views'), 'captured': c.get('captured_at', '')[:16]})
            continue
        r = c.get('retention')
        if c.get('status') != 'ok' or not r or not r.get('per_second'):
            why = ('Instagram returned no retention curve' if not r else f'curve not sampled every second ({r.get("n")} points, steps {r.get("steps_s")})')
            nc.append({'id': sc, 'name': name, 'url': m.get('url'), 'why': why, 'views': c.get('views'), 'captured': c.get('captured_at', '')[:16]})
            continue
        ret = [round(v, 4) for _, v in r['points']]
        W = (load(os.path.join(LIB, sc, 'words.json'), {}) or {}).get('words', [])
        G = ((load(os.path.join(LIB, sc, 'gemini.json'), {}) or {}).get('analysis') or {})
        words = [' '.join(w['w'] for w in W if t <= w['s'] < t + 1) for t in range(len(ret))]
        events = [[round(x['t'], 1), x['what_changes']] for x in G.get('cut_log', []) if isinstance(x.get('t'), (int, float))]
        likest = [0] * len(ret)
        for s_, n_ in c.get('like_timing') or []:
            if s_ is not None and 0 <= int(s_) < len(likest): likest[int(s_)] = n_
        pulled = datetime.datetime.fromisoformat(c['captured_at'])
        age_h = (pulled.timestamp() - m['created_ts']) / 3600 if m.get('created_ts') else 0
        out.append({'id': sc, 'name': name, 'age_h': round(age_h), 'settled': age_h >= SETTLED_H, 'posted': m.get('posted') or '',
                    'posted_ts': m.get('created_ts') or 0, 'dur': m.get('duration_s') or len(ret) - 1, 'views': c.get('views'),
                    'avg': c.get('avg_watch_s'), 'skip': c.get('skip_rate_pct'), 'likes': c.get('likes'), 'saves': c.get('saves'),
                    'comments': c.get('comments'), 'shares': c.get('shares'), 'follows': c.get('follows'), 'visits': c.get('profile_visits'),
                    'nonfol': c.get('non_followers_views'), 'sources': ', '.join(f'{l} {v * 100:.0f}%' for l, v in (c.get('view_sources') or [])[:3]),
                    'ret': ret, 'npts': r['n'], 'likest': likest, 'words': words, 'events': events, 'snaps': len(caps),
                    'url': m.get('url') or f'https://www.instagram.com/reel/{sc}/',
                    'f0': media(sc, 'f0.jpg') or '', 'f2': media(sc, 'f2.jpg') or '', 'mp4': media(sc, 'video.mp4')})
    return sorted(out, key=lambda v: -v['posted_ts']), nc

def settled(D):
    S = [v for v in D if v['settled']]
    return S if len(S) >= 3 else D

def median_curve(D):
    D = settled(D)
    n = max((len(v['ret']) for v in D), default=0); med = []
    for t in range(n):
        vals = [v['ret'][t] for v in D if t < len(v['ret'])]
        med.append(round(statistics.median(vals), 4) if len(vals) >= max(2, math.ceil(len(D) / 2)) else None)
    while med and med[-1] is None: med.pop()
    return med

def rng(vals, unit='%'):
    vals = [round(v) for v in vals if v is not None]
    if not vals: return 'n/a'
    lo, hi = min(vals), max(vals)
    return f'{lo}{unit}' if lo == hi else f'{lo} to {hi}{unit}'

def tokens(D, med, narr):
    ALL, D = D, settled(D)
    at = lambda v, t: v['ret'][t] if t < len(v['ret']) else None
    decay = [(v['ret'][3] - v['ret'][-1]) / (len(v['ret']) - 4) * 100 for v in D if len(v['ret']) > 5]
    return {
        'n_videos': str(len(ALL)), 'n_settled': str(len([v for v in ALL if v['settled']])), 'n_provisional': str(len([v for v in ALL if not v['settled']])),
        'views_range': rng([v['views'] for v in ALL], '') if ALL else 'n/a',
        'p1_loss_range': rng([(1 - at(v, 1)) * 100 for v in D if at(v, 1) is not None]),
        'p2_loss_range': rng([(at(v, 1) - at(v, 2)) * 100 for v in D if at(v, 2) is not None], ''),
        'p3_range': rng([at(v, 3) * 100 for v in D if at(v, 3) is not None]),
        'p10_range': rng([at(v, 10) * 100 for v in D if at(v, 10) is not None]),
        'p30_range': rng([at(v, 30) * 100 for v in D if at(v, 30) is not None]),
        'skip_range': rng([v['skip'] for v in D if v['skip'] is not None]),
        'decay_after_3s': f'{statistics.mean(decay):.1f}' if decay else 'n/a',
        'median_p3': f'{med[3] * 100:.0f}%' if len(med) > 3 and med[3] is not None else 'n/a',
        'median_p10': f'{med[10] * 100:.0f}%' if len(med) > 10 and med[10] is not None else 'n/a',
        'updated': narr.get('updated') or datetime.date.today().isoformat(),
    }

def fill(s, T):
    def rep(m):
        k = m.group(1)
        if k not in T: raise KeyError(f'unknown token {{{{{k}}}}} in narrative.json')
        return T[k]
    return re.sub(r'\{\{(\w+)\}\}', rep, s)

def render(D, NC, med, narr):
    T = tokens(D, med, narr)
    frames = '<div class="frames">' + ''.join(
        f'<figure><img src="{v["f0"]}" alt="First frame of {html.escape(v["name"])}" loading="lazy"><figcaption>{html.escape(v["name"])}</figcaption></figure>'
        for v in D[:10]) + '</div>'
    L = []
    for i, l in enumerate([l for l in narr['lessons'] if l.get('status') != 'retired'] + [l for l in narr['lessons'] if l.get('status') == 'retired'], 1):
        st = l.get('status', 'holding')
        hyp = f'<div class="hyp"><span class="lab">Possible explanation (not tested)</span>{l["hypothesis_html"]}</div>' if l.get('hypothesis_html') else ''
        L.append(f'''<article class="lesson" id="lesson-{l["id"]}">
  <div class="n">LESSON {i} · {l["tag"]}<span class="pill {st}">{st}</span><span class="dim">since {l.get("since", "")}{(" · updated " + l["updated"]) if l.get("updated") else ""}</span></div>
  <h3>{l["title"]}</h3>
  {frames if l.get("frames") else ""}
  <div class="ev">{l["evidence_html"]}</div>
  {hyp}
  <p class="do">{l["do_html"]}</p>
  <div class="cite">{l.get("cite", "")}</div>
</article>''')
    if not L: L = ['<p class="dim">No lessons yet. A lesson needs the same pattern in 3+ settled Reels, bigger than the noise.</p>']
    order = {v['id']: v['posted_ts'] for v in D}; names = {v['id']: v['name'] for v in D}; urls = {v['id']: v['url'] for v in D}
    R = []
    for sc, r in sorted(narr.get('rewrites', {}).items(), key=lambda kv: -order.get(kv[0], 0)):
        watch = f' · <a href="{urls[sc]}" target="_blank" rel="noopener">Watch ↗</a>' if sc in urls else ''
        R.append(f'''<div class="card"><div class="eyebrow">{html.escape(names.get(sc, r.get("label", sc)))}{watch}</div>
  <div class="was">{r["was"]}</div><div class="now">{r["now"]}</div>
  <div class="meta">{"".join(f"<div>{m}</div>" for m in r.get("meta", []))}</div></div>''')
    C = ''.join(f'<li>{c}</li>' for c in narr.get('checklist', [])) or \
        '<li class="dim">No checklist yet. Add your own pre-record questions to narrative.json, "checklist".</li>'
    G = ''.join(f'<li><span class="d">{c["date"]}</span><span>{c["note"]}</span></li>' for c in sorted(narr.get('changelog', []), key=lambda c: c['date'], reverse=True))
    N = ''.join(f'<p>{n}</p>' for n in narr.get('notes', []))
    NCH = ''
    if NC:
        NCH = '<div class="nocurve"><b>Not drawn (no per-second curve):</b><ul>' + ''.join(
            f'<li>{html.escape(x["name"])} · <a href="{x["url"]}" target="_blank" rel="noopener">Watch ↗</a> · {html.escape(x["why"])} · {x["views"] if x["views"] is not None else "-"} views · captured {x["captured"]}</li>'
            for x in NC) + '</ul></div>'
    page = open(os.path.join(HERE, 'report_template.html')).read()
    data = json.dumps(D, ensure_ascii=False).replace('</', '<\\/')
    rep = {'__SINCE__': (' (posted since ' + A['since'] + ')') if A.get('since') else '', '__HANDLE__': html.escape(A['handle']), '__N__': T['n_videos'],
           '__UPDATED__': T['updated'], '__VERDICT__': fill(narr['verdict_html'], T), '__LESSONS__': fill('\n'.join(L), T),
           '__REWRITES__': fill('\n'.join(R), T) or '<p class="dim">No rewrite cards yet.</p>', '__CHECKLIST__': fill(C, T),
           '__CHANGELOG__': fill(G, T), '__NOTES__': fill(N, T), '__NOCURVE__': NCH, '__MEDIAN__': json.dumps(med), '__DATA__': data}
    for k, v in rep.items(): page = page.replace(k, v)
    left = re.findall(r'\{\{\w+\}\}', page)
    if left: raise SystemExit(f'unfilled tokens: {left}')
    return page

def stats(D, NC, med):
    print('shortcode     posted      views   1s  2s-drop  3s  10s  30s  30/3  avg/len     skip  saves follows nonfol  name')
    for v in D:
        r = v['ret']; g = lambda t: r[t] if t < len(r) else None
        s30 = f'{g(30) / g(3):.2f}' if g(30) and g(3) else '-'
        nf = f"{v['nonfol'] / v['views'] * 100:.0f}%" if v['nonfol'] is not None and v['views'] else '-'
        print(f"{v['id']:<12}  {v['posted'][:10]}  {v['views'] or 0:>6}  {g(1) * 100:3.0f}  {(g(1) - g(2)) * 100:5.1f}   {g(3) * 100:3.0f}  {g(10) * 100 if g(10) is not None else 0:3.0f}  "
              f"{(g(30) or 0) * 100:3.0f}  {s30:>4}  {(v['avg'] or 0):5.1f}/{v['dur']:<4.0f}  {v['skip'] if v['skip'] is not None else 0:5.1f}%  {v['saves'] or 0:>4}  {v['follows'] or 0:>6}  {nf:>5}  "
              f"{v['name']}{'' if v['settled'] else ' (provisional ' + str(v['age_h']) + ' h)'}")
    for x in NC: print(f"{x['id']:<12}  NOT DRAWN: {x['why']} · {x['name']}")
    print('median 1s/3s/10s/30s:', [f'{med[t] * 100:.0f}%' if t < len(med) and med[t] is not None else '-' for t in (1, 3, 10, 30)])
    print('tokens:', json.dumps(tokens(D, med, load(NARR, {}) or {})))

def main():
    narr = load(NARR)
    if narr is None: sys.exit(f'missing {NARR}')
    D, NC = reels(narr.get('names', {})); med = median_curve(D)
    if '--stats' in sys.argv: return stats(D, NC, med)
    open(OUT, 'w').write(render(D, NC, med, narr))
    print(f'wrote {OUT} · {len(D)} Reels drawn, {len(NC)} without a per-second curve')

if __name__ == '__main__':
    main()
