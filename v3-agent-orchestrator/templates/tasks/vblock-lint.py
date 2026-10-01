#!/usr/bin/env python3
"""V-blokk-linter — mekanisk deteksjon av kjente vakuøs-vakt-mønstre i en plan.

Bakgrunn: i uke 38/2026 var 29 av 33 BLOKKERENDE review-funn samme feilklasse —
«en vakt som ikke kan bli rød av riktig grunn». Hver enkelt ble funnet av en
adversariell Opus-review til $3–15 per runde, og hver utløste en fix-runde til
~$10. De fleste variantene er tekstmønstre, ikke dømmekraft. Denne linteren
kjenner dem igjen for ~$0.

Den erstatter IKKE plan-review. Den fjerner de mekaniske funnene fra
review-budsjettet, så revieweren kan bruke det på det som faktisk krever
dømmekraft.

Bruk:
    python3 tasks/vblock-lint.py <planfil> [--json] [--log]

Exit 0 = ingen HARD-funn. SOFT-funn vises, men blokkerer ikke.
Exit 1 = minst ett HARD-funn.
Exit 2 = fila kunne ikke leses, eller argumentene var ugyldige.
"""
# ────────────────────────────────────────────────────────────────────────────────
# MAL-NOTAT — LES FØR BRUK I ET NYTT PROSJEKT
#
# Regelsettet under er IKKE plattformagnostisk. Det er skrevet ut av opphavsprosjektets eget
# lesson-korpus, og bærer prosjektspesifikke antakelser:
#   • R8 siterer React Natives `setUpGlobals.js:18` — usant i et prosjekt uten RN.
#   • R1/R2/R3/R6 hardkoder `vitest` og `playwright` som testløpere.
#   • `origin`-feltet peker på TODO-numre som ikke finnes i ditt prosjekt.
#
# Kun R7 og R10 er plattformagnostiske. Behandle resten som EKSEMPLER på formen en
# regel skal ha, og skriv dem om mot dine egne lessons før du stoler på dem.
#
# Ingen regel er HARD i utgangspunktet — se nivå-noten under. Forfremmelse krever
# motprøve begge veier mot en navngitt, datert lesson i DITT korpus.
# ────────────────────────────────────────────────────────────────────────────────
import json
import os
import re
import sys
from datetime import datetime, timezone

LOG_PATH = 'tasks/metrics/vblock-lint-log.jsonl'

# Hver regel: (id, tittel, opphav). Opphavet er todoen der klassen først bet oss —
# det gjør regelen sporbar og gir neste leser kontekst for hvorfor den finnes.
RULES = []


# To nivåer, fordi presisjon er målt ulikt:
#   HARD — motprøvd BEGGE VEIER mot en navngitt, datert lesson: rød på den formen
#          lessonen beskriver, OG ren på den fiksede formen. Gir exit 1.
#   SOFT — mønsteret er ekte, men presisjonen er ikke etablert. Vises, blokkerer ikke.
#
# **Unntak: R0 er HARD fra start.** Den er strukturell, ikke et mønster-gjett: planen har en
# Steg-seksjon med avkrysningsbokser eller ikke, og det er samme test kode-revieweren og §4 teller
# med. Motprøvd begge veier i `--self-test`. Målt i et annet prosjekt med samme loop: to plannere
# på rad leverte uten Steg-seksjon, og hver gang kostet det en full review-runde.
#
# **Utover R0 er INGEN regel HARD, og det er en målt konklusjon, ikke forsiktighet.**
# Kode-review av PR #852 (2026-09-17) viste to ting over 259 arkiverte planfiler:
#   1. Mønsteret til de to kandidatene forekom ÉN gang hver i hele korpuset. Med base
#      rate 1 kan presisjon ikke måles, og `exit 1` har aldri vært oppnåelig for en
#      reell plan — en gate som ikke kan bli rød av riktig grunn.
#   2. R6 var samtidig falsk-rød på den FIKSEDE formen (probe F: en mutant-rad som
#      korrekt sier at Playwright gir `Error: expect(...)` og ikke `AssertionError`
#      ga exit 1). Altså rød av feil grunn. Begge halvdelene av samme feilklasse i
#      én regel.
# Unntaket er lagt inn (se R6), men forfremmelse tilbake til HARD hører til TODO 379
# og krever at regelen faktisk påkalles et sted OG at base raten gjør presisjon
# målbar. Til da er dette et RAPPORTERINGSVERKTØY, ikke en gate.
HARD, SOFT = 'HARD', 'SOFT'


