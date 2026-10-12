#!/usr/bin/env python3
"""Tallgrunnlaget for retroen etter en release (mal: docs/superpowers/loop/retro-template.md).

Bruk: python3 tasks/retro-numbers.py <versjon> --since <iso> [--until <iso>]
      python3 tasks/retro-numbers.py --self-test

Skriver markdown til stdout: runder, beslutninger, kostnad, hovedsesjoner, diff, ledetid og bugs.
`--since`/`--until` avgrenser beslutninger og hovedsesjoner. Kostnad, runder og diff er avgrenset
av releasens scope. Kjøres fra rota av repoet. Diff og ledetid trenger `gh` med nett.
Beslutningsloggen fører lokal tid og transkriptene UTC: samme `--since` kutter dem ulikt.
Kalibreringen under Kostnad limes inn uansett utfall og setter aldri exit-koden.

Det som ikke kan måles, står som `IKKE MÅLT: <årsak>`, aldri som 0.
  exit 0  alle seksjoner målt
  exit 1  minst én seksjon er IKKE MÅLT, helt eller på én linje (`- … IKKE MÅLT: <årsak>`)
  exit 2  tomt scope (også ukjent release) eller feil bruk. Ingenting skrives til stdout.
"""
import importlib.util, json, os, re, subprocess, sys, tempfile
from datetime import datetime
from statistics import mean, median

RUNLOG, DECLOG = 'docs/superpowers/loop/run-log.md', 'docs/superpowers/loop/decision-log.md'
# Første treff vinner, ellers appkode. Substituert av /setup fra `retro_file_classes` i loop.config.yaml,
# ikke lest ved kjøring. Endre lista der og kjør /setup på nytt.
{{RETRO_FILE_CLASSES}}
NOT_MEASURED = ['tid per steg i prod-releasen', 'støy i full e2e-suite']
# Høyeste bugnummer og datoen da `Oppdaget`-linja ble påkrevd. Udaterte oppføringer til og med
# nummeret fantes den dagen. (0, '') = linja har vært påkrevd fra første bug.
BUGS_RULE = (0, '')
_spec = importlib.util.spec_from_file_location(   # filnavnet har bindestrek
    'decision_level', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'decision-level.py'))
_dl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_dl)
SLAG = _dl.SLAG


class NotMeasured(Exception):
    pass


def no(x, d=None):
    """Norsk tallform: mellomrom mellom tusener, komma som desimaltegn."""
    if d is None and x != int(x):
        d = 1
    return (f'{x:,.{d}f}' if d is not None else f'{int(x):,}').replace(',', ' ').replace('.', ',')


def stat(label, vals, unit='TODO', d=1, money=False):
    """Én linje for {nøkkel: tall}: sum, median, snitt og høyest med nøkkel."""
    top, f = max(vals, key=vals.get), (lambda x: no(x, 2)) if money else no
    return (f'- {label}: sum {f(sum(vals.values()))}, median {f(median(vals.values()))}, '
            f'snitt {no(mean(vals.values()), 2 if money else d)}, høyest {f(vals[top])} ({unit} {top})')


def classify(path):
    return next((name for name, pats in CLASSES if any(p in path for p in pats)), 'appkode')


def merged_rows(runlog_text, scope):
    """[(todo, kolonner, linje)] for `merged`-radene i scope."""
    rows = ((([x.strip() for x in ln.split(' | ')]), ln) for ln in runlog_text.splitlines())
    return [(c[1], c, ln) for c, ln in rows if len(c) > 7 and c[3] == 'merged' and c[1] in scope]


def pr_todos(runlog_text, scope):
    """{PR-nummer: todo} fra kolonne 5 (samme regex som measure-cost.py)."""
    return {pr: nr for nr, c, _ in merged_rows(runlog_text, scope)
            for pr in re.findall(r'(?:#|/pull/)(\d{3,4})', c[5])}


