#!/usr/bin/env python3
"""kit-release-check.py — Kit-vakten i /release-prod og i kode-review.

  python3 scripts/kit-release-check.py [--range A..B]   releasevakt (standard: origin/{{PROD_BRANCH}}..origin/{{BASE_BRANCH}})
  python3 scripts/kit-release-check.py --pr <nr>        review-sjekk av én PR
  python3 scripts/kit-release-check.py --self-test
  (--kit-repo <eier/navn> bytter kit-repo, standard toreolavfurreness/claudecode)

Regelen: en PR eller direktecommit som endrer en kitfil, har linja «Kit: claudecode#NN» eller
«Kit: ingen endring – <begrunnelse>» i PR-teksten (commit-meldingen når commiten ikke har en PR).
«Kit: porteres …» godtas i review (pending), men er et brudd i releasevakten.
Kitfil-lista leses fra kit-repoets tre med ett gh api-kall. Skriptet bare leser (git og gh).
En merge-commit dømmes aldri på commit-meldingen: finner oppslaget ikke PR-en, er det FEIL (exit 2).
Exit 0 = ok, 1 = brudd, 2 = bruks-/oppslagsfeil (kit-repoet kunne ikke leses, git/gh feilet, eller
en merge-commit som endrer en kitfil, fikk ikke PR-treff). Commits i --range må være pushet:
PR-oppslaget gir HTTP 422 og FEIL for en commit GitHub ikke kjenner.
"""
import argparse, json, re, subprocess, sys

KIT_ROOT = 'v3-agent-orchestrator/'
# Stien er lastbærende: «regel i kraft» for en commit = denne stien finnes i forelderen.
SELF = 'scripts/kit-release-check.py'
# Kitfiler som bare er skjelett eller tom mal i kitet og prosjektinnhold her: sti -> begrunnelse.
EXCEPTIONS = {
    'CLAUDE.md': 'skjelett i kitet, prosjektregler her',
    'docs/data-model.md': 'skjelett i kitet, prosjektets datamodell her',
    'docs/naming-conventions.md': 'skjelett i kitet, prosjektkonvensjoner her',
    'docs/superpowers/loop/decision-log.md': 'prosjektlogg, tom mal i kitet',
    'docs/superpowers/loop/run-log.md': 'prosjektlogg, tom mal i kitet',
    'docs/superpowers/loop/retro-log.md': 'prosjektlogg, tom mal i kitet',
}
# Brudd i en direktecommit (meldingen kan ikke rettes): full sha -> begrunnelse, som navngir
# kit-PR-en (claudecode#NN) eller sier hvorfor kitet ikke trenger endringen.
# En sha som har en PR, frafalles ikke her: den rettes med gh pr edit.
WAIVED = {}
# ponytail: regexen ser ikke markdown-struktur, så en Kit-linje i en kodeblokk eller et sitat (>)
# teller også. Fjern fenced blokker før søket hvis det viser seg å bli et hull.
_PREFIX = r'^[ \t>*_-]*Kit:[*_]*[ \t]*'
KIT_LINE = re.compile(
    _PREFIX + r'(?:(?:toreolavfurreness/)?claudecode#\d+|ingen endring[ \t]*[–—-][ \t]*\S)', re.M | re.I)
PENDING_LINE = re.compile(_PREFIX + r'porteres\b', re.M | re.I)


def kit_paths(tree_paths):
    """Stier i kit-treet -> mengden av tilsvarende stier her."""
    # ponytail: nye loop-filer her som ennå ikke finnes i kitet, fanges ikke. Krever en egen
    # liste over loop-mapper hvis det viser seg å bli et hull.
    out = set()
    for p in tree_paths:
        if not p.startswith(KIT_ROOT):
            continue
        p = p[len(KIT_ROOT):]
        if p.startswith('templates/'):
            out.add(p[len('templates/'):].replace('PROJECT_NAME-', '{{PROJECT_NAME}}-'))
        elif p.startswith('examples/hooks/') and p.endswith('.example.sh'):
            out.add('.claude/hooks/' + p[len('examples/hooks/'):-len('.example.sh')] + '.sh')
        elif p.startswith('examples/tech-review-agents/') and p.endswith('.example.md'):
            out.add('.claude/agents/' + p[len('examples/tech-review-agents/'):-len('.example.md')] + '.md')
    return out


def load_kit(fetch):
    """fetch() gir JSON-teksten fra git/trees. Uleselig, avkortet eller tomt tre -> RuntimeError."""
    d = json.loads(fetch())
    if d.get('truncated'):
        raise RuntimeError('kit-treet er avkortet (truncated), kitfil-lista er ufullstendig')
    kit = kit_paths(t['path'] for t in d['tree'] if t.get('type') == 'blob')
    if not kit:
        raise RuntimeError('ingen kitfiler i kit-treet')
    return kit - set(EXCEPTIONS)


