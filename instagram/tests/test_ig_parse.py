#!/usr/bin/env python3
"""Tests for scraping/ig_parse.py that need no private data. No network, no invented analytics.

Run: python3 ~/.claude/skills/instagram-retention-teardown/tests/test_ig_parse.py

What is here: shortcode parsing, the shortcode-to-media-id decoding, the stop signals on two error bodies Instagram
really returned (quoted verbatim below; they hold no account data), the signed-URL scrub, and the HTML-answer guard.

What is NOT here, and why: the tests that check merge() and normalize() against a full insights answer (units per
field, the per-second curve, placeholder zeros on a minutes-old Reel). They need a captured answer of a real Reel,
which is that account's private analytics, so those fixtures are not published. When this tool was built they ran
against real answers, and the numbers matched the phone app's Insights screen. If you change ig_parse.py, capture one
Reel of your own (step 01) and compare its captures.jsonl line with your phone before trusting the change.
"""
import json, os, sys
HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'scraping'))
import ig_parse as P

# Real answers seen 2026-10-14: graphql_www signed out, and web_profile_info rate-limited.
SIGNED_OUT = '{"errors":[{"message":"Unauthorized logged out query.","severity":"CRITICAL","code":1675002}],"extensions":{"is_final":true}}'
RATE_LIMITED = '{"message":"Please wait a few minutes before you try again.","require_login":true,"igweb_rollout":true,"status":"fail"}'
# A shortcode-shaped placeholder: the parser only cares about the URL forms, not whose Reel it is.
SC = 'AbC-d_12345'


def test_shortcode_from_url_forms():
    for u in (f'https://www.instagram.com/reel/{SC}/', f'https://www.instagram.com/someone/reel/{SC}/?igsh=x',
              f'https://www.instagram.com/p/{SC}', f'https://www.instagram.com/reels/{SC}/', SC):
        assert P.shortcode_from(u) == SC, u
    for bad in ('https://example.com/reel/', 'not a shortcode!'):
        try: P.shortcode_from(bad); assert False, bad
        except ValueError: pass


def test_media_igid_is_base64_digits():
    # The alphabet is A-Z a-z 0-9 - _, read as base-64 digits, most significant first.
    assert P.media_igid('AAAAA') == '0'
    assert P.media_igid('AAAAB') == '1'
    assert P.media_igid('AAABA') == '64'
    assert P.media_igid('AAA__') == str(63 * 64 + 63)
    try: P.media_igid('bad!'); assert False
    except ValueError: pass


def test_signals_on_real_error_bodies():
    assert P.signal(200, P.split_stream(SIGNED_OUT))[0] == 'logged_out'
    assert P.signal(401, RATE_LIMITED)[0] == 'rate_limit'
    assert P.signal(429, '')[0] == 'rate_limit'


def test_signed_out_answer_has_no_insights():
    data, meta = P.merge(P.split_stream(SIGNED_OUT))
    assert data is None and meta['errors'] and meta['is_final'] is True


def test_scrub_and_garbage():
    s = json.dumps(P.scrub_signed_urls({'video_url': 'https://scontent.cdninstagram.com/x?oh=1&oe=2', 'n': {'thumbnail_url': 'https://x'}}))
    assert 'cdninstagram' not in s and 'oh=' not in s
    try: P.split_stream('<!DOCTYPE html><html>'); assert False, 'HTML must raise FormatChanged'
    except P.FormatChanged: pass


if __name__ == '__main__':
    n = 0
    for k, f in list(globals().items()):
        if k.startswith('test_'): f(); n += 1; print('ok', k)
    print(f'{n} tests passed')