def rule(rid, title, origin, level=HARD):
    def deco(fn):
        RULES.append((rid, title, origin, level, fn))
        return fn
    return deco


# Forklarende prosa nevner de gale formene for å advare mot dem. En vakt som
# ikke skiller en FEIL fra en ADVARSEL om feilen er falsk-rød — nøyaktig
# klassen denne linteren finnes for (TODO 306, Hermes-grepet som rødnet på
# filens egne kommentarer). Linjer som bærer en av disse markørene er
# forklaring, ikke instruks, og nøytraliseres før reglene kjører.
# `re.I` er BEVISST fjernet. Markørene er emfase-former forfatteren skriver med vilje
# i store bokstaver; med `re.I` ble `ALDRI` til `aldri` — et helt ordinært norsk ord som
# nullet 1965 linjer over arkivet, og `er feil` traff substrengen i «returnerer feil».
# Målt i kode-review av PR #852: en linje med et ekte R8-treff ble usynlig bare ved at
# ordet `ikke` byttes til `aldri`, uten at noe i outputen sa fra. Et filter som kan skjule
# et funn i stillhet er selv en vakt som ikke kan bli rød. (2026-09-17.)
# Splittet i to, fordi begrunnelsen ikke er den samme for alle markørene:
#   VERSAL — emfase forfatteren skriver med vilje i store bokstaver. Case-SENSITIV,
#            ellers blir `ALDRI` til `aldri`, et ordinært norsk ord som nullet 1965
#            linjer over arkivet og kunne skjule et ekte funn i stillhet.
#   PROSA  — alminnelige uttrykk der versal er tilfeldig. Case-INSENSITIV: målt i
#            arkivet skrives «Forventet rød» med stor F 6 ganger og liten f 5 ganger,
#            altså myntkast. Én felles case-sensitiv regel gjorde R6 falsk-rød på en
#            KORREKT mutant-rad bare fordi forfatteren valgte liten forbokstav
#            (kode-review PR #852 runde 2, probe E: base exit 0 → head exit 1 på
#            samme rad). Ordgrensen i `\b(?:var|er) feil\b` bærer fortsatt fiksen mot
#            «returnerer feil», uavhengig av flagget.
EXPLANATORY = re.compile(
    r'\bUSANT\b|\bALDRI\b|\bIKKE bruk\b|\bBINDENDE\b'
    r'|(?i:\b(?:var|er) feil\b|plan-review r\d|kode-review r\d'
    r'|Forventet rød|først sett|Bakgrunn:|feilklasse)'
)


def strip_explanatory(text):
    """Blank ut forklarende linjer, men behold linjenummereringen.

    Returnerer (tekst, antall_strippede_linjer). Tallet rapporteres, fordi reglene
    R1/R4/R8/R9/R10 skanner vilkårlige linjer — ikke bare V-/M-rader — og et treff
    filteret spiser der ville ellers vært både usynlig OG utellet.
    """
    out, n = [], 0
    for l in text.splitlines():
        if l.strip() and EXPLANATORY.search(l):
            out.append('')
            n += 1
        else:
            out.append(l)
    return '\n'.join(out), n


def v_rows(text):
    """V-radene i planen, som (linjenr, rå rad)."""
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        if re.match(r'^\|\s*\*\*V-?\w*\d', line):
            out.append((i, line))
    return out


# `M1`, `M2` … brukes i planene BÅDE for mutanter og for målinger. Radmønsteret
# alene ga 254 treff over arkivet, nesten alle målings-tabeller. Mutant-rader
# må derfor identifiseres av overskriften de står under.
# Rå, ustrippet tekst for den ene regelen som må se en OVERSKRIFT: strippingen er
# linje-basert, så en rad som forklarer den riktige formen forsvinner helt — og med den
# forsvinner rad-konteksten en overskrifts-regel trenger. Settes i check().
RAW = ''

MUTANT_HEADING = re.compile(r'^#{1,4}\s.*\b(mutant|mutasjon)', re.I)
ANY_HEADING = re.compile(r'^#{1,4}\s')


