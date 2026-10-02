#!/usr/bin/env python3
"""Tokenbruk per todo/rolle/modell fra subagent-transkripter (denne sesjonen + evt. flere).

Bruk: python3 tasks/measure-cost.py [<since-iso>] [<session-dir>...] [--html <sti>] [--cutover <iso>]
  session-dir = ~/.claude/projects/<kanonisert-prosjektsti>/<session-id>
  Uten session-dir brukes alle sesjoner under prosjektmappa.
  --html <sti>     skriver målesiden (artifact, fast lenke) — stien SKAL stå rett etter flagget.
  --trend          skriver trend-dommene som tekst (for §8c i coordinator-runbook.md) og
                   avslutter med exit 1 hvis minst én måling har gått i feil retning.
  --cutover <iso>  skillet før/etter kostnadsgrepene (standard 2026-09-15T18:30Z).
  --release <ver>  bare todoene i releasens scope (`tasks/release.py scope <ver>`): kost per release.
  --brake <nr>     kostnadsbrems (TODO 455): én linje `brake todo=… class=… usd=… median=… n=… over=…`.
                   over=yes når todoens kost > 2× medianen for arkiverte todoer i samme effort-klasse.
  --pr <n>         (med --brake) todoens åpne PR: rader tilskrevet `PR<n>` (review/fix før merge-raden
                   finnes i run-loggen) legges til todoens sum. Uten --pr teller de ikke med.
  --brake-self-test  5 asserts mot brake_verdict/fold_pr.
  Uten <since-iso> brukes nå − 30 dager (UTC).
  MEASURE_ROWS=<sti.json> skriver i tillegg radene som JSON (legg den i scratchpad, ikke i repoet).
Merk: Claude Code sletter transkripter eldre enn `cleanupPeriodDays` (standard 30 dager), så et
vindu lenger tilbake blir stille ufullstendig. Hev innstillingen før du måler lengre perioder.
Dedupliserer usage per message.id (strømmede svar gjentar usage per content-blokk).
Vektet = input + 1.25*cache_create + 0.1*cache_read + 5*output (relativ til input-pris, samme modell).
"""
import json, os, re, subprocess, sys, glob
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import median

_RANK = {'S': 1, 'M': 2, 'L': 3}

def effort_class(v):
    """Største av S < M < L i en effort-verdi (`M/L` → L). None hvis ingen."""
    found = re.findall(r'[SML]', v or '')
    return max(found, key=_RANK.get) if found else None

def brake_verdict(nr, usd_by_todo, class_by_todo, cls):
    """(median|None, n, over) — over ∈ {'yes','no','unknown'}."""
    nr = str(nr).lower()
    usd_l = {str(k).lower(): v for k, v in usd_by_todo.items()}
    cls_l = {str(k).lower(): v for k, v in class_by_todo.items()}
    if cls is None:
        return None, 0, 'unknown'
    sample = [usd_l[t] for t, c in cls_l.items() if c == cls and t != nr and t in usd_l]
    if len(sample) < 5:
        return None, len(sample), 'no'
    med = median(sample)
    return med, len(sample), 'yes' if usd_l.get(nr, 0.0) > 2 * med else 'no'

def fold_pr(nr, usd_by_todo, pr):
    """Legg `PR<pr>`-radene til todo `nr` (en åpen PR finnes ikke i PR_TODO før merge-raden)."""
    out = dict(usd_by_todo)
    if pr:
        nr = next((k for k in out if str(k).lower() == str(nr).lower()), nr)
        out[nr] = out.get(nr, 0.0) + out.pop('PR' + str(pr), 0.0)
    return out

def _brake_self_test():
    cl = {str(i): 'M' for i in range(1, 6)}
    us = {str(i): 10.0 for i in range(1, 6)}
    assert brake_verdict('99', {**us, '99': 25.0}, {**cl, '99': 'M'}, 'M') == (10.0, 5, 'yes'), 'over'
    assert brake_verdict('99', {**us, '99': 15.0}, {**cl, '99': 'M'}, 'M') == (10.0, 5, 'no'), 'under'
    assert brake_verdict('99', {'1': 1.0, '99': 99.0}, {'1': 'M'}, 'M') == (None, 1, 'no'), 'få utvalg'
    assert brake_verdict('99', us, cl, None)[2] == 'unknown', 'ukjent klasse'
    assert fold_pr('99', {'99': 8.0, 'PR1091': 1.5}, '1091') == {'99': 9.5}, 'PR-rad teller i usd='
    print('brake-self-test: 5/5')

_KEY = r'([0-9]+(?:[A-Za-z][0-9]*)?)'

