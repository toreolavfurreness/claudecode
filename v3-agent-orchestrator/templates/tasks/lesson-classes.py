#!/usr/bin/env python3
"""Teller feilklasser i lessons over et tidsvindu — varselsignal for §8c.

Bruk:  python3 tasks/lesson-classes.py [--days N] [--json]

Hver lesson klassifiseres i ÉN primærklasse — første treff i CLASSES-rekkefølge, matchet
mot tittelen og `**Problem:**`-linja. Ikke mot `**Løsning:**`/`**Unngå:**`: de nevner nesten
alltid et verktøy eller en plattform uten at DET er feilklassen, og å matche dem ga 6 av 6
klasser over terskel på første kjøring — en teller som alltid utløser er like verdiløs som
en vakt som aldri blir rød.

Formålet er IKKE å dømme, men å rangere: den høyest rangerte klassen UTEN mekanisk gate
(GATES-tabellen under) er den §8c i coordinator-runbook.md plikter koordinatoren å handle
på — én per helsesjekk, ikke alle over en terskel.

Exit 0 alltid — dette er en måling, ikke en vakt. Terskelvurderingen gjøres i §8c.
"""
# ────────────────────────────────────────────────────────────────────────────────
# MAL-NOTAT — LES FØR BRUK I ET NYTT PROSJEKT
#
# `CLASSES` og `GATES` under er utledet av ett konkret lesson-korpus. Klassenavnene
# og mønstrene er eksempler på formen, ikke en fasit: et nytt prosjekt har andre
# gjentakende feilklasser, og de finnes ved å lese egne lessons — ikke ved å arve
# disse.
#
# `GATES` skal stå TOM til en gate faktisk er koblet inn og motprøvd. Feltet er
# selv-forseglende: en ikke-tom verdi filtrerer klassen ut av `ungated` og slår den
# permanent av.
# ────────────────────────────────────────────────────────────────────────────────
import glob, json, os, re, sys
from datetime import date, timedelta

DEFAULT_DAYS = 7

# Hvilken mekanisk gate dekker klassen allerede? Tom streng = ingen dekning.
# Dette feltet — ikke et råtall — er det som utløser §8c-plikt: en klasse som topper
# lista OG mangler gate er et mønster vi betaler for på nytt hver gang.
#
# KRAV FOR Å FYLLE INN EN VERDI: en gate føres opp
# her først når den er motprøvd BEGGE VEIER mot minst én navngitt, datert lesson i
# klassen — rød på den formen lessonen beskriver, ren på den fiksede formen. Det er
# samme krav §8c steg 3 utfall (a) stiller, og det gjelder også denne tabellen.
#
# Feltet er selv-forseglende: en ikke-tom verdi filtrerer klassen ut av `ungated`, så
# en påstått gate slår klassen permanent av for §8c. Fire verdier ble ført opp uten
# motprøve og er derfor tømt igjen — de tre reelle formene for `vakuos-vakt` gav
# exit=0 mot linteren som var påstått å dekke dem. Oppgi lesson-datoen i verdien når
# du fyller inn, slik at dekningen er etterprøvbar og ikke bare påstått.
GATES = {
    'vakuos-vakt': '',
    'verktoy-output': '',
    'plattform-antakelse': '',
    'falsk-rod': '',
    'state-usynlighet': '',
    'mutant-svikt': '',
}