def m_rows(text):
    """Mutant-radene — kun de som står under en mutant-overskrift."""
    out, in_mutants = [], False
    for i, line in enumerate(text.splitlines(), 1):
        if ANY_HEADING.match(line):
            in_mutants = bool(MUTANT_HEADING.match(line))
            continue
        if in_mutants and re.match(r'^\|\s*\*?\*?M\d', line):
            out.append((i, line))
    return out


STEG_HEAD = re.compile(r'^#{1,4} .*\bsteg\b', re.I)   # «## Steg», «## §8 Steg», «## 9. Fremgangsmåte (steg)»


@rule('R0', 'plan uten Steg-seksjon med avkrysningsbokser', 'N1')
def r0(_text, _v, _m):
    # Leser RÅ tekst: strippingen av forklarende linjer skal aldri kunne skjule en steg-linje.
    # Et steg er en avkrysningsboks, et nummerert punkt, en tabellrad med nummer i første celle
    # eller en `### Steg N`-overskrift. Målt mot 319 planer i opphavsprosjektet: et krav om bokser
    # alene ga 41 røde, og de fleste var reviewede og mergede planer med stegene i liste eller tabell.
    # Med dagens regel er 17 røde: 15 er eldre enn malen, ett er et målenotat, og én av 223 nyere
    # planer har stegene under «Rekkefølge». Den siste er en ekte avvisning: malen krever `## Steg`.
    in_steg, steps = False, 0
    for line in RAW.splitlines():
        if STEG_HEAD.match(line):
            in_steg = True
            steps += bool(re.match(r'#{3,4} .*\bsteg \d', line, re.I))
        elif line.startswith('## '):
            in_steg = False
        elif in_steg and re.match(r'- \[[ xX]\]|\d+\.\s|\|\s*\**[A-Z]?\d+', line):
            steps += 1
    if steps:
        return []
    return [(1, 'planen mangler en `## Steg`-seksjon med minst ett steg (`- [ ]`, `1.` eller '
                '`### Steg 1`). §4, TDD-STEG-tellingen og kode-reviewerens L1 leser stegene derfra. '
                'Send planen tilbake til planneren før review')]


@rule('R1', '-t-filter i testkommando', 'TODO 306', SOFT)
def r1(text, _v, _m):
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if re.search(r'vitest[^|]*\s-t\s', line):
            hits.append((i, 'et `-t`-filter uten treff gir `Tests 1 skipped` og exit 0 — '
                            'kriteriet kan ikke skille «ingen treff» fra «bestått»'))
    return hits


@rule('R2', 'flere testfiler navngitt uten Test Files-sitat', 'TODO 375', SOFT)
def r2(text, v, _m):
    hits = []
    for ln, row in v:
        # Kun vitest: Playwright skriver aldri «Test Files» — den skriver
        # «Total: N tests in M files». Playwright-rader dekkes av R3.
        if 'playwright' in row.lower() or 'vitest' not in row.lower():
            continue
        files = sorted(set(re.findall(r'\S+\.(?:test|spec)\.(?:ts|tsx|mjs)', row)))
        if len(files) >= 2 and not re.search(r'Test Files\s+\d+\s+passed', row):
            hits.append((ln, f'{len(files)} testfiler navngitt, men kriteriet siterer ikke '
                             f'`Test Files  N passed (N)`. En fil som ikke finnes telles '
                             f'ikke og gir exit 0'))
    return hits


@rule('R3', 'playwright uten --list-krav', 'TODO 377', SOFT)
def r3(text, v, _m):
    hits = []
    for ln, row in v:
        if 'playwright' in row.lower() and '--list' not in row:
            hits.append((ln, '`playwright test` på en spec som ikke finnes gir '
                             '`Total: 0 tests in 0 files` og exit 0 — krev `--list`-output '
                             'sitert før kjøringen teller'))
    return hits


@rule('R4', 'PCRE-klasse i sed/grep (BSD-inkompatibel)', 'TODO 375', SOFT)
def r4(text, _v, _m):
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if re.search(r'\b(sed|grep)\b', line) and re.search(r'\\[sdw]', line):
            hits.append((i, r'BSD-`sed`/`grep` på macOS støtter ikke `\s`/`\d`/`\w` — '
                            'bruk POSIX-klassene `[[:space:]]`, `[[:digit:]]`, `[[:alnum:]]`'))
    return hits