def rounds(runlog_text, scope):
    names = ['plan-review', 'kode-review', 'fix-runder (`fix_rounds=`)', 'auto_decided']
    per = {}
    for nr, c, ln in merged_rows(runlog_text, scope):
        v = per.setdefault(nr, [0, 0, 0, 0])
        v[0] += int(c[6]) if c[6].isdigit() else 0
        v[1] += int(c[7]) if c[7].isdigit() else 0
        v[2] += sum(int(n) for n in re.findall(r'fix_rounds=(\d+)', ln))
        v[3] += sum(int(n) for _, n in _dl._TOKEN.findall(ln))   # samme regex som D4: nøkkelen kan ha bindestrek
    if not per:
        raise NotMeasured('ingen `merged`-rad i run-loggen for todoene i scope')
    out = [f'{len(scope)} todoer i scope, {len(per)} med `merged`-rad.']
    for i, name in enumerate(names):
        vals = {nr: v[i] for nr, v in per.items()}
        tail = sorted((nr for nr, n in vals.items() if n >= 3), key=lambda nr: -vals[nr])
        out.append(stat(name, vals) + f'. Tre eller flere: {len(tail)}'
                   + (f" ({', '.join(f'{nr}: {vals[nr]}' for nr in tail)})" if tail else ''))
    missing = sorted(set(scope) - set(per))
    return '\n'.join(out + [f"- Todoer i scope uten rad: {', '.join(missing) or 'ingen'}"])


def decisions(text, since, until):
    lines = text.splitlines()
    heads = [i for i, l in enumerate(lines) if re.match(r'#{2,3} ', l)] + [len(lines)]
    rules, slag, a0, total, unknown, waits = {}, {}, [], 0, [], []
    untyped = se = waiting = unprompted = nowait = 0
    t_re = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2})'
    for k, i in enumerate(heads[:-1]):
        m = re.match(r'### (\d{4}-\d{2}-\d{2})(?: (\d{2}:\d{2}))?', lines[i])
        ts = m and f"{m.group(1)}T{m.group(2) or '00:00'}"
        if not ts or ts < since or (until and ts[:len(until)] > until):
            continue
        total += 1
        rule = re.search(r'\[([AB]\d)\]', lines[i])   # merket står ikke på fast plass i overskriften
        if not rule:
            continue
        rules[rule.group(1)] = rules.get(rule.group(1), 0) + 1
        if rule.group(1) != 'A0':
            continue
        field = lambda name: next((l.split(':**', 1)[1].strip() for l in lines[i:heads[k + 1]]
                                   if l.startswith(f'- **{name}:**')), None)
        svar, t = field('Eierens svar') or '', field('Type')
        if _dl._SE.match(svar):   # svaret har egen oppføring, og den teller
            se += 1
            continue
        kind = t and SLAG.get(t.split(':')[0].strip())
        if kind:
            slag[kind] = slag.get(kind, 0) + 1
        elif t:
            unknown.append(t)
        else:
            untyped += 1
        if not kind:
            a0.append(lines[i])
        m = re.search(rf'\(spurt {t_re}, svart {t_re}\)', svar)
        if svar.lower().startswith('venter'):
            waiting += 1
        elif '(uoppfordret)' in svar.lower():
            unprompted += 1
        elif m and m.group(2) >= m.group(1):   # overskriftstiden brukes aldri
            h = (datetime.fromisoformat(m.group(2)) - datetime.fromisoformat(m.group(1))).total_seconds() / 3600
            todo = re.search(r'TODO (\w+)', lines[i])
            waits.append((h, f'TODO {todo.group(1)}' if todo else ts))
        else:
            nowait += 1
    if not total:
        raise NotMeasured(f"ingen overskrift i beslutningsloggen i vinduet {since} til {until or 'nå'}")
    level = lambda x: sum(n for r, n in rules.items() if r[0] == x)
    out = [f'{total} overskrifter i vinduet, {sum(rules.values())} med regelmerke, '
           f'{total - sum(rules.values())} uten.',
           f"- Nivå A: {level('A')}. Nivå B: {level('B')}.",
           '- Per regel: ' + ', '.join(f'{r}: {n}' for r, n in sorted(rules.items(), key=lambda x: (-x[1], x[0])))]
    if slag:
        out.append(f'- `[A0]` etter slag ({sum(slag.values())} med kjent `Type`): '
                   + ', '.join(f'{k}: {n}' for k, n in sorted(slag.items(), key=lambda x: (-x[1], x[0]))))
    if a0:
        out.append(f'- `[A0]` uten slag: IKKE MÅLT: {untyped} uten `Type`, {len(unknown)} med ukjent `Type`'
                   + (f" ({', '.join(sorted(set(unknown)))})" if unknown else ''))
    if waits:   # ingen sum: ventetidene overlapper
        top = max(waits)
        out.append(f'- Ventetid på eier ({len(waits)} spørsmål): median {no(median(h for h, _ in waits), 1)}, '
                   f'lengst {no(top[0], 1)} timer ({top[1]})')
    if nowait:
        out.append(f'- Ventetid på eier: IKKE MÅLT: {nowait} `[A0]` uten `spurt` og `svart`')
    out += [f'- {label}: {n}' for label, n in (('Venter fortsatt', waiting), ('Uoppfordret fra eier', unprompted),
                                               ('Besvart i egen oppføring', se)) if n]
    if a0:
        out += ['', '<details><summary>`[A0]`-overskriftene uten slag, til håndtelling</summary>', '',
                *a0, '', '</details>']
    return '\n'.join(out)


