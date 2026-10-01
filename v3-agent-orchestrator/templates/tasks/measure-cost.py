#!/usr/bin/env python3
"""Tokenbruk per todo/rolle/modell fra subagent-transkripter (denne sesjonen + evt. flere).

Bruk: python3 tasks/measure-cost.py <since-iso> [<session-dir>...] [--html <sti>] [--cutover <iso>]
  session-dir = ~/.claude/projects/<kanonisert-prosjektsti>/<session-id>
  Uten session-dir brukes alle sesjoner under prosjektmappa.
  --html <sti>     skriver målesiden (artifact, fast lenke) — stien SKAL stå rett etter flagget.
  --trend          skriver trend-dommene som tekst (for §8c i coordinator-runbook.md) og
                   avslutter med exit 1 hvis minst én måling har gått i feil retning.
  --cutover <iso>  skillet før/etter kostnadsgrepene (standard 2026-09-15T18:30Z).
  MEASURE_ROWS=<sti.json> skriver i tillegg radene som JSON (legg den i scratchpad, ikke i repoet).
Dedupliserer usage per message.id (strømmede svar gjentar usage per content-blokk).
Vektet = input + 1.25*cache_create + 0.1*cache_read + 5*output (relativ til input-pris, samme modell).
"""
import json, os, re, subprocess, sys, glob
from collections import defaultdict

args = sys.argv[1:]
def _opt(flag, default=None):
    if flag in args:
        i = args.index(flag); v = args[i + 1]; del args[i:i + 2]; return v
    return default
html_path = _opt('--html')
# Fjern flagget FRA args, ikke bare les det fra sys.argv: `dirs = args[1:]` tolker ellers
# «--trend» som en sesjonskatalog, og hele kostnadssiden blir tom uten at noe feiler.
want_trend = '--trend' in args
if want_trend:
    args.remove('--trend')
cutover = _opt('--cutover', '2026-09-15T18:30')
# Claude Code kanoniserer prosjektstien ved å bytte hvert ikke-alfanumeriske tegn
# med `-`. Utledes fra repo-roten — IKKE fra cwd — så malen verken bærer én utviklers
# hjemmekatalog inn i et nytt prosjekt eller bommer fra en worktree.
#
# cwd-varianten var en vakuøs vakt: alle loop-agenter jobber i worktrees, og derfra
# ga den `…-<repo>--claude-worktrees-agent-xxxx`, en katalog som ikke finnes.
# Resultatet var `dirs = []` → `rows = []` → «SUM: $0.00» med exit 0, uten én advarsel.
# (Kode-review PR #852 runde 2, 2026-09-17.)
def _project_dir():
    """Kanonisert sesjonskatalog for repoet vi står i, sett fra hvilken som helst worktree."""
    try:
        common = subprocess.check_output(
            ['git', 'rev-parse', '--path-format=absolute', '--git-common-dir'],
            text=True, stderr=subprocess.DEVNULL).strip()
        root = os.path.dirname(common)          # …/repo/.git → …/repo
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        root = os.getcwd()
    return os.path.expanduser('~/.claude/projects/' + re.sub(r'[^a-zA-Z0-9]', '-', root))


PROJECT_DIR = _project_dir()
since = args[0]
dirs = args[1:] or sorted(d for d in glob.glob(os.path.join(PROJECT_DIR, '*')) if os.path.isdir(os.path.join(d, 'subagents')))

# Et tomt `dirs` skal ALDRI kunne leses som en måling: uten denne vakten rapporterer
# scriptet «SUM: $0.00» med exit 0 når PROJECT_DIR peker feil. (Kode-review PR #852.)
if not dirs:
    sys.exit(f'ingen sesjonskataloger med subagents under {PROJECT_DIR}\n'
             f'  cwd = {os.getcwd()}\n'
             f'  Dette er IKKE et $0-resultat — det er en manglende måling.')


def weight(u):
    return (u['in'] + 1.25 * u['cc'] + 0.1 * u['cr'] + 5 * u['out'])

# USD per MTok (platform.claude.com/docs/en/about-claude/pricing, hentet 2026-09-15;
# Opus 5.5 lagt til 2026-09-23 fra claude-api-skillens modelltabell):
# (input, cache-write 5m, cache-write 1h, cache-read, output)
PRICES = {
    # Opus 5.5 er billigere per token enn Opus 5. Uten egen rad prises den som 'opus', og et
    # modellbytte ser da 25 % dyrere ut enn det er. Cache-write = standard 1,25x / 2x av input.
    'opus-5-5': (4, 5.00, 8, 0.20, 20),
    'opus': (5, 6.25, 10, 0.50, 25),       # Opus 5 / 4.8 / 4.7 / 4.6 / 4.5
    'sonnet-5': (2, 2.50, 4, 0.20, 10),
    'sonnet': (3, 3.75, 6, 0.30, 15),      # Sonnet 4.x
    'haiku': (1, 1.25, 2, 0.10, 5),
    'fable': (10, 12.50, 20, 0.25, 50),
}
def price_of(model):
    m = model or ''
    for k in ('sonnet-5', 'opus-5-5', 'opus', 'sonnet', 'haiku', 'fable'):
        if k in m: return PRICES[k]
    return PRICES['opus']