@rule('R5', 'mutant uten forventet feiltekst', 'TODO 306', SOFT)
def r5(text, _v, m):
    hits = []
    for ln, row in m:
        if not re.search(r'AssertionError|expect\(|Error:', row):
            hits.append((ln, 'mutant-raden oppgir ingen forventet feiltekst. Uten den kan '
                             'en `SyntaxError` eller `Cannot find module` passere som «rød»'))
    return hits


@rule('R6', 'Playwright-mutant som krever AssertionError', 'TODO 377', SOFT)
def r6(text, _v, m):
    hits = []
    why = ('Playwright skriver ALDRI strengen `AssertionError` — den skriver '
           '`Error: expect(received).toEqual(expected)` med diff, eller et '
           'timeout-predikat. Kravet gjør korrekt kode til «ikke bestått»')
    for ln, row in m:
        # Samme differensierings-unntak som overskrifts-grenen under: en rad som selv
        # sier at Playwright gir `Error: expect(...)` og IKKE `AssertionError` nevner
        # strengen, men stiller ikke det gale kravet — den sier det riktige. Uten
        # unntaket er regelen falsk-rød på nøyaktig den formen den ber om, altså den
        # feilklassen den finnes for. Motprøvd i kode-review PR #852 runde 2 (probe F).
        if ('playwright' in row.lower() and 'AssertionError' in row
                and 'expect(' not in row and 'Error:' not in row):
            hits.append((ln, why))

    # Et kollektivt krav i SEKSJONSOVERSKRIFTEN er samme feil, bare flyttet opp én
    # linje: «## 5 Mutasjonstester (4) — hver skal gi `AssertionError`» over en tabell
    # som inneholder en Playwright-mutant påstår noe usant om den mutanten, selv om
    # hver enkelt rad er riktig. Først sett på todo-377-planen 2026-09-17, av denne
    # linteren, etter at R6 selv var grønn på radene.
    head_ln = head = None
    for i, line in enumerate(RAW.splitlines(), 1):
        if ANY_HEADING.match(line):
            head_ln, head = ((i, line) if MUTANT_HEADING.match(line)
                             and not EXPLANATORY.search(line) else (None, None))
            continue
        # En overskrift som selv DIFFERENSIERER («vitest ⇒ AssertionError; Playwright ⇒
        # Error: expect(...)») nevner fortsatt strengen, men stiller ikke det gale kravet.
        # Uten dette unntaket ville regelen vært falsk-rød på nøyaktig den fiksede formen
        # den ber om — feilklassen den selv finnes for å fange.
        if (head and 'AssertionError' in head
                and 'playwright' not in head.lower() and 'expect(' not in head
                and re.match(r'^\|\s*\*?\*?M\d', line) and 'playwright' in line.lower()
                and not any(h[0] == head_ln for h in hits)):
            hits.append((head_ln, 'Seksjonsoverskriften krever `AssertionError` av ALLE '
                                  f'mutantene, men raden på linje {i} er en Playwright-mutant. '
                                  + why))
    return hits


@rule('R7', 'V-rad uten målt-rød-bevis', 'TODO 306', SOFT)
def r7(text, v, _m):
    hits = []
    for ln, row in v:
        cells = [c.strip() for c in row.split('|')]
        # Færre enn 5 celler = kompakt tabellform uten egen målt-kolonne.
        # Den formen er lovlig; R7 uttaler seg bare om den brede formen.
        if len(cells) < 6:
            continue
        evidence = re.search(
            r'\d+\s+(passed|failed|skipped)|exit\s*[01]|AssertionError|Error:'
            r'|Total:\s*\d+|n/a|ikke kjørbar', row, re.I)
        if not evidence:
            hits.append((ln, 'V-raden har en målt-kolonne, men ingen celle bærer en faktisk '
                             'måling (tall + passed/failed, exit-kode, assertion-tekst). '
                             'En V-rad som aldri er sett rød er ikke verifisert'))
    return hits