def planned(runlog_text, scope, prs):
    """Planlagt mot faktisk diff per `merged`-rad med `planned=<linjer>/<filer>`. prs: gh-svar."""
    by = {str(p['number']): p for p in prs}
    got, bad, noplan = [], [], 0
    for nr, c, ln in merged_rows(runlog_text, scope):
        tok = re.search(r'planned=([^ |;]*)', ln)
        m = re.fullmatch(r'(\d+)/(\d+)', tok.group(1) if tok else '')
        ps = [by[n] for n in re.findall(r'(?:#|/pull/)(\d{3,4})', c[5]) if n in by]
        if tok and tok.group(1) == 'n/a':
            noplan += 1
        elif m and int(m.group(1)) > 0 and not ps:
            bad.append(f'{nr}: {tok.group(1)} uten PR')
        elif m and int(m.group(1)) > 0:
            act = sum(p['additions'] + p['deletions'] for p in ps)
            got.append((act / int(m.group(1)), nr, act, m.group(1), sum(p['changedFiles'] for p in ps), m.group(2)))
        else:
            bad.append(f"{nr}: {tok.group(1) if tok else 'mangler'}")
    out = []
    if got:
        r, nr, act, pl, f, pf = max(got)
        out.append(f'- Planlagt mot faktisk diff ({len(got)} rader): linjer faktisk/planlagt median '
                   f'{no(median(g[0] for g in got), 2)}, høyest {no(r, 2)} (TODO {nr}: {act} mot {pl} linjer, {f} mot {pf} filer)')
    if noplan:
        out.append(f'- Rader uten plan (`planned=n/a`): {noplan}')
    if bad:
        out.append(f"- Planlagt diff: IKKE MÅLT: {len(bad)} rader uten gyldig `planned=` ({', '.join(bad)})")
    return '\n'.join(out)


def bugs(text, since, until):
    """Bugs oppdaget i vinduet, fra tasks/bugs.md og tasks/bugs_archive.md lest etter hverandre."""
    since, until, seen = since[:10], until and until[:10], {}   # `Oppdaget` er en dato: vinduet kuttes til dato
    for part in re.split(r'^(?=## )', text, flags=re.M):
        m = re.match(r'## BUG-(\d+)', part)
        if m:
            d = (re.search(r'^(?:- )?\*\*Oppdaget:\*\*.*?(\d{4}-\d{2}-\d{2})', part, re.M)
                 or re.search(r'^(?:- )?\*\*Oppdaget i:\*\*.*?(\d{4}-\d{2}-\d{2})', part, re.M))
            seen[int(m.group(1))] = seen.get(int(m.group(1))) or (d and d.group(1))
    if not seen:
        raise NotMeasured('ingen `## BUG-<nr>`-oppføring i tasks/bugs.md eller tasks/bugs_archive.md')
    names = lambda ns: ', '.join(f'BUG-{n}' for n in sorted(ns))
    hit = [n for n, d in seen.items() if d and since <= d and not (until and d > until)]
    new = [n for n, d in seen.items() if not d and n > BUGS_RULE[0]]
    old = len([n for n, d in seen.items() if not d and n <= BUGS_RULE[0]])
    out = [f'{len(hit)} bugs oppdaget i vinduet' + (f': {names(hit)}' if hit else '')]
    if new:
        out.append(f'- Uten datert `Oppdaget`-linje, nummer over {BUGS_RULE[0]}: IKKE MÅLT: {names(new)}')
    if old and since <= BUGS_RULE[1]:
        out.append(f'- Uten datert `Oppdaget`-linje, nummer til og med {BUGS_RULE[0]}: IKKE MÅLT: {old} oppføringer kan ligge i vinduet')
    elif old:
        out.append(f'- Uten datert `Oppdaget`-linje: {old} oppføringer som fantes {BUGS_RULE[1]}, altså eldre enn vinduet')
    return '\n'.join(out)