def verdict(pr, kit, waived=WAIVED):
    """pr = {sha, files, body, rule_in_force} -> skip | waived | ok | pending | offender | backlog."""
    if not any(f in kit for f in pr['files']):
        return 'skip'
    if pr.get('sha') in waived:
        return 'waived'
    body = pr['body'] or ''
    if KIT_LINE.search(body):
        return 'ok'
    if not pr['rule_in_force']:
        return 'backlog'
    return 'pending' if PENDING_LINE.search(body) else 'offender'


def exit_code(verdicts, review):
    """offender blokkerer alltid; pending blokkerer bare i releasevakten."""
    return 1 if 'offender' in verdicts or (not review and 'pending' in verdicts) else 0


def row(label, files, v, sha=None, waived=WAIVED):
    return f"{label} ({', '.join(files)}) → {v}" + (f': {waived[sha]}' if v == 'waived' else '')


def summary(n_kit, verdicts):
    n = verdicts.count
    return (f"kit-release-check: kitfiler={n_kit} commits={len(verdicts)} etterslep={n('backlog')} "
            f"frafalt={n('waived')} brudd={n('offender') + n('pending')}")


def run(*cmd, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}: {r.stderr.strip()[:200]}")
    return r


def pick_pr(pulls, m):
    """PR-en mot dev med merge_commit_sha == m (merge eller squash), ellers None. En PR som bare
    inneholder m, har en annen merge_commit_sha og treffer ikke."""
    return next((p for p in pulls if p.get('merge_commit_sha') == m and p['base']['ref'] == '{{BASE_BRANCH}}'), None)


def find_pr(m):
    # commits/<sha>/pulls er et direkte oppslag, ikke søkeindeksen (som kan mangle en fersk merge).
    url = f'repos/{{owner}}/{{repo}}/commits/{m}/pulls?per_page=100'
    return pick_pr(json.loads(run('gh', 'api', url).stdout), m)


def subject(pr, m, is_merge):
    """-> (etikett, sha for WAIVED-oppslaget). sha gis bare når commiten ikke har en PR."""
    if pr:
        return f"PR #{pr['number']}", None
    if is_merge:
        raise RuntimeError(f'fant ikke PR for merge-commit {m[:9]}, kjør på nytt')
    return f'commit {m[:9]}', m


def main(rng, kit):
    a, _ = rng.split('..')
    verdicts, late, broken = [], [], []
    # Alle first-parent-commits, ikke bare merger: squash- og direktecommits rører kitfiler.
    for m in run('git', 'rev-list', '--first-parent', rng).stdout.split():
        if run('git', 'merge-base', '--is-ancestor', m + '^2', a, check=False).returncode == 0:
            continue  # back-merge main -> dev
        diff = run('git', 'diff', '--name-only', '--no-renames', m + '^1', m).stdout
        files = [f for f in diff.splitlines() if f in kit]
        if not files:
            verdicts.append('skip')
            continue
        pr = find_pr(m)
        is_merge = run('git', 'rev-parse', '-q', '--verify', m + '^2', check=False).returncode == 0
        label, sha = subject(pr, m, is_merge)
        body = pr['body'] if pr else run('git', 'log', '-1', '--format=%B', m).stdout
        rule = run('git', 'cat-file', '-e', f'{m}^1:{SELF}', check=False).returncode == 0
        v = verdict({'sha': sha, 'files': files, 'body': body, 'rule_in_force': rule}, kit)
        verdicts.append(v)
        print(row(label, files, v, m))
        if v == 'backlog':
            late.append(label)
        elif v in ('offender', 'pending'):
            broken.append(label)
    for label in late:
        print(f'ETTERSLEP {label}')
    for label in broken:
        print(f'BRUDD {label}')
    print(summary(len(kit), verdicts))
    return exit_code(verdicts, review=False)


def review(nr, kit):
    files = [f for f in run('gh', 'pr', 'diff', nr, '--name-only').stdout.splitlines() if f in kit]
    body = json.loads(run('gh', 'pr', 'view', nr, '--json', 'body').stdout)['body']
    v = verdict({'files': files, 'body': body, 'rule_in_force': True}, kit)
    print(row(f'PR #{nr}', files, v))
    return exit_code([v], review=True)


