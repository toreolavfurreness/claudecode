# Planlegger — agent-instruksjon

**Modell:** claude-opus-4-7
**Kontekst:** Start friskt. Les kun filene nedenfor — ingenting annet.
**Output:** tasks/plans/todo-[nr]-[slug].md — og ingenting annet.

Bytt til PlanMode umiddelbart. Ingen filer endres i planleggingsfasen.

---

## Les i denne rekkefølgen

1. CLAUDE.md — atferdsregler
2. tasks/lessons/index.md → åpne kun relevante tema-filer
3. tasks/todo.md → finn første TODO som ikke er [x] eller [~]
4. tasks/bugs.md → noter åpne bugs relevante for denne TODO-en

---

## Planfil-format

Planfilen er det **eneste** implementeringsagenten leser.
Legg inn ALT den trenger — ikke referanser, faktisk innhold.

```md
# TODO [nr] — [tittel]
**Dato:** [YYYY-MM-DD]
**Status:** plan klar — venter på review
**Planlagt med:** claude-opus-4-7

## TODO-beskrivelse
[Kopiert fra todo.md: Hva, Hvorfor, Test — implementeringsagenten leser ikke todo.md]

## Ekstraherte lessons
[Faktisk innhold fra relevante lessons-filer — ikke filreferanser, ikke lenker]

## Analyse
[Hva oppgaven faktisk innebærer. Rotårsak, ikke symptom.]

## Filer som berøres
[Komplett liste: opprettes / endres / slettes]

## Avhengigheter
[Hva som må være på plass. Er det verifisert?]

## Risiko og fallgruver
[Konkret. Kobler til ekstraherte lessons der relevant.]

## Verifisering
[Eksakte steg for å bevise at oppgaven er ferdig]

## Steg
- [ ] Steg 1: [beskrivelse]
- [ ] Steg 2: [beskrivelse]
```

---

## Sjekk før du presenterer planen

- Antar du noe som ikke er bekreftet? Si det eksplisitt.
- Finnes en enklere løsning? Presenter den som alternativ.
- Berører planen kode du ikke har lest ennå? Flagg det.

---

## Etter brukeren godkjenner

1. Avslutt PlanMode
2. Skriv planfilen til disk
3. Verifiser: `ls tasks/plans/todo-[nr]-[slug].md`
4. Commit: `git add tasks/plans/... && git commit -m "plan: TODO [nr]"`
5. Oppdater tasks/todo.md → Status: `plan klar — venter på review`
6. Informer bruker: neste steg er /todo-plan-review
7. Avslutt — ikke implementer, ikke les flere filer
