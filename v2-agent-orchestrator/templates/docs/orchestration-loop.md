<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->
# Orkestreringsloopen — operatør-guide

Denne guiden forklarer **hvordan den autonome utviklingsloopen fungerer i praksis**, og — viktigst — **hvor du som menneske passer inn**. Den er for deg som kjører loopen, ikke for den som bygger den.

- **Design og begrunnelse:** [docs/superpowers/specs/2026-06-18-orchestration-loop-design.md](superpowers/specs/2026-06-18-orchestration-loop-design.md)
- **Implementasjonsplan:** [docs/superpowers/plans/2026-06-18-orchestration-loop-phase-0.md](superpowers/plans/2026-06-18-orchestration-loop-phase-0.md)
- **Koordinator-runbook (når bygget):** `docs/superpowers/loop/coordinator-runbook.md`

---

## Hva loopen er

Et system som tar todos fra `tasks/todos/` og kjører dem gjennom planlegging → review → implementering → merge **uten at du må trigge hvert steg**. Du går fra å være den som setter i gang alt, til å være den som styrer retning og svarer på unntak.

**Kjernidé:** en **koordinator** dispatcher kortlevde **subagenter** («workers») som gjør det tunge arbeidet i isolerte kontekster og returnerer korte rapporter. Koordinatoren er **eneste skriver** til delt state (lessons, arkiv, bugs, status), så flere agenter aldri tråkker på hverandre.

---

## Hvordan en runde fungerer

```
DU starter loopen
   │
   ▼
KOORDINATOR  ── velger neste todo (prioritert → order, deps oppfylt, ikke claimet)
   │
   ├─→ PLANNER       ({{MODEL_PLANNER}})        skriver en plan for todoen
   ├─→ REVIEWER      ({{MODEL_REVIEWER}})       uavhengig djevelens advokat — godkjenner eller sender tilbake
   ├─→ IMPLEMENTER   ({{MODEL_IMPLEMENTER}})    koder, verifiserer, lager PR mot {{BASE_BRANCH}}
   ├─→ CODE REVIEWER ({{MODEL_CODE_REVIEWER}})  uavhengig review av PR-diffen — godkjenner eller sender tilbake
   │
   ▼
KOORDINATOR  ── skriver lessons, arkiverer todo, merger til {{BASE_BRANCH}}, går til neste
```

Hver worker kjører i sin egen worktree (isolert), så de kolliderer ikke. Du ser fremdriften rulle forbi, og blir kun stoppet ved ekte veiskiller (se under).

---

## Hvor du passer inn (human in the loop)

Du har tre roller. Ingen av dem krever at du sitter og venter.

### 1. Du starter og stopper loopen
Loopen kjører sekvensielt (én todo om gangen i første versjon) og **du bestemmer når den kjører**. Du kan la den gå til køen er tom, eller stoppe når du vil.

Start den med slash-commanden **`/run-loop`** i en fersk sesjon:
- `/run-loop` — kjør kontinuerlig til køen er tom eller et pausepunkt treffes
- `/run-loop once` — kjør nøyaktig én todo, så stopp (forsiktig oppstart / validering)
- `/run-loop 41` — start med en bestemt todo

Merk: må kjøres i en sesjon startet *etter* at `{{PROJECT_NAME}}-*`-agentene finnes (Claude Code laster agent-registeret ved sesjonsstart).

### 2. Du styrer køen (rattet)
Du trenger ikke røre koordinatoren for å endre hva som blir gjort. Rediger **ett felt i én fil** under `tasks/todos/`:

| Vil du… | Gjør dette |
|---|---|
| Prioritere en oppgave | Sett `priority: prioritert` på todo-fila |
| Finjustere rekkefølge | Endre `order` |
| Ta noe ut av køen midlertidig | Sett `status: deferred` |
| Legge til ny oppgave | Lag en ny `tasks/todos/todo-NN-slug.md` |
| Tvinge en rekkefølge | Sett `deps: ["NN"]` |

Koordinatoren leser dette på nytt ved hver runde, så endringene slår inn umiddelbart.

### 3. Du svarer på pausepunkter
Loopen stopper og spør deg kun ved ekte veiskiller (se neste seksjon). Ellers går den av seg selv.

---

