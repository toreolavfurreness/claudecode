# /todo-execute

**Agent:** `@implementer` (claude-sonnet-4-6) — delegeres automatisk eller via @-mention
**Eksplisitt:** Skriv `@implementer implementer TODO-[nr]` i Claude Code

---

Les følgende filer i denne rekkefølgen:
1. CLAUDE.md — atferdsregler
2. tasks/plans/todo-<nr>-<slug>.md — finn planfilen for TODO-en med status `reviewet — klar for /todo-execute`

Planfilen inneholder all nødvendig kontekst: TODO-beskrivelse, ekstraherte lessons og risiko.
Du leser ikke tasks/todo.md eller tasks/lessons/ direkte — alt er i planfilen.
Mangler du kontekst? Si fra til brukeren — ikke søk på eget initiativ.

Før du begynner implementering:
- Kjør: git status — er det ucommittede endringer fra forrige sesjon?
- Er alle avhengigheter i planfilen oppfylt?

Hvis noe mangler: rapporter til bruker og vent på instruksjon. Ikke start implementering.

Hvis alt er klart:
1. Oppdater **Status:** til `under arbeid` i planfilen
2. Velg riktig startpunkt:
   - **Ny feature:** Kjør `/tdd` — skriv failing test før første linje produksjonskode.
     *(Krever Superpowers. Ikke installert? Skriv testene manuelt basert på Verifisering-seksjonen.)*
   - **Bug:** Kjør `/systematic-debugging` — identifiser rot-årsak FØR du rører kode.
     *(Krever Superpowers. Ikke installert? Dokumenter hypotese og bevis rot-årsak eksplisitt.)*
   - **Refaktor/konfig:** Gå direkte til steg 3.
3. Implementer steg for steg basert på steg-listen i planfilen:
   - Marker hvert steg som fullført i planfilen etterhvert som det er gjort og verifisert: [ ] → [x]
   - Etter hvert steg: gi bruker en kort statusmelding om hva som ble gjort og hvilket steg som er neste
   - Ikke gå videre til neste steg uten at forrige er verifisert

Ikke marker hele TODO-en som [x] — det gjøres av /todo-done.
Ikke start på neste TODO uten eksplisitt instruksjon fra bruker.
