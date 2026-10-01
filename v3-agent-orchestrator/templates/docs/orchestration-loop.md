<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->
# Orkestreringsloopen — operatør-guide

Denne guiden forklarer **hvordan den autonome utviklingsloopen fungerer i praksis**, og — viktigst — **hvor du som menneske passer inn**. Den er for deg som kjører loopen, ikke for den som bygger den.

- **Design og begrunnelse:** [v3-agent-orchestrator/docs/PORTING.md](../v3-agent-orchestrator/docs/PORTING.md)
- **Koordinator-runbook (prosedyren loopen kjører):** `docs/superpowers/loop/coordinator-runbook.md` — kjerne-sjekkliste; prosedyren per steg i `docs/superpowers/loop/steps/`, begrunnelser i `docs/superpowers/loop/runbook-hvorfor.md`

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
Loopen implementerer og merger **én todo om gangen**, og **du bestemmer når den kjører**. Planleggingen av neste todo kan overlappe implementeringen av den nåværende (pipelining, `coordinator-runbook.md` §5c) — men det er aldri mer enn én todo under implementering. Du kan la loopen gå til køen er tom, eller stoppe når du vil.

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
| Sørge for at loop-forbedringer ikke sulter | Sett `priority: prioritert` på en `loop`-tagget todo. Koordinatoren rapporterer kø-sammensetningen (`N av M åpne todos er loop-taggede`) i §1 hver runde. |

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
- **Periodisk helsesjekk** (`/loop-health-check`): koordinatoren kjører tester, type-check, lint, web-smoke (A5b — minste web-lastings-/login-gate, tetter BUG-076-blindsonen) og tech-sweep (pluggbar; f.eks. RLS-sweep via rls-auditor hvis konfigurert) mot integrert `origin/{{BASE_BRANCH}}` — enten etter {{HEALTH_CHECK_INTERVAL}} merges eller når køen tømmes. Resultatet skrives som en `outcome=health`-rad i run-loggen. Rød helsesjekk er et pausepunkt (se under).
- **Release-rådgiver**: som del av helsesjekken sammenlignes `origin/{{BASE_BRANCH}}` mot `origin/{{PROD_BRANCH}}`, brukervendte endringer oppsummeres, og en go/no-go-anbefaling produseres. Selve releasen utføres aldri av loopen — kun av deg via `{{RELEASE_COMMAND}}`.

**NB (B1 — sesjonsstart-krav):** §5b kode-review er aktiv i koordinator-sesjoner startet ETTER at `.claude/agents/{{PROJECT_NAME}}-code-reviewer.md` ble merget til `{{BASE_BRANCH}}`. Sesjoner startet FØR merge vil ikke ha agenten i registeret — preflight-proben i `/run-loop` fanger dette og eskalerer til deg.

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
| **Teknisk risiko (nivå A)** — migrasjon, RLS-endring, prod-/{{PROD_BRANCH}}-push, secrets, native/EAS/iOS-Modal, Edge Function-deploy | Uopprettelig — krever din godkjenning. Unntak: `technical_risk` fra PLAN-rapporten klassifisert som **pausepunkt-regel B5** (docs-/hook-selvmodifisering med kjørbar testgate, TODO 246) — koordinatoren avgjør selv og logger i `decision-log.md`. `technical_risk` flagget av en REVIEWER er alltid nivå A. |
| **Brainstorm-påkrevd todo** | Krever designvalg bare du kan ta — hoppes over, rapporteres |
| **Reviewer-no-go som ikke løses** | Planen har blokkerende svakheter etter 1–2 revisjoner |
| **Kode-reviewer revise-gate etter 2/2 — pausepunkt-regel B1 (TODO 246)** | Koordinatoren velger selv (én ekstra fix-runde, merge m/carry-forwards, eller stopp) og logger valget i `decision-log.md`; eskalerer til deg (nivå A) kun hvis den ene ekstra runden også er brukt og gaten fortsatt ikke er tom (§5b) |
| **Agent-probe i preflight feiler («Agent type not found», dekker §5b)** | Start en fersk koordinator-sesjon (se sesjonsstart-noten (B1) over) |
| **Helsesjekk rød** | Regresjon eller infra-feil i integrert `{{BASE_BRANCH}}` — koordinatoren eskalerer med detaljer, du bestemmer neste steg |
| **Uventet feil / merge-konflikt** | Loopen gjetter ikke — den stopper og rapporterer |

