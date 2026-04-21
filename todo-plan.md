Bytt til PlanMode før du gjør noe som helst. Ingen filer skal endres i denne kommandoen.

Les følgende filer i denne rekkefølgen:
1. tasks/todo.md — finn første TODO som ikke er merket [x] eller [~]
2. tasks/lessons.md — les hele filen før du gjør noen som helst analyse
3. tasks/bugs.md — sjekk åpne bugs som kan være relevante

For den aktuelle TODO-en, presenter en detaljert plan som dekker:

1. **Analyse:** Hva oppgaven faktisk innebærer — bryt ned i konkrete steg
2. **Filer som berøres:** List alle filer som skal opprettes, endres eller slettes
3. **Avhengigheter:** Er det noe som må være på plass først? Sjekk mot todo.md
4. **Risiko og fallgruver:** Hva kan gå galt? Trekk eksplisitt på erfaringer fra lessons.md
5. **Verifisering:** Eksakte steg for å bekrefte at oppgaven er ferdig (basert på TODO-ens testkriterier)

Still deg spørsmålet: "Hva ville en senior utvikler gjort her?"

Presenter planen og vent på tilbakemelding fra bruker.

Etter at brukeren godkjenner planen:
1. Avslutt PlanMode
2. Opprett tasks/plans/todo-<nr>-<slug>.md med følgende format:

   # TODO <nr> — <tittel>
   **Dato:** [dato]
   **Status:** plan klar — venter på review

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
   - [ ] Steg 2: [beskrivelse]
   *(osv.)*

3. Verifiser at filen faktisk eksisterer på disk: ls tasks/plans/todo-<nr>-<slug>.md
   Hvis filen ikke eksisterer: opprett den på nytt før du går videre. Ikke fortsett uten at denne filen er på plass.
4. Commit planfilen umiddelbart:
   git add tasks/plans/todo-<nr>-<slug>.md
   git commit -m "plan: legg til planfil for TODO <nr>"
5. Oppdater tasks/todo.md under den aktuelle TODO-en:
   - Sett **Status:** til `plan klar — venter på review`
6. Informer brukeren om at neste steg er /todo-plan-review
