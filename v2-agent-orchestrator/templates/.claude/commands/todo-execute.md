<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->
Les følgende filer i denne rekkefølgen:
1. `tasks/todos/README.md` — forstå status-enum og deps-gating
2. Glob over `tasks/todos/todo-*.md`, finn todo med `status: reviewed` (eller `status: in_progress` hvis sesjonen gjenopptas)
   Sorter på `order` og ta den laveste.
3. Les den aktuelle todofilen i sin helhet: `tasks/todos/todo-<nr>-<slug>.md`
4. Les planfilen via `plan`-feltet i frontmatter: `tasks/plans/todo-<nr>-<slug>.md`
5. tasks/lessons.md (indeks) — identifiser hvilke detaljfiler under tasks/lessons/ som er relevante for denne TODO-en
6. Detaljfiler fra tasks/lessons/ — frisk opp relevante erfaringer før du begynner (typisk 1–3 stk)

Før du begynner implementering:
- Kjør: git branch --show-current — er du på riktig branch for denne TODO-en?
- Kjør: git status — er det ucommittede endringer fra forrige sesjon?
- **Deps-gating:** for hvert dep-nr i `deps`-feltet:
  - Prøv å finn `tasks/todos/todo-{dep}-*.md`.
  - Fil ikke funnet → dep er done og arkivert → OK.
  - Fil funnet med `status: done` → OK.
  - Fil funnet med annen status → rapporter og vent på instruksjon. Ikke start implementering.

Hvis noe mangler eller branch er feil: rapporter og vent på instruksjon. Ikke start implementering.

Hvis alt er klart:
1. Aktiver automode — kjør steg uten å spørre om tillatelse for hver filendring
2. Oppdater `tasks/todos/todo-<nr>-<slug>.md` frontmatter: sett `status: in_progress` og `claimed_by: <branch-navn>`
3. Implementer steg for steg basert på steg-listen i planfilen:

   - Marker hvert steg som fullført etterhvert som det er gjort og verifisert: [ ] → [x]
   - **Committ INKREMENTELT etter hvert grønt steg** (lokale commits i worktreet — push skjer samlet
     til slutt): et API-dødsfall skal aldri sitte på 30+ ucommittede filer (todo-317: implementer
     døde 2× ved commit-punktet; §5a-rescue reddet det, men inkrementelle commits fjerner klassen)
   - Verifisering betyr å kjøre relevante kommandoer og lese faktisk output — ikke anta at noe fungerer
   - Etter hvert steg: gi en kort statusmelding om hva som ble gjort og hva som er neste
   - **Rødt før grønt på steg merket `TDD-STEG`** (utvidelse av regelen over, ikke en ny mekanisme
     ved siden av). Bruk `superpowers:test-driven-development`-skillen via `Skill`-verktøyet; er den
     ikke tilgjengelig i denne kjørekonteksten, gjelder oppskriften her:
     1. Skriv ÉN minimal feilende test for oppførselen steget navngir. Ingen produksjonskode ennå.
     2. Kjør den scopet (`{{CMD_TEST}} <fil>`) og LES outputen. Rødt av riktig grunn = feilen handler
        om oppførselen som mangler — ikke skrivefeil i testen, feil import-sti eller manglende
        testoppsett. Består testen med det samme: den tester eksisterende atferd — skriv den om.
     3. Committ den røde testen ALENE. Subject: `test(red): <hva testen krever>`. Body linje 1:
        `RED: <testfil> :: <testnavn ordrett>`, linje 2: `FAILURE: <ordrett feillinje fra runneren>`.
        Kode-revieweren sjekker ut nettopp denne commiten og kjører testen på nytt — en påstand du
        ikke kan reprodusere blir et BLOKKERENDE funn.
     4. Skriv minimal implementasjon, kjør samme test til grønn, committ grønt steg som vanlig.
     - Steg UTEN `TDD-STEG` har intet rødt-krav (UI/CSS/layout, migrasjon, config, dokumentasjon og
       prompt-/mal-filer, ren refaktor uten atferdsendring).
     - Hele `verification.tdd`-blokken limes ordrett inn i PR-bodyen — feltet er ellers
       skrive-bare (ingen leser ferdig-rapporten i §5b-dispatchen; verifiseringsrunde 2).
     - Lar et merket steg seg ikke rødt-bevise (feilmerket, eller oppførselen kan ikke isoleres uten
       ny testinfrastruktur): IKKE hopp over det stille. Før det i `verification.tdd.deviations[]`
       med steg-referanse og målt grunn, og gjenta det i PR-bodyen.

   - Hvis et steg er merket ⚠️ PAUSE:
     Deaktiver automode, beskriv hva som skal skje, og vent på eksplisitt bekreftelse.
     Aktiver automode igjen etterpå.

   - Hvis du støter på uventet feil:
     Deaktiver automode. Bruk `/systematic-debugging` (Superpowers) hvis tilgjengelig.
     Ellers: bruk inline fallback-protokollen:
       (1) Isoler eksakt feilmelding — kopier den ordrett.
       (2) Reproduser med minimalreproduksjon — fjern alt unødvendig.
       (3) Formuler én hypotese om rotårsak — én om gangen.
       (4) Test — endre én ting; observer resultatet.
       (5) Bekreft at fix løser feilmeldingen.
       (6) Kjør {{CMD_BUILD}} + {{CMD_TYPE_CHECK}} for å bekrefte ingen ny regresjon.
     Rapporter funn og vent på bekreftelse før du fortsetter.

   - E2E-verifisering:
     Kjør E2E via {{CMD_E2E}} (f.eks. Playwright MCP, `mcp__playwright__browser_navigate` m.fl.) hvis tilgjengelig.
     Ellers: hopp over E2E-steg, men sett `verification.e2e_skipped: true` og
     `verification.playwright_available: false` i ferdig-rapporten.
     Ikke marker todoen som fullt E2E-verifisert uten at E2E faktisk ble kjørt.

   - For database-migrasjoner: alltid kjør mot dev-miljøet (env-id: {{DEV_ENV_ID}}).
     Aldri push til prod uten eksplisitt bekreftelse.

   - For endringer i tilgangs-/sikkerhetspolicies (f.eks. RLS): kjør prosjektets relevante
     tech-review-agent (se loop.config tech_review_agents — f.eks. rls-auditor) etter at
     migrasjonen er kjørt for å verifisere dekning på alle tabeller. Verifiser i tillegg med en
     faktisk spørring at policyen blokkerer det den skal blokkere — ikke bare at syntaksen er riktig.

Ikke marker hele TODO-en som done — det gjøres av /todo-done.
Ikke start på neste TODO uten eksplisitt instruksjon.