**Plan-godkjenning er IKKE et pausepunkt.** Den uavhengige reviewer-agenten erstatter deg som plan-port, så du slipper å godkjenne hver enkelt plan. Du trekkes kun inn hvis reviewen ikke konvergerer.

## Nivå B (TODO 246) — koordinatoren bestemmer selv, du kan vetoe

Et mindretall av pausepunktene (merket **pausepunkt-regel B1–B7** i `coordinator-runbook.md` §
Pausepunkter — f.eks. B1 over) er nivå B: koordinatoren tar valget selv, logger det i
`docs/superpowers/loop/decision-log.md` (grunnlag, valg, forkastede alternativer, reversibel-til),
skriver `auto_decided=<todo>:<antall>` i run-loggen, og skriver én linje i sluttmeldingen sin. Du
kan **vetoe** et hvilket som helst nivå-B-valg ved å svare i chatten — koordinatoren ruller da
tilbake til punktet decision-log-entryen oppgir som «Reversibel til». Nivå A (tabellen over) er
uendret: loopen stopper og venter på et eksplisitt svar fra deg.

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
| `plan:` på en **u-claimet** todo (pipelinet plan) | Koordinator | ❌ ikke rør — men todoen er IKKE under arbeid: `priority`/`order`/`deferred` er fortsatt trygt |
| `lessons*`, `followups/`, `todo_archive.md`, `bugs.md` | Koordinator | ❌ ikke rør manuelt |
| `.claude/worktrees/agent-*` | Koordinator (rydder etter hver worker-dispatch; beholder ved abort for forensikk) | ❌ ikke rydd manuelt mens loopen kjører; ✅ trygt når den står stille (det er TODO 245s modus) |
| `.claude/agent-memory/<agent>/MEMORY.md` | Agenten selv, committes av implementeren i dens egen PR | ❌ ikke rediger manuelt |
| `tasks/graph.json` | Ingen — genereres on-demand, committes aldri | ❌ ikke opprett |
| `tasks/graph-build.py` | `/setup` (kit-generert) | ❌ rediger templaten (`v3-agent-orchestrator/templates/tasks/graph-build.py`) |
| `tasks/graph-query.py` | `/setup` (kit-generert) | ❌ rediger templaten (`v3-agent-orchestrator/templates/tasks/graph-query.py`) |
| `tasks/review-lens-select.py` | `/setup` (kit-generert) | ❌ rediger templaten (`v3-agent-orchestrator/templates/tasks/review-lens-select.py`) — kjøres av koordinatoren i §5b, aldri av kode-revieweren |
| `tasks/review-severity-floor.py` | `/setup` (kit-generert) | ❌ rediger templaten (`v3-agent-orchestrator/templates/tasks/review-severity-floor.py`) — håndhever `severity_floor` per agent, kjøres av koordinatoren i §5b, aldri av kode-revieweren |
| `tasks/decision-level.py` | `/setup` (kit-generert) | ❌ rediger templaten (`v3-agent-orchestrator/templates/tasks/decision-level.py`) — klassifiserer nivå A/B per hendelse (TODO 246), kjøres av koordinatoren OG implementeren, aldri av kode-revieweren |
| `tasks/review-fan-in-verify.py` | `/setup` (kit-generert) | ❌ rediger templaten (`v3-agent-orchestrator/templates/tasks/review-fan-in-verify.py`) — mekanisk `observe`-logg for `fan_in`-rapporten (TODO 250A), kjøres av koordinatoren i §5b, aldri av kode-revieweren |
| `docs/superpowers/loop/decision-log.md` | Koordinator (seed-only, samme vern som `run-log.md`) | ❌ ikke rør manuelt — koordinatoren appender nivå-B-entries; se `decision-log.md` § Format |
| `tasks/plans/todo-NN-*.md` | Koordinator til §5-dispatch; deretter branch-eid av implementeren (fix-runde-seksjoner) til merge | ❌ ikke rediger manuelt mens todoen er in-flight |

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