def cost(rows):
    if not rows:
        raise NotMeasured('ingen agenter knyttet til scopet i transkriptene')
    todo, role = {}, {}
    for r in rows:
        todo[r['todo']] = todo.get(r['todo'], 0.0) + r['usd']
        n, s = role.get(r['type'], (0, 0.0))
        role[r['type']] = (n + 1, s + r['usd'])
    top4 = sorted(todo, key=lambda t: -todo[t])[:4]
    return '\n'.join([
        f"{len(rows)} agenter, {no(sum(todo.values()), 2)} USD. Eldste `t0`: {min(r['t0'] for r in rows)[:16]} "
        '(transkripter eldre enn 30 dager er slettet, så en eldre release er stille ufullstendig).',
        stat('Per todo (USD)', todo, money=True),
        '- Fire dyreste: ' + ', '.join(f'{t}: {no(todo[t], 2)}' for t in top4),
        '- Per rolle: ' + ', '.join(f'{t}: {no(s, 2)} USD ({n} agenter)'
                                    for t, (n, s) in sorted(role.items(), key=lambda x: -x[1][1]))])


def mains(stdout, stderr=''):
    if sum(l.startswith('SUM ') for l in stdout.splitlines()) != 2:
        raise NotMeasured('measure-cost.py --main-usd ga ikke de to SUM-linjene '
                          f"({stderr.strip().splitlines()[-1] if stderr.strip() else 'ingen feiltekst'})")
    return 'Rollen til en økt står ikke i transkriptet: les `dir=` og `agents=`.\n\n```\n' + stdout.strip() + '\n```'


def diff(prs, pr_numbers, pr_todo=None, plan_t0=None):
    """prs: gh-svar (med `number`). pr_todo: {PR: todo}. plan_t0: {todo: ISO-tid planfila ble committet}."""
    if not pr_numbers:
        raise NotMeasured('ingen PR-numre i `merged`-radene for scopet')
    gone = sorted(set(map(str, pr_numbers)) - {str(p['number']) for p in prs})
    if gone or len(prs) != len(pr_numbers):
        raise NotMeasured(f"`gh` ga ikke svar for PR {', '.join(gone)}")
    ts = lambda s: datetime.fromisoformat(s.strip().replace('Z', '+00:00'))
    hours = lambda a, b: (ts(b) - ts(a)).total_seconds() / 3600
    lead = lambda v: f'median {no(median(v), 2)}, snitt {no(mean(v), 2)}, lengst {no(max(v), 1)} timer'
    out = [f'{len(prs)} PR-er.']
    for label, key in (('Linjer lagt til', 'additions'), ('Linjer fjernet', 'deletions'), ('Filer', 'changedFiles')):
        out.append(stat(label, {str(p['number']): p[key] for p in prs}, unit='PR', d=0))
    dist = {}
    for p in prs:
        # ponytail: gh gir høyst 100 filer per PR; største i 1.16.0 var 37. Bytt til gh api --paginate ved behov.
        for f in p['files']:
            dist[classify(f['path'])] = dist.get(classify(f['path']), 0) + f['additions']
    out.append('- Linjer lagt til per klasse: ' + ', '.join(f'{k}: {no(n)}' for k, n in sorted(dist.items(), key=lambda x: -x[1])))
    out.append(f"- Ledetid, PR åpnet til merget ({len(prs)} PR-er): " + lead([hours(p['createdAt'], p['mergedAt']) for p in prs]))
    last = {}
    for p in prs:
        t = (pr_todo or {}).get(str(p['number']))
        last[t] = max(last.get(t, p['mergedAt']), p['mergedAt'], key=ts)
    with_plan = [hours(plan_t0[t], m) for t, m in last.items() if (plan_t0 or {}).get(t)]
    if with_plan:
        out.append(f'- Ledetid, planfil committet til siste PR merget ({len(with_plan)} todoer): ' + lead(with_plan))
    else:
        out.append('- Ledetid fra planfil: IKKE MÅLT: ingen todo i scope har planfil i git-historikken')
    without = sorted(t for t in last if t and not (plan_t0 or {}).get(t))
    return '\n'.join(out + [f"- Todoer uten planfil: {', '.join(without) or 'ingen'}"])


