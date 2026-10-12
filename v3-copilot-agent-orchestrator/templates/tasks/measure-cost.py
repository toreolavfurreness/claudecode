#!/usr/bin/env python3
"""Kostnad i AI credits per todo, økt, rolle og modell — fra Copilot-sesjonslogger og run-loggen.

Bruk: python3 tasks/measure-cost.py [<since-iso>] [<session-dir>...] [flagg]
  session-dir = $COPILOT_HOME/session-state/<session-id> (standard ~/.copilot/session-state/<id>)
  Uten session-dir brukes alle økter under session-state som ble startet i dette repoet
  (`cwd` i økta er repo-roten eller en mappe under den, også `.loop-worktrees/…`).

Kilder:
  1. `assistant.usage`-hendelser i øktens `events.jsonl` (model, inputTokens, outputTokens, cost,
     cacheReadTokens, cacheWriteTokens). Formen er tolerant: hendelsen kan ligge som
     {"type": "assistant.usage", "data": {...}} eller med feltene på toppnivå; ukjente felt ignoreres.
     `cost` summeres som AI credits. Hendelsene er flyktige og lagres normalt IKKE i events.jsonl;
     finnes de ikke, måler denne kilden ingenting.
  2. Manuelle tall fra `/usage` (tokens og AI credits per modell for økta):
     - per todo: tokenet `credits=<n>` i todoens run-log-rad (docs/loop/run-log.md), skrevet av
       koordinatoren. Flere rader for samme todo summeres.
     - på kommandolinja: `--credits <n>` (se flaggene under).
  Mangler begge, står tallet som `IKKE MÅLT` — aldri 0, aldri gjettet.

Flagg:
  --html <sti>     skriver målesiden (fast lenke) — stien SKAL stå rett etter flagget.
  --trend          skriver trend-dommene som tekst (for §8c i coordinator-runbook.md) og
                   avslutter med exit 1 hvis minst én måling har gått i feil retning.
  --cutover <iso>  skillet før/etter kostnadsgrepene (standard 2026-09-15T18:30Z).
  --release <ver>  bare todoene i releasens scope (`tasks/release.py scope <ver>`): kost per release.
  --brake <nr>     kostnadsbrems: én linje `brake todo=… class=… credits=… median=… n=… over=…`.
                   over=yes når todoens credits > 2× medianen for arkiverte todoer i samme effort-klasse.
                   over=few når klassen har færre enn 5 andre todoer med målte credits (ingen median).
                   over=unknown når effort-klassen mangler ELLER todoens credits er IKKE MÅLT.
                   Todoens tall: `--credits <n>` (fra `/usage`, så langt i todoen) hvis gitt, ellers
                   summen av `credits=` i run-loggen.
  --pr <n>         (med --brake) todoens åpne PR: rader tilskrevet `PR<n>` legges til todoens sum.
  --brake-self-test  7 asserts mot brake_verdict/fold_pr.
  --calibrate      summen av `assistant.usage.cost` i én økt mot `/usage`-tallet for samme økt:
                   `calibrate session=… usage=… events=… diff=…% over=…`. Krever `--credits <n>` og
                   økta (`--session <id>`, `$COPILOT_SESSION_ID` eller nøyaktig én session-dir).
                   Exit 1 ved over=yes (avvik > 10 %), exit 2 når en side mangler (IKKE MÅLT).
  --calibrate-self-test  kjører CLI-en mot konstruerte økter og run-logger.
  --main-credits   credits per økt (koordinator + underagenter i samme økt), én linje per økt med
                   hendelser i vinduet og to SUM-linjer. Med `--session <id> --credits <n>` brukes
                   `/usage`-tallet for den økta. Exit 2 når ingen økt er målt.
  --until <iso>    (med --main-credits) øvre grense for vinduet, til og med. Uten --main-credits: exit 2.
  --session <id>   økt-ID (mappe under session-state, eller en sti). Standard: $COPILOT_SESSION_ID.
  --credits <n>    manuelt AI credits-tall fra `/usage`. Gjelder bare sammen med --brake,
                   --calibrate eller --main-credits; et tall for en ferdig todo skrives som
                   `credits=<n>` i run-log-raden.
  Uten <since-iso> brukes nå − 30 dager (UTC).
  MEASURE_ROWS=<sti.json> skriver i tillegg todo-radene som JSON (legg den i scratchpad, ikke i repoet).
UVERIFISERT: hvor lenge Copilot beholder session-state, om VS Code-økter skrives dit, og at summen av
`cost` er lik AI credits i `/usage`. `--calibrate` er beviset for det siste; kjør den før tallene
fra events.jsonl brukes i en beslutning.
Dedupliserer `assistant.usage` per id (samme id to ganger telles én gang, siste linje vinner).
"""
import json, os, re, subprocess, sys, glob
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import median

