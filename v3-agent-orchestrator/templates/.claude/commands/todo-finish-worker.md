---
description: "Implementer-workerens avslutningsprosedyre: verifiser, simplify, code-review, PR."
---
{{GENERATED_HEADER}}

Du er en implementer-worker som nettopp har fullført implementeringen av én todo. Kjør KUN steg 1–6 under. Du skal IKKE arkivere, skrive lessons, lukke bugs eller sette `status: done` — det gjør koordinatoren fra rapporten din.

1. **Rydd kjørende prosesser — PORT-SCOPET, aldri navnebasert:** `lsof -ti :{{DEV_SERVER_PORT}} | xargs -r kill 2>/dev/null || true`; bekreft `lsof -i :{{DEV_SERVER_PORT}}` tomt. (et navnebasert drap på prosessnavnet `{{DEV_SERVER_PROCESS}}` dreper ALLE dev-servere på maskinen — også eierens og andre prosjekters. Bruk port-varianten.)
1b. **Bootstrap worktree (idempotent):** kjør `.claude/scripts/bootstrap-worktree.sh` — synker `node_modules` mot lockfile (`npm ci` hvis mangler/stale) og kopierer et minimalt sett env-nøkler fra hovedsjekkuten. Rapporter hva som ble gjort/hoppet over/mangler. Trygt å kjøre på nytt her selv om Steg 0 i implementer-charteret allerede kjørte det (rask no-op andre gang).
2. **Verifiser testkriteriene** i planfila (`tasks/plans/todo-<nr>-<slug>.md`). Les faktisk output — «burde funke» er ikke godkjent. Kjør minst: `{{CMD_BUILD}}`, `{{CMD_TYPE_CHECK}}`, `{{CMD_FORMAT_CHECK}}` (prettier — uformatert kode er BLOKKERENDE; kjør `npm run format` og commit på nytt før PR), relevante tester (`{{CMD_TEST}}`). Kjør deretter full E2E via {{CMD_E2E}} hvis tilgjengelig (se `run-loop.md` §1 for hvordan tilgjengelighet avgjøres). Dette steget skriver **KUN** `verification.e2e_outcome` — aldri `web_smoke_outcome`.
2a. **Web-smoke (obligatorisk minstebar for klientkode-todos):** hvis diffen rører `app/`, `components/` eller `lib/`, kjør `{{CMD_WEB_SMOKE}}` — den minste web-lastings-/login-gaten som beviser at appen faktisk laster i en browser (BUG-076-klassen: en hook som kaster på web, usett av tsc/lint/unit). Todos som KUN rører `supabase/`, `docs/`, `tasks/` e.l. (ingen klientkode) kan hoppe over dette steget. Dette steget skriver **KUN** `verification.web_smoke_outcome` — aldri `e2e_outcome`. En grønn web-smoke gjør ALDRI hele ankeret grønt; de to feltene er uavhengige, og begge er obligatoriske i hver ferdig-rapport.

   **Gren-til-verdi-tabell (gjelder begge steg 2 og 2a — tom/utelatt verdi er aldri lovlig når steget var relevant):**

   | Gren | `e2e_outcome` (steg 2) | `web_smoke_outcome` (steg 2a) |
   |---|---|---|
   | Hoppet over (diffen rører ikke klientkode) | `e2e_not_applicable` | `e2e_not_applicable` |
   | Kjørte, alt passerte | `e2e_green` | `e2e_green` |
   | Kjørte, reell assert-feil | `e2e_red` (BLOKKERENDE, stopp) | `e2e_red` (BLOKKERENDE, stopp) |
   | Spec-drift fikset i samme PR | `e2e_green` + `notes` | `e2e_green` + `notes` |
   | Metro/bundling blokkerte | `e2e_blocked:metro_bundling` | `e2e_blocked:metro_bundling` |
   | Env-nøkler manglet | `e2e_blocked:env_missing` | `e2e_blocked:env_missing` |
   | Verktøyet fantes ikke (etter korrekt probe) | `e2e_unavailable` | `e2e_unavailable` |

   - **Reell spec-FEIL** (assert traff faktisk feil UI-state/krasj) → BLOKKERENDE. Ikke rapporter grønt — fiks feilen eller stopp.
   - **Nav-/locator-assert feiler urelatert til din diff** (f.eks. en tekst-/label-endring andre steder brøt en `getByText`-selector i spec-en) → dette er spec-drift, IKKE en web-regresjon fra din diff. Fiks selve spec-en (foretrekk testID-baserte locators, samme mønster som TODO 151s tab-today-fix) i samme PR, re-kjør, og noter i `notes` at det var spec-drift, ikke kode-feil.
   - **Worktree-Metro blokkerer bundling** (ikke sett opp automatisk): `node_modules` og env-nøkler skal allerede være på plass fra Steg 1b (`.claude/scripts/bootstrap-worktree.sh`) — det er eneste kilde til npm-ci/env-kopi-oppskriften, dupliser den ikke her. Hvis fortsatt blokkert etter bootstrap: curl-probe mot bundle-endepunktet for å bekrefte ÅRSAKEN (ikke bare anta), sett riktig `e2e_blocked:<reason>`-verdi + skriv den FAKTISKE blokkeringsårsaken i `notes` — ikke fabrikker et grønt resultat.
