Les følgende filer i denne rekkefølgen:
1. tasks/todo.md — finn TODO-en med status `reviewet — klar for /todo-execute`
2. tasks/plans/todo-<nr>-<slug>.md — finn planfilen via TODO-nummeret
3. tasks/lessons.md — frisk opp relevante erfaringer før du begynner

Før du begynner implementering:
- Kjør: git status — er det ucommittede endringer fra forrige sesjon?
- Er alle avhengigheter merket [x] i tasks/todo.md?

Hvis noe mangler: rapporter til bruker og vent på instruksjon. Ikke start implementering.

Hvis alt er klart:
1. Oppdater **Status:** til `under arbeid` i tasks/todo.md og i planfilen
2. Implementer steg for steg basert på steg-listen i planfilen:
   - Marker hvert steg som fullført i planfilen etterhvert som det er gjort og verifisert: [ ] → [x]
   - Etter hvert steg: gi bruker en kort statusmelding om hva som ble gjort og hvilket steg som er neste
   - Ikke gå videre til neste steg uten at forrige er verifisert

Ikke marker hele TODO-en som [x] — det gjøres av /todo-done.
Ikke start på neste TODO uten eksplisitt instruksjon fra bruker.
