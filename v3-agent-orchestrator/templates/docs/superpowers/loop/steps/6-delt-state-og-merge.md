<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# 6. Skriv delt state (seriell, re-kjørbar) + merge (kun koordinator)

→ Kjerne: `coordinator-runbook.md` § 6 · Begrunnelser: `runbook-hvorfor.md` § 6

> **Selv-modifiserende PR-er.** Når en merget PR endret `.claude/commands/run-loop.md`,
> `docs/superpowers/loop/coordinator-runbook.md` eller
> `docs/superpowers/loop/report-schema.md`: re-les de endrede filene fra disk FØR neste §6-rad
> skrives og FØR neste worker dispatches. Koordinatorens kontekst er et snapshot fra
> sesjonsstart; å skrive telemetri med gammelt vokabular etter en vokabular-endring produserer
> en rad som ser gyldig ut, men er usann.

<!-- mekanisk-kandidat: template↔generert-identitet — scratch-regen + cmp per generert fil, substitusjons-bevisst (mangler) -->

**0. CI-gate — FØR steg 1, før noe delt state røres (TODO 216).** Kjør gaten som EGEN kommando og
kjed den aldri med merge-kallet: `guard-main-merge.sh` sjekker bare kommandoer som STARTER med
`gh`, så `python3 … && gh api … /merge` slipper forbi base-vakten.
   ```bash
   python3 tasks/ci-gate.py <pr-nummer>
   ```
   Kjør den i forgrunnen fra repo-roten med Bash-verktøyets `timeout: 600000`. Bruk aldri
   `run_in_background`, og aldri shell-`timeout`, som ikke finnes på macOS (lesson 2026-09-17).
   Gaten henter PR-ens head-SHA og venter (tak 540 s, under verktøyets 600 s) til alle
   workflow-kjøringer, check-runs og commit-statuser for NETTOPP den SHA-en er ferdige. Linje 1 er
   run-log-tokenet `ci=<klasse>`, linje 2 er `sha=<head-sha>`. Dommen gjelder bare den SHA-en, og
   steg 4 merger med `-f sha=`. Exit 0 kun ved `ci=green`. Et kall som blir drept før det har
   skrevet en `ci=`-linje, regnes som `ci=error`.
   - `ci=green` ⇒ steg 1. Ta med `sha=` til steg 4 og `ci=green` til raden i steg 5.
   - `ci=red` ⇒ ikke merge. Les feilen: `gh run view <run-id> --log-failed` (run-id står i
     gatens detaljlinjer; tom logg ⇒ les ANNOTATIONS i `gh run view <run-id>`, lesson
     2026-09-17). Er den røde linja en `status <context>` (ingen run-id), ⇒ PAUSEPUNKT.
     Peker feilen ellers på en fil i PR-ens egen diff (`gh pr diff <pr> --name-only`) ⇒
     tilbake til §5b fix-mode med CI-feilen som BLOKKERENDE funn; B1-reglene og rundetaket gjelder
     uendret. Ellers (samme sjekk rød på `{{BASE_BRANCH}}`, jobb som aldri startet, uklar årsak)
     ⇒ ⚠️ PAUSEPUNKT.
   - `ci=cancelled` ⇒ `gh run rerun <run-id>` én gang, deretter gaten på nytt. Fortsatt ikke
     `ci=green` ⇒ ⚠️ PAUSEPUNKT.
   - `ci=error` (gh-/API-feil, eller et kall som ble drept uten `ci=`-linje) ⇒ gaten én gang til;
     fortsatt ikke `ci=green` ⇒ ⚠️ PAUSEPUNKT.
   - `ci=pending` (taket nådd) eller `ci=missing` (ingen workflow-kjøring for SHA-en) ⇒
     ⚠️ PAUSEPUNKT.
   Ved pausepunkt: release claim og skriv raden med `outcome=paused`, `pause_event=ci-rød` og
   gatens `ci=`-linje i notat-feltet (`ci=error` hvis kallet ble drept). Steg 1–6 kjøres ikke.

<!-- mekanisk-kandidat: CI-gate før merge — PreToolUse-hook på merge-kallet som krever ci=green for samme sha (mangler; guard-main-merge.sh håndhever A4 og ble bevisst ikke endret i TODO 216) -->