3. **Forenkle (minste diff):** gå gjennom din egen diff og list funnene, én linje per funn:
   `<fil>:L<linje>: <tag> <hva>. <erstatning>.`, der tag er `delete` (død kode, ubrukt fleksibilitet), `stdlib`/`native`
   (hjemmelaget kode for noe plattformen allerede har), `yagni` (abstraksjon med én bruker, konfig ingen setter) eller
   `shrink` (samme logikk på færre linjer). Rett alle før review. Rapporter `verification.min_diff_net` = netto linjer
   fjernet i dette steget (0 er gyldig) og `verification.min_diff_findings` = antall funn. **Kuttes aldri:** sikkerhet,
   validering, tilgjengelighet, feilhåndtering som hindrer datatap, og tester som beviser planens kriterier.
4. **Sikkerhetssjekk:** hvis todoen berørte noe under pause-triggerne ({{PAUSE_TRIGGERS}}) → STOPP (teknisk risiko, ikke din rolle å pushe — sett `status: "blocked"` i rapporten). Hvis den berørte auth-/tilgangskontroll-kode → vurder sikkerhet nøye; rapporter KRITISK/HØY-funn i `verification.security_findings`.
4b. **`verification.tdd`:** ett par per `TDD-STEG` i planen (`red_commit`, `test`, `failure`, `green_commit`), eller et eksplisitt avvik i `deviations[]`. Ingen `TDD-STEG` i planen ⇒ `{"required_steps": 0, "pairs": [], "deviations": []}` — fravær skal være skrevet, ikke utledet av stillhet. Lim hele blokken ordrett inn i PR-bodyen i steg 6 (kode-revieweren leser PR-en, ikke ferdig-rapporten).
5. **Code review:** se kritisk gjennom diffen. Fiks alle Critical/Important før PR; rapporter uløste i `verification.review_findings`.
6. **Commit + PR mot {{BASE_BRANCH}}:** commit etter `docs/naming-conventions.md`, push branchen, og `gh pr create --base {{BASE_BRANCH}}` (ALDRI `--base {{PROD_BRANCH}}`).

STOPP her. Ikke gå videre til arkivering/lessons/status. Returner ferdig-rapporten (skjema: `docs/superpowers/loop/report-schema.md`).

Ferdig-rapporten MÅ inneholde BEGGE feltene `verification.e2e_outcome: <verdi>` og `verification.web_smoke_outcome: <verdi>` (se `report-schema.md` for fem-verdi-enumet). Disse er sporbar degraderings-historikk — koordinatoren avleder `degradation`-kolonnen i run-log fra begge feltene sammen.

Ferdig-rapporten MÅ i tillegg bære `scout_usage` når `scout.enabled` er `true` — `{"dispatches": 0, "bytes_read": 0, "findings": 0}` hvis ingen scout ble brukt.

**Forbud (single-writer):** rør ALDRI noe under `tasks/` — verken `tasks/lessons*`, `tasks/bugs*`, `tasks/todo_archive.md` eller todo-frontmatteren (`status`/`claimed_by` eies av koordinatoren). Du redigerer kun koden på din egen branch.

**Ett unntak:** planfila for DIN todo, `tasks/plans/todo-<nr>-<slug>.md`. Du oppdaterer dens
fix-runde-seksjoner (`### Fix-runde <N>` / `#### V-blokk re-kjørt mot HEAD …`) og committer
den i samme PR. Ingen andre filer under `tasks/` — særlig ikke `tasks/lessons*` (lessons returneres
som DATA i rapporten; koordinatoren skriver dem).

## Fix-mode (kode-review-revisjon)

Koordinatoren kan sende deg tilbake hit etter at den uavhengige kode-revieweren (§5b) har funnet BLOKKERENDE eller VIKTIG funn. I fix-mode gjelder denne prosedyren — IKKE `todo-execute.md`:

1. `git fetch origin <branch> && git checkout <branch>` — bytt til PR-branchen.
2. `git fetch origin {{BASE_BRANCH}} && git merge origin/{{BASE_BRANCH}}` — bygg på ferskeste delt state FØR re-push. Konflikt i planfila løses ved å BEHOLDE BEGGE SIDERS fix-runde-seksjoner — de er additive. Bruk aldri `--ours`/`--theirs` på hele planfila.
3. Rett **UTELUKKENDE** de oppgitte kode-review-funnene (severity + file:line + issue + fix). Rør ingenting utenom.
4. Hvis denne worktreen mangler `node_modules`/env-filer (f.eks. et fix-mode-oppdrag dispatchet til en annen worktree enn den opprinnelige): kjør `.claude/scripts/bootstrap-worktree.sh` før byggkommandoene under.
4b. **Commit-meldingens emnelinje MÅ inneholde `fix-runde <N>`** (samme `<N>` som V-blokk-
   seksjonen under). Dette er ikke kosmetikk: det er den ENESTE persisterte grensen mellom
   fix-rundene. `gh api repos/{owner}/{repo}/pulls/<n>/commits` er den eneste kilden som overlever
   squash-merge til `{{BASE_BRANCH}}`, og uten rundenummeret i emnelinja kan ingen — verken menneske eller
   script — si hvilke commits som hørte til hvilken runde. Målt 2026-09-10 på fem PR-er med
   flere commits: alle fem navnga minst én runde, men to hadde HULL (fant 4 av 5 og 1 av 2
   runder) fordi konvensjonen var uskreven. Denne linja lukker hullet.

