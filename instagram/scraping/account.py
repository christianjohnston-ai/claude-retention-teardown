#!/usr/bin/env python3
"""Which Instagram account a teardown run is for: alias, @handle, cmux browser profile, data folder, official token.

Usage:
  python3 ~/.claude/skills/instagram-retention-teardown/scraping/account.py add <alias> <@handle>    # a new account: folder + cmux profile ig-<alias>
  python3 ~/.claude/skills/instagram-retention-teardown/scraping/account.py show [<alias>]           # print the resolved config (never a token)
  python3 ~/.claude/skills/instagram-retention-teardown/scraping/account.py login <alias>            # open Instagram's sign-in page in that account's profile
  python3 ~/.claude/skills/instagram-retention-teardown/scraping/account.py check <alias|all>        # who is signed in? (writes only web_pk, once)
  python3 ~/.claude/skills/instagram-retention-teardown/scraping/account.py unpause <alias>          # clear a pause after the user cleared Instagram's prompt

Every account lives in accounts/<alias>/ (account.json, library/, runs/, state/, narrative.json, account_notes.md once
written, retention-teardown.html, media/). No account is built into the code and every account is equal; setup creates
the first one with `add`. accounts/ is gitignored, so nobody's analytics can reach the public repository by accident.

Why one cmux browser profile per account: each named profile is its own WebKit data store on disk
(~/Library/WebKit/com.cmuxterm.app/WebsiteDataStore/<uuid>/), so the Instagram logins never share cookies.
A pane or workspace does NOT isolate anything; only the profile does (verified when this was built, cmux 0.64).

The official Instagram API is optional. Its token and the account's Instagram user id are read from the environment or
from the skill folder's .env (gitignored): by default IG_TOKEN_<ALIAS> and IG_USER_ID_<ALIAS> (alias in capitals, - as _).
account.json may name other variables in "token_env" / set "graph_user_id"; it never holds the token itself.
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.realpath(__file__))
# realpath, not abspath: the skill is installed as a symlink (~/.claude/skills/instagram-retention-teardown -> the clone).
SKILL_ROOT = os.path.dirname(HERE)
ACCOUNTS = os.path.join(SKILL_ROOT, 'accounts')
STARTER = os.path.join(SKILL_ROOT, 'narrative.json')       # the empty page content every new account starts from
VENV = os.path.join(os.path.dirname(SKILL_ROOT), '.venv')   # claude-retention-teardown/.venv, shared with the TikTok skill
ALIAS_RE = r'[a-z0-9][a-z0-9_-]*'
ADD_HINT = 'python3 ~/.claude/skills/instagram-retention-teardown/scraping/account.py add <alias> <@handle>'


def path(alias, *p): return os.path.join(ACCOUNTS, alias, *p)


def aliases():
    return sorted(a for a in os.listdir(ACCOUNTS) if os.path.exists(path(a, 'account.json'))) if os.path.isdir(ACCOUNTS) else []


def env_value(key):
    """A setting from the environment, else from the skill folder's .env (gitignored). Callers never print it."""
    v = os.environ.get(key)
    if v and v.strip(): return v.strip()
    p = os.path.join(SKILL_ROOT, '.env')
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if line.startswith('export '): line = line[7:].strip()
            if line.startswith(key + '='):
                return line.split('=', 1)[1].strip().strip('"\'') or None
    return None


def _env_suffix(alias): return alias.upper().replace('-', '_')


def load(alias):
    """Resolve an alias (or an @handle) to its config dict. Exits with a clear message if unknown."""
    alias = resolve(alias)
    cfg = json.load(open(path(alias, 'account.json')))
    token_env = cfg.get('token_env') or f'IG_TOKEN_{_env_suffix(alias)}'
    # The user id pins the official token to this account (collect.token_identity). It is not a secret, but it is
    # personal, so it lives in .env next to the token by default rather than in a file that might get shared.
    graph_user_id = cfg.get('graph_user_id') or env_value(f'IG_USER_ID_{_env_suffix(alias)}')
    return {'alias': alias, 'handle': cfg['handle'].lstrip('@'), 'profile': cfg['profile'], 'web_pk': cfg.get('web_pk'),
            'graph_user_id': str(graph_user_id) if graph_user_id else None, 'token_env': token_env, 'since': cfg.get('since'),
            'eligible': cfg.get('eligible'), 'reels': cfg.get('reels') or [], 'root': path(alias)}


