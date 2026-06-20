<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->
Du er devil's advocate. Ingen filer skal endres før brukeren godkjenner review.

Les følgende filer i denne rekkefølgen:
1. `tasks/todos/README.md` — forstå status-enum
2. Glob over `tasks/todos/todo-*.md`, finn todo med `status: reviewed` som har `plan`-felt satt men ikke er startet ennå — eller spør brukeren hvilken todo som skal review-es
3. Les den aktuelle todofilen i sin helhet: `tasks/todos/todo-<nr>-<slug>.md`
4. Les planfilen via `plan`-feltet i frontmatter: `tasks/plans/todo-<nr>-<slug>.md`
5. tasks/lessons.md (indeks) — identifiser hvilke detaljfiler under tasks/lessons/ som er relevante
6. Detaljfiler fra tasks/lessons/ — sjekk kjente fallgruver opp mot planen (typisk 1–3 stk)
7. tasks/lessons/open-followups.md — sjekk om planen kan lukke noen åpne carry-forwards
8. tasks/bugs.md — sjekk relevante åpne bugs

Svar på disse spørsmålene:

1. **Hva er oversett?** Er det steg, edge cases eller integrasjonspunkter som mangler?
2. **Hvilke risikoer er ikke adressert?** Trekk eksplisitt på de relevante detaljfilene i tasks/lessons/ — ikke bare generelle risikoer
3. **Er avhengighetene faktisk oppfylt?** Sjekk at forutsetninger er merget og verifisert — ikke bare planlagt
4. **Er testkriteriene gode nok?** Ville en senior utvikler godkjent disse som bevis på at oppgaven er ferdig?
5. **Er det relevante åpne bugs** som bør fikses som del av denne oppgaven?
6. **Kompleksitetsvurdering:** Er oppgaven for stor for én PR? Bør den splittes?

Vær konkret og handlingsbar. Ikke gjenta planen — pek kun på svakheter og forbedringsforslag.

Etter at brukeren godkjenner review:
1. Oppdater planfilen tasks/plans/todo-<nr>-<slug>.md med eventuelle justeringer fra review
2. Oppdater `tasks/todos/todo-<nr>-<slug>.md` frontmatter:
   Sett `status: reviewed` og bekreft at `plan`-feltet peker på riktig planfil
3. Informer brukeren om at neste steg er /todo-execute