_RANK = {'S': 1, 'M': 2, 'L': 3}
NOT_MEASURED = 'IKKE MÅLT'


def effort_class(v):
    """Største av S < M < L i en effort-verdi (`M/L` → L). None hvis ingen."""
    found = re.findall(r'[SML]', v or '')
    return max(found, key=_RANK.get) if found else None


def brake_verdict(nr, credits_by_todo, class_by_todo, cls):
    """(median|None, n, over) — over ∈ {'yes','no','few','unknown'}.

    En todo uten målte credits er `unknown`, aldri `no`: 0 er ikke en måling."""
    nr = str(nr).lower()
    cr_l = {str(k).lower(): v for k, v in credits_by_todo.items()}
    cls_l = {str(k).lower(): v for k, v in class_by_todo.items()}
    if cls is None or nr not in cr_l:
        return None, 0, 'unknown'
    sample = [cr_l[t] for t, c in cls_l.items() if c == cls and t != nr and t in cr_l]
    if len(sample) < 5:
        return None, len(sample), 'few'
    med = median(sample)
    return med, len(sample), 'yes' if cr_l[nr] > 2 * med else 'no'


def fold_pr(nr, credits_by_todo, pr):
    """Legg `PR<pr>`-radene til todo `nr` (en åpen PR finnes ikke i PR_TODO før merge-raden)."""
    out = dict(credits_by_todo)
    if pr and 'PR' + str(pr) in out:
        nr = next((k for k in out if str(k).lower() == str(nr).lower()), nr)
        out[nr] = out.get(nr, 0.0) + out.pop('PR' + str(pr))
    return out


def _brake_self_test():
    cl = {str(i): 'M' for i in range(1, 6)}
    cr = {str(i): 10.0 for i in range(1, 6)}
    assert brake_verdict('99', {**cr, '99': 25.0}, {**cl, '99': 'M'}, 'M') == (10.0, 5, 'yes'), 'over'
    assert brake_verdict('99', {**cr, '99': 15.0}, {**cl, '99': 'M'}, 'M') == (10.0, 5, 'no'), 'under'
    assert brake_verdict('99', {'1': 1.0, '99': 99.0}, {'1': 'M'}, 'M') == (None, 1, 'few'), 'få utvalg'
    four = {k: v for k, v in cr.items() if k != '5'}
    assert brake_verdict('99', {**four, '99': 99.0}, cl, 'M') == (None, 4, 'few'), 'fire er for få'
    assert brake_verdict('99', cr, cl, None)[2] == 'unknown', 'ukjent klasse'
    assert brake_verdict('99', cr, cl, 'M') == (None, 0, 'unknown'), 'IKKE MÅLT er unknown, ikke no'
    assert fold_pr('99', {'99': 8.0, 'PR1091': 1.5}, '1091') == {'99': 9.5}, 'PR-rad teller i credits='
    print('brake-self-test: 7/7')


# ---------------------------------------------------------------------------
# Copilot-sesjonslogger
# ---------------------------------------------------------------------------

def copilot_home():
    return os.environ.get('COPILOT_HOME') or os.path.expanduser('~/.copilot')


def session_root():
    return os.path.join(copilot_home(), 'session-state')


