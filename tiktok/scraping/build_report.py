#!/usr/bin/env python3
"""Rebuild accounts/<name>/retention-teardown.html from that account's library + narrative.json.

Usage: python3 ~/.claude/skills/tiktok-retention-teardown/scraping/build_report.py            # write the page
       python3 ~/.claude/skills/tiktok-retention-teardown/scraping/build_report.py --stats    # print the numbers lessons cite
       add --account <name> for another account (see account.py); without it, the default account.

Data parts (chart, table, frames, explorer) come from library/<id>/ (latest snapshot of each video).
Aggregate tokens and the account median use only settled videos (48+ hours old at their last snapshot).
Written parts (verdict, lessons, rewrites, checklist, update log, notes) come from narrative.json.
Narrative strings may use {{tokens}} that are recomputed every build, so aggregate numbers never go stale:
  n_videos, n_settled, n_provisional, views_range, p1_loss_range, p2_loss_range, p3_range, p10_range, p30_range,
  decay_after_3s, median_p3, median_p10, updated
"""
import json, os, re, sys, math, statistics, datetime, html, shutil

import account as acct

HERE = os.path.dirname(os.path.realpath(__file__))
if '--help' in sys.argv or '-h' in sys.argv:
    print(__doc__); sys.exit(0)
# Every path points into accounts/<name>/ (account.load), page and media/ side by side because cmux's browser only
# reads files inside the page's own folder.
_A = acct.from_argv()
ROOT = _A['root']
LIB = os.path.join(ROOT, 'library')
OUT = os.path.join(_A['page_dir'], 'retention-teardown.html')
MEDIA = os.path.join(_A['page_dir'], 'media')            # hard links to library frames/videos (gitignored)
NARR = os.path.join(ROOT, 'narrative.json')
SETTLED_H = 48   # curves move a lot in the first two days; aggregates and the median use settled videos only

def load(p, d=None):
    try: return json.load(open(p))
    except Exception: return d

def media(vid, name):
    """Page-relative path to library/<vid>/<name>, hard-linked into media/ next to the page. cmux's browser only
    reads files inside the page's own folder, and symlinks out of it don't load there, so these are hard links."""
    src = os.path.join(LIB, vid, name)
    if not os.path.exists(src): return None
    dst = os.path.join(MEDIA, vid, name)
    if not (os.path.exists(dst) and os.path.samefile(src, dst)):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.lexists(dst): os.remove(dst)
        try: os.link(src, dst)
        except OSError: shutil.copy2(src, dst)
    return f'media/{vid}/{name}'

def videos(names):
    out = []
    for vid in (os.listdir(LIB) if os.path.isdir(LIB) else []):
        meta = load(os.path.join(LIB, vid, 'meta.json'), {}) or {}
        sp = os.path.join(LIB, vid, 'snapshots.jsonl')
        if not meta.get('analyzed') or not os.path.exists(sp): continue
        snaps = [json.loads(l) for l in open(sp)]
        s = snaps[-1]
        if not s.get('ret'): continue
        W = (load(os.path.join(LIB, vid, 'words.json'), {}) or {}).get('words', [])
        G = ((load(os.path.join(LIB, vid, 'gemini.json'), {}) or {}).get('analysis') or {})
        words = [' '.join(w['w'] for w in W if t <= w['s'] < t + 1) for t in range(len(s['ret']))]
        events = [[round(c['t'], 1), c['what_changes']] for c in G.get('cut_log', []) if isinstance(c.get('t'), (int, float))]
        pulled = datetime.datetime.fromisoformat(s.get('pulled_at') or s['date'] + 'T12:00:00')
        age_h = (pulled - datetime.datetime.fromtimestamp(meta['create_time'])).total_seconds() / 3600
        out.append({'id': vid, 'name': names.get(vid) or meta.get('name') or vid, 'age_h': round(age_h), 'settled': age_h >= SETTLED_H, 'posted': meta['posted'], 'posted_ts': meta['create_time'],
                    'dur': meta.get('duration_s') or len(s['ret']), 'views': s.get('views'), 'avg': s.get('avg_watch_s'),
                    'finish': s.get('finish_rate'), 'likes': s.get('likes'), 'saves': s.get('saves'), 'comments': s.get('comments'),
                    'shares': s.get('shares'), 'ret': s['ret'], 'words': words, 'events': events, 'source': s.get('source'),
                    'snaps': len(snaps), 'first_views': snaps[0].get('views'), 'url': meta['url'],
                    'f0': media(vid, 'f0.jpg') or f'library/{vid}/f0.jpg', 'f2': media(vid, 'f2.jpg') or f'library/{vid}/f2.jpg',
                    'mp4': media(vid, 'video.mp4')})
    return sorted(out, key=lambda v: -v['posted_ts'])

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
    return (f'{lo}{unit}' if lo == hi else f'{lo} to {hi}{unit}')

