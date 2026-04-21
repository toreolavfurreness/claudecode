Implementeringen er fullført. Gjør følgende i rekkefølge — ikke hopp over steg:

1. **Rydd opp kjørende prosesser:**
   - Kjør: pkill -f "playwright" 2>/dev/null || true
   - Kjør: pkill -f "expo start" 2>/dev/null || true
   - Kjør: pkill -f "next dev" 2>/dev/null || true
   - Bekreft at prosessene er stoppet: lsof -i :8081 -i :3000 -i :3001 2>/dev/null
   - Rapporter hvilke prosesser som ble drept, eller "ingen kjørende prosesser funnet"

2. **Verifiser** at alle steg i planfilen tasks/plans/todo-<nr>-<slug>.md er merket [x]
3. **Testkriterier:** Kjør /verification-before-completion — ingen ferdig-påstand uten fersk kjøring.
   Les faktisk output og bekreft at hvert verifiseringskriterium i planfilen er bestått.
   Ord som "burde fungere" er ikke godkjent — bevis det med output.
4. **Rydd opp koden:** Kjør /simplify på alle endrede filer.
   Kjør tester etterpå og bekreft at ingenting er ødelagt.
5. **Code review:** Kjør /requesting-code-review.
   Fiks alle funn merket Critical eller Important før du går videre.
   Minor-funn kan noteres men trenger ikke blokkere.
6. **Marker TODO som ferdig:** Sett [x] på selve TODO-en og oppdater **Status:** til `ferdig` i tasks/todo.md
7. **Arkiver TODO:** Flytt hele TODO-en til tasks/todo_archive.md med dato.
   Bruk alltid dette formatet — ikke kopier format fra eksisterende innhold i todo_archive.md:

   ---
   ## TODO <nr> — <tittel>
   **Arkivert:** [dato]
   **Status:** ferdig
   **Branch:** [feat/branch-navn]
   **PR:** [PR-nummer hvis relevant]

   ### Beskrivelse
   [original beskrivelse fra todo.md]

   ### Gjennomføring
   - **Komplikasjoner:** [beskriv hva som ikke gikk som planlagt, eller "ingen"]
   - **Workarounds/fixes:** [beskriv løsninger som ble valgt, eller "ingen"]
   - **Avvik fra planen:** [beskriv hvis implementeringen endte opp annerledes enn planlagt, eller "ingen"]

   ### Planfil
   tasks/plans/archive/todo-<nr>-<slug>.md

8. **Arkiver planfil:** Flytt tasks/plans/todo-<nr>-<slug>.md til tasks/plans/archive/todo-<nr>-<slug>.md
   Filnavnet forblir identisk — TODO-nummeret er alltid nøkkelen for å finne planfilen fra arkivet.
9. **Lukk bugs:** Hvis denne TODO-en lukket én eller flere bugs, flytt dem fra tasks/bugs.md til tasks/bugs_archive.md med følgende format:

   ## BUG-XXX — [tittel]
   **Lukket:** [dato]
   **Lukket av:** [TODO-nummer]
   **Løsning:** [kort beskrivelse av hva som fikset det]

   Fjern dem fra tasks/bugs.md etterpå.
10. **Lessons learned:** Gå gjennom komplikasjonene og workarounds du dokumenterte.
    For hver enkelt: vurder aktivt om dette er noe fremtidige TODOs kan støte på igjen.
    Oppdater tasks/lessons.md — vær konkret og handlingsbar, ikke generell.
    Dette steget er obligatorisk, ikke valgfritt.
11. **Nye bugs:** Ble det avdekket nye bugs underveis? Legg dem til tasks/bugs.md
12. **Git:** Commit alle endringer med en beskrivende melding, push branchen
13. **Oppsummering:** Gi bruker en kort rapport:
    - Prosesser som ble ryddet opp
    - Hva ble implementert
    - Komplikasjoner og hvordan de ble løst
    - Funn fra /simplify og /code-review
    - Bugs lukket og eventuelle nye bugs oppdaget
    - Hva som ble lagt til i lessons.md
    - Neste TODO i køen (men ikke start på den)

Vent på eksplisitt bekreftelse fra bruker før neste TODO påbegynnes.