def _ts(v):
    """Tidsstempel → 'YYYY-MM-DDTHH:MM:SS' (UTC). Godtar ISO-streng og epoch (s eller ms)."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        sec = v / 1000 if v > 1e11 else v
        return datetime.fromtimestamp(sec, timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
    if isinstance(v, str) and re.match(r'\d{4}-\d\d-\d\dT', v):
        return v[:19]
    return ''


def _num(d, *keys):
    for k in keys:
        v = d.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return v
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                pass
    return None


def usage_of(e):
    """Én `assistant.usage`-hendelse → dict, ellers None. Tolerant for begge formene."""
    if not isinstance(e, dict):
        return None
    if (e.get('type') or e.get('event') or e.get('kind')) != 'assistant.usage':
        return None
    d = e.get('data') if isinstance(e.get('data'), dict) else e
    i, o = _num(d, 'inputTokens', 'input_tokens') or 0, _num(d, 'outputTokens', 'output_tokens') or 0
    cr = _num(d, 'cacheReadTokens', 'cache_read_tokens') or 0
    cw = _num(d, 'cacheWriteTokens', 'cache_write_tokens') or 0
    agent = None
    for src in (d, e):
        agent = agent or src.get('agentName') or src.get('agentType') or src.get('agent_type')
    return {
        'id': d.get('id') or e.get('id') or d.get('apiCallId') or d.get('requestId'),
        'ts': _ts(e.get('timestamp') or d.get('timestamp') or e.get('ts')),
        'model': d.get('model') or '?',
        'in': int(i), 'out': int(o), 'cr': int(cr), 'cw': int(cw), 'ctx': int(i + cr + cw),
        'credits': _num(d, 'cost', 'credits'),
        'agent': agent if isinstance(agent, str) and agent else None,
        'effort': d.get('reasoningEffort') or d.get('reasoning_effort') or d.get('effort'),
    }


def read_usage(session_dir):
    """Unike `assistant.usage`-hendelser i én økt (siste linje vinner per id)."""
    f = os.path.join(session_dir, 'events.jsonl')
    seen = {}
    if not os.path.exists(f):
        return []
    for n, line in enumerate(open(f, encoding='utf-8', errors='replace')):
        try:
            e = json.loads(line)
        except Exception:
            continue
        u = usage_of(e)
        if u is None:
            continue
        u['session'] = os.path.basename(session_dir.rstrip('/'))
        seen[u['id'] or ('#', n)] = u
    return list(seen.values())


def session_cwd(d):
    """Arbeidsmappa økta ble startet i (workspace.yaml eller session.start-hendelsen), ellers None."""
    ws = os.path.join(d, 'workspace.yaml')
    if os.path.exists(ws):
        for line in open(ws, encoding='utf-8', errors='replace'):
            m = re.match(r'\s*cwd:\s*["\']?(.+?)["\']?\s*$', line)
            if m:
                return m.group(1)
    f = os.path.join(d, 'events.jsonl')
    if os.path.exists(f):
        for k, line in enumerate(open(f, encoding='utf-8', errors='replace')):
            if k > 50:
                break
            try:
                e = json.loads(line)
            except Exception:
                continue
            if not isinstance(e, dict):
                continue
            data = e.get('data') if isinstance(e.get('data'), dict) else {}
            ctx = data.get('context') if isinstance(data.get('context'), dict) else {}
            cwd = e.get('cwd') or data.get('cwd') or ctx.get('cwd')
            if isinstance(cwd, str) and cwd:
                return cwd
    return None


# Repo-roten utledes fra git-common-dir — IKKE fra cwd — så målingen treffer det samme repoet
# fra hovedsjekkouten og fra hver worktree under .loop-worktrees/.
def _repo_root():
    """Hovedsjekkoutens rot, sett fra hvilken som helst worktree, ellers cwd."""
    try:
        common = subprocess.check_output(
            ['git', 'rev-parse', '--path-format=absolute', '--git-common-dir'],
            text=True, stderr=subprocess.DEVNULL).strip()
        return os.path.dirname(common)          # …/repo/.git → …/repo
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return os.getcwd()


def project_sessions():
    """(økter i dette repoet, antall økter uten kjent cwd). Ukjent cwd tas IKKE med stille:
    tallet meldes, så en tom måling ikke kan leses som 0."""
    root = os.path.realpath(_repo_root())
    out, unknown = [], 0
    for d in sorted(glob.glob(os.path.join(session_root(), '*'))):
        if not os.path.isdir(d):
            continue
        cwd = session_cwd(d)
        if cwd is None:
            unknown += 1
            continue
        cwd = os.path.realpath(cwd)
        if cwd == root or cwd.startswith(root + os.sep):
            out.append(d)
    return out, unknown


def resolve_session(sid):
    if not sid:
        return None
    return sid.rstrip('/') if os.path.isdir(sid) else os.path.join(session_root(), sid)


# ---------------------------------------------------------------------------
# Run-loggen: credits per todo
# ---------------------------------------------------------------------------

_KEY = r'([0-9]+(?:[A-Za-z][0-9]*)?)'
_CREDITS = re.compile(r'(?<![\w-])credits=([0-9]+(?:[.,][0-9]+)?)(?![\w.,])')
RUN_LOG = 'docs/loop/run-log.md'


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


def ledger_rows(since, path=RUN_LOG):
    """Én rad per run-log-rad med `credits=<n>`: {todo, credits, t0, outcome, …}."""
    rows = []
    try:
        lines = open(path, encoding='utf-8').read().splitlines()
    except OSError:
        return rows
    for ln in lines:
        c = [x.strip() for x in ln.split(' | ')]
        ts = re.sub(r'^\|\s*', '', c[0])
        if len(c) < 4 or not re.match(r'\d{4}-\d\d-\d\dT', ts):
            continue
        m = _CREDITS.search(ln)
        if not m or c[1] in ('-', '') or ts < since:
            continue
        rows.append({'todo': c[1], 'type': 'todo', 'agent': None, 'parent': None, 'desc': c[2],
                     'model': '-', 't0': ts, 't1': ts, 'credits': float(m.group(1).replace(',', '.')),
                     'source': 'run-log', 'outcome': c[3]})
    return rows


def _sum_by_todo(rows):
    out = defaultdict(float)
    for r in rows:
        out[r['todo']] += r['credits']
    return dict(out)


def fmt_cr(x):
    return NOT_MEASURED if x is None else f'{x:,.2f}'


# ---------------------------------------------------------------------------
# Kalibrering og per økt
# ---------------------------------------------------------------------------

# Terskel 10 %: summen av `cost` i events.jsonl skal stemme med `/usage` for samme økt. Et større
# avvik betyr at hendelsene er ufullstendige eller at `cost` ikke er AI credits, og da er
# events-tallene ikke en måling før årsaken er funnet.
CALIB_THRESHOLD = 10.0


def calibrate(session_dir, usage_credits, since):
    """Summen av `cost` i økta mot `/usage`. Exit 0 innenfor 10 %, 1 over, 2 IKKE MÅLT."""
    if not session_dir or not os.path.isdir(session_dir):
        print(f'calibrate: fant ikke økta ({session_dir or "ingen --session"}) — {NOT_MEASURED}.', file=sys.stderr)
        return 2
    sid = os.path.basename(session_dir.rstrip('/'))
    ev = [u for u in read_usage(session_dir) if u['ts'] >= since]
    with_cost = [u for u in ev if u['credits'] is not None]
    if usage_credits is None:
        print(f'calibrate session={sid[:8]} usage={NOT_MEASURED} hendelser={len(ev)} — oppgi --credits <n> fra /usage.')
        return 2
    if not with_cost:
        print(f'calibrate session={sid[:8]} usage={usage_credits:.2f} events={NOT_MEASURED} '
              f'(ingen assistant.usage med cost i events.jsonl)')
        return 2
    own = sum(u['credits'] for u in with_cost)
    if usage_credits == 0:
        diff = 0.0 if own == 0 else 100.0
    else:
        diff = 100.0 * (own - usage_credits) / usage_credits
    over = abs(diff) > CALIB_THRESHOLD
    print(f'calibrate session={sid[:8]} usage={usage_credits:.2f} events={own:.2f} n={len(with_cost)} '
          f'uten_cost={len(ev) - len(with_cost)} diff={diff:+.1f}% over={"yes" if over else "no"}')
    return 1 if over else 0


def main_credits(sessions, since, until, manual_dir=None, manual=None):
    """Credits per økt. Rollen til en økt står ikke i loggen: leseren avgjør fra agents=."""
    tot = {True: [0.0, 0], False: [0.0, 0]}   # har underagenter → [credits, økter]
    unmeasured = 0
    for d in sessions:
        sid = os.path.basename(d.rstrip('/'))
        ev = [u for u in read_usage(d) if u['ts'] >= since and (not until or u['ts'][:len(until)] <= until)]
        agents = len({u['agent'] for u in ev if u['agent']})
        cost = [u['credits'] for u in ev if u['credits'] is not None]
        if manual is not None and manual_dir and d.rstrip('/') == manual_dir.rstrip('/'):
            val, src = manual, 'usage'
        elif cost:
            val, src = sum(cost), 'events'
        else:
            if ev:
                unmeasured += 1
                print(f'main session={sid[:8]} agents={agents} credits={NOT_MEASURED} n={len(ev)} '
                      '(assistant.usage uten cost)')
            continue
        tot[agents > 0][0] += val; tot[agents > 0][1] += 1
        span = (f' first={min(u["ts"] for u in ev)} last={max(u["ts"] for u in ev)}' if ev else '')
        print(f'main session={sid[:8]} agents={agents} credits={val:.2f} kilde={src} n={len(ev)}{span}')
    n = tot[True][1] + tot[False][1]
    if not n:
        print(f'main-credits: ingen økt med målte credits i vinduet — {NOT_MEASURED}. '
              'Oppgi --session <id> --credits <n> fra /usage.', file=sys.stderr)
        return 2
    tail = f', {unmeasured} økter {NOT_MEASURED}' if unmeasured else ''
    print(f'SUM økter med underagenter: {tot[True][0]:.2f} credits ({tot[True][1]} økter)')
    print(f'SUM alle økter: {tot[True][0] + tot[False][0]:.2f} credits ({n} økter{tail})')
    return 0


# ---------------------------------------------------------------------------
# Selvtest for CLI-en
# ---------------------------------------------------------------------------

def _calibrate_self_test():
    import tempfile
    def ev(ts, eid, cost=5.0, top=False, agent=None):
        d = {'id': eid, 'model': 'deep-model-a', 'inputTokens': 1000, 'outputTokens': 200,
             'cacheReadTokens': 50, 'cacheWriteTokens': 0}
        if cost is not None:
            d['cost'] = cost
        if agent:
            d['agentName'] = agent
        return ({'type': 'assistant.usage', 'timestamp': ts, **d} if top
                else {'type': 'assistant.usage', 'timestamp': ts, 'data': d})
    def session(events, name='sess0001'):
        d = os.path.join(tempfile.mkdtemp(), name)
        os.makedirs(d)
        lines = [{'type': 'session.start', 'timestamp': '2026-09-01T08:00:00.000Z',
                  'data': {'sessionId': name}}] + events
        with open(os.path.join(d, 'events.jsonl'), 'w', encoding='utf-8') as fh:
            fh.write(''.join(json.dumps(x) + '\n' for x in lines))
        return d
    two = lambda **kw: session([ev('2026-09-01T10:30:00.000Z', 'u-a', **kw), ev('2026-09-01T12:00:00.000Z', 'u-b', **kw)])
    man = session([], name='sessman')
    runlog = ('2026-09-02T10:00 | 99 | x | merged | - | #1001 | 1 | 1 | m | - | credits=12.5; fix_rounds=0\n'
              '2026-09-02T11:00 | 98 | y | merged | - | #1002 | 1 | 1 | m | - | fix_rounds=0\n'
              '2026-09-02T12:00 | 97 | z | merged | - | #1003 | 1 | 1 | m | - | xcredits=99\n')
    cases = [   # (navn, args etter since, exit, skal stå i utskriften, skal IKKE stå i stdout[, run-log])
        ('vindu', [two(), '--calibrate', '--credits', '10'], 0, ['over=no', 'events=10.00', 'usage=10.00'], []),
        ('toppnivå-form', [two(top=True), '--calibrate', '--credits', '10'], 0, ['over=no', 'events=10.00'], []),
        ('over', [two(), '--calibrate', '--credits', '20'], 1, ['over=yes', 'diff=-50.0%'], []),
        ('dedup per id', [session([ev('2026-09-01T10:30:00Z', 'u-a'), ev('2026-09-01T10:31:00Z', 'u-a')]),
                          '--calibrate', '--credits', '5'], 0, ['events=5.00', 'n=1'], []),
        ('før since', [session([ev('2019-01-01T10:00:00Z', 'u-0'), ev('2026-09-01T10:30:00Z', 'u-a')]),
                       '--calibrate', '--credits', '5'], 0, ['events=5.00'], []),
        ('epoch ms', [session([{'type': 'assistant.usage', 'timestamp': 1788258600000, 'data': {'id': 'x', 'cost': 5}}]),
                      '--calibrate', '--credits', '5'], 0, ['over=no'], []),
        ('uten --credits', [two(), '--calibrate'], 2, [NOT_MEASURED], ['over=']),
        ('uten usage-hendelser', [session([]), '--calibrate', '--credits', '10'], 2, [NOT_MEASURED], ['over=']),
        ('usage uten cost', [two(cost=None), '--calibrate', '--credits', '10'], 2, [NOT_MEASURED], ['over=']),
        ('main-credits', [two(), '--main-credits'], 0,
         ['credits=10.00', 'kilde=events', 'SUM alle økter: 10.00 credits (1 økter)'], []),
        ('main-credits underagent', [session([ev('2026-09-01T10:30:00Z', 'u-a', agent='demo-planner')]), '--main-credits'],
         0, ['agents=1', 'SUM økter med underagenter: 5.00 credits (1 økter)'], []),
        ('main-credits until', [two(), '--main-credits', '--until', '2026-09-01T11:00'], 0, ['credits=5.00'], ['credits=10.00']),
        ('main-credits manuelt', [man, '--main-credits', '--session', man, '--credits', '7'],
         0, ['credits=7.00 kilde=usage', 'SUM alle økter: 7.00'], []),
        ('main-credits uten tall', [two(cost=None), '--main-credits'], 2, [NOT_MEASURED], ['SUM ']),
        ('until uten main-credits', [two(), '--until', '2026-09-01T10:00'], 2, [], ['credits=']),
        ('credits uten mål', [two(), '--credits', '3'], 2, [], ['SUM ']),
        ('rapport uten data', [session([])], 1, [NOT_MEASURED], ['SUM', '0.00']),
        ('rapport fra run-log', [session([])], 0, ['    99', '12.50', 'SUM todoer (run-log/--credits): 12.50'],
         ['    98', '    97', 'SUM økter (assistant.usage): 0'], runlog),
        ('rapport fra events', [two()], 0, ['koordinator', 'deep-model-a', 'SUM økter (assistant.usage): 10.00',
                                            f'SUM todoer (run-log/--credits): {NOT_MEASURED}'], []),
        ('brake fra run-log', [session([]), '--brake', '99'], 0, ['credits=12.50', 'over=unknown'], [], runlog),
        ('brake uten tall', [session([]), '--brake', '98'], 0, ['credits=IKKE-MÅLT', 'over=unknown', NOT_MEASURED], [], runlog),
        ('brake --credits', [session([]), '--brake', '98', '--credits', '4'], 0, ['credits=4.00'], [], runlog),
    ]
    env = {k: v for k, v in os.environ.items() if k != 'COPILOT_SESSION_ID'}
    for name, rest, code, has, hasnt, *log in cases:
        cwd = tempfile.mkdtemp()
        os.makedirs(os.path.join(cwd, 'docs', 'loop'))
        if log:
            open(os.path.join(cwd, RUN_LOG), 'w', encoding='utf-8').write(log[0])
        # COPILOT_HOME peker på en tom mappe: bare øktene i argumentene teller.
        r = subprocess.run([sys.executable, os.path.abspath(__file__), '2020-01-01T00:00', *rest],
                           capture_output=True, text=True, cwd=cwd, env={**env, 'COPILOT_HOME': cwd})
        out = r.stdout + r.stderr
        assert (r.returncode == code and all(x in out for x in has)
                and not any(x in r.stdout for x in hasnt)), f'{name}: exit={r.returncode} {r.stdout!r} {r.stderr[-300:]!r}'
    print(f'calibrate-self-test: {len(cases)}/{len(cases)}')


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

args = sys.argv[1:]
def _opt(flag, default=None):
    if flag in args:
        i = args.index(flag); v = args[i + 1]; del args[i:i + 2]; return v
    return default
def _flag(flag):
    if flag in args:
        args.remove(flag); return True
    return False
if '--brake-self-test' in args:
    _brake_self_test(); sys.exit(0)
if '--calibrate-self-test' in args:
    _calibrate_self_test(); sys.exit(0)
want_calibrate = _flag('--calibrate')
brake_nr = _opt('--brake')
brake_pr = _opt('--pr')
html_path = _opt('--html')
release = _opt('--release')
# Fjern flagget FRA args, ikke bare les det fra sys.argv: `explicit = args[1:]` tolker ellers
# «--trend» som en sesjonskatalog, og hele kostnadssiden blir tom uten at noe feiler.
want_trend = _flag('--trend')
cutover = _opt('--cutover', '2026-09-15T18:30')
want_main = _flag('--main-credits')
until = _opt('--until')
session_arg = _opt('--session') or os.environ.get('COPILOT_SESSION_ID')
credits_arg = _opt('--credits')
if until and not want_main:
    print('--until gjelder bare sammen med --main-credits', file=sys.stderr)
    sys.exit(2)
if credits_arg is not None:
    try:
        credits_arg = float(credits_arg.replace(',', '.'))
    except ValueError:
        print(f'--credits må være et tall, fikk {credits_arg!r}', file=sys.stderr)
        sys.exit(2)
    if not (brake_nr or want_calibrate or want_main):
        print('--credits gjelder bare sammen med --brake, --calibrate eller --main-credits. '
              'Et tall for en ferdig todo skrives som `credits=<n>` i run-log-raden.', file=sys.stderr)
        sys.exit(2)

since = args[0] if args else (datetime.now(timezone.utc) - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M')
explicit = [d.rstrip('/') for d in args[1:]]
for d in explicit:
    if not os.path.isdir(d):
        sys.exit(f'FEIL: {d} er ikke en sesjonskatalog (forventet $COPILOT_HOME/session-state/<id>)')
if explicit:
    sessions, unknown_cwd = explicit, 0
else:
    sessions, unknown_cwd = project_sessions()

if want_calibrate:
    target = resolve_session(session_arg) or (explicit[0] if len(explicit) == 1 else None)
    sys.exit(calibrate(target, credits_arg, since))

if want_main:
    manual_dir = resolve_session(session_arg) if credits_arg is not None else None
    if manual_dir and manual_dir not in sessions:
        sessions = sessions + [manual_dir]   # /usage-tallet står på egne ben, også uten lokal logg
    sys.exit(main_credits(sessions, since, until, manual_dir, credits_arg))

# ---- Data ----
events = [u for d in sessions for u in read_usage(d) if u['ts'] >= since]
rows = ledger_rows(since)

if brake_nr:
    cr_by = _sum_by_todo(rows)
    if credits_arg is not None:
        key0 = next((k for k in cr_by if str(k).lower() == brake_nr.lower()), brake_nr)
        cr_by[key0] = credits_arg     # ferskeste tall: /usage så langt i todoen
    cr_by = fold_pr(brake_nr, cr_by, brake_pr)
    archived, active = effort_classes()
    key = brake_nr.lower()
    cls = ({k.lower(): v for k, v in active.items()}.get(key)
           or {k.lower(): v for k, v in archived.items()}.get(key))
    med, n, over = brake_verdict(brake_nr, cr_by, archived, cls)
    mine = {k.lower(): v for k, v in cr_by.items()}.get(key)
    why = ''
    if mine is None:
        why = (f' {NOT_MEASURED}: ingen `credits=` i run-loggen for todoen — oppgi --credits <n> '
               'fra /usage; manglende data er nivå A')
    elif cls is None:
        why = ' (effort-klassen mangler — sett `effort` i todo-fila)'
    print(f"brake todo={brake_nr} class={cls or '?'} credits={'IKKE-MÅLT' if mine is None else f'{mine:.2f}'} "
          f"median={'-' if med is None else f'{med:.2f}'} n={n} over={over}" + why)
    sys.exit(0)

if release:
    # Tomt scope gir ellers en tom tabell med exit 0, som ser ut som en billig release.
    _sc = subprocess.run([sys.executable, 'tasks/release.py', 'scope', release], capture_output=True, text=True)
    scope = set(_sc.stdout.split())
    if _sc.returncode != 0 or not scope:
        sys.exit(f"FEIL: fant ingen todoer i scope for release {release} ({_sc.stderr.strip() or 'tomt scope'})")
    rows = [r for r in rows if r['todo'] in scope]
    print(f"Release {release}: {len(scope)} todoer i scope, {len(rows)} run-log-rader med credits= knyttet til dem")

if os.environ.get('MEASURE_ROWS'):
    json.dump(rows, open(os.environ['MEASURE_ROWS'], 'w'), indent=1)

# Ingen kilde i det hele tatt skal ALDRI kunne leses som en måling på 0.
if not rows and not events and not release:
    sys.exit(f'{NOT_MEASURED}: ingen `credits=` i {RUN_LOG} og ingen assistant.usage-hendelser i '
             f'{len(sessions)} økter under {session_root()} siden {since}'
             + (f' ({unknown_cwd} økter uten kjent cwd ble hoppet over — oppgi dem som session-dir)' if unknown_cwd else '')
             + '.\n  Dette er IKKE et 0-resultat — det er en manglende måling. Skriv `credits=<n>` fra /usage i run-log-raden.')

def fmt(n): return f"{n/1000:,.0f}k"

print(f"Kilder siden {since}: {len(rows)} run-log-rader med credits=, {len(sessions)} økter "
      f"({len({u['session'] for u in events})} med assistant.usage, {len(events)} hendelser)"
      + (f', {unknown_cwd} økter uten kjent cwd hoppet over' if unknown_cwd else ''))

print("\n== Per todo (AI credits fra run-loggen / --credits, sortert) ==")
per_todo = _sum_by_todo(rows)
if not per_todo:
    print(f"  {NOT_MEASURED}: ingen todo har `credits=` i run-loggen i vinduet")
for t, v in sorted(per_todo.items(), key=lambda x: -x[1]):
    n = sum(1 for r in rows if r['todo'] == t)
    print(f"{t:>6}  rader={n:3d}  credits={v:>9.2f}")

agg = defaultdict(lambda: {'n': 0, 'credits': 0.0, 'miss': 0, 'in': 0, 'out': 0, 'cr': 0, 'cw': 0})
for u in events:
    a = agg[(u['agent'] or 'koordinator', u['model'])]
    a['n'] += 1
    for k in ('in', 'out', 'cr', 'cw'):
        a[k] += u[k]
    if u['credits'] is None:
        a['miss'] += 1
    else:
        a['credits'] += u['credits']
print("\n== Per rolle/modell (assistant.usage) ==")
if not events:
    print(f"  {NOT_MEASURED}: ingen assistant.usage-hendelser i events.jsonl (de lagres normalt ikke — bruk /usage)")
for (t, m), a in sorted(agg.items(), key=lambda x: -x[1]['credits']):
    c = f"{a['credits']:>8.2f}" if a['n'] > a['miss'] else f'{NOT_MEASURED:>8}'
    print(f"{t:>26} {m:>22}  kall={a['n']:4d}  credits={c}  input={fmt(a['in']):>7}  output={fmt(a['out']):>7}  "
          f"cache_read={fmt(a['cr']):>8}  cache_write={fmt(a['cw']):>7}" + (f"  uten_cost={a['miss']}" if a['miss'] else ''))

print("\n== Per økt (assistant.usage) ==")
per_s = defaultdict(list)
for u in events:
    per_s[u['session']].append(u)
for sid, us in sorted(per_s.items(), key=lambda x: min(u['ts'] for u in x[1])):
    cost = [u['credits'] for u in us if u['credits'] is not None]
    print(f"  session={sid[:8]}  kall={len(us):4d}  credits={fmt_cr(sum(cost) if cost else None)}  "
          f"{min(u['ts'] for u in us)[:16]} – {max(u['ts'] for u in us)[:16]}")

print(f"\nSUM todoer (run-log/--credits): {fmt_cr(sum(per_todo.values()) if per_todo else None)}")
ev_cost = [u['credits'] for u in events if u['credits'] is not None]
print(f"SUM økter (assistant.usage): {fmt_cr(sum(ev_cost) if ev_cost else None)}")

if html_path or want_trend:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import measure_cost_html

if html_path:
    measure_cost_html.render(html_path, rows, events, since, cutover)
    print(f"HTML skrevet: {html_path}")

if want_trend:
    # Samme data og samme dom som trend-seksjonen i siden — ÉN kilde, slik at en
    # graf som viser oppgang og en §8c-kjøring som sier «uendret» aldri kan sprike.
    sys.exit(measure_cost_html.trend_report(rows, events, since))
