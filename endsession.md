Før du gjør noe annet — rydd opp kjørende prosesser:
- Kjør: pkill -f "playwright" 2>/dev/null || true
- Kjør: pkill -f "expo start" 2>/dev/null || true
- Kjør: pkill -f "next dev" 2>/dev/null || true
- Bekreft at prosessene er stoppet: lsof -i :8081 -i :3000 -i :3001 2>/dev/null
- Rapporter hvilke prosesser som ble drept, eller "ingen kjørende prosesser funnet"

Kjør deretter: git status && git diff --stat

Hvis det finnes ucommittede endringer:
- Commit med en beskrivende melding om hva som er gjort og hva som gjenstår
- Push branchen

Oppdater tasks/todo.md:
- Marker fullførte todos med [x]
- Marker påbegynte todos med [~] og legg til en kort note om hva som gjenstår

Skriv tasks/sessions/todo-<nr>-<slug>.md med følgende format:

## Session dump — <branch-navn>
**Dato:** [dato]
**Branch:** [branch-navn]

### Hvor vi er
[ett avsnitt — hvilket steg er neste]

### Viktig kontekst
[kun det som ikke fremgår av planfilen eller koden]

### Ikke glem
[konkrete fallgruver eller beslutninger tatt i denne sesjonen]

Gi meg en oppsummering:
- Prosesser som ble ryddet opp
- Branch og commit som ble gjort
- Todo-status
- Neste steg

Ikke start på noe nytt arbeid.