def effort_classes():
    """({todo: klasse} for arkiverte todoer fra git-slettinger, {todo: klasse} for aktive)."""
    archived, active = {}, {}
    out = subprocess.run(['git', 'log', '--diff-filter=D', '-p', '--format=', '--', 'tasks/todos/'],
                         capture_output=True, text=True).stdout
    cur = None
    for ln in out.splitlines():
        m = re.match(r'diff --git a/tasks/todos/todo-' + _KEY + '-', ln)
        if m:
            # Nyeste sletting vinner (git log går fra nyeste til eldste).
            cur = m.group(1) if m.group(1) not in archived else None
            continue
        if cur and ln.startswith('-effort:'):
            archived[cur] = effort_class(ln[len('-effort:'):]); cur = None
    for f in glob.glob('tasks/todos/todo-*.md'):
        m = re.match(r'todo-' + _KEY + '-', os.path.basename(f))
        if not m:
            continue
        for ln in open(f, encoding='utf-8'):
            if ln.startswith('effort:'):
                active[m.group(1)] = effort_class(ln[len('effort:'):]); break
    return archived, active


args = sys.argv[1:]
def _opt(flag, default=None):
    if flag in args:
        i = args.index(flag); v = args[i + 1]; del args[i:i + 2]; return v
    return default
if '--brake-self-test' in args:
    _brake_self_test(); sys.exit(0)
brake_nr = _opt('--brake')
brake_pr = _opt('--pr')
html_path = _opt('--html')
release = _opt('--release')
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


# Alle prosjektmapper som inneholder repo-stien, ikke bare hovedsjekkoutens: en koordinator som
# kjører fra en worktree eller scratchpad får egen mappe (`…-<repo>--claude-worktrees-…`,
# `…-<repo>-…-scratchpad-…`). Med bare hovedmappa var 64 % av én release usynlig i
# opphavsprosjektet (målt 2026-09-27).
PROJECT_DIR = os.path.join(os.path.dirname(_project_dir()), '*' + os.path.basename(_project_dir()) + '*')
since = args[0] if args else (datetime.now(timezone.utc) - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M')
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

# PR-nummer → todo fra run-loggens merge-rader (`| <todo> | <slug> | merged | - | #NNNN |`). Uten dette
# ble «PR 1007» lest som todo 100 (`\d{3}` tok de tre første sifrene).
PR_TODO = {}
try:
    for _ln in open('docs/superpowers/loop/run-log.md', encoding='utf-8'):
        _c = [x.strip() for x in _ln.split(' | ')]
        if len(_c) > 5 and _c[3] == 'merged':
            for _pr in re.findall(r'(?:#|/pull/)(\d{3,5})', _c[5]):
                PR_TODO[_pr] = _c[1]
except OSError:
    pass

def todo_of(desc):
    d = desc or ''
    m = re.search(r'TODO\s*([0-9]+(?:[A-Za-z][0-9]*)?)', d)
    if m:
        return m.group(1)
    m = re.search(r'\bPR\s*#?(\d{3,5})\b', d)
    if m:
        return PR_TODO.get(m.group(1), 'PR' + m.group(1))
    m = re.search(r'\b([0-9]{2,3}(?:[A-Z][0-9]*)?)\b', d)
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
        # Nøklene settes eksplisitt: en agent uten usage-rader ennå (nettopp startet) ga
        # ellers KeyError i weight() og felte hele målesiden.
        tot = defaultdict(int, {'in': 0, 'cc': 0, 'cr': 0, 'out': 0})
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

if brake_nr:
    usd_by = defaultdict(float)
    for r in rows:
        usd_by[r['todo']] += r['usd']
    usd_by = fold_pr(brake_nr, usd_by, brake_pr)
    archived, active = effort_classes()
    key = brake_nr.lower()
    cls = ({k.lower(): v for k, v in active.items()}.get(key)
           or {k.lower(): v for k, v in archived.items()}.get(key))
    med, n, over = brake_verdict(brake_nr, usd_by, archived, cls)
    mine = {k.lower(): v for k, v in usd_by.items()}.get(key, 0.0)
    print(f"brake todo={brake_nr} class={cls or '?'} usd={mine:.2f} "
          f"median={'-' if med is None else f'{med:.2f}'} n={n} over={over}")
    sys.exit(0)

if release:
    # Tomt scope gir ellers «SUM: $0.00» med exit 0, som ser ut som en billig release.
    _sc = subprocess.run([sys.executable, 'tasks/release.py', 'scope', release], capture_output=True, text=True)
    scope = set(_sc.stdout.split())
    if _sc.returncode != 0 or not scope:
        sys.exit(f"FEIL: fant ingen todoer i scope for release {release} ({_sc.stderr.strip() or 'tomt scope'})")
    rows = [r for r in rows if r['todo'] in scope]
    print(f"Release {release}: {len(scope)} todoer i scope, {len(rows)} agenter knyttet til dem")

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