def section(title, fn):
    """(tekst, målt). Ethvert unntak fra kilden blir IKKE MÅLT med årsak, aldri et tall.
    En seksjon med en `- … IKKE MÅLT: `-linje er delvis målt, og det er heller ikke målt."""
    try:
        text = fn()
        return f'## {title}\n\n{text}\n', not re.search(r'^- .*IKKE MÅLT: ', text, re.M)
    except Exception as e:
        why = str(e) if isinstance(e, NotMeasured) else f'{type(e).__name__}: {e}'
        return f'## {title}\n\nIKKE MÅLT: {why}\n', False


def render(sections):
    parts = [section(t, fn) for t, fn in sections]
    tail = '## Ikke målt\n\n' + '\n'.join(f'- IKKE MÅLT: {x}' for x in NOT_MEASURED) + '\n'
    return '\n'.join([p[0] for p in parts] + [tail]), 0 if all(p[1] for p in parts) else 1


def run(*cmd, env=None):
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


def measure(*args, env=None):
    return run(sys.executable, 'tasks/measure-cost.py', *args, env=env)


def cost_io(version, since):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'rows.json')
        r = measure('--release', version, env={**os.environ, 'MEASURE_ROWS': path})   # uten since: scopet avgrenser
        if r.returncode or not os.path.exists(path):
            raise NotMeasured(f"measure-cost.py --release {version}: {(r.stderr.strip() or f'exit {r.returncode}').splitlines()[-1]}")
        rows = json.load(open(path, encoding='utf-8'))
    text = cost(rows)
    cal = measure(since, '--calibrate')   # per økt, ikke per scope. Limes inn urørt uansett exit-kode.
    return (f'{text}\n\n### Forbehold\n\n`measure-cost.py {since} --calibrate` (exit {cal.returncode}):\n\n'
            f'```\n{(cal.stdout + cal.stderr).strip()}\n```')


def mains_io(since, until):
    r = measure(since, '--main-usd', *(['--until', until] if until else []))
    return mains(r.stdout, r.stderr)


def diff_io(runlog_text, scope):
    pr_todo = pr_todos(runlog_text, scope)
    prs = []
    for n in pr_todo:
        r = run('gh', 'pr', 'view', n, '--json', 'number,additions,deletions,changedFiles,files,createdAt,mergedAt')
        if r.returncode == 0:
            prs.append(json.loads(r.stdout))
    plan_t0 = {}
    for nr in set(pr_todo.values()):
        added = run('git', 'log', '--diff-filter=A', '--format=%cI', '--', f'tasks/plans/todo-{nr}-*.md').stdout.split()
        plan_t0[nr] = added[-1] if added else None
    return diff(prs, list(pr_todo), pr_todo, plan_t0) + '\n' + planned(runlog_text, scope, prs)