@rule('R8', 'typeof window brukt som plattformsjekk', 'TODO 377', SOFT)
def r8(text, _v, _m):
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if re.search(r"typeof\s+window\s*===?\s*'undefined'", line) :
            hits.append((i, 'React Native setter `global.window = global` '
                            '(`setUpGlobals.js:18`), så dette er USANT på native — og vitest '
                            "kjører `environment: 'node'` der det ER sant, så vakten er "
                            'utestbar. Bruk `Platform.OS` på kallstedet'))
    return hits


@rule('R9', 'mockReturnValueOnce brukt som tidsbevis', 'TODO 375', SOFT)
def r9(text, _v, _m):
    lines = text.splitlines()
    hits = []
    for i, line in enumerate(lines, 1):
        if 'mockReturnValueOnce' not in line:
            continue
        window = ' '.join(lines[max(0, i - 4):i + 3]).lower()
        if re.search(r'\b(før|etter|under|pre-|rundtur|rekkefølge|snapshot)\b', window):
            hits.append((i, '`mockReturnValueOnce` sekvenserer på KALLREKKEFØLGE, ikke på tid. '
                            'Skal testen vise at noe skjer «under» et async-kall, muter '
                            'tilstanden fra selve den asynkrone mocken'))
    return hits


@rule('R10', 'denylist brukt som import-syklus-garanti', 'TODO 375', SOFT)
def r10(text, _v, _m):
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        low = line.lower()
        if 'denylist' in low or ('forbudt' in low and 'import' in low):
            hits.append((i, 'en denylist av navngitte moduler er ikke transitivt sikker — '
                            'en ny mellom-modul utenfor lista gjenoppretter syklusen. '
                            'Bruk allowlist over tillatte spesifikatorer'))
    return hits


def lint(path):
    with open(path, encoding='utf-8') as fh:
        raw = fh.read()
    # V-/M-radene telles på RÅ tekst (en forklart rad er fortsatt en rad),
    # men regelmatchingen kjøres på strippet tekst.
    global RAW
    RAW = raw
    v_raw, m_raw = v_rows(raw), m_rows(raw)
    text, n_stripped = strip_explanatory(raw)
    v = [(ln, row) for ln, row in v_rows(text) if row]
    m = [(ln, row) for ln, row in m_rows(text) if row]
    n_v, n_m = len(v_raw), len(m_raw)
    findings = []
    for rid, title, origin, level, fn in RULES:
        for ln, detail in fn(text, v, m):
            findings.append({'rule': rid, 'title': title, 'origin': origin,
                             'level': level, 'line': ln, 'detail': detail})
    findings.sort(key=lambda f: (f['level'] != HARD, f['line'], f['rule']))
    # Siste to: hvor mange rader strippingen gjorde usynlige for reglene. En rad som
    # forklarer den gale formen skal ikke matche, men leseren må se at den er unntatt
    # — ellers ser «4 mutanter, OK» ut som fire prøvde rader når bare tre ble prøvd.
    return findings, n_v, n_m, n_v - len(v), n_m - len(m), n_stripped


def log_run(path, findings, n_v, n_m, sk_v, sk_m, n_stripped):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    row = {
        'ts': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'plan': os.path.basename(path),
        'v_rows': n_v, 'm_rows': n_m, 'v_skipped': sk_v, 'm_skipped': sk_m,
        'lines_stripped': n_stripped,
        'findings': len(findings),
        'hard': sum(1 for f in findings if f['level'] == HARD),
        'soft': sum(1 for f in findings if f['level'] == SOFT),
        'rules': sorted({f['rule'] for f in findings}),
    }
    with open(LOG_PATH, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + '\n')


KNOWN_FLAGS = {'--json', '--log', '--self-test'}