def resolve(name):
    """Alias, '@handle' or 'handle' -> alias."""
    if not aliases(): sys.exit(f'No Instagram account yet. Create the first one with: {ADD_HINT}')
    if not name: sys.exit('Name an account: ' + ', '.join(aliases()))
    n = name.strip().lstrip('@').lower()
    if n in aliases(): return n
    for a in aliases():
        if json.load(open(path(a, 'account.json')))['handle'].lstrip('@').lower() == n: return a
    sys.exit(f'Unknown account "{name}". Known: ' + ', '.join(f"{a} (@{json.load(open(path(a, 'account.json')))['handle']})" for a in aliases()))


def save_field(alias, key, value):
    p = path(alias, 'account.json'); cfg = json.load(open(p)); cfg[key] = value
    json.dump(cfg, open(p, 'w'), indent=1)


def token(acct):
    """The official API token for this account, from the environment or the skill .env. Never printed or stored elsewhere."""
    return env_value(acct['token_env']) if acct.get('token_env') else None


def add(alias, handle):
    if not re.fullmatch(ALIAS_RE, alias): sys.exit(f'Bad alias "{alias}": lowercase letters, digits, - and _ only.')
    handle = handle.lstrip('@').strip()
    if not handle: sys.exit('Give the Instagram @handle.')
    if os.path.exists(path(alias, 'account.json')): sys.exit(f'{path(alias, "account.json")} exists; edit it by hand.')
    for d in ('library', 'runs', 'state'): os.makedirs(path(alias, d), exist_ok=True)
    json.dump({'handle': handle, 'profile': f'ig-{alias}', 'web_pk': None, 'graph_user_id': None, 'token_env': None,
               'since': None, 'eligible': None, 'reels': []}, open(path(alias, 'account.json'), 'w'), indent=1)
    # Lessons, rewrite cards and the verdict start EMPTY: they are conclusions earned from that account's own Reels and
    # are never copied from TikTok or from another Instagram account (same rule as the TikTok skill).
    if not os.path.exists(path(alias, 'narrative.json')):
        json.dump(json.load(open(STARTER)), open(path(alias, 'narrative.json'), 'w'), indent=2, ensure_ascii=False)
    try:
        r = subprocess.run(['cmux', 'browser', 'profiles', 'add', f'ig-{alias}'], capture_output=True, text=True)
        made = (r.stdout or r.stderr).strip() or 'added'
    except FileNotFoundError:
        made = 'NOT created (the cmux command was not found; run this inside a cmux terminal, or create it later with: ' \
               f'cmux browser profiles add ig-{alias})'
    print(f'created {path(alias)}; cmux profile ig-{alias}: {made}')
    print(f'Next: python3 ~/.claude/skills/instagram-retention-teardown/scraping/account.py login {alias}')


def login(alias):
    a = load(alias)
    args = ['cmux', '--json', 'browser', 'open', 'https://www.instagram.com/accounts/login/', '--profile', a['profile'], '--focus', 'true']
    if os.environ.get('CMUX_WORKSPACE_ID'): args += ['--workspace', os.environ['CMUX_WORKSPACE_ID']]
    r = subprocess.run(args, capture_output=True, text=True)
    try: s = json.loads(r.stdout).get('surface_ref')
    except Exception: sys.exit(f'could not open a cmux browser: {r.stdout} {r.stderr}')
    label_tab(s, a)
    print(f'Opened {s} in profile {a["profile"]}, labeled "Sign in here as @{a["handle"]}". The user signs in there '
          f'(password, 2FA, "Save login info"). Never use "Switch accounts" inside this profile. Then: account.py check {a["alias"]}')