Fra ferdig-rapporten, `status: "implemented"`:
1. **Lessons:** for hver `lessons[]`, skriv én fil `tasks/lessons/<topic>/<YYYY-MM-DD>-<slug>.md` etter skrive-protokollen i `tasks/lessons.md` og formatet i `docs/loop-rules.md` § «Lessons learned — én fil per lesson»: `sources` → frontmatter-`kilder`, `pattern`/`checklist` → **Problem:**/**Løsning:**/**Unngå:**. Ingen indeks å oppdatere. Dekker en eksisterende lesson samme mønster: utvid den i stedet. Carry-forwards (planens CF-seksjon, rapportens `notes`) går til `tasks/followups/`, én fil per oppfølging — de er ikke et lessons-tema.
2. **Bugs:** `bugs_new[]` → `tasks/bugs.md`; `bugs_closed[]` → `tasks/bugs_archive.md` (opprett fila hvis den ikke finnes).
3. **Arkiver todo:** flytt til `tasks/todo_archive.md` (format: se eksisterende oppføringer). Slett `tasks/todos/todo-<nr>-<slug>.md`. Flytt planfil → `tasks/plans/archive/`.
4. **Merge:** verifiser base FØR merge — `gh pr view <pr> --json baseRefName -q .baseRefName` → MÅ være `{{BASE_BRANCH}}`, ALDRI `{{PROD_BRANCH}}`.

   **Todo-nr-kollisjonssjekk FØR merge (TO gater — hver ser en tilstand den andre strukturelt
   ikke ser):**
   - **(a)** `sh scripts/check-todo-nr-collisions.sh` i `{{BASE_BRANCH}}`-arbeidstreet. Dekker
     koordinatorens EGNE ucommitterte §6.3/§6b/§7-endringer (arkivering, bug-triage,
     nummer-reservasjon) — den eneste tilstanden (b) aldri ser, fordi (b) kun leser committede refs.
   - **(b)** `sh scripts/check-todo-nr-premerge.sh "$(gh pr view <pr> --json headRefName -q .headRefName)"`.
     Bygger `git merge-tree`-resultatet av fersk `origin/{{BASE_BRANCH}}` og PR-branchen og kjører
     (a)-scriptet mot DET — PR-ens **innkommende** nr mot fersk base.
     Exit: `0` ingen kollisjon — **men står det en WARN om fetch-svikt på stderr, er basen
     muligens foreldet og 0 er IKKE grønt** · `1` kollisjon → ⚠️ STOPP, IKKE merge, følg
     renummereringen i **§9**, re-kjør (b) · `2` intern feil (ukjent ref, ubeslektede historier,
     `tasks/` mangler) → ⚠️ STOPP, les ALDRI som grønt · `3` merge-konflikt → samme pause som en
     vanlig merge-konflikt; en konfliktsti under `tasks/todos/` med samme nr+slug og ulikt
     innhold ER en nr-kollisjon (§9).

   Kjør (b) som **siste handling før merge-kallet** — den leser `origin/{{BASE_BRANCH}}` på
   kjøretidspunktet og krymper TOCTOU-vinduet, men lukker det ikke. Avanserer
   `{{BASE_BRANCH}}` i mellomtiden, kjør (b) på nytt. CI-jobben `todo-nr-guard`
   (`scaffolding/github-workflows/ci.yml`) er backstop for NESTE PR, ikke for et race mot en
   base som flyttet seg etter siste grønne CI-kjøring.

   Deretter merge via REST som default (bruker core-kvoten i stedet for GraphQL — lesson 2026-07-13):
   ```bash
   gh api --method PUT "repos/{owner}/{repo}/pulls/<pr-nummer>/merge" -f merge_method=merge -f sha=<sha fra steg 0>
   ```
   `sha=` er SHA-en gaten i steg 0 godkjente. HTTP 409 betyr at head har flyttet seg siden gaten ⇒
   kjør steg 0 på nytt og følg den nye dommen.

   Verifiser `merged: true` i responsen, og sett deretter `stadium: merged` på DENNE invokasjonens
   rad i in-flight-tabellen FØR §0b-kallene under (kode-review-funn, fix-runde 2, MINDRE 4) —
   allowlisten i «In-flight-tabell» (§5d) gater §0b nettopp på denne verdien, og ingen tidligere
   linje sa NÅR den skulle skrives. Endepunktet tar PR-**nummer** (ikke URL), og nummeret må stå som et **literalt tall** i kallet — en shell-variabel blokkeres av `guard-main-merge.sh` (TODO 172 D). Faktumet at base settes ved PR-oppretting og ikke ved selve merge-operasjonen gjelder uansett merge-form. Fallback ved REST-problemer: `gh pr merge <pr> --merge --match-head-commit <sha fra steg 0>` (bruker GraphQL-kvoten, som kan tømmes ved høyt volum — lesson 2026-07-13).

   `guard-main-merge.sh` er registrert i `PreToolUse` i `.claude/settings.json` (TODO 173) og
   kjører i alle sesjoner og alle worktrees — verifisert 2026-08-31 ved at en throwaway
   worktree-sub-agent ble blokkert på `gh pr merge`. Hooks lastes ved **sesjonsstart** fra
   **hovedsjekkuten** (`$CLAUDE_PROJECT_DIR` resolver dit også for worktree-agenter), så en
   endring i skriptet eller i `settings.json` får effekt først i en fersk sesjon etter at
   hovedsjekkuten er oppdatert — ikke i den sesjonen som gjorde endringen. Hooks kan i tillegg
   komme fra den gitignorerte `.claude/settings.local.json`; sjekk begge hvis atferden avviker.
   **Begrensning:** vakten inspiserer kun kommandoens FØRSTE linje — flerlinjede eller prefiksede
   kommandoer (`git add -A` ⏎ `git push origin main`, `cd x && git push origin main`) omgår den.
   Lukkes i TODO 188. Base-sjekken over er derfor fortsatt den vakten som aldri kan hoppes over.

   **GraphQL-kvote-fellen:** hvis vakten blokkerer med «kunne ikke bekrefte base (fail-safe)» midt
   i et løp, er årsaken sannsynligvis tom GraphQL-kvote, ikke en farlig merge — `gh pr view` bruker
   GraphQL, og lesson 2026-07-13 er nettopp at den kvoten tømmes under tunge løp. Verifiser base
   med core-REST (`gh api repos/{owner}/{repo}/pulls/<pr-nummer> --jq .base.ref`) og kjør
   merge-kommandoen manuelt i terminal.

   Merge-konflikt → ⚠️ STOPP, release claim, rapporter.

   **Worktree-rydding etter merge (§0b, erstatter det gamle inline-oppslaget):** ett §0b-kall per
   **deduplisert** akkumulert implementer-PAR fra §5 (sti + rundens pre-snapshot-fil), med
   `evidence.toplevel` som nøkkel og ferdig-rapportens `branch`-felt som ren `<branch_kryss_sjekk>`.
   (i) **Dedupliser sti-lista før iterasjon** — dedup på STIEN; behold den FØRSTE rundens
   snapshot-fil for stien (det er den som er «før» for nettopp den worktreen).
   (ii) **«Branchen finnes ikke» er IKKE ADVARSEL** og telles ikke i «bærer commits»-bøtta — kun
   `-d`-nekt på en EKSISTERENDE branch teller der (§0b punkt 8).
   (iii) **K3** (den forlatte basis-branchen, oppstått når workeren byttet branch selv) dekkes av
   den **sti-utledede** slettingen i §0b punkt 7(b) — IKKE av noe sveip.
   **Ingen glob-sveip legges inn her** — historiske foreldreløse branches (fra FØR denne PR-en)
   eies av mennesket via TODO 245, aldri av loopen selv.
   **Ved en §5d-armert (parallell) runde er A og B TO adskilte §6-invokasjoner** (§5d,
   «Sekvensen»): denne worktree-ryddingen kjører per invokasjon på DEN invokasjonens egen
   akkumulerte liste alene — §6(A) sender aldri B sin rad til §0b og omvendt (§5d, «In-flight-
   tabell», tilstandsvakten på `stadium`).

   **Serialisert merge + `{{BASE_BRANCH}}`-CI-differensial (KUN ved §5d-armert runde).** Rekkefølgen er
   claim-rekkefølge: A merges så snart A er klar (steg 0–6 over), UAVHENGIG av hvor B står. Deretter:
   1. **`{{BASE_BRANCH}}`-CI-differensial #1** — mål CI-konklusjonen på `{{BASE_BRANCH}}`-tippen FØR A ble claimet (baseline,
      notert av koordinatoren ved claim-tidspunktet), og CI-konklusjonen på `{{BASE_BRANCH}}`-tippen ETTER A sin
      merge-commit:
      ```bash
      gh run list --branch {{BASE_BRANCH}} --limit 5 --json conclusion,status,headSha,workflowName,createdAt
      ```
      Velg kjøringen for den EKSAKTE merge-commit-SHA-en. `cancelled`/`null`/`in_progress` ⇒
      ikke-konklusiv ⇒ poll (maks 10 min), ALDRI rød og ALDRI grønn. rød → rød = ingen regresjon fra
      A ⇒ videre, med preeksisterende rødhet notert. grønn → rød = regresjon fra A ⇒
      ⚠️ PAUSEPUNKT (B merges ikke). Ikke-konklusiv etter 10 min ⇒ videre, med «CI ikke konklusiv»
      notert i §6-meldingen — IKKE pausepunkt (treg CI skal ikke stoppe loopen). **Ingen overlapp
      med CI-gaten i steg 0** (den gjelder PR-**head** FØR merge; dette gjelder
      `{{BASE_BRANCH}}`-branchen ETTER hver merge — ulike SHA-er, ulikt formål).
   2. **B `go` ⇒ gate M, bindende** (§5d) — deretter **MERGEABLE-sjekk for B** mot ny `{{BASE_BRANCH}}`:
      ```bash
      gh pr view <B-pr> --json mergeable,mergeStateStatus -q '.mergeable + " " + .mergeStateStatus'
      ```
      `MERGEABLE` ⇒ fortsett. `UNKNOWN` ⇒ poll (maks 2 min), ikke rød. `CONFLICTING` ⇒
      ⚠️ PAUSEPUNKT — filene var per gate M disjunkte (målt med `gh pr diff` på BEGGE sider, ingen
      deklarerte lister), så en konflikt her betyr at én av gatene selv er defekt, ikke at runden er
      det; en fix-runde ville skjult defekten.
   3. **§6 for B** i sin helhet (steg 0–6, egen `$TS`; B får sin egen gate-kjøring og sin egen `sha=` — A-mergen flytter ikke B-head, men endrer basen), med `parallel_with=<A>` skrevet på B sin rad
      (og `pipelined_from=<A>` i tillegg hvis B også var pipelinet via §5c) — se notat-feltet under.
      A sin rad får `parallel_with=<B>`.
   4. **`{{BASE_BRANCH}}`-CI-differensial #2** — samme prosedyre som #1, men med #1 sitt utfall som BASELINE
      (kjedet, ikke uavhengig): rød → rød ⇒ ingen regresjon fra B. grønn → rød ⇒ regresjon som
      først oppsto når BEGGE var i `{{BASE_BRANCH}}` ⇒ ⚠️ PAUSEPUNKT, med begge SHA-er i eskaleringen. Dette er
      den ENESTE sjekken som fanger «fil-disjunkt ≠ atferds-disjunkt» i den retningen som faktisk
      betyr noe — risikoen manifesterer seg per definisjon først når begge PR-ene er i `{{BASE_BRANCH}}`.
