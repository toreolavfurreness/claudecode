<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->
Implementeringen er fullført. Gjør følgende i rekkefølge — ikke hopp over steg:

1. **Rydd opp kjørende prosesser:**
   - Kjør: pkill -f "{{DEV_SERVER_PROCESS}}" 2>/dev/null || true
   - Bekreft: lsof -i :{{DEV_SERVER_PORT}} 2>/dev/null
   - Rapporter hvilke prosesser som ble stoppet, eller "ingen kjørende prosesser funnet"

2. **Verifiser** at alle steg i planfilen tasks/plans/todo-<nr>-<slug>.md er merket [x]

3. **Testkriterier:** Bruk /verification-before-completion fra Superpowers.
   Les faktisk output og bekreft at hvert verifiseringskriterium i planfilen er bestått.
   "Burde fungere" er ikke godkjent — bevis det med output.

4. **Forenkle:** Bruk /simplify fra Superpowers.
   Se gjennom diffen for duplisering, ubrukt kode, unødvendige abstraksjoner
   eller "just in case"-logikk. Fiks det før code review.

5. **Sikkerhetssjekk:**
   - Hvis diffen berører de stiene som er konfigurert for en tech-review-agent: kjør prosjektets
     relevante tech-review-agent (se loop.config tech_review_agents). Eksempler:
     `rls-auditor` hvis migrasjons-/skjemastier er berørt; `security-reviewer` hvis auth-/
     server-action-/klientkode er berørt.
   - Funn merket KRITISK eller HØY blokkerer — fiks og verifiser på nytt

6. **Code review:** Bruk /requesting-code-review fra Superpowers.
   Fiks alle funn merket Critical eller Important før du går videre.
   Minor-funn noteres men blokkerer ikke.

7. **Marker TODO som ferdig:**
   Oppdater `tasks/todos/todo-<nr>-<slug>.md` frontmatter: sett `status: done`

8. **Arkiver TODO:** Flytt innholdet til tasks/todo_archive.md med dette formatet:

   ---
   ## TODO <nr> — <tittel>
   **Arkivert:** [dato]
   **Status:** ferdig
   **Branch:** [feature/branch-navn]
   **PR:** [PR-nummer hvis relevant]

   ### Beskrivelse
   [original beskrivelse fra todofilen]

   ### Gjennomføring
   - **Komplikasjoner:** [beskriv hva som ikke gikk som planlagt, eller "ingen"]
   - **Workarounds/fixes:** [beskriv løsninger som ble valgt, eller "ingen"]
   - **Avvik fra planen:** [beskriv hvis implementeringen endte opp annerledes, eller "ingen"]

   ### Planfil
   tasks/plans/archive/todo-<nr>-<slug>.md

   Slett deretter todofilen: `tasks/todos/todo-<nr>-<slug>.md`

9. **Arkiver planfil:** Flytt tasks/plans/todo-<nr>-<slug>.md til tasks/plans/archive/todo-<nr>-<slug>.md

10. **Lukk bugs:** Hvis denne TODO-en lukket én eller flere bugs i tasks/bugs.md,
   flytt dem til tasks/bugs_archive.md med følgende format:

   ## BUG-XXX — [tittel]
   **Lukket:** [dato]
   **Lukket av:** TODO-[nummer]
   **Løsning:** [kort beskrivelse av hva som fikset det]

   Fjern dem fra tasks/bugs.md etterpå.

11. **Lessons learned:** Gå gjennom komplikasjoner og workarounds.
   For hver enkelt: vurder aktivt om dette er noe fremtidige TODOs kan støte på igjen.
   Vær konkret og handlingsbar, ikke generell. Dette steget er obligatorisk, ikke valgfritt.

   **Hvor lessons skrives:**
   - Identifiser hvilken tema-fil under tasks/lessons/ hver lesson hører hjemme i.
     Gyldige tema: {{LESSONS_TOPICS}}.
   - Skriv hver lesson med Pattern/Symptom + Sjekkliste fremover + `**Kilder:**`-linje.
   - Hvis 2+ tidligere lessons dekker samme mønster: konsolider med flere kilder, ikke duplikat.
   - Oppdater `tasks/lessons.md` (indeksen) med en ny én-linjes bullet under riktig tema-header.
   - Carry-forward-bullets (oppfølginger til fremtidige TODO-er): legg i `tasks/lessons/open-followups.md` under en seksjon for opprinnelig TODO.

   Rut hver lesson til tema-filen som best matcher rotårsaken (f.eks. tilgangs-/sikkerhetspolicy-feil,
   migrasjonsfeil, framework-/routing-gotchas, eller typefeil) blant de gyldige temaene over.

12. **Nye bugs:** Ble det avdekket nye bugs underveis?
    Legg dem til tasks/bugs.md med dette formatet:

    ## BUG-XXX — [tittel]
    **Oppdaget:** [dato]
    **Oppdaget i:** TODO-[nummer]
    **Beskrivelse:** [hva som skjer]
    **Reprodusere:** [steg for å reprodusere]
    **Prioritet:** høy / middels / lav

13. **Git:** Commit alle endringer med beskrivende melding etter konvensjonen
    i docs/naming-conventions.md, og push branchen.

14. **Oppsummering:** Gi en kort rapport:
    - Prosesser som ble ryddet opp
    - Hva ble implementert
    - Komplikasjoner og hvordan de ble løst
    - Funn fra sikkerhetssjekk og code review
    - Bugs lukket og eventuelle nye bugs
    - Hva som ble lagt til i tasks/lessons/<tema>.md (og indeksen)
    - Neste TODO i køen (men ikke start på den)

Vent på eksplisitt bekreftelse før neste TODO påbegynnes.
