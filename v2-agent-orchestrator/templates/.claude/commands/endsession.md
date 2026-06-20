<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->
Før du gjør noe annet — rydd opp kjørende prosesser:
- Kjør: pkill -f "{{DEV_SERVER_PROCESS}}" 2>/dev/null || true
- Bekreft: lsof -i :{{DEV_SERVER_PORT}} 2>/dev/null
- Rapporter hvilke prosesser som ble stoppet, eller "ingen kjørende prosesser funnet"

Kjør deretter: git status && git diff --stat

Hvis det finnes ucommittede endringer:
- Commit med en beskrivende melding (følg konvensjonen i docs/naming-conventions.md)
- Push branchen

**Oppdater aktiv todo:**
Finn `tasks/todos/todo-*.md` med `status: in_progress` (glob).
- Hvis todoen er **ferdig**: bruk /todo-done i stedet for /endsession
- Hvis todoen er **påbegynt men ikke ferdig**: behold `status: in_progress`; oppdater evt. `claimed_by` til nåværende branch
- Hvis ingen `in_progress` men det finnes en todo med `status: reviewed` eller `status: open` på nåværende branch: behold som den er — ingen statusendring nødvendig

Skriv tasks/sessions/todo-<nr>-<slug>.md med følgende format:

## Session dump — <branch-navn>
**Dato:** [dato]
**Branch:** [branch-navn]

### Hvor vi er
[ett avsnitt — hvilket steg er neste, og hvilken fil/funksjon er vi midt i]

### Viktig kontekst
[kun det som ikke fremgår av planfilen eller koden — beslutninger tatt, valg gjort]

### Ikke glem
[konkrete fallgruver eller beslutninger fra denne sesjonen som er lette å glemme]

### Prosjekt-spesifikt
[eventuelle midlertidige hacks, TODO-kommentarer i koden, eller halvferdige tilgangs-/sikkerhetspolicies (f.eks. RLS)]

Gi meg en oppsummering:
- Prosesser som ble ryddet opp
- Branch og commit som ble gjort
- Todo-status
- Neste steg når vi fortsetter

Ikke start på noe nytt arbeid.
