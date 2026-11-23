#!/usr/bin/env python3
"""Check that every line the page quotes from the creator really appears in a transcript.

Usage: python3 ~/.claude/skills/tiktok-retention-teardown/scraping/check_quotes.py [--account <name>] [narrative.json]

Looks at <q>"…"</q> quotes in lessons, the struck-through `was` line and `Keep: "…"` lines of each rewrite
card, and any meta line marked "(your line …)". Comparison ignores case, spacing, punctuation and number
formatting, and treats Whisper's brand typos as the brand (ChatBt = ChatGPT, Cloud = Claude, Prop = Prompt, …).
A quote with "…" in it is checked fragment by fragment (fragments of 3+ words).
Exit code 1 if any quote is not found.
"""
import json, os, re, sys, html

import account as acct

HERE = os.path.dirname(os.path.realpath(__file__))
if '--help' in sys.argv or '-h' in sys.argv:
    print(__doc__); sys.exit(0)
ROOT = acct.from_argv()['root']          # --account <name> for another account; default = the default account
LIB = os.path.join(ROOT, 'library')
# Brand names Whisper misspelled on the AI-tool videos this skill was built on. A quote with the real brand still
# matches a transcript with the typo. Add the names of your own niche here if Whisper mangles them the same way.
BRANDS = [(r'\bchat\s?bt\b|\bchat\s?gpt\b|\bchatgbt\b|\bchatbpt\b', 'chatgpt'), (r'\banthropik\b|\banthropics\b', 'anthropic'), (r'\bcloud\b|\bclaude\b', 'claude'),
          (r'\bnan\b|\bn8n\b', 'neightn'), (r'\bkroc\b|\bgrok\b', 'grok'), (r'\bdots?\b', 'dots'), (r'\bprop\b', 'prompt')]

def norm(s):
    s = html.unescape(re.sub(r'<[^>]+>', ' ', s)).lower().replace('’', "'")
    for pat, rep in BRANDS: s = re.sub(pat, rep, s)
    return re.sub(r'[^a-z0-9]', '', s)

def transcripts():
    T = {}
    for vid in (os.listdir(LIB) if os.path.isdir(LIB) else []):
        p = os.path.join(LIB, vid, 'words.json')
        if os.path.exists(p):
            T[vid] = norm(' '.join(w['w'] for w in json.load(open(p)).get('words', [])))
    return T

def quotes(N):
    out = []
    for l in N.get('lessons', []):
        for q in re.findall(r'<q>(.*?)</q>', l.get('evidence_html', '') + l.get('do_html', ''), re.S):
            out.append((f"lesson {l['id']}", None, q))
    for vid, r in N.get('rewrites', {}).items():
        for q in re.findall(r'"([^"]+)"', re.sub(r'<[^>]+>', '', r.get('was', ''))):
            out.append((f'rewrite {vid} was', vid, q))
        for m in r.get('meta', []):
            if 'your line' in m:
                for q in re.findall(r'"([^"]+)"', re.sub(r'<[^>]+>', '', m)):
                    out.append((f'rewrite {vid} meta', vid, q))
    return out

def main():
    N = json.load(open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'narrative.json')))
    T = transcripts(); bad = 0; n = 0
    for where, vid, q in quotes(N):
        frags = [f for f in re.split(r'…|\.\.\.', q.strip('"“” ')) if len(f.split()) >= 3] or [q]
        pool = [T[vid]] if vid in T else list(T.values())
        miss = [f for f in frags if not any(norm(f) in t for t in pool)]
        n += 1
        if miss:
            bad += 1; print(f'MISS  {where}: "{q[:90]}"  (not found: {"; ".join(m[:50] for m in miss)})')
    print(f'{n - bad}/{n} quotes found in transcripts')
    sys.exit(1 if bad else 0)

if __name__ == '__main__':
    main()
