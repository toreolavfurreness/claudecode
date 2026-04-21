Du er devil's advocate. Ingen filer skal endres før brukeren godkjenner review.

Les følgende filer i denne rekkefølgen:
1. tasks/todo.md — finn TODO-en med status `plan klar — venter på review`
2. tasks/plans/todo-<nr>-<slug>.md — finn planfilen via TODO-nummeret
3. tasks/lessons.md — sjekk kjente fallgruver opp mot planen
4. tasks/bugs.md — sjekk relevante åpne bugs

Svar på disse spørsmålene:

1. **Hva er oversett?** Er det steg, edge cases eller integrasjonspunkter som mangler?
2. **Hvilke risikoer er ikke adressert?** Trekk eksplisitt på lessons.md — ikke bare generelle risikoer
3. **Er avhengighetene faktisk oppfylt?** Sjekk at forutsetninger er merget og verifisert — ikke bare planlagt
4. **Er testkriteriene gode nok?** Ville en senior utvikler godkjent disse som bevis på at oppgaven er ferdig?
5. **Er det relevante åpne bugs** som bør fikses som del av denne oppgaven?
6. **Kompleksitetsvurdering:** Er oppgaven for stor for én PR? Bør den splittes?

Vær konkret og handlingsbar. Ikke gjenta planen — pek kun på svakheter og forbedringsforslag.

Etter at brukeren godkjenner review:
1. Oppdater planfilen tasks/plans/todo-<nr>-<slug>.md med eventuelle justeringer fra review
2. Oppdater **Status:** til `reviewet — klar for /todo-execute` i både planfilen og tasks/todo.md
3. Informer brukeren om at neste steg er /todo-execute