def usd(u, model):
    pi, p5, p1, pr, po = price_of(model)
    cc = u.get('cache_creation') or {}
    c5 = cc.get('ephemeral_5m_input_tokens'); c1 = cc.get('ephemeral_1h_input_tokens')
    if c5 is None and c1 is None:
        c5, c1 = (u.get('cache_creation_input_tokens') or 0), 0
    return ((u.get('input_tokens') or 0) * pi + (c5 or 0) * p5 + (c1 or 0) * p1
            + (u.get('cache_read_input_tokens') or 0) * pr + (u.get('output_tokens') or 0) * po) / 1e6

def todo_of(desc):
    d = desc or ''
    m = (re.search(r'TODO\s*([0-9]+[A-Za-z]?)', d) or re.search(r'\bPR\s*#?(\d{3})', d)
         or re.search(r'\b([0-9]{2,3}[A-Z]?)\b', d))
    return m.group(1) if m else '-'

rows = []
for d in dirs:
    for f in glob.glob(os.path.join(d, 'subagents', 'agent-*.jsonl')):
        meta_p = f.replace('.jsonl', '.meta.json')
        meta = json.load(open(meta_p)) if os.path.exists(meta_p) else {}
        seen = {}
        models = set()
        t0 = t1 = None
        for line in open(f, encoding='utf-8', errors='replace'):
            try:
                e = json.loads(line)
            except Exception:
                continue
            ts = e.get('timestamp')
            if ts:
                t0 = ts if t0 is None or ts < t0 else t0
                t1 = ts if t1 is None or ts > t1 else t1
            msg = e.get('message') or {}
            u = msg.get('usage')
            if not u or not isinstance(msg, dict):
                continue
            mid = msg.get('id') or id(e)
            models.add(msg.get('model', '?'))
            seen[mid] = (u, msg.get('model', '?'))
        if not t0 or t0 < since:
            continue
        tot = defaultdict(int)
        tot_usd = 0.0
        for u, mdl in seen.values():
            tot_usd += usd(u, mdl)
            tot['in'] += u.get('input_tokens', 0) or 0
            tot['cc'] += u.get('cache_creation_input_tokens', 0) or 0
            tot['cr'] += u.get('cache_read_input_tokens', 0) or 0
            tot['out'] += u.get('output_tokens', 0) or 0
        rows.append({
            'agent': os.path.basename(f)[6:-6], 'type': meta.get('agentType', '?'),
            'desc': meta.get('description', ''), 'parent': meta.get('parentAgentId'),
            'model': ','.join(sorted(m for m in models if m and m != '<synthetic>')),
            't0': t0, 't1': t1, **tot, 'w': 0, 'usd': tot_usd,
        })
for r in rows:
    r['w'] = weight(r)

# Knytt lens-agenter (parent = code-reviewer) til forelderens todo
by_id = {r['agent']: r for r in rows}
for r in rows:
    r['todo'] = todo_of(r['desc'])
    p = r['parent']
    while r['todo'] == '-' and p and p in by_id:
        r['todo'] = todo_of(by_id[p]['desc']); p = by_id[p]['parent']

def fmt(n): return f"{n/1000:,.0f}k"

if os.environ.get('MEASURE_ROWS'):
    json.dump(rows, open(os.environ['MEASURE_ROWS'], 'w'), indent=1)

print(f"Agenter siden {since}: {len(rows)}")
agg = defaultdict(lambda: defaultdict(float))
for r in rows:
    for k in ('in', 'cc', 'cr', 'out', 'w', 'usd'):
        agg[(r['todo'])][k] += r[k]
    agg[r['todo']]['n'] += 1
print("\n== Per todo (vektet, sortert) ==")
for t, a in sorted(agg.items(), key=lambda x: -x[1]['w']):
    print(f"{t:>6}  agenter={int(a['n']):3d}  vektet={fmt(a['w']):>8}  usd=${a['usd']:>7.2f}  output={fmt(a['out']):>7}  cache_read={fmt(a['cr']):>8}")

agg2 = defaultdict(lambda: defaultdict(float))
for r in rows:
    key = (r['type'], r['model'])
    for k in ('out', 'w', 'usd'): agg2[key][k] += r[k]
    agg2[key]['n'] += 1
print("\n== Per rolle/modell ==")
for (t, m), a in sorted(agg2.items(), key=lambda x: -x[1]['w']):
    print(f"{t:>26} {m:>22}  n={int(a['n']):3d}  vektet={fmt(a['w']):>8}  snitt={fmt(a['w']/a['n']):>7}  usd=${a['usd']:>7.2f}  usd/kjøring=${a['usd']/a['n']:>5.2f}  output={fmt(a['out']):>7}")

print("\n== Enkeltagenter, topp 25 (vektet) ==")
for r in sorted(rows, key=lambda r: -r['w'])[:25]:
    print(f"${r['usd']:>6.2f} {fmt(r['w']):>8}  {r['todo']:>5}  {r['type']:>24}  {r['model']:>18}  {r['t0'][5:16]}  {r['desc'][:60]}")

print(f"\nSUM underagenter: ${sum(r['usd'] for r in rows):.2f}")

if html_path or want_trend:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import measure_cost_html

if html_path:
    measure_cost_html.render(html_path, rows, dirs, since, cutover, usd)
    print(f"HTML skrevet: {html_path}")

if want_trend:
    # Samme data og samme dom som trend-seksjonen i artifactet — ÉN kilde, slik at en
    # graf som viser oppgang og en §8c-kjøring som sier «uendret» aldri kan sprike.
    sys.exit(measure_cost_html.trend_report(rows, dirs, since, usd))