4b. **Worktree-sweep — kjøres HER, FØR raden under skrives (fix-runde 1, B1).** Kjør
   `./tasks/worktree-sweep.sh` nå og fang dens oppsummeringslinje i `$WTSWEEP`
   (`wtsweep=<fjernet>/<beholdt> ...`). **Ikke etter §6b, og ikke i §6c/§6d sin egen
   dokumentposisjon** — en rad som allerede er skrevet i steg 5 kan ikke få `wtsweep=`
   ettermontert. `--gate` (§6c, Del A) er token-basert, IKKE tidsstempel-basert (fix-runde 2,
   B1): den leser INNHOLDET i denne syklusens §6-rad og krever at `wtsweep=<n>/<n>` faktisk
   står der — et tidsstempel-sammenligning ble forkastet fordi steg 5 kan skrive raden i et
   senere minutt enn sweepens egen kjøretid selv når rekkefølgen (steg 4b FØR steg 5) er
   riktig, noe som ga falskt RØDT på en sweep som faktisk kjørte. Se §6d for hvorfor denne
   oppsamleren finnes ved siden av §0b — den fulle forklaringen står der, ikke duplisert her.
   Feiler kallet (script mangler, `exit 2`-flagg-feil): sett `$WTSWEEP` til en tydelig
   feilverdi (`wtsweep=feilet:<årsak>`) i stedet for å utelate tokenet — et manglende token er
   umulig å skille fra «glemte å skrive det», og gaten gir RØDT på begge (fravær ELLER
   feil-formet verdi).

   **Deretter: navngitt kjøring for denne todoens egne trær (TODO 401).** Kallet over rydder
   normalt ikke denne todoens egne trær: de er rørt siste døgn, og aldersvakten (`AGE_MIN`,
   §6d punkt 4) beholder dem. Kjør derfor også `./tasks/worktree-sweep.sh agent-<id> agent-<id> …`
   med ett `agent-<id>` per worktree-isolert dispatch denne todoen har hatt: planner,
   plan-reviewer, implementer og kode-reviewer, alle runder og forkastede re-dispatcher.
   **Navngi bare dispatcher der koordinatoren har mottatt resultatet (sluttrapport eller feil).**
   `<id>` er agent-ID-en fra dispatch-resultatet; treet er `.claude/worktrees/agent-<id>`, som
   også er `basename` av rapportens `evidence.toplevel`. Oppgi navnet, ikke stien: alt annet enn
   `agent-…` avvises med `exit 2`. Scout og lenser har ingen egen worktree og navngis ikke.
   **Aldri** en agent fra et pipelinet (§5c) eller parallelt (§5d) B-spor: den kan fortsatt leve,
   og låsen er ikke noe vern — en agent vekket med `SendMessage` er målt uten lås (2026-09-25).
   **Et agent-ID som har vært navngitt i en navngitt kjøring, er dødt: det skal aldri vekkes med
   `SendMessage` igjen, dispatch en fersk agent.** Skriptet vurderer KUN de navngitte trærne og
   hopper over aldersvakten for dem; alle andre vakter og redningen gjelder uendret. Et navn uten
   tre gir `IKKE FUNNET <navn>` (typisk allerede ryddet av §0b i steg 4) — det er ingen feil.
   Oppsummeringslinja er `wtsweep_named=<fjernet>/<beholdt> …`. Skriv begge tokenene inn i
   notat-feltet i steg 5, skilt med `; ` og ALDRI med komma:
   `…; wtsweep=<n>/<n>; wtsweep_named=<n>/<n>`. Gaten leser tokenet fram til mellomrom eller `;`,
   så `wtsweep=3/1,wtsweep_named=2/0` blir ett feilformet token ⇒ RØD. Feiler kallet, eller er
   ID-ene tapt (f.eks. etter kontekst-komprimering): skriv `wtsweep_named=feilet:<årsak>`; trærne
   tas da av døgnsweepen når `AGE_MIN` er passert. `--gate` leser KUN `wtsweep=`, og
   `wtsweep_named=` inneholder ikke den understrengen: den navngitte kjøringen kan verken gjøre
   gaten grønn eller rød.

   **Overgang (TODO 401):** 401s egen §6-rad SKAL bære både `wtsweep=` og `wtsweep_named=`.

   **Overgang: 380s egen §6-rad SKAL bære `wtsweep=` — kjør steg 4b allerede for 380-mergen**
   (fix-runde 3, mikro).