def tokens(D, med, narr):
    ALL, D = D, settled(D)
    at = lambda v, t: v['ret'][t] if t < len(v['ret']) else None
    decay = [(v['ret'][3] - v['ret'][-1]) / (len(v['ret']) - 4) * 100 for v in D if len(v['ret']) > 5]
    return {
        'n_videos': str(len(ALL)), 'n_settled': str(len(D)), 'n_provisional': str(len(ALL) - len(D)),
        'views_range': rng([v['views'] for v in ALL], '') if ALL else 'n/a',
        'p1_loss_range': rng([(1 - at(v, 1)) * 100 for v in D if at(v, 1) is not None]),
        'p2_loss_range': rng([(at(v, 1) - at(v, 2)) * 100 for v in D if at(v, 2) is not None], ''),
        'p3_range': rng([at(v, 3) * 100 for v in D if at(v, 3) is not None]),
        'p10_range': rng([at(v, 10) * 100 for v in D if at(v, 10) is not None]),
        'p30_range': rng([at(v, 30) * 100 for v in D if at(v, 30) is not None]),
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

def render(D, med, narr):
    T = tokens(D, med, narr)
    frames = '<div class="frames">' + ''.join(
        f'<figure><img src="{v["f0"]}" alt="First frame of {html.escape(v["name"])}" loading="lazy"><figcaption>{html.escape(v["name"])}</figcaption></figure>'
        for v in D[:10]) + '</div>'
    L = []
    for i, l in enumerate([l for l in narr['lessons'] if l.get('status') != 'retired'] + [l for l in narr['lessons'] if l.get('status') == 'retired'], 1):
        st = l.get('status', 'holding')
        L.append(f'''<article class="lesson" id="lesson-{l["id"]}">
  <div class="n">LESSON {i} · {l["tag"]}<span class="pill {st}">{st}</span><span class="dim">since {l.get("since", "")}{(" · updated " + l["updated"]) if l.get("updated") else ""}</span></div>
  <h3>{l["title"]}</h3>
  {frames if l.get("frames") else ""}
  <div class="ev">{l["evidence_html"]}</div>
  <p class="do">{l["do_html"]}</p>
  <div class="cite">{l.get("cite", "")}</div>
</article>''')
    # Empty states (a new account): say what earns content here instead of rendering a blank section.
    if not L: L = ['<p class="dim">No lessons yet. A lesson needs the same pattern in 3+ videos, bigger than the noise.</p>']
    order = {v['id']: v['posted_ts'] for v in D}
    names = {v['id']: v['name'] for v in D}
    urls = {v['id']: v['url'] for v in D}
    R = []
    for vid, r in sorted(narr.get('rewrites', {}).items(), key=lambda kv: -order.get(kv[0], 0)):
        watch = f' · <a href="{urls[vid]}" target="_blank" rel="noopener">Watch ↗</a>' if vid in urls else ''
        R.append(f'''<div class="card"><div class="eyebrow">{html.escape(names.get(vid, r.get("label", vid)))}{watch}</div>
  <div class="was">{r["was"]}</div><div class="now">{r["now"]}</div>
  <div class="meta">{"".join(f"<div>{m}</div>" for m in r.get("meta", []))}</div></div>''')
    C = ''.join(f'<li>{c}</li>' for c in narr.get('checklist', [])) or \
        '<li class="dim">No checklist yet. Add your own pre-record questions to narrative.json, "checklist".</li>'
    G = ''.join(f'<li><span class="d">{c["date"]}</span><span>{c["note"]}</span></li>' for c in sorted(narr.get('changelog', []), key=lambda c: c['date'], reverse=True))
    N = ''.join(f'<p>{n}</p>' for n in narr.get('notes', []))
    page = open(os.path.join(HERE, 'report_template.html')).read()
    data = json.dumps(D, ensure_ascii=False).replace('</', '<\\/')
    rep = {'__SINCE__': (' (posted since ' + _A['since'] + ')') if _A.get('since') else '', '__HANDLE__': html.escape(_A['handle']), '__N__': T['n_videos'], '__UPDATED__': T['updated'], '__VERDICT__': fill(narr['verdict_html'], T),
           '__LESSONS__': fill('\n'.join(L), T), '__REWRITES__': fill('\n'.join(R), T) or '<p class="dim">No rewrite cards yet.</p>',
           '__CHECKLIST__': fill(C, T),
           '__CHANGELOG__': fill(G, T), '__NOTES__': fill(N, T), '__MEDIAN__': json.dumps(med), '__DATA__': data}
    for k, v in rep.items(): page = page.replace(k, v)
    left = re.findall(r'\{\{\w+\}\}', page)
    if left: raise SystemExit(f'unfilled tokens: {left}')
    return page

def stats(D, med):
    print('id                   posted      views  1s   2s-drop 3s   10s  30s  30/3   avg/len   fin    saves  name')
    for v in D:
        r = v['ret']; g = lambda t: r[t] if t < len(r) else None
        s30 = f'{g(30) / g(3):.2f}' if g(30) and g(3) else '-'
        print(f"{v['id']}  {v['posted'][:10]}  {v['views']:>5}  {g(1) * 100:3.0f}  {(g(1) - g(2)) * 100:5.0f}   {g(3) * 100:3.0f}  {g(10) * 100:3.0f}  "
              f"{(g(30) or 0) * 100:3.0f}  {s30:>5}  {(v['avg'] or 0):5.1f}/{v['dur']:<4.0f} {(v['finish'] or 0) * 100:4.1f}%  {v['saves']:>4}   {v['name']}")
    print('median 1s/3s/10s/30s:', [f'{med[t] * 100:.0f}%' if t < len(med) and med[t] is not None else '-' for t in (1, 3, 10, 30)])
    print('tokens:', json.dumps(tokens(D, med, load(NARR, {}) or {})))

def main():
    narr = load(NARR)
    if narr is None: sys.exit(f'missing {NARR}')
    D = videos(narr.get('names', {})); med = median_curve(D)
    if '--stats' in sys.argv: return stats(D, med)
    open(OUT, 'w').write(render(D, med, narr))
    print(f'wrote {OUT} · {len(D)} videos')

if __name__ == '__main__':
    main()