def self_test():
    global CLASSES, BUGS_RULE   # testdataene er skrevet mot disse verdiene, ikke prosjektets
    CLASSES = [('bevisrigg', ('tfiles',)), ('tester', ('e2e/', '__tests__', '.test.', '.spec.')),
               ('planer/docs/loop', ('tasks/', 'docs/', '.claude/', '.md'))]
    BUGS_RULE = (156, '2026-10-11')
    scope = {'1', '2'}
    log = ('2026-01-01T10:00 | 1 | a | merged | - | #101 | 3 | 2 | m | - | - | auto_decided=koordinator:4; planned=20/2; fix_rounds=1; x\n'
           '2026-01-01T11:00 | 9 | b | merged | - | #109 | 7 | 7 | m | - | - | auto_decided=9:7; fix_rounds=7\n')
    ok = 'fulgt (spurt 2026-01-02 10:00, svart 2026-01-02 12:30)'
    a0 = lambda hm, typ, svar: (f'### 2026-01-02 {hm} — TODO 1 [A0]: x\n\n' + (f'- **Type:** {typ}\n' if typ else '')
                                + (f'- **Eierens svar:** {svar}\n' if svar else '') + '\n')
    dlog = (a0('12:30', 'revise_gate', ok) + '### 2026-01-02 11:00 [B1] Eieren: merket foran teksten\n\n'
            + a0('12:00', 'eiervalg:farge', 'ordre: x (uoppfordret)')
            + '### 2026-01-02 13:00 uten merke\n\n### 2026-02-01 10:00 — TODO 2 [A2]: utenfor vinduet\n')
    rows = [{'todo': '1', 'type': 'implementer', 'usd': 2.5, 't0': '2026-01-01T09:00:00Z'}]
    sums = 'main session=abc\nSUM hovedsesjoner med underagenter: $1.00 (1 økter)\nSUM alle hovedsesjoner: $2.00 (2 økter)\n'
    pr = lambda n: {'number': n, 'additions': 10, 'deletions': 2, 'changedFiles': 1, 'createdAt': '2026-01-01T10:00:00Z',
                    'mergedAt': '2026-01-01T12:00:00Z', 'files': [{'path': 'app/x.tsx', 'additions': 10}]}
    win = ('2026-01-01T00:00', '2026-01-31T23:59')
    good = [('Runder', lambda: rounds(log, scope)), ('Beslutninger', lambda: decisions(dlog, *win)),
            ('Kostnad', lambda: cost(rows)), ('Hovedsesjoner', lambda: mains(sums)),
            ('Diff', lambda: diff([pr(101)], ['101'], {'101': '1'}, {'1': '2026-01-01T08:00:00+00:00'})
             + '\n' + planned(log, scope, [pr(101)]))]

    def fails(name, fn, why):
        text, code = render([(name, fn)])
        body = text.split('## Ikke målt')[0]
        assert f'IKKE MÅLT: {why}' in body and code == 1, f'{name}: tom kilde skal gi IKKE MÅLT og exit 1, fikk {code}: {body!r}'
        assert not any(x in body for x in ('0 PR-er', '$0.00', '0 agenter')), f'{name}: tom kilde ble skrevet som tall: {body!r}'

    def glad():
        text, code = render(good)
        assert code == 0 and 'IKKE MÅLT' not in text.split('## Ikke målt')[0], f'render: gladsti skal gi exit 0: {text!r}'
        assert text.count('IKKE MÅLT: ') == len(NOT_MEASURED), 'render: den faste sluttlista mangler'

    def t_rounds():
        t = rounds(log, scope)
        assert 'plan-review: sum 3,' in t and 'auto_decided: sum 4,' in t and 'fix_rounds=`): sum 1,' in t, f'rounds: feil sum: {t!r}'
        assert 'uten rad: 2' in t and '7' not in t, f'rounds: todo utenfor scope telt, eller manglende rad ikke listet: {t!r}'

    def t_decisions():
        t = decisions(dlog, *win)
        assert '4 overskrifter i vinduet, 3 med regelmerke, 1 uten' in t, f'decisions: begge overskriftsformer skal telles: {t!r}'
        assert 'A0: 2, B1: 1' in t and 'A2' not in t, f'decisions: per regel eller vindu er feil: {t!r}'
        assert 'etter slag (2 med kjent `Type`): eiervalg: 1, runder: 1' in t, f'decisions: [A0] etter slag er feil: {t!r}'

    def t_noplan():
        text, code = render([('Diff', lambda: diff([pr(101)], ['101']))])
        assert code == 1 and 'Ledetid fra planfil: IKKE MÅLT: ' in text, f'diff: uten planfil skal gi exit 1, fikk {code}: {text!r}'

    def t_planned():
        row = lambda nr, tok: f'2026-01-01T10:00 | {nr} | a | merged | - | #101 | 1 | 1 | m | - | - | {tok}x\n'
        text, code = render([('Diff', lambda: planned(log, scope, [pr(101)]))])
        assert code == 0 and 'median 0,60, høyest 0,60 (TODO 1: 12 mot 20 linjer, 1 mot 2 filer)' in text, f'planned: feil forhold: {text!r}'
        text, code = render([('Diff', lambda: planned(log + row(2, ''), scope, [pr(101)]))])
        assert code == 1 and 'IKKE MÅLT: 1 rader uten gyldig `planned=` (2: mangler)' in text, f'planned: rad uten token skal gi IKKE MÅLT: {text!r}'
        text, code = render([('Diff', lambda: planned(log + row(2, 'planned=40; '), scope, [pr(101)]))])
        assert code == 1 and '(1 rader)' in text and '(2: 40)' in text, f'planned: feil form skal gi IKKE MÅLT: {text!r}'
        text, code = render([('Diff', lambda: planned(log + row(2, 'planned=n/a; '), scope, [pr(101)]))])
        assert code == 0 and '`planned=n/a`): 1' in text, f'planned: n/a er uten plan, ikke umålt: {text!r}'
        assert '(1: 20/2 uten PR)' in planned(log, scope, []), 'planned: gyldig token uten PR skal si årsaken'

    def t_bugs():
        bug = lambda n, line='': f'## BUG-{n} — x\n\n{line}\n**Status:** åpen\n\n'
        old = (bug(200, '**Oppdaget:** 2026-01-10') + bug(201, '- **Oppdaget:** under test, 2026-01-12') + '## Arkiv\n\n'
               + bug(204, '**Oppdaget i:** TODO 1, 2026-01-15') + bug(202, '**Oppdaget:** 2026-03-01') + bug(5)
               + bug(200, '**Oppdaget:** 2026-01-10'))
        text, code = render([('Bugs', lambda: bugs(old + bug(203), '2026-01-10T00:00', '2026-01-31'))])
        assert 'BUG-200' in text, f'bugs: bug oppdaget dagen vinduet åpner skal telles: {text!r}'
        assert '3 bugs oppdaget i vinduet: BUG-200, BUG-201, BUG-204\n' in text, f'bugs: feil telling: {text!r}'
        assert code == 1 and 'nummer over 156: IKKE MÅLT: BUG-203\n' in text, f'bugs: ny oppføring uten Oppdaget skal gi IKKE MÅLT: {text!r}'
        text, code = render([('Bugs', lambda: bugs(old, '2026-11-01T00:00', None))])
        assert code == 0 and '0 bugs oppdaget i vinduet\n' in text, f'bugs: eldre udaterte skal ikke gi exit 1 i et senere vindu: {text!r}'
        fails('bugs', lambda: bugs('## Arkiv\n', '2026-01-01', None), 'ingen `## BUG-<nr>`-oppføring')

    def t_wait():
        d = (dlog + a0('13:00', 'kvittering', 'fulgt (svart 2026-01-02 15:00)') + a0('13:30', 'kvittering', None)
             + a0('14:00', 'kvittering', 'venter (spurt 2026-01-02 09:00)') + a0('14:30', 'kvittering', 'Se 2026-01-02 12:30') + a0('15:00', 'kvittering', 'se over'))
        text, code = render([('Beslutninger', lambda: decisions(d, *win))])
        assert code == 1 and 'Ventetid på eier: IKKE MÅLT: ' in text, f'ventetid: [A0] uten spurt og svart skal gi IKKE MÅLT: {text!r}'
        line = next((l for l in text.splitlines() if l.startswith('- Ventetid på eier (')), '')
        assert '(1 spørsmål): median 2,5, lengst 2,5 timer (TODO 1)' in line, \
            f'ventetid: uten spurt skal gi IKKE MÅLT, aldri overskriftstid: {text!r}'
        assert 'IKKE MÅLT: 3 `[A0]`' in text, f'ventetid: `se` uten tid er ikke en peker og skal gi IKKE MÅLT: {text!r}'
        assert 'sum' not in line, f'ventetid: ventetidene overlapper og summeres ikke: {line!r}'
        assert all(x in text for x in ('Uoppfordret fra eier: 1', 'Venter fortsatt: 1', 'Besvart i egen oppføring: 1')), \
            f'ventetid: venter, uoppfordret og se-linje skal telles hver for seg: {text!r}'

    def t_slag():
        d = (''.join(a0('10:00', typ, ok) for typ in ('revise_gate_choice', 'eiervalg:farge', 'kvittering', 'worker_blocked', 'hokus', None))
             + a0('11:00', 'kvittering', 'se 2026-01-02 10:00'))
        text, code = render([('Beslutninger', lambda: decisions(d, *win))])
        assert code == 1 and 'uten slag: IKKE MÅLT: 1 uten `Type`, 1 med ukjent `Type` (hokus)' in text, f'slag: ukjent Type skal gi IKKE MÅLT: {text!r}'
        assert '(4 med kjent `Type`): eiervalg: 2, kvittering: 1, runder: 1' in text, f'slag: oppføring med se-linje skal ikke telles: {text!r}'

    def t_until():
        text, code = render([('Beslutninger', lambda: decisions(dlog, '2026-01-01T00:00', '2026-01-02'))])
        assert code == 0 and '4 overskrifter i vinduet' in text, f'decisions: --until som ren dato skal ta med hele dagen: {text!r}'

    def t_classify():
        got = [classify(p) for p in ('tasks/tfiles/t1.sql', 'lib/x.test.ts', 'README.md', 'app/(app)/index.tsx')]
        assert got == ['bevisrigg', 'tester', 'planer/docs/loop', 'appkode'], f'classify: {got}'

    def t_oserror():
        def boom():
            raise OSError('kilden forsvant')
        fails('section', boom, 'OSError: kilden forsvant')

    cases = [glad, t_rounds, t_decisions, t_classify, t_oserror, t_noplan, t_planned, t_bugs, t_wait, t_slag, t_until,
             lambda: fails('rounds', lambda: rounds(log, {'404'}), 'ingen `merged`-rad'),
             lambda: fails('decisions', lambda: decisions(dlog, '2030-01-01T00:00', None), 'ingen overskrift'),
             lambda: fails('cost', lambda: cost([]), 'ingen agenter'),
             lambda: fails('mains', lambda: mains('', 'ingen økt i vinduet'), 'measure-cost.py --main-usd'),
             lambda: fails('diff', lambda: diff([], []), 'ingen PR-numre'),
             lambda: fails('diff', lambda: diff([pr(101)], ['101', '102']), '`gh` ga ikke svar for PR 102')]
    for case in cases:
        case()
    print(f'retro-numbers self-test: {len(cases)}/{len(cases)}')
    return 0


