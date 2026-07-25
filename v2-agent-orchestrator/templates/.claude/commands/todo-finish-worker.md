{{GENERATED_HEADER}}

Du er en implementer-worker som nettopp har fullført implementeringen av én todo. Kjør KUN steg 1–6 under. Du skal IKKE arkivere, skrive lessons, lukke bugs eller sette `status: done` — det gjør koordinatoren fra rapporten din.

1. **Rydd kjørende prosesser:** `pkill -f "{{DEV_SERVER_PROCESS}}" 2>/dev/null || true`; bekreft `lsof -i :{{DEV_SERVER_PORT}}` tomt.
2. **Verifiser testkriteriene** i planfila (`tasks/plans/todo-<nr>-<slug>.md`). Les faktisk output — «burde funke» er ikke godkjent. Kjør minst: `{{CMD_BUILD}}`, `{{CMD_TYPE_CHECK}}`, relevante tester (`{{CMD_TEST}}`). Kjør deretter E2E via {{CMD_E2E}} hvis tilgjengelig. Ellers: hopp over E2E, men sett `verification.e2e_skipped: true` og `verification.playwright_available: false` i ferdig-rapporten — ikke marker todoen som fullt E2E-verifisert.
3. **Forenkle (`/simplify`):** kjør `/simplify`-skillen på diffen — den gransker endret kode for gjenbruk, duplisering, ubrukt kode og unødvendige abstraksjoner og retter funnene direkte. Er skillen ikke tilgjengelig i denne kjørekonteksten (f.eks. cloud/headless), gå gjennom diffen manuelt for de samme tingene og fiks før review.
4. **Sikkerhetssjekk:** hvis todoen berørte noe under pause-triggerne ({{PAUSE_TRIGGERS}}) → STOPP (teknisk risiko, ikke din rolle å pushe — sett `status: "blocked"` i rapporten). Hvis den berørte auth-/tilgangskontroll-kode → vurder sikkerhet nøye; rapporter KRITISK/HØY-funn i `verification.security_findings`.
5. **Code review:** se kritisk gjennom diffen. Fiks alle Critical/Important før PR; rapporter uløste i `verification.review_findings`.
6. **Commit + push mot {{BASE_BRANCH}}:** commit etter `docs/naming-conventions.md`, `git push -u origin <branch>`. **Forsøk deretter `gh pr create` selv** (base `{{BASE_BRANCH}}`, tittel/body fra arbeidet ditt) — worker-sandboxer HAR gh-tilgang (verifisert ved probe; «mangler tilgang»-rapporter er som regel arvede mal-antakelser, ikke en reell begrensning). Lykkes det → sett `pr_url` i rapporten. Feiler det → IKKE feilsøk; sett `pr_url: null` + `branch` med det faktiske branch-navnet, så oppretter koordinatoren PR-en.
7. **Siste sjekkliste — bekreft FØR du returnerer rapporten, ikke etterpå:**
   - `git status` viser `nothing to commit, working tree clean`.
   - `git log origin/<branch>` (eller `git ls-remote origin <branch>`) bekrefter branchen faktisk er pushet — ikke bare committet lokalt.
   - Din ALLER SISTE melding er ETT JSON-objekt per `report-schema.md`. Ikke avslutt med prosa, et ekstra selvpålagt steg (f.eks. et frittstående sikkerhets-review-avsnitt), eller noe annet som ikke er selve rapport-JSON-en — en avsluttende melding uten denne JSON-en blir lest som en stanset/ufullstendig kjøring av koordinatoren.

STOPP her. Ikke gå videre til arkivering/lessons/status. Returner ferdig-rapporten (skjema: `docs/superpowers/loop/report-schema.md`).

Ferdig-rapporten MÅ inneholde feltene `verification.playwright_available: <bool>` og `verification.e2e_skipped: <bool>`. Disse er sporbar degraderings-historikk — koordinatoren mapper dem til `degradation`-kolonnen i run-log.

**Forbud (single-writer):** rør ALDRI noe under `tasks/` — verken `tasks/lessons*`, `tasks/bugs*`, `tasks/todo_archive.md` eller todo-frontmatteren (`status`/`claimed_by` eies av koordinatoren). Du redigerer kun koden på din egen branch.

## Fix-mode (kode-review-revisjon)

Koordinatoren kan sende deg tilbake hit etter at den uavhengige kode-revieweren (§5b) har funnet BLOKKERENDE eller VIKTIG funn. I fix-mode gjelder denne prosedyren — IKKE `todo-execute.md`:

1. `git fetch origin <branch> && git checkout <branch>` — bytt til PR-branchen.
2. `git fetch origin {{BASE_BRANCH}} && git merge origin/{{BASE_BRANCH}}` — bygg på ferskeste delt state FØR re-push.
3. Rett **UTELUKKENDE** de oppgitte kode-review-funnene (severity + file:line + issue + fix). Rør ingenting utenom.
4. Kjør `{{CMD_BUILD}}` + `{{CMD_TYPE_CHECK}}` + relevante tester på nytt.
5. `git push` til **samme branch** (samme PR — IKKE ny PR, IKKE ny `gh pr create`). Verifiser med `git log origin/<branch>` at pushen faktisk landet.
6. Returner oppdatert ferdig-rapport — samme sluttsjekkliste som steg 7 over gjelder (JSON som aller siste melding, ingen unntak).

`verification.review_findings` i ferdig-rapporten er din **selvgransking** fra steg 5 over. `code_review.findings[]` er den **uavhengige §5b-reviewen** — de er to distinkte kilder; forveksle dem ikke.
