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
   - Verifisering betyr å kjøre relevante kommandoer og lese faktisk output — ikke anta at noe fungerer
   - Etter hvert steg: gi en kort statusmelding om hva som ble gjort og hva som er neste

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
