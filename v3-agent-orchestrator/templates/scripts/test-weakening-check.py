#!/usr/bin/env python3
"""Test-svekkingsvakten: feller en diff som sletter en testfil, fjerner
tester/assersjoner fra en eksisterende testfil, eller legger skip-markører i den.

Bruk: test-weakening-check.py <base> <head>   (kjører git i cwd)

Exit 0: ingen funn, eller funn dekket av en linje `Test-svekking: <begrunnelse>` i
        miljøvariabelen PR_BODY (skrives da som WAIVED + ::warning:: per funn).
Exit 1: funn uten gyldig linje.
Exit 2: git feiler (ukjent rev) eller diffen har 0 endrede filer (feil base).

Tellingen er netto per fil og ser ikke endrede forventede verdier: kjente hull står under.
Kjent hull: Playwrights `test.fail()` kalt inne i en eksisterende test snur forventningen uten å endre noen telling.
Markørlista er lukket: skip/fixme/only, x-former, `ignore: true`, describe.todo/skipIf/runIf. Andre former er kjente hull, ikke defekter.
Kjent hull: betinget `ignore: <uttrykk>` i Deno.test telles ikke.
Kjent falskt funn: `ignore: true` som testdata telles som markør. Frafalles med Test-svekking-linja.
"""
import os
import re
import subprocess
import sys

TEST_FILE = re.compile(r'(\.spec\.ts|\.test\.(ts|tsx|mjs)|_test\.ts)$')
TESTS = re.compile(r'^\s*(?:it|test|Deno\.test)(?:\.each)?\s*[(`]', re.M)
MARKERS = re.compile(
    r'\.(?:skip|fixme|only)\s*\(|\bdescribe\.(?:todo|skipIf|runIf)\s*\(|\bignore:\s*true\b'
    r'|^\s*x(?:it|describe|test)\s*\(',
    re.M,
)
EXPECTS = re.compile(r'\b(?:expect|assert\w*)(?:\.\w+)*\s*\(')
# Ubetingede markører: aldri rabatt for nye tester.
HARD = re.compile(
    r'''\.(?:fixme|only)\s*\(|\.skip\s*\(\s*(?:true\b|['"`)])|\bdescribe\.(?:todo|skipIf|runIf)\s*\('''
    r'''|\bignore:\s*true\b|^\s*x(?:it|describe|test)\s*\(''',
    re.M,
)
COMMENT = re.compile(r'^\s*(//|\*|/\*).*$', re.M)  # fjernes før telling
# «Test-svekking: ingen …» er en vanelinje, ikke et frafall.
WAIVER = re.compile(r'^Test-svekking: (?!(?i:ingen))\S.{9,}$', re.M)


def git(*args):
    # quotePath=false: ellers siteres stier med æøå i diff-lista, og TEST_FILE bommer.
    r = subprocess.run(['git', '-c', 'core.quotePath=false', *args], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FEIL: git {' '.join(args)}: {r.stderr.strip()}")
        sys.exit(2)
    return r.stdout


def counts(rev, path):
    text = COMMENT.sub('', git('show', f'{rev}:{path}'))
    return [len(rx.findall(text)) for rx in (TESTS, MARKERS, EXPECTS, HARD)]


def check(base, head):
    rows = [line.split('\t') for line in git('diff', '-M', '--name-status', base, head).splitlines()]
    finds = []
    for row in rows:
        status, old, new = row[0], row[1], row[-1]
        if status == 'A' or not TEST_FILE.search(old):
            continue
        if status == 'D' or not TEST_FILE.search(new):
            finds.append(f'deleted\t{old}')
            continue
        (t0, m0, e0, h0), (t1, m1, e1, h1) = counts(base, old), counts(head, new)
        if t1 < t0:
            finds.append(f'fewer_tests\t{new}\t{t0}->{t1}')
        if h1 > h0 or m1 - m0 > max(0, t1 - t0):
            finds.append(f'more_skips\t{new}\t{m0}->{m1}')
        if e1 < e0:
            finds.append(f'fewer_expects\t{new}\t{e0}->{e1}')
    return rows, finds


def main():
    base, head = sys.argv[1], sys.argv[2]
    rows, finds = check(base, head)
    for find in finds:
        print(find)
    print(
        f"test-weakening: base={git('rev-parse', base).strip()} head={git('rev-parse', head).strip()}"
        f' endrede_filer={len(rows)} funn={len(finds)}'
    )
    if not rows:
        return 2
    if not finds:
        return 0
    waiver = WAIVER.search(os.environ.get('PR_BODY', '').replace('\r', ''))
    if not waiver:
        return 1
    for find in finds:
        print(f"::warning::Test-svekking (frafalt): {find.replace(chr(9), ' ')}")
    print(f'WAIVED: {waiver.group(0)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