# Klassene er navngitt etter FEILEN, ikke etter symptomet — to lessons hører til samme
# klasse når den samme gaten ville fanget begge. Mønstrene er bevisst brede: en falsk
# positiv koster et blikk, en falsk negativ koster at mønsteret forblir usynlig.
CLASSES = [
    ('vakuos-vakt',
     'vakt som ikke kan bli rød av den feilen den er skrevet mot',
     r'kan ikke bli rød|aldri rød|vakuøs|tautolog|passerer uansett|grønn uansett'
     r'|exit 0|0 tests|ingen treff|skipped|ikke diskriminer|no-op'),
    ('verktoy-output',
     'antakelse om et verktøys output- eller exit-kontrakt som ikke holder',
     r'AssertionError|Test Files|--list|--reporter|exit(?:code)?\s*(?:=|er)?\s*0'
     r'|PIPESTATUS|pipestatus|stderr|stdout|exit-kode'),
    ('plattform-antakelse',
     'antakelse om runtime/plattform (native vs web, BSD vs GNU, zsh vs bash)',
     r'typeof window|globalThis|Platform\.OS|BSD|GNU|macOS|zsh|bash|Hermes'
     r'|react-native/Libraries|node_modules/react-native'),
    ('falsk-rod',
     'vakt som rødner på noe annet enn feilen (egne kommentarer, severity-gulv)',
     r'falsk[- ]rød|rødner på|treffer sin egen|egen kommentar|severity-gulv|gulv'
     r'|floor_exempt|false positive|falsk positiv'),
    ('state-usynlighet',
     'en tilstand som er sann, men usynlig for filteret som skulle fanget den',
     r'usynlig|skjult for|filteret|claimed_by|status: in_progress|ikke plukket opp'
     r'|falt mellom|manglet oppfølger|aldri registrert'),
    ('mutant-svikt',
     'mutant som ikke beviser det den skulle (egen vakt til no-op, feil feiltekst)',
     r'mutant|mutasjon|motprøv'),
]
COMPILED = [(k, d, re.compile(p, re.I)) for k, d, p in CLASSES]

def lessons(paths):
    """Yield (dato, tittel, fil, full tekst) per lesson-fil (én fil per lesson)."""
    for path in sorted(paths):
        name = os.path.basename(path)
        if not re.match(r'\d{4}-\d{2}-\d{2}-', name):
            continue
        text = open(path, encoding='utf-8').read()
        m = re.search(r'^# (.+)$', text, re.M)
        yield [name[:10], m.group(1).strip() if m else name[11:-3], path, text]


def main(argv):
    days = DEFAULT_DAYS
    if '--days' in argv:
        days = int(argv[argv.index('--days') + 1])
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    hits = {k: [] for k, _, _ in CLASSES}
    total = unclassified = 0
    for d, title, path, text in lessons(glob.glob('tasks/lessons/**/*.md', recursive=True)):
        if d < cutoff:
            continue
        total += 1
        probs = re.findall(r'^\*\*Problem:\*\*(.*)$', text, re.M)
        subject = title + ' ' + ' '.join(probs)
        for k, _, rx in COMPILED:          # første treff vinner — én primærklasse
            if rx.search(subject):
                hits[k].append({'date': d, 'title': title, 'file': path})
                break
        else:
            unclassified += 1

    rows = sorted(((k, desc, hits[k]) for k, desc, _ in CLASSES),
                  key=lambda r: -len(r[2]))
    ungated = [(k, len(h)) for k, _, h in rows if h and not GATES.get(k)]

    if '--json' in argv:
        print(json.dumps({
            'window_days': days, 'cutoff': cutoff, 'lessons_in_window': total,
            'unclassified': unclassified, 'gates': GATES,
            'action_class': ungated[0][0] if ungated else None,
            'classes': {k: hits[k] for k in hits},
        }, ensure_ascii=False, indent=2))
        return 0

    print(f'{total} lessons siste {days} døgn (fra {cutoff}), '
          f'{unclassified} uklassifisert.')
    if total and unclassified / total > 0.5:
        pct = round(100 * unclassified / total)
        print(f'ADVARSEL: {pct} % av korpuset er uklassifisert. Rangeringen under '
              f'hviler på et mindretall, og en klasse som mangler her kan være '
              f'større enn den som topper lista.')
    print()
    for k, desc, h in rows:
        if not h:
            continue
        gate = GATES.get(k) or '— INGEN GATE'
        print(f'{len(h):3d}  {k:22s} {desc}')
        print(f'     gate: {gate}')
        for e in h[:4]:
            print(f'       {e["date"]}  {e["title"][:76]}')
        if len(h) > 4:
            print(f'       … +{len(h) - 4} til')
        print()
    if ungated:
        k, n = ungated[0]
        print(f'§8c-HANDLING: «{k}» ({n} lessons) er den høyest rangerte klassen uten '
              f'mekanisk gate.\n  Innfør en gate, ELLER logg i decision-log hvorfor '
              f'klassen ikke kan gates mekanisk.')
    elif total == 0:
        print('0 lessons i vinduet — ingen måling. Det er ikke et frikjennende '
              'resultat, og det er ikke grunnlag for «ingen §8c-handling».')
    else:
        print('Alle forekommende klasser har en mekanisk gate. Ingen §8c-handling.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
