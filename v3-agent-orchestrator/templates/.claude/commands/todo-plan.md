---
description: "Planlegg neste TODO i PlanMode; ingen filendringer før godkjent."
---
<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->
Bytt til PlanMode før du gjør noe som helst. Ingen filer skal endres i denne kommandoen.

Les følgende filer i denne rekkefølgen:
1. `tasks/todos/README.md` — forstå frontmatter-skjema og status-enum
2. Glob over `tasks/todos/todo-*.md`, les frontmatter (`nr`, `status`, `order`, `title`, `deps`).
   Sorter på `order`. Finn første todo med `status: open`.
   **Deps-sjekk:** for hvert dep-nr: prøv å finn `tasks/todos/todo-{dep}-*.md`.
   Fil ikke funnet → dep er done (arkivert) → OK. Fil funnet med annen status enn done → hopp til neste kandidat.
3. Les den valgte todofilen i sin helhet: `tasks/todos/todo-NN-slug.md`
4. tasks/lessons.md — tema-katalog + lese-protokoll. Velg 1–3 tema (gyldige tema: `ls tasks/lessons/`)
5. Lessons fra tasks/lessons/<tema>/ etter lese-protokollen: titler og nøkkelordsøk først, les så de 3–5 relevante lesson-filene i sin helhet — aldri en hel tema-mappe
6. `tasks/followups/` er oppfølgingskøen (én fil per carry-forward), ikke lessons. `grep -rl` etter todo-nummeret og filene/symbolene todoen berører, les kun treff-filene, og sjekk om denne TODO-en kan lukke noen av de åpne carry-forwardene.
7. tasks/bugs.md — sjekk åpne bugs som kan være relevante
8. docs/naming-conventions.md — frisk opp konvensjonene
9. `docs/data-model.md` (eller prosjektets tilsvarende datamodell-doc) — hvis det finnes og todoen berører database eller tilgangskontroll

For den aktuelle TODO-en, presenter en detaljert plan som dekker:

1. **Analyse:** Hva oppgaven faktisk innebærer — bryt ned i konkrete steg
2. **Filer som berøres:** List alle filer som skal opprettes, endres eller slettes
3. **Avhengigheter:** Er det noe som må være på plass først? Sjekk mot dep-feltet i todofilen
4. **Risiko og fallgruver:** Hva kan gå galt? Trekk eksplisitt på erfaringer fra de relevante lesson-filene (etter lese-protokollen i tasks/lessons.md)
5. **Verifisering:** Eksakte steg for å bekrefte at oppgaven er ferdig (basert på TODO-ens testkriterier)

Merk alle risikable steg eksplisitt med ⚠️ PAUSE i steg-listen. Risikable steg er {{PAUSE_TRIGGERS}}, typisk:
- Database-migrasjoner / skjemaendringer
- Endringer i tilgangs-/sikkerhetspolicies (f.eks. RLS-policies)
- Sletting av filer eller data
- Push til remote / merge til {{PROD_BRANCH}}
- Endringer i miljøvariabler eller secrets
- Alt som berører produksjonsmiljøet ({{PROJECT_NAME}}-prod)

Merk i tillegg hvert **logikk-bærende** steg med tokenet `TDD-STEG` — **rett etter steg-tittelen på
FØRSTE fysiske linje** (et token på en fortsettelseslinje treffes aldri av det ankrede grepet). Står
både `TDD-STEG` og `⚠️ PAUSE` på samme steg: `TDD-STEG` først, PAUSE-halen sist, f.eks.
`- [ ] Steg 3: beregn rabatten for årsabonnement TDD-STEG ⚠️ PAUSE — krever manuell bekreftelse`.
Logikk-bærende = steget navngir en testbar funksjon/oppførsel der man kan formulere ÉN feilende test
(ren funksjon, beregning, API-handler, datatransform, server-funksjon).
**Merk ALDRI:** UI/CSS/layout, migrasjoner, config/env, dokumentasjon, prompt-/mal-filer, ren
refaktor uten atferdsendring. Overmerking er like skadelig som undermerking: den lager krav
implementeren ikke kan innfri, og hver umulig markør brenner en fiks-runde.

Still deg spørsmålet: "Hva ville en senior utvikler gjort her?"

Presenter planen og vent på tilbakemelding.

---

Etter at du godkjenner planen:

1. Bytt rolle: du er nå devil's advocate. Vurder planen kritisk.
   Svar på disse spørsmålene:
   - Hva er oversett? Mangler det steg, edge cases eller integrasjonspunkter?
   - Hvilke risikoer er ikke adressert? Trekk eksplisitt på de relevante lesson-filene (etter lese-protokollen i tasks/lessons.md)
   - Er avhengighetene faktisk oppfylt? Sjekk at forutsetninger er merget og verifisert
   - Er testkriteriene gode nok? Vil de faktisk bevise at todoen er ferdig?
   - Er det relevante åpne bugs som bør fikses som del av denne oppgaven?
   - Er oppgaven for stor for én PR? Bør den splittes?
   Vær konkret og handlingsbar. Ikke gjenta planen — pek kun på svakheter.
   Vent på tilbakemelding.

2. Etter at du godkjenner review:
   - Avslutt PlanMode
   - Opprett tasks/plans/todo-<nr>-<slug>.md med følgende format:

     # TODO <nr> — <tittel>
     **Dato:** [dato]
     **Plan-SHA:** [full 40-tegns SHA — `git rev-parse origin/{{BASE_BRANCH}}` etter synk]
     **Status:** reviewet — klar for /todo-execute

     ## Analyse
     [analysedel]

     ## Filer som berøres
     [filliste]

     ## Avhengigheter
     [avhengigheter]

     ## Risiko og fallgruver
     [risikovurdering med referanser til relevante lessons]

     ## Verifisering
     [testkriterier]

     ## Steg
     - [ ] Steg 1: [beskrivelse]
     - [ ] Steg 2: [beskrivelse] ⚠️ PAUSE — krever manuell bekreftelse
     *(osv.)*

   `**Plan-SHA:**` er `{{BASE_BRANCH}}`-tippen planen ble laget mot. Skal ALLTID reflektere den
   `{{BASE_BRANCH}}`-tippen DENNE versjonen ble synket mot — også i en revisjonsrunde (se
   `coordinator-runbook.md` §5c, «re-plan-runde»). Koordinatoren bruker den i ferskhets-gaten
   (`coordinator-runbook.md` §5c) og ved revalidering av en gammel plan.

   - Oppdater `tasks/todos/todo-<nr>-<slug>.md` frontmatter:
     Sett `status: reviewed` og `plan: "tasks/plans/todo-<nr>-<slug>.md"`
   - Informer om at neste steg er /todo-execute