def self_test():
    def tree(*paths, **extra):
        return lambda: json.dumps({'tree': [{'path': KIT_ROOT + p, 'type': 'blob'} for p in paths], **extra})

    def raises(fn):
        try:
            return fn()
        except RuntimeError:
            return 'RuntimeError'

    def boom():
        raise RuntimeError('gh: Not Found (HTTP 404)')

    kf = '.claude/commands/run-loop.md'
    kit = load_kit(tree('templates/CLAUDE.md', 'templates/' + kf))
    base = {'sha': 'abc', 'files': [kf], 'body': '', 'rule_in_force': True}
    v = lambda waived={}, **kw: verdict({**base, **kw}, kit, waived)
    cases = [
        ('K1', v(body='Kit: claudecode#24'), 'ok'),
        ('K2', v(body='Kit: ingen endring – FH-spesifikk'), 'ok'),
        ('K3', v(), 'offender'),
        ('K4', v(files=['CLAUDE.md']), 'skip'),
        ('K5', raises(lambda: load_kit(boom)), 'RuntimeError'),
        ('K6', v(body='Tekst\n\nKit: toreolavfurreness/claudecode#18. Mer tekst'), 'ok'),
        ('K7', v(body='Kit: porteres av koordinator etter merge til x'), 'pending'),
        ('K8', v(body='Kit: ingen endring –\n\nMer tekst'), 'offender'),
        ('K9', v(body='Kit: claudecode#'), 'offender'),
        ('K10', v(body='Se Kit: claudecode#1'), 'offender'),
        ('K11', v(files=['CLAUDE.md', kf]), 'offender'),
        ('K12', v(files=['lib/x.ts']), 'skip'),
        ('K13', v(rule_in_force=False), 'backlog'),
        ('K14', kit_paths(KIT_ROOT + p for p in (
            'templates/.claude/agents/PROJECT_NAME-code-reviewer.md',
            'examples/hooks/guard-supabase-ref.example.sh',
            'examples/tech-review-agents/race-reviewer.example.md',
            'README.md', 'scaffolding/githooks/pre-commit')),
         {'.claude/agents/{{PROJECT_NAME}}-code-reviewer.md', '.claude/hooks/guard-supabase-ref.sh',
          '.claude/agents/race-reviewer.md'}),
        ('K15', raises(lambda: load_kit(tree('templates/' + kf, truncated=True))), 'RuntimeError'),
        ('K16', raises(lambda: load_kit(tree('README.md'))), 'RuntimeError'),
        ('K17', [exit_code(['pending'], False), exit_code(['pending'], True), exit_code(['offender'], True),
                 exit_code(['backlog', 'ok', 'skip', 'waived'], False)], [1, 0, 1, 0]),
        ('K18', all(isinstance(r, str) and r.strip() for r in [*EXCEPTIONS.values(), *WAIVED.values()]), True),
        ('K19', v(waived={'abc': 'x'}), 'waived'),
        ('K20', v(waived={'def': 'x'}), 'offender'),
        ('K21', row('commit abc', [kf], 'waived', 'abc', {'abc': 'claudecode#9'}),
         f'commit abc ({kf}) → waived: claudecode#9'),
        ('K22', summary(96, ['skip', 'ok', 'waived', 'backlog', 'pending', 'offender']),
         'kit-release-check: kitfiler=96 commits=6 etterslep=1 frafalt=1 brudd=2'),
        ('K23', raises(lambda: subject(None, 'abc', True)), 'RuntimeError'),
        ('K24', [subject(None, 'abc', False), subject({'number': 5}, 'abc', True)],
         [('commit abc', 'abc'), ('PR #5', None)]),
        ('K25', v(sha=subject({'number': 5}, 'abc', False)[1], waived={'abc': 'x'}), 'offender'),
        ('K26', [pick_pr([{'number': 1, 'merge_commit_sha': 'zzz', 'base': {'ref': '{{BASE_BRANCH}}'}},
                          {'number': 2, 'merge_commit_sha': 'abc', 'base': {'ref': 'main'}}], 'abc'),
                 pick_pr([{'number': 3, 'merge_commit_sha': 'abc', 'base': {'ref': '{{BASE_BRANCH}}'}}], 'abc')['number']],
         [None, 3]),
    ]
    ok = 0
    for name, got, want in cases:
        good = got == want
        ok += good
        print(('PASS' if good else 'FAIL'), name, got if not good else '')
    print(f'kit-release-check --self-test: {ok}/{len(cases)}')
    return 0 if ok == len(cases) else 1


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--range', default='origin/{{PROD_BRANCH}}..origin/{{BASE_BRANCH}}')
    ap.add_argument('--pr')
    ap.add_argument('--kit-repo', default='toreolavfurreness/claudecode')
    ap.add_argument('--self-test', action='store_true')
    args = ap.parse_args()
    try:
        if args.self_test:
            sys.exit(self_test())
        kit = load_kit(lambda: run('gh', 'api', f'repos/{args.kit_repo}/git/trees/main?recursive=1').stdout)
        sys.exit(review(args.pr, kit) if args.pr else main(args.range, kit))
    except (RuntimeError, ValueError, KeyError, OSError) as e:
        print(f'FEIL {e}')
        sys.exit(2)
