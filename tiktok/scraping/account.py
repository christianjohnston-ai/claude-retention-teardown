#!/usr/bin/env python3
"""Which TikTok account a teardown run is for: its folder, its @handle and its cmux browser profile.

Usage:
  python3 ~/.claude/skills/tiktok-retention-teardown/scraping/account.py add <name> <@handle>   # a new account: folder + cmux profile
  python3 ~/.claude/skills/tiktok-retention-teardown/scraping/account.py show [<name>]          # print the resolved paths
  python3 ~/.claude/skills/tiktok-retention-teardown/scraping/account.py list                   # every account and which is the default

Every account lives in accounts/<name>/ with the same layout: account.json, library/, runs/, narrative.json,
account_notes.md (written by the analyst once there are settled videos), retention-teardown.html and media/.
No account is built into the code. Setup creates the first one with `add`, and the first account added is the
default: a script run without --account uses it. Any other account is opt-in with `--account <name>`.
accounts/ is gitignored, so nobody's analytics can reach the public repository by accident.

Why a separate cmux browser profile per account (tt-<name>): TikTok keeps one signed-in account per browser profile,
so signing account B into account A's profile would sign A out. Each account's login lives in its own profile and
every account stays signed in at once.
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.realpath(__file__))
# realpath, not abspath: the skill is installed as a symlink (~/.claude/skills/tiktok-retention-teardown -> the clone).
# Resolving it means the data folders and the shared .venv are found next to the real files, however the script was called.
SKILL_ROOT = os.path.dirname(HERE)
ACCOUNTS = os.path.join(SKILL_ROOT, 'accounts')
STARTER = os.path.join(SKILL_ROOT, 'narrative.json')    # the empty page content every new account starts from
VENV = os.path.join(os.path.dirname(SKILL_ROOT), '.venv')   # claude-retention-teardown/.venv, shared with the Instagram skill
NAME_RE = r'[a-z0-9][a-z0-9_-]*'
ADD_HINT = 'python3 ~/.claude/skills/tiktok-retention-teardown/scraping/account.py add <name> <@handle>'


def names():
    """Account names that have an account.json, sorted."""
    if not os.path.isdir(ACCOUNTS): return []
    return sorted(n for n in os.listdir(ACCOUNTS) if os.path.exists(os.path.join(ACCOUNTS, n, 'account.json')))


def _cfg(name):
    return json.load(open(os.path.join(ACCOUNTS, name, 'account.json')))


def default_name():
    """The account a run uses when no --account is given: the only account, else the one marked "default": true."""
    ns = names()
    if not ns:
        sys.exit(f'No TikTok account yet. Create the first one with: {ADD_HINT}')
    if len(ns) == 1: return ns[0]
    marked = [n for n in ns if _cfg(n).get('default')]
    if len(marked) == 1: return marked[0]
    sys.exit('More than one TikTok account and no single default. Pass --account <name>. Known: '
             + ', '.join(f'{n} (@{_cfg(n)["handle"]})' for n in ns))


def load(name=None):
    """Resolve an account to {name, handle, profile, root, page_dir, since}. None = the default account.

    root     = where library/, runs/ and narrative.json live.
    page_dir = where retention-teardown.html and its media/ hard links live. cmux's browser only reads files inside
               the page's own folder, so the page and media/ must be siblings (here both are the account folder).
    profile  = the cmux browser profile TikTok Studio is opened in.
    """
    if name in (None, ''):
        name = default_name()
    if not re.fullmatch(NAME_RE, name):
        sys.exit(f'Bad account name "{name}": use lowercase letters, digits, - and _ only.')
    root = os.path.join(ACCOUNTS, name)
    if not os.path.exists(os.path.join(root, 'account.json')):
        sys.exit(f'Unknown account "{name}". Known: {", ".join(names()) or "none"}. Create it with: {ADD_HINT}')
    cfg = _cfg(name)
    # since = YYYY-MM-DD: only posts created on or after this day are tracked. Set by hand in account.json when a
    # large back catalog should not be analyzed (video downloads, Whisper and Gemini cost minutes per post). None = all.
    return {'name': name, 'handle': cfg['handle'].lstrip('@'), 'profile': cfg.get('profile') or f'tt-{name}',
            'root': root, 'page_dir': root, 'since': cfg.get('since')}


def from_argv(argv=None):
    """Pull `--account <name>` out of argv (so scripts with their own positional args keep working) and resolve it."""
    argv = sys.argv if argv is None else argv
    name = None
    for i, a in enumerate(argv):
        if a == '--account' and i + 1 < len(argv):
            name = argv[i + 1]; del argv[i:i + 2]; break
        if a.startswith('--account='):
            name = a.split('=', 1)[1]; del argv[i]; break
    return load(name)


def add(name, handle):
    handle = handle.lstrip('@').strip()
    if not handle: sys.exit('Give the TikTok @handle, e.g. account.py add main @your_handle')
    if not re.fullmatch(NAME_RE, name): sys.exit(f'Bad account name "{name}": use lowercase letters, digits, - and _ only.')
    root = os.path.join(ACCOUNTS, name)
    if os.path.exists(os.path.join(root, 'account.json')): sys.exit(f'{root}/account.json already exists; edit it by hand.')
    first = not names()
    os.makedirs(os.path.join(root, 'library'), exist_ok=True); os.makedirs(os.path.join(root, 'runs'), exist_ok=True)
    profile = f'tt-{name}'
    json.dump({'handle': handle, 'profile': profile, 'default': first, 'since': None},
              open(os.path.join(root, 'account.json'), 'w'), indent=1)
    # Every account starts from the same EMPTY page content. Lessons, rewrite cards and the verdict are never copied
    # from another account: they are conclusions about that account's own videos and would be false for this one.
    np_ = os.path.join(root, 'narrative.json')
    if not os.path.exists(np_):
        json.dump(json.load(open(STARTER)), open(np_, 'w'), indent=2, ensure_ascii=False)
    try:
        r = subprocess.run(['cmux', 'browser', 'profiles', 'add', profile], capture_output=True, text=True)
        made = (r.stdout or r.stderr).strip() or 'added'
    except FileNotFoundError:
        made = 'NOT created (the cmux command was not found; run this inside a cmux terminal, or create it later with: ' \
               f'cmux browser profiles add {profile})'
    print(f'created {root}' + (' (the default account)' if first else '') + f'\ncmux profile "{profile}": {made}')
    print(f'Next: check the sign-in (the first time it opens a TikTok Studio tab in that profile for you to sign in as @{handle}):\n'
          f'  python3 ~/.claude/skills/tiktok-retention-teardown/scraping/daily.py' + ('' if first else f' --account {name}') + ' --check')


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
    elif a[:1] == ['show']: print(json.dumps(load(a[1] if len(a) > 1 else None), indent=1))
    elif a[:1] == ['list']:
        ns = names()
        if not ns: print(f'No TikTok account yet. Create one with: {ADD_HINT}')
        for n in ns:
            c = _cfg(n); print(f'{n}  @{c["handle"]}  profile {c.get("profile") or "tt-" + n}' + ('  (default)' if c.get('default') else ''))
    else: sys.exit(__doc__)