def main(argv):
    if '--self-test' in argv:
        return self_test()
    opt = lambda flag: argv[argv.index(flag) + 1] if flag in argv[:-1] else None
    since, until = opt('--since'), opt('--until')
    if not argv or argv[0].startswith('-') or not since:
        print(__doc__, file=sys.stderr)
        return 2
    version = argv[0]
    scope = set(run(sys.executable, 'tasks/release.py', 'scope', version).stdout.split())
    if not scope:
        print(f'retro-numbers: tomt scope for release {version}', file=sys.stderr)
        return 2
    read = lambda p: open(p, encoding='utf-8').read()
    text, code = render([
        ('Runder', lambda: rounds(read(RUNLOG), scope)),
        ('Beslutninger', lambda: decisions(read(DECLOG), since, until)),
        ('Kostnad', lambda: cost_io(version, since)),
        ('Hovedsesjoner', lambda: mains_io(since, until)),
        ('Diff og ledetid', lambda: diff_io(read(RUNLOG), scope)),
        ('Bugs i perioden', lambda: bugs(read('tasks/bugs.md') + '\n' + read('tasks/bugs_archive.md'), since, until))])
    print(f"# Tallgrunnlag for release {version}\n\nVindu: {since} til {until or 'nå'}. Scope: {len(scope)} todoer.\n\n{text}")
    return code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