<!-- mekanisk-kandidat: wtsweep= i §6-raden (finnes: tasks/worktree-sweep.sh --gate, §6c Del A) -->

5. **Run-log merged-rad (dedup-guardet), FØR git-halen:**
   ```bash
   # $TS holdes KONSTANT ved en re-kjøring av samme §6-invokasjon (se «Re-kjørbarhet» under).
   ROW="$TS | $TODO_NR | $SLUG | merged | $PAUSE | $PR | $PRR | $CRR | $MODELS | - | $DEGR"
   grep -qF "$TS | $TODO_NR |" docs/superpowers/loop/run-log.md \
     || printf '%s\n' "$ROW" >> docs/superpowers/loop/run-log.md
   ```
   Rett etter raden: `python3 tasks/loop-cadence.py`. Exit 1 ⇒ §6c (Trigger 2) kjøres etter
   git-halen, før neste dispatch.
   Telemetri: (a) ferdig-rapportens `todo_nr`, `slug`, `pr_url`; (b) egne kontekst-tellere
   (§4-revisjonsrunder → `$PRR`, §5b-kode-review-runder → `$CRR`; fast-path (§2b): `skipped`
   for hoppede stadier, `$PRR=0`); (c) Modeller-tabellen i `docs/orchestration-loop.md` →
   `$MODELS`; (d) `verification.e2e_outcome` + `verification.web_smoke_outcome` fra
   ferdig-rapporten → `$DEGR`, etter formelen i `run-log.md`:
   ```
   outcome=health                                       ⟹ degradation = "-"   (carve-out)
   outcome=paused UTEN ferdig-rapport                   ⟹ degradation = "-"   (carve-out)
   e2e_outcome == e2e_green OG web_smoke_outcome == e2e_green
                                                        ⟹ degradation = "-"
   ellers                                                  "e2e=<e2e_outcome>;web_smoke=<web_smoke_outcome>"
   ```
   Manglende `*_outcome`-felt i en ferdig-rapport (rader som HAR en rapport) ⟹
   `e2e_blocked:missing_outcome_field` for det manglende feltet — aldri stille `-`.
   `e2e_not_applicable` er IKKE en degradering, men logges eksplisitt (redundant nøkkel=verdi,
   ikke en slurvefeil — gjør kolonnen eksakt greppbar). Denne formelen skal være ordrett den
   samme i `run-log.md`, denne fila og deres genererte tvillinger — avvik er en ny
   silent-node-failure-kilde. `printf` (ikke heredoc-&&-kjede) unngår
   del-eksekverings-fellen. Dedup-nøkkelen er `timestamp | todo_nr` — **to rader for samme
   todo i samme minutt støttes IKKE av denne nøkkelen**; bruk et distinkt `$TS` per rad
   (129-presedensen, run-log 2026-07-11T18:52 ×2, er et historisk unntak FRA FØR denne
   guarden fantes — ikke en gjentakbar mal). Workers rører ALDRI run-log.md.

   **NB — notat-feltet (`selector=`/`floor=`/`viol=`/`floor_exempt=`/`pipelined_from=`/`parallel_with=`/
   `auto_decided=`/`attest=`/`vblock=`/`scout=`/`wtsweep=`/`ci=`) er IKKE med i `$ROW`-malen over.** De fleste
   appenderes som SISTE felt etter at raden er skrevet (§5b, §5c, §5d, § Pausepunkter) — feltets eget
   NUMMER er omstridt mellom spec-tabellen og de faktiske radene (eies av TODO 210, CF-246-1/CF-246-2,
   ikke løst av denne PR-en). `wtsweep=` er UNNTAKET: verdien er allerede kjent FØR raden skrives
   (§6 steg 4b over), så den skrives inn i notat-feltet SAMTIDIG med resten av raden i steg 5, ikke
   appendert etterpå — se steg 4b for hvorfor rekkefølgen er bindende (B1). `ci=` (TODO 216) er samme
   slags unntak: verdien er linje 1 fra steg 0, ordrett, og skrives sammen med raden. Fravær av `ci=`
   på en `merged`-rad skrevet etter TODO 216 er et kontraktbrudd, fordi raden da ikke kan skilles fra
   en merge uten gate. `auto_decided=` er
   OBLIGATORISK på ALLE ikke-`health`-rader (også når verdien er `:0`)
   og FORBUDT på `outcome=health`-rader. `attest=` (TODO 250A) skrives i samme felt, KUN på rader
   som har hatt en §5b-kode-review, ALDRI på `outcome=health`-rader — og til forskjell fra
   `auto_decided=` er fravær IKKE et kontraktbrudd (`observe`, se §5b). `parallel_with=<annen-todo>`
   (TODO 233, §5d) skrives på BEGGE rader i en §5d-armert runde — A får `parallel_with=<B>`, B får
   `parallel_with=<A>` (og bærer `pipelined_from=<A>` I TILLEGG hvis B også var pipelinet via §5c;
   de to nøklene er ikke gjensidig utelukkende). Fravær av `parallel_with=` betyr «ikke parallell»
   og er ALDRI et kontraktbrudd — samme prinsipp som `pipelined_from=`.

   **`scout=<dispatches>d/<KB>kb` (lokaliserings-workeren).** Skrives i samme felt, på ALLE
   ikke-`health`-rader så lenge `scout.enabled` er `true` i `loop.config.yaml`. Summer
   `scout_usage` fra ALLE rapportene som gjaldt denne raden — plan-rapporten, ferdig-rapporten og
   hver fix-rundes ferdig-rapport — og regn `<KB>` som `bytes_read / 1024` avrundet til nærmeste
   heltall. Ingen scout brukt: `scout=0` (kortformen). Til forskjell fra `attest=`/`parallel_with=`
   er FRAVÆR HER ET KONTRAKTBRUDD: en manglende `scout=` kan ikke skilles fra en runde uten
   scout-bruk, og da måler serien ingenting — som er hele grunnen til at tokenet finnes. Mangler
   `scout_usage` i en rapport (og scout er på), be workeren om feltet i stedet for å gjette;
   fabrikkert telemetri er verre enn ingen. Kunne workeren ikke spørres i det hele tatt (sesjonen
   avsluttet uten rapport, eller rapporten har `status: "blocked"`/`"failed"` og likevel mangler
   `scout_usage`): skriv `scout=unknown` — ALDRI `scout=0`, som betyr «spurt, ingen brukt» og ville
   kollapset «ikke brukt» og «ikke kjent» til samme verdi (`report-schema.md` § frittekst-notatfelt).
   Er `scout.enabled` `false`, utelates tokenet helt.

   **Hva `scout=`-serien kan og ikke kan svare på.** `<KB>` er filinnhold scouten leste i stedet
   for en dyrere rolle — en ØVRE GRENSE for spart kontekst, ikke en besparelse (`report-schema.md`
   § Scout-rapport). Les den derfor som en TREND over mange runder, holdt opp mot rundenes øvrige
   form (`plan_review_rounds`, antall fix-runder, `vblock=`): stiger fix-rundene i takt med at
   `scout=` stiger, koster delegeringen kvalitet i stedet for å spare kontekst. Ett enkelt høyt
   tall betyr ingenting.