5. Kjør `{{CMD_BUILD}}` + `{{CMD_TYPE_CHECK}}` + `{{CMD_FORMAT_CHECK}}` + relevante tester på nytt.
6. **Re-kjør HELE V-blokken i planen mot HEAD** og lim inn ordrett kommando + output i planfilas
   seksjon `#### V-blokk re-kjørt mot HEAD (fix-runde <N>)`. Endre ALDRI et tall i planen uten at
   kommandoen som ga det står ved siden av.
   **Format (bindende — koordinatorens gate F måler nøyaktig dette):**
   - **Plassering:** har planen en innledende `## 0`-blokk OG en `## 1. Analyse`-seksjon, legg
     seksjonen i `## 0` under `### Fix-runde <N>`, umiddelbart FØR `## 1. Analyse`. **Mange planer
     har ingen av delene** (målt 2026-09-16: 33 av 253 planfiler har `## 0`, 25 har `## 1. Analyse`)
     — da legges fix-runden som en EGEN toppnivå-seksjon sist i fila, `## <neste nr>. Fix-runde <N>`,
     med V-blokken under. Følg alltid presedensen i DEN planfilen du jobber i: har forrige fix-runde
     en plassering gaten allerede godtok, bruk samme. Gate F måler ikke posisjon — den ankrer på
     overskriftsteksten, fence-pariteten og attestasjonslinjen under. Velg derfor plassering etter
     lesbarhet, og rapporter avviket i `deviations` hvis du fraviker punktet over.
   - Overskriften skrives ORDRETT og UTEN suffiks: `#### V-blokk re-kjørt mot HEAD (fix-runde <N>)`.
     Ingen «— delvis», ingen tillegg etter parentesen (gate F ankrer med `$`).
   - **Ingen `#`-overskrift inne i seksjonen** — mellom overskriften og attestasjonslinjen skal det
     ikke finnes én eneste linje som starter med `#` etterfulgt av mellomrom. Gaten avslutter
     seksjonen ved første slike linje.
   - **Hvert** V-kriterium fra planens verifiseringsseksjon skal med — også de du ikke kunne kjøre
     (skriv da kommandoen og grunnen i kodeblokken). Skriv ID-en som `**V<id>**` på EGEN linje ved
     LINJESTART **og utenfor enhver kodeblokk**, umiddelbart etterfulgt av minst én fenced
     kodeblokk med kommando + ORDRETT output — ikke bare balanserte fence-par: en tom fenced blokk
     komponerer aldri et gulv, den blir talt som manglende bevis. Ingen V-kriterier i tabellceller.
     Samme ID gjentatt flere ganger teller som ÉN — hvert distinkt kriterium må navngis for seg.
     `**V<id>**`-linjer som står INNE i en kodeblokk (f.eks. i limt plantekst) telles ikke.
   - Alle fences skal være balanserte — partall antall ```-linjer i seksjonen, og partall i
     HELE planfila. Én løs ` ``` ` hvor som helst i fila gjør gaten rød.
   - **Avkortningsregel for «ordrett output» (bindende).** Kommandoer hvis resultat er et TALL, en
     exit-kode eller en filliste (`grep -c`, `wc -l`, `diff -rq`, `git diff --name-only`, `git
     status --porcelain`) limes inn ORDRETT I SIN HELHET. Bygg, typecheck, formatter, enhetstester
     og e2e limes inn som **kommandoen + de SISTE 10 linjene av output + `exit=<kode>`**; hele
     loggen ligger i scratchpaden og siteres på forespørsel. Avkorting er ikke et unntak fra
     kilde-kravet: kommandoen og exit-koden MÅ stå.
   - **Avslutt seksjonen med attestasjonslinjen ORDRETT, på egen linje, UTENFOR enhver kodeblokk:**
     `Ingen tall arves fra en tidligere runde.`
     Linjen teller ikke hvis den bare finnes inne i en limt kommando eller kodeblokk.
   - Skriv rundens lesson-kandidater i SAMME seksjon — ikke bare i rapporten; koordinatoren skriver
     dem videre til `tasks/lessons/`, det gjør du aldri.
7. `git push` til **samme branch** (samme PR — IKKE ny PR, IKKE ny `gh pr create`).
8. Returner oppdatert ferdig-rapport.

`verification.review_findings` i ferdig-rapporten er din **selvgransking** fra steg 5 over. `code_review.findings[]` er den **uavhengige §5b-reviewen** — de er to distinkte kilder; forveksle dem ikke.