**Drain retro-logg (§8b):** koordinatoren drainer `docs/superpowers/loop/retro-log.md` ved BEGGE
§6c-helsesjekk-triggere (kun ved grønn helsesjekk), ikke bare ved grooming — før
grooming-forslagene skrives (kø-tom) OG rett etter helseraden ved hver N-te merge (ingen kø-tom
nødvendig). Uten den andre triggeren ville §8b i praksis sjelden fyre, siden kø-tom er en langt
sjeldnere hendelse enn merge-takten. Hver utriagert `Forbedringsforslag`-linje klassifiseres som
`adopted` (allerede innført), `promoted` (fremmet til todo-utkast), `obsolete` (utdatert) —
eller hoppes over uten rad ved «ingen» (ingen beslutning å logge) — og resultatet appendes som
en rad til `docs/superpowers/loop/retro-triage.md`. Formål: forslag som ble skrevet i
mini-retroen (under) skal ikke bare stå der ulest — §8b lukker sløyfen mellom observasjon og kø.

**Utestående-tak, ikke rundebudsjett:** §8b-promoteringer bindes til et **utestående-tak på 3**
— maks 3 §8b-promoterte todo-utkast kan ligge utriagert i køen samtidig, uansett hvor ofte §8b
kjører. Før §8b promoterer noe, teller koordinatoren hvor mange tidligere §8b-promoterte utkast
som fortsatt venter på din triage; er det allerede 3, promoteres ingen nye før du har triaget
noen av de eksisterende. Dette er bevisst forskjellig fra et per-invokasjons-budsjett (som ville
gitt friskt rom hver eneste Trigger 2-kjøring og latt køen vokse ubegrenset over tid) — kadensen
kan derfor være hyppig uten at køen fylles opp. Ved kø-tom-grooming (Trigger 1) teller det §8b
faktisk promoterer denne runden i tillegg mot §7s eget, separate rundebudsjett på inntil 3 nye
forslag totalt for runden. Overstiger antallet `promoted`-kandidater plassen som er igjen under
utestående-taket, promoteres kun de høyest rangerte (nyeste først) — overskuddet forblir
utriagert til neste §8b-runde, det slettes eller tvangsklassifiseres aldri.

**Mini-retro (§8):** rett etter grooming-forslagene skriver koordinatoren en 5-linjers
strukturert retro (Fungerte / Friksjon / Forbedringsforslag + kontekst-linje) til append-only
`docs/superpowers/loop/retro-log.md`. Formål: loop-evaluering blir en del av loopen selv, ikke
noe som skjer først når du spør. Samme lesekadanse som run-log — en rask skumlesing viser deg
hva koordinatoren selv opplevde som friksjon siste runde.

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
{{SCOUT_MODEL_ROW}}| Fix-runde 3+ (eskalering, TODO 252) | {{MODEL_CODE_REVIEWER}} (effort {{EFFORT_CODE_REVIEWER}}) | Sene fix-runder krever re-verifisering av planens V-blokk — samme resonneringskrav som kode-review |

---

## Forutsetninger — lokal vs. cloud/headless

Loopen har eksterne avhengigheter som ikke finnes i alle kjørekontekster. Preflight-sjekken i `/run-loop` rapporterer status ved oppstart og avgjør om loopen kjører i FULL eller DEGRADERT modus.