6. **Delt-state-git-hale (gjenbrukbar — samme blokk brukes av §6c/§7/§8/§8b, se der):**
   ```bash
   # 1. Speil-guard: HEAD er dev ELLER et rent speil (tip == origin/{{BASE_BRANCH}}, fordi
   #    {{BASE_BRANCH}} er utsjekket i et annet worktree) — ingen ikke-delt-state-commits.
   #    merge-base-formen er timing-robust uavhengig av fetch-rekkefølge: is-ancestor mot
   #    origin/{{BASE_BRANCH}} ville vært skjør avhengig av om origin/{{BASE_BRANCH}} er
   #    fetchet post-merge (etter at PR-en er merget ligger origin/{{BASE_BRANCH}} foran
   #    speilets HEAD, så is-ancestor ville feile på et ellers legitimt speil FØR neste
   #    fetch — den holder kun post-fetch). merge-base-formen passerer BEGGE (ekte
   #    {{BASE_BRANCH}} og rent speil, tom diff mot felles ancestor) og avviser en drevet
   #    feature-branch (kode-commits i diffen) — uansett fetch-rekkefølge.
   mb=$(git merge-base origin/{{BASE_BRANCH}} HEAD)
   non_shared=$(git diff "$mb"..HEAD --name-only | grep -vE '^(tasks/|docs/superpowers/loop/)' || true)
   [ -z "$non_shared" ] || { echo "FEIL: HEAD har commits utenfor delt state ($non_shared) — feil branch"; exit 1; }

   # 2. Stage KUN delt state — ingen glemt sti (fikser tidligere 'git add docs/'-glippen)
   git add -A tasks/ docs/superpowers/loop/

   # 2b. Delt-checkout-vern: indeksen deles med andre sesjoner i hovedsjekkouten — et `git add`
   #     derfra blir ellers med i denne commiten. `.githooks/pre-commit` er kun backstop.
   leaked=$(git diff --cached --name-only | grep -vE '^(tasks/|docs/superpowers/loop/)' || true)
   [ -z "$leaked" ] || { echo "FEIL: stagede filer utenfor delt state: $leaked — av-stage med 'git restore --staged <fil>'"; exit 1; }

   # 3. Commit — tolerer «ingenting å committe» (idempotens ved re-kjøring)
   git diff --cached --quiet && echo "ingenting å committe" || git commit -m "$MSG"

   # 4. Synk + push: fetch henter mergede PR-er, rebase replayer delta, push via HEAD-refspec
   git fetch origin {{BASE_BRANCH}} \
     && git rebase origin/{{BASE_BRANCH}} \
     && git push origin HEAD:{{BASE_BRANCH}}
   ```
   `$MSG` for §6 = `"chore(loop): TODO $TODO_NR delt-state — $SLUG"` (fast-path: append
   `(fast-path; presedens: TODO XXX / lesson YYYY-MM-DD)` per §2b-audit-kravet).

   **`$MSG`-suffiks ved ADVARSEL fra §0b (VIKT-6 fra r2, r5-formen):** er rundens ADVARSEL-teller
   `> 0`, append `(wtwarn=<n>: <role>@<basename> — <reason>; …)` til `$MSG` (maks tre oppføringer,
   deretter `…`). `<role>` ∈ `planner` | `plan-reviewer` | `code-reviewer` | `implementer`.
   `<basename>` er worktree-katalogens navn (`agent-<hex>`) — **aldri den absolutte stien**.
   `<reason>` er ett ord fra enumet `dirty` | `locked` | `artifact-missing` | `cmd-error` |
   `branch-not-deleted` | `preexisting` | `snapshot-missing` | `unknown-path` |
   `handoff-mismatch` | `branch-mismatch`. ADVARSLER som oppstod
   på et pipelinet B-spor føres i A sin melding, med `<B-nr>:` foran rolle-leddet. Samme presedens
   som fast-path-parentesen over. Kanalen bærer ÅRSAK og dekker **kun mergede runder** — abort-
   runder når aldri §6 og dekkes av pause-rapporten (§5, «Bevaringsregel ved abort»). Den
   maskinlesbare TELLEREN `wtwarn=<antall>` i `run-log.md` eies av TODO 194B — denne suffiksen er
   ikke det.

   **Re-kjørbarhet, ikke atomisk:** commit→fetch→rebase→push er IKKE én atomisk operasjon —
   seksjonen er derfor «seriell, re-kjørbar», ikke «atomisk». Recovery:
   **(a)** commit OK men push avvist → re-kjør HELE git-halen (steg 1–4 over); speil-guarden
   passerer fortsatt (ingen nye ikke-delt-state-commits), og steg 3 blir automatisk
   «ingenting å committe» (allerede committet). Ved denne recoveryen re-kjøres **KUN
   git-halen — ALDRI rad-/retro-appendene** (run-log-rad i steg 5, §8-retro-entry): de står
   allerede i working tree/er allerede committet, og re-kjøring av selve append-kommandoen
   ville trigget dedup-guardens «allerede der»-gren uansett, så det er unødvendig arbeid.
   (Dette er også grunnen til at §6c sin health-rad IKKE trenger egen dedup-guard — den
   berøres aldri av denne recoveryen.)
   **(b)** rebase-konflikt → ⚠️ PAUSEPUNKT: release claim, eskalér til mennesket.

<!-- mekanisk-kandidat: speil-guard + stage KUN delt state — wrap git-halen i ett skript (mangler) -->