def self_test():
    import tempfile
    good = '# Plan\n\n## Steg\n- [ ] Steg 1: gjør X TDD-STEG\n\n## Verifisering\n'
    cases = [
        (good, 0, 'plan med Steg-seksjon og boks → exit 0'),
        ('# Plan\n\n## Analyse\n- [ ] ikke et steg\n', 1, 'boks utenfor Steg-seksjon → R0'),
        ('# Plan\n\n## Steg\nGjør X, så Y.\n', 1, 'Steg-seksjon uten steg → R0'),
        ('# Plan\n\n## Steg\n\n1. **Synk.** git fetch\n2. **Kode.**\n', 0, 'nummererte steg → exit 0'),
        ('# Plan\n\n## Løsningen\n### Steg 1 — del predikatet\ntekst\n', 0, '### Steg 1-overskrift → exit 0'),
        ('# Plan\n\n## Implementering\n1. gjør X\n', 1, 'nummerert liste uten Steg-seksjon → R0'),
        ('# Plan\n\n## §3 Fremgangsmåte (steg)\n| # | Steg |\n|---|---|\n| 1 | gjør X |\n', 0,
         'nummerert Steg-overskrift med tabell → exit 0'),
        ('# Plan\n\n### 2. Steg\n- [x] Steg 1: ALDRI hopp over\n', 0,
         'nummerert overskrift + ALDRI-linje (stripping skal ikke skjule den) → exit 0'),
    ]
    fails = 0
    for body, want, msg in cases:
        with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False, encoding='utf-8') as fh:
            fh.write(body)
        findings = lint(fh.name)[0]
        os.unlink(fh.name)
        got = 1 if any(f['level'] == HARD for f in findings) else 0
        print(('PASS ' if got == want else 'FAIL ') + msg)
        fails += got != want
    return 1 if fails else 0


def main():
    args = [a for a in sys.argv[1:]]
    flags = [a for a in args if a.startswith('--')]
    unknown = [f for f in flags if f not in KNOWN_FLAGS]
    if unknown:
        # En typo i `--json` som forkastes i stillhet gir menneskelesbar output til
        # en JSON-parser. Feil høyt i stedet.
        print(f'ukjent flagg: {" ".join(unknown)}. Kjente: '
              f'{" ".join(sorted(KNOWN_FLAGS))}', file=sys.stderr)
        return 2
    if '--self-test' in args:
        return self_test()
    as_json = '--json' in args
    do_log = '--log' in args
    paths = [a for a in args if not a.startswith('--')]
    if not paths:
        print(__doc__.strip().split('Bruk:')[1].strip(), file=sys.stderr)
        return 2
    if len(paths) > 1:
        # `vblock-lint.py tasks/plans/*.md` ville ellers rapportert «OK» for filer
        # verktøyet aldri åpnet — et stille kutt runbooken forbyr.
        print(f'{len(paths)} filer oppgitt, men linteren leser én om gangen. '
              f'Kjør den per fil (RAW-globalen i R6 er per kjøring).', file=sys.stderr)
        return 2
    path = paths[0]
    try:
        findings, n_v, n_m, sk_v, sk_m, n_stripped = lint(path)
    except OSError as err:
        print(f'kan ikke lese {path}: {err}', file=sys.stderr)
        return 2

    if do_log:
        log_run(path, findings, n_v, n_m, sk_v, sk_m, n_stripped)

    if as_json:
        print(json.dumps({'plan': path, 'v_rows': n_v, 'm_rows': n_m,
                          'v_skipped': sk_v, 'm_skipped': sk_m,
                          'lines_stripped': n_stripped,
                          'findings': findings}, ensure_ascii=False, indent=2))
        return 1 if any(f['level'] == HARD for f in findings) else 0

    hard = [f for f in findings if f['level'] == HARD]
    soft = [f for f in findings if f['level'] == SOFT]
    note = ''
    if sk_v or sk_m or n_stripped:
        parts = []
        if sk_v or sk_m:
            parts.append(f'{sk_v} V + {sk_m} mutanter')
        parts.append(f'{n_stripped} linjer totalt')
        note = (f'  ({" / ".join(parts)} unntatt som forklarende — reglene ser dem '
                'ikke)')
    print(f'{path}: {n_v} V-rader, {n_m} mutanter{note}')
    if not findings:
        print('OK — ingen kjente vakuøs-mønstre.')
        return 0
    if hard:
        print(f'\n{len(hard)} BLOKKERENDE:\n')
        for f in hard:
            print(f"  {f['rule']} linje {f['line']} — {f['title']}  (først sett: {f['origin']})")
            print(f"      {f['detail']}\n")
    if soft:
        print(f'{len(soft)} til vurdering (blokkerer ikke):')
        for f in soft:
            print(f"  {f['rule']} linje {f['line']} — {f['title']}")
    return 1 if hard else 0


if __name__ == '__main__':
    sys.exit(main())