## Kvalitetssikring (uten å lese hver plan)

Du har sluttet å godkjenne planer per todo — så kvaliteten sikres i tre lag, og dine øyne flyttes fra «hver plan» til «hver release»:

**Loopens egne lag (automatisk):**
- Uavhengig plan-reviewer (devil's advocate) før implementering
- Uavhengig kode-review på PR-diffen etter implementering, før merge (`{{PROJECT_NAME}}-code-reviewer`; adversariell, read-only, maks 2 revise-runder)
- Implementer-selvgransking + CI (build/type-check/lint/test) på hver PR
- **Periodisk helsesjekk** (`/loop-health-check`): koordinatoren kjører tester, type-check, lint og tech-sweep (pluggbar; f.eks. RLS-sweep via rls-auditor hvis konfigurert) mot integrert `origin/{{BASE_BRANCH}}` — enten etter {{HEALTH_CHECK_INTERVAL}} merges eller når køen tømmes. Resultatet skrives som en `outcome=health`-rad i run-loggen. Rød helsesjekk er et pausepunkt (se under).
- **Release-rådgiver**: som del av helsesjekken sammenlignes `origin/{{BASE_BRANCH}}` mot `origin/{{PROD_BRANCH}}`, brukervendte endringer oppsummeres, og en go/no-go-anbefaling produseres. Selve releasen utføres aldri av loopen — kun av deg via `{{RELEASE_COMMAND}}`.

**NB (B1 — sesjonsstart-krav):** §5b kode-review er aktiv i koordinator-sesjoner startet ETTER at `.claude/agents/{{PROJECT_NAME}}-code-reviewer.md` ble merget til `{{BASE_BRANCH}}`. Sesjoner startet FØR merge vil ikke ha agenten i registeret — §5b-proben fanger dette og eskalerer til deg.

**Dine lag (lavt arbeid, høy verdi):**
1. **Per release — hovedporten:** før hver prod-release, se gjennom den samlede diffen `git diff origin/{{PROD_BRANCH}}..origin/{{BASE_BRANCH}}` som én bolk. Du reviewer alle todos siden forrige release i kontekst, rett før de når brukere. Release-rådgiveren (del av `/loop-health-check`) gir deg lista og en go/no-go automatisk.
2. **Skumlesing:** `tasks/todo_archive.md` — les «komplikasjoner» og «avvik» per todo. Fordøyd; du ser raskt hvor noe gikk sidelengs.
3. **Stikkprøve:** les 1–2 merge-de PR-differ på todos du bryr deg om — ikke alle.
4. **Run-log:** `docs/superpowers/loop/run-log.md` er den raskeste verifiseringskilden — én linje per todo med tidsstempel, utfall, PR og modeller brukt. Koordinatoren appender den i §6.5 av runbooken (etter merge, før commit+push). Se der for format-spec.

Review-kadansen din går altså fra *per plan* til *per release* + stikkprøver. Mindre arbeid, treffer rett før det betyr noe.

---

## Når loopen stopper og venter på deg

| Pausepunkt | Hvorfor |
|---|---|
| **Teknisk risiko** — migrasjon, RLS-endring, prod-/{{PROD_BRANCH}}-push, secrets | Uopprettelig — krever din godkjenning |
| **Brainstorm-påkrevd todo** | Krever designvalg bare du kan ta — hoppes over, rapporteres |
| **Reviewer-no-go som ikke løses** | Planen har blokkerende svakheter etter 1–2 revisjoner |
| **Kode-reviewer revise-gate konvergerer ikke** | PR-diffen har BLOKKERENDE/VIKTIG funn etter 2 revise-runder (§5b) |
| **§5b-probe feiler («Agent type not found»)** | Start en fersk koordinator-sesjon (se B1-note over) |
| **Helsesjekk rød** | Regresjon eller infra-feil i integrert `{{BASE_BRANCH}}` — koordinatoren eskalerer med detaljer, du bestemmer neste steg |
| **Uventet feil / merge-konflikt** | Loopen gjetter ikke — den stopper og rapporterer |

**Plan-godkjenning er IKKE et pausepunkt.** Den uavhengige reviewer-agenten erstatter deg som plan-port, så du slipper å godkjenne hver enkelt plan. Du trekkes kun inn hvis reviewen ikke konvergerer.

---

## Eierskaps-skille (slik unngår du å kollidere med koordinatoren)

Loopen og du kan jobbe «samtidig» så lenge dere holder dere til hver deres filer:

| Fil / felt | Eier | Kan du redigere? |
|---|---|---|
| Ny `tasks/todos/todo-NN-*.md` | Deg | ✅ ny fil = null konflikt |
| Ny `tasks/bugs/inbox/bug-*.md` | Deg | ✅ ny fil = null konflikt |
| `priority` / `order` / `status: deferred` på **u-claimet** todo | Deg | ✅ trygt |
| `status: deferred↔open` + `tags`-endring på **u-claimet** todo (triage av grooming-forslag) | Deg | ✅ trygt — dette er triage-handlingen (se Grooming-seksjonen) |
| `claimed_by`, `status: in_progress/done` | Koordinator | ❌ ikke rør (= «in-flight»-signal) |
| `lessons*`, `todo_archive.md`, `bugs.md` | Koordinator | ❌ ikke rør manuelt |

Ser en todo `claimed_by: <koordinator>`, er den under arbeid akkurat nå — la den være.

---

## Rapportere en bug

`bugs.md` er koordinatorens — du skriver den aldri direkte. I stedet:

- **Logg en bug for senere:** lag `tasks/bugs/inbox/bug-<slug>.md`. Koordinatoren triagerer den inn i `bugs.md` (eller forfremmer til en todo) automatisk.
- **Bug du vil ha fikset nå:** lag en todo direkte med `priority: prioritert`.
- **Bruker-teamet (ikke-tekniske):** de rapporterer til deg → du slipper en innboks-fil. (GitHub Issues / in-app-knapp er framtidige alternativer.)

Innboks-fil-format:
```markdown
---
reporter: <navn>
date: <YYYY-MM-DD>
priority: høy | middels | lav
---
Hva skjer, hvordan reprodusere, hvilken side/flyt.
```

---

## Sparre om nye features

Gjør dette i en **egen sesjon** — ikke inne i koordinator-sesjonen (den skal holdes slank). Brainstorm en ny feature, og resultatet blir en **ny todo-fil** (og evt. en spec) som du merger til `{{BASE_BRANCH}}`. Koordinatoren plukker den opp neste runde. Dette er samme «foreslå → du disponerer»-mønster som loopens egen grooming-modus, bare initiert av deg.

---

## Når køen blir tom (grooming)

Loopen stopper ikke dødt — den går i **grooming-modus**: den foreslår nye todos/bugs som **utkast** (basert på backlog, arkiv, observasjoner), opptil et fast antall, og stopper så for din triage. Den **auto-implementerer aldri** selvgenerert arbeid — du beholder vetoet på *hva* som bygges.

Grooming-forslag fødes med `status: deferred` + `tags: [forslag]` — de er ikke-kvalifiserte for køen inntil du triagerer dem.

### Triage-rubrikk (gjelder hvert forslag)

Vurder hvert forslag mot disse fire spørsmålene:

1. **Er det reelt?** — løser det et faktisk problem du ser i kodebasen/brukeropplevelsen, eller er det spekulativt?
2. **Duplikat eller allerede feilet?** — finnes det i `tasks/todo_archive.md` som avvist, eller i `tasks/bugs.md`?
3. **Verdi vs. kost / treffer kjerneverdiene?** — er innsatsen proporsjonal med gevinsten? Peker det mot prosjektets kjerneverdier?
4. **Riktig klassifisert?** — bør det være en bug-rapport, en enkel kodeendring, eller en større spec?

### Triage-handling

- **Godkjenn forslaget:** flippe `status: deferred → open` OG fjerne `forslag`-taggen (`tags: []`) på todo-filen. Begge endringer er nødvendige — koordinatoren plukker det opp i neste runde.
- **Avvis forslaget:** la filen stå som `status: deferred` + `tags: [forslag]`, eventuelt slett den. Koordinatoren fanger ikke opp forkastede forslag.
- **Juster innholdet:** rediger title/body fritt — du eier todo-filen inntil den er claimet.

---

## Git og miljøer (trygghet)

- Loopen **brancher fra og merger kun til `{{BASE_BRANCH}}`**. `{{PROD_BRANCH}}` (= produksjon) berøres aldri uten at du eksplisitt gir en prod-release som egen oppgave. Merge-steget er hardkodet `--base {{BASE_BRANCH}}`.
- Alle migrasjoner og DB-arbeid går mot **dev** (`{{DEV_ENV_ID}}`), aldri prod (`{{PROD_ENV_ID}}`) automatisk.
- **Manuell kuratering + git:** enklest er å pause loopen mens du redigerer på `{{BASE_BRANCH}}`, og gjenoppta etterpå. Vil du jobbe samtidig: bruk en feature-branch → PR til `{{BASE_BRANCH}}`, som loopens neste synk plukker opp.

---

## Modeller

| Steg | Modell | Hvorfor |
|---|---|---|
| Planlegging | {{MODEL_PLANNER}} (effort {{EFFORT_PLANNER}}) | Dype designvalg, risikovurdering |
| Plan-review | {{MODEL_REVIEWER}} (effort {{EFFORT_REVIEWER}}) | Uavhengig kritikk trenger sterkest resonnering |
| Implementering | {{MODEL_IMPLEMENTER}} (effort {{EFFORT_IMPLEMENTER}}) | Følger en ferdig plan; raskere/billigere |
| Kode-review (§5b) | {{MODEL_CODE_REVIEWER}} (effort {{EFFORT_CODE_REVIEWER}}) | Adversariell diff-review trenger sterk resonnering |

---

## Forutsetninger — lokal vs. cloud/headless

Loopen har eksterne avhengigheter som ikke finnes i alle kjørekontekster. Preflight-sjekken i `/run-loop` rapporterer status ved oppstart og avgjør om loopen kjører i FULL eller DEGRADERT modus.

| Avhengighet | Gir | Lokal (standard) | Cloud/headless | Degradering hvis mangler |
|---|---|---|---|---|
| E2E-verktøyet (f.eks. Playwright MCP, `mcp__playwright__*`) | E2E-verifisering av brukerflyt i browser | Tilgjengelig via plugin/MCP-oppsett | Ikke tilgjengelig | E2E hoppes over; `verification.e2e_skipped: true` + `verification.playwright_available: false` i ferdig-rapport; `degradation: e2e_skipped` i run-log |
| Superpowers `/systematic-debugging` | Strukturert 6-stegs rotårsaks-feilsøking | Tilgjengelig | Ikke tilgjengelig | Inline 6-stegs fallback-protokoll trer i kraft i `todo-execute.md`; degraderingen loggføres i `notes`-feltet i ferdig-rapporten |
| Superpowers `/verification-before-completion` | Strukturert ferdig-sjekk | Tilgjengelig | Ikke tilgjengelig | Manuell verifisering per planens testkriterier. NB: brukes kun ved manuell `/todo-done`, ikke i loop-worker-stien — preflight-sjekker den kun for fullstendighetens skyld |
| Superpowers `/requesting-code-review` og `/simplify` | Post-impl review og DRY-analyse | Tilgjengelig | Ikke tilgjengelig | Utføres allerede inline i `todo-finish-worker.md` steg 3 og 5 — ingen ytterligere degradering |
| In-repo-agenter (`{{PROJECT_NAME}}-*`) | Planner, reviewer, implementer, code-reviewer | Tilgjengelig etter sesjon startet post-merge | Ikke tilgjengelig | **Kritisk** — loopen STOPPER; eskalerer til koordinator (eksisterende §5b-probe og agent-probe i `/run-loop`) |

In-repo-agenter er den eneste avhengigheten der manglende tilgjengelighet STOPPER loopen. Alle andre avhengigheter degraderer kontrollert med sporbar historikk i run-log.

---

## Status og faser

| Fase | Hva | Status |
|---|---|---|
| **0** | Valider mønsteret i en live-sesjon på 1–2 ekte todos | Infrastruktur bygget — klar for validering på ekte todos |
| **1** | Port til et Workflow-script (bakgrunnskjøring + resume) | Etter at fase 0 er validert |
| **2** | Parallelle workers (flere todos samtidig) | Senere, på din beslutning |

Detaljene for hver fase ligger i spec-en og planen lenket øverst.