| Avhengighet | Gir | Lokal (standard) | Cloud/headless | Degradering hvis mangler |
|---|---|---|---|---|
| E2E-verktøyet (konfigurert probe — CLI eller MCP, se `run-loop.md` §1) | E2E-verifisering av brukerflyt i browser | Tilgjengelig via CLI/plugin/MCP-oppsett | Ikke tilgjengelig | E2E hoppes over; `verification.e2e_outcome: "e2e_unavailable"` i ferdig-rapport; `degradation`-kolonnen avledes av `e2e_outcome` + `web_smoke_outcome` sammen (se `run-log.md`) |
| Superpowers `/systematic-debugging` | Strukturert 6-stegs rotårsaks-feilsøking | Tilgjengelig | Ikke tilgjengelig | Inline 6-stegs fallback-protokoll trer i kraft i `todo-execute.md`; degraderingen loggføres i `notes`-feltet i ferdig-rapporten |
| Superpowers `/verification-before-completion` | Strukturert ferdig-sjekk | Tilgjengelig | Ikke tilgjengelig | Manuell verifisering per planens testkriterier. NB: brukes kun ved manuell `/todo-done`, ikke i loop-worker-stien — preflight-sjekker den kun for fullstendighetens skyld |
| Superpowers `/requesting-code-review` og `/simplify` | Post-impl review og DRY-analyse | Tilgjengelig | Ikke tilgjengelig | Utføres allerede inline i `todo-finish-worker.md` steg 3 og 5 — ingen ytterligere degradering |
| In-repo-agenter (`{{PROJECT_NAME}}-*`) | Planner, reviewer, implementer, code-reviewer | Tilgjengelig etter sesjon startet post-merge | Ikke tilgjengelig | **Kritisk** — loopen STOPPER; eskalerer til koordinator (agent-probene i `/run-loop`-preflighten — planner + code-reviewer) |

In-repo-agenter er den eneste avhengigheten der manglende tilgjengelighet STOPPER loopen. Alle andre avhengigheter degraderer kontrollert med sporbar historikk i run-log.

---

## Status og faser

| Fase | Hva | Status (per 2026-09-06) |
|---|---|---|
| **0** | Valider mønsteret i en live-sesjon på 1–2 ekte todos | **Validert** — i ordinær drift siden 2026-06-19, med 68 merget runder i opphavsprosjektets run-logg (`docs/superpowers/loop/run-log.md`) |
| **1** | Port til et Workflow-script (bakgrunnskjøring + resume) | **Ikke planlagt** — fase 1 er ingen forutsetning for fase 2, og pipelining (fase 2 trinn 1) ble prioritert foran |
| **2** | Parallelle workers (flere todos samtidig) | **Trinn 1 (pipelining) levert OG kjørt i drift** (to runder: 246→250, 250→195B) — `coordinator-runbook.md` §5c; en pipelinet runde kjennes igjen på `pipelined_from=` i run-loggen. **Trinn 2 (parallelle implementere) levert (TODO 233), ikke kjørt i drift ennå** — `coordinator-runbook.md` §5d + `tasks/parallel-disjoint.py`; armet via `parallel_implementers.max` i `loop.config.yaml`. Første parallelle runde kjennes igjen på `parallel_with=` i run-loggen (CF-233-6, forventet inert inntil køen blander loop- og app-arbeid, jf. § 1.3.2 i planen) |

Statuskolonnen er en **datert observasjon**, ikke en løpende sannhet. Skifter en fase tilstand, oppdateres cellen — og datoen i kolonneoverskriften — i templaten `v3-agent-orchestrator/templates/docs/orchestration-loop.md` etterfulgt av `/setup`, aldri i denne genererte fila (headeren øverst gjelder tokeniserte verdier i `loop.config.yaml`; narrativt innhold ligger i templaten).