def label_tab(s, a):
    """Put the "Sign in here as @handle" banner on sign-in tab `s`. Used by login() and by collect.py when it leaves a
    sign-in page open after NOT_SIGNED_IN: every tab where the user may type a password must say which account it is for.
    When this was built, the wrong account was once signed into a profile anyway; the identity gate caught it."""
    # A visible label naming the account this tab is for. With two sign-in tabs open it was impossible to tell which
    # surface was which, and easy to sign an account into the wrong profile. So: one sign-in tab at a time (step 01
    # closes the others first), and this banner on every page of the flow (addinitscript re-adds it after the 2FA
    # navigations). Display only: pointer-events none, it reads nothing and sends nothing.
    banner = ("(()=>{const add=()=>{if(document.getElementById('rt-acct-label'))return;const d=document.createElement('div');"
              "d.id='rt-acct-label';d.textContent=%s;d.style.cssText='position:fixed;top:0;left:0;right:0;z-index:2147483647;"
              "background:#d95926;color:#fff;font:600 17px -apple-system,system-ui,sans-serif;text-align:center;padding:12px;pointer-events:none';"
              "(document.body||document.documentElement).appendChild(d)};if(document.readyState==='loading')"
              "document.addEventListener('DOMContentLoaded',add);else add();})()") % json.dumps(
                  f'Sign in here as @{a["handle"]}  ·  cmux profile {a["profile"]}  ·  only this account in this tab')
    subprocess.run(['cmux', 'browser', s, 'addinitscript', '--script', banner], capture_output=True, text=True)
    subprocess.run(['cmux', 'browser', s, 'wait', '--load-state', 'complete', '--timeout', '20'], capture_output=True, text=True)
    subprocess.run(['cmux', 'browser', s, 'eval', '--script', banner], capture_output=True, text=True)


def unpause(alias):
    a = load(alias); p = path(a['alias'], 'state', 'pause.json')
    if not os.path.exists(p): print(f'{a["alias"]}: not paused'); return
    old = json.load(open(p)); os.remove(p)
    print(f'{a["alias"]}: pause cleared (was: {old.get("reason")} at {old.get("at")}). Run check before collecting.')


def show(alias=None):
    for x in ([resolve(alias)] if alias else aliases()):
        a = load(x); a['token_present'] = token(a) is not None
        a['paused'] = json.load(open(path(x, 'state', 'pause.json'))) if os.path.exists(path(x, 'state', 'pause.json')) else None
        print(json.dumps(a, indent=1))
    if not aliases(): print(f'No Instagram account yet. Create one with: {ADD_HINT}')


def use_venv():
    """Re-run the calling script inside claude-retention-teardown/.venv when that venv exists and this is not it yet.

    WHY: mlx-whisper needs Python 3.10 or newer, and Homebrew's Python refuses `pip install` outside a virtual
    environment (PEP 668), so setup installs the packages into one venv shared by both skills. Re-running here lets
    every step file keep calling plain `python3`. No venv = nothing happens, so packages installed another way still work.
    """
    py = os.path.join(VENV, 'bin', 'python')
    if not os.path.exists(py) or os.environ.get('RT_IN_VENV'): return
    if os.path.realpath(sys.prefix) == os.path.realpath(VENV): return
    os.environ['RT_IN_VENV'] = '1'      # guard: never loop if the venv's python somehow reports another prefix
    os.execv(py, [py] + sys.argv)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] in (['--help'], ['-h']): print(__doc__); sys.exit(0)
    if a[:1] == ['add'] and len(a) == 3: add(a[1], a[2])
    elif a[:1] == ['login'] and len(a) == 2: login(a[1])
    elif a[:1] == ['unpause'] and len(a) == 2: unpause(a[1])
    elif a[:1] == ['show']: show(a[1] if len(a) > 1 else None)
    elif a[:1] == ['check'] and len(a) == 2:
        import collect  # the identity gate lives with the collector so check and collect can never disagree
        sys.exit(collect.check_cli(a[1]))
    else: sys.exit(__doc__)
