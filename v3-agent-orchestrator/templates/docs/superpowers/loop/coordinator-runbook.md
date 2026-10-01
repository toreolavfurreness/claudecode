<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# Koordinator-runbook (fase 0, live-sesjon)

Du er koordinatoren. Du er eneste skriver til delt state. Workers gjør tungt arbeid i isolerte worktrees og returnerer rapporter (`report-schema.md`).

> ⚠️ **Forutsetning:** koordinatoren MÅ kjøre i en sesjon som ble startet ETTER at `.claude/agents/{{PROJECT_NAME}}-*.md` finnes på disk. Claude Code snapshotter agent-registeret ved sesjonsstart — nyopprettede custom agenter er ikke tilgjengelige i en allerede kjørende sesjon. Verifiser med to trivielle probe-dispatcher (`subagent_type: {{PROJECT_NAME}}-planner`, prompt: «Svar kun: {"ok": true}. Ikke les filer.» — ordrett identisk med preflight-proben i `run-loop.md`, som utløser planner-charterets probe-modus-unntak; og `subagent_type: {{PROJECT_NAME}}-code-reviewer`, prompt: «Svar kun: {"ok": true}. Ikke synk, ikke les filer.» — dekker §5b sitt register-oppslag for hele sesjonen, se §5b) før du starter en runde; «Agent type not found» betyr at du må starte en fersk sesjon. **Sesjonsstart-epoch (TODO 250B):** rett etter probe-dispatchene kjører du `date -u +%s` ÉN gang og noterer tallet som sesjonens `T_start`; umiddelbart etter kjører du i tillegg de tre kommandoene i «Kontrakt-vakt (TODO 250B)»s session-predikat (ledd (a)–(c)) og noterer resultatet HER — ikke først når §5b nås. `T_start` er ledd (b) i predikatet og re-måles ALDRI senere i sesjonen. Finnes ingen registrert `T_start`, er predikatet USANT og form A kjøres.

## Slik leser du denne fila (kjerne, stegfiler, hvorfor)

Denne fila er kjernen: hvert steg står som sjekkliste med én peker til stegfilen under
`docs/superpowers/loop/steps/`. Stegfilen er den bindende prosedyren for steget — les hele stegfilen FØR
steget kjøres, hver gang, også etter kontekst-komprimering; sjekklisten her er ikke et sammendrag du kan
kjøre steget fra. Begrunnelser og målinger står i `runbook-hvorfor.md`; en regel gjelder uten at
begrunnelsen er lest. Stegfilene er utsnitt av én runbook: relative henvisninger («over», «under», «denne
fila», «øverst») gjelder runbooken som helhet — §-nummeret eller seksjonsnavnet i samme setning er den
bindende referansen. Ved motstrid mellom sjekklisten her og stegfilen vinner stegfilen; rett kjernen.
<!-- mekanisk-kandidat: hook som krever at steps/<id>-*.md er lest (Read) i sesjonen før en Agent-dispatch for rollen steget eier (mangler) -->


## Bevis-regel (global, jf. `report-schema.md`)

Enhver «bekreftet/verifisert X»-påstand i en worker-rapport MÅ følges av kommando + ordrett output. En prosa-bekreftelse UTEN kommando+output regnes som IKKE verifisert. Alle fire worker-chartere (planner, reviewer, implementer, code-reviewer) bærer nå denne regelen STRUKTURELT i egen «## Bevis»-seksjon — dispatch-promptene under (§3/§4/§5/§5b) holdes derfor bevisst MINIMALE og gjentar IKKE sitat-/anti-fab-instruksene: én kilde til bevis-kravet (charterne), ikke to. `evidence`-feltet i rapportene er en billig førstelinje-tripwire og erstatter ALDRI koordinatorens egen uavhengige sjekk (`git status`/`wc -l`/`gh pr view`/`gh pr diff`).

Konkret grense,
som er etterprøvbar i motsetning til ordet «minimale»: **review-funn siteres ALDRI inline i en
fix-/revisjons-dispatch.** Skriv rapporten til fil og pek på stien. Prompten skal bære oppdraget og
pekeren, ikke innholdet. Dette er ikke en ny regel — det er den gamle, gjort målbar.

<!-- mekanisk-kandidat: review-funn siteres ALDRI inline i en fix-dispatch — PreToolUse-hook på Agent som måler promptlengde og BLOKKERENDE-blokk (mangler) -->


## 0. Synk
→ `steps/0-synk.md` — les hele fila FØR steget kjøres.
- [ ] Først, før synken: finnes `steps/0c-sjekkpunkt.md`, skriv sjekkpunkt-stubben derfra (§0c).
- [ ] Hva: ff-only-synk av `{{BASE_BRANCH}}` (eller sesjonens speil-branch) før hver runde; skittent tre eller divergert branch → STOPP.
- [ ] Vakt/kommando: `git fetch origin {{BASE_BRANCH}} && git merge --ff-only origin/{{BASE_BRANCH}}`; `core.hooksPath .githooks` settes idempotent hvis `.githooks/` finnes
- [ ] Pausepunkt: `git`/working-tree ikke ren (§0)

## 0c. Sjekkpunkt ved komprimering (valgfri)
→ `steps/0c-sjekkpunkt.md` — finnes bare når `hooks.compaction_checkpoint` er på. Les hele fila FØR §0.
- [ ] Hva: egen sjekkpunkt-fil per sesjon, skrevet ved hver steg-overgang og lagt tilbake i konteksten etter en komprimering; sjekkpunktet vinner over sammendraget.
- [ ] Vakt/kommando: `sessionstart-checkpoint.sh` (SessionStart/`compact`), `precompact-checkpoint.sh` (PreCompact/`auto`); ser du ingen `KOORDINATOR-CHECKPOINT GJENOPPRETTET`-blokk etter komprimering, les fila selv

## 0b. Rydd en worker-worktree (gjenbrukbar prosedyre)
→ `steps/0b-rydd-worker-worktree.md` — les hele fila FØR steget kjøres.
- [ ] Hva: gjenbrukbar prosedyre som rydder én workers worktree etter mottatt rapport, kun når alle vakter (pre-snapshot-par, artefakt-gate, ren/ulåst, branch-kryssjekk) er grønne; ellers ADVARSEL og BEHOLD.
- [ ] Vakt/kommando: `git worktree list --porcelain`; `git cat-file -e`
- [ ] Pausepunkt: ingen (ADVARSEL føres videre som suffiks i §6-raden)

## 1. Kø-utvelgelse (med ekte deps-gating)
→ `steps/1-koe-utvelgelse.md` — les hele fila FØR steget kjøres.
- [ ] Hva: `release.py status` først; kjør kø-skriptet i stegfilen (deps-resolvert, ekskluderer claimed/brainstorm/forslag/prod-release, bare den aktive releasens scope, prioritet → order), velg øverste `elig=YES`; ingen kandidat → DOM avgjør (`INGEN AKTIV RELEASE` → §7, ellers pausepunkt); et bevisst hopp er nivå B3.
- [ ] Vakt/kommando: `python3 tasks/release.py status` (exit 2 ⇒ pausepunkt); kø-skriptet `python3 - <<'PY'` i stegfilen; `decision-level.py` (B3)
- [ ] Pausepunkt: Brainstorm-påkrevd todo (hoppet over i §1); Release: scope tomt eller blokkert, eller `release.py` exit 2 (§1); B3

## 2. Claim + pre-løs lessons-tema
→ `steps/2-claim-og-lessons-tema.md` — les hele fila FØR steget kjøres.
- [ ] Hva: sett `claimed_by`; pipelinet plan → hopp §3/§4 via §5c-ferskhetsgaten; graf-oppslag + velg 1–3 tema fra katalogen i tasks/lessons.md; claim-release i ENHVER stopp-sti.
- [ ] Vakt/kommando: `python3 tasks/graph-query.py --todo <nr>`
- [ ] Pausepunkt: ingen

## 2b. Fast-path (hopp §3/§4 → rett til §5)
→ `steps/2b-fast-path.md` — les hele fila FØR steget kjøres.
- [ ] Hva: hopp §3/§4 kun når alle tre betingelsene i stegfilen holder (dokumentert presedens, ingen teknisk risiko mulig, komplette verifiseringskriterier); §5b kan ALDRI hoppes; presedensen navngis i §5-noten og §6-commit-meldingen.
- [ ] Vakt/kommando: ingen skript — de tre betingelsene i stegfilen
- [ ] Pausepunkt: ingen

## 3. Dispatch planner
→ `steps/3-dispatch-planner.md` — les hele fila FØR steget kjøres.
- [ ] Hva: velg canary, ta pre-snapshot, dispatch, verifiser canary + `evidence.toplevel`, overlever planfila (`cp` + `cmp -s`), commit/push med speil-guard, §0b-rydding; re-dispatch akkumulerer per forsøk.
- [ ] Vakt/kommando: proporsjonalitetsport (grep etter eksisterende løsning, kjerne-anslag, budsjett i dispatchen); canary med linjenummer; `git worktree list --porcelain > "<scratch>/wt-pre-3-planner-<runde>.txt"`; `cmp -s`
- [ ] Pausepunkt: `canary`-mismatch som ikke løses (§3)

## 4. Dispatch reviewer + gate
→ `steps/4-dispatch-reviewer.md` — les hele fila FØR steget kjøres.
- [ ] Hva: pre-snapshot, dispatch, bevis-sjekk (`evidence.reviewed_head`), gate på `verdict` (no-go → Konsolideringsgate (≥ 400 linjer og tidligere runde) → §3-revisjon, maks 2 runder; go → re-mål `effort`, bær VIKTIG/MINDRE til §5); `technical_risk` → STOPP med mindre klassifiseringen gir B5.
- [ ] Vakt/kommando: `python3 tasks/vblock-lint.py <plan> --log` FØR dispatch (exit 1 ⇒ tilbake til planneren, teller ikke som runde); `planned_diff` > ~5× budsjettet ⇒ pausepunkt; `python3 tasks/decision-level.py --event technical_risk`
- [ ] Pausepunkt: Reviewer no-go som ikke konvergerer etter 2 runder (§4); Proporsjonalitet: `planned_diff` > ~5× budsjettet (§4); Teknisk risiko flagget (§4) eller truffet (§5/§6); B5; B7

## 5. Dispatch implementer
→ `steps/5-dispatch-implementer.md` — les hele fila FØR steget kjøres.
- [ ] Hva: pipelining på → §5c dispatcher par 1; ellers pre-snapshot + dispatch med plan-review-funnene; `status: failed|blocked` → STOPP; noter `F3a_ref`; akkumuler (toplevel, snapshot)-par for §6; bevaringsregel ved abort.
- [ ] Vakt/kommando: `git worktree list --porcelain > "<scratch>/wt-pre-5-implementer-<runde>.txt"`; `F3a_ref`
- [ ] Pausepunkt: Teknisk risiko flagget (§4) eller truffet (§5/§6); andre `plan_invalid` på samme todo (§5); ingen egen rad for STOPP ved `status: failed|blocked` (pre-eksisterende — står kun i stegfilen)

## 5b. Uavhengig kode-review
→ `steps/5b-kode-review.md` — les hele fila FØR steget kjøres.
- [ ] Hva: Minne-gate → trigger-sett beregnet SELV → dispatch kode-reviewer → gate på severity (revise-gate) med kontrakt-vakt og liveness-vakt → fix-mode-dispatch («Rotårsaksanalyse før fix-runde 3»; «Modell-eskalering fra fix-runde 3»: dyp modell fra runde 3) → Gate F re-verifisering av V-blokken før neste runde. Riving/migrering av brukervendt flate: gatene G1–G3.
- [ ] Vakt/kommando: `tasks/review-lens-select.py`; `tasks/review-severity-floor.py` (se «Gulvunntak for ordlyd»); `tasks/review-fan-in-verify.py`; `python3 tasks/decision-level.py --event revise_gate_choice`; `.claude/hooks/guard-fix-round-model.sh` (krever eksplisitt `model` på HVER implementer-dispatch, dyp modell fra fix-runde 3)
- [ ] Pausepunkt: Kode-reviewer revise-gate — **nivå B1 innenfor taket**; Agent-probe i preflight feiler; B1

## 5c. Pipelining (plan neste todo mens denne implementeres)
→ `steps/5c-pipelining.md` — les hele fila FØR steget kjøres.
- [ ] Hva: ved §5-dispatch av A: velg B, par 1 = implementer(A) + planner(B) i ÉN melding, par 2 = kode-reviewer(A) + reviewer(B); B sin plan committes i pre-par-2-halen; ferskhets-gate ved gjenopptakelse i §2; pausepunkt på B ⇒ B droppes, A fortsetter (B4).
- [ ] Vakt/kommando: `pipelining.max_in_flight`; `tasks/review-lens-select.py`
- [ ] Pausepunkt: Ferskhets-gaten for en pipelinet plan er fortsatt ikke-tom etter én re-plan-runde (§5c); B4

## 5d. Parallelle implementere (fil-disjunkt-gate — TODO 233)
→ `steps/5d-parallelle-implementere.md` — les hele fila FØR steget kjøres.
- [ ] Hva: når B er `go`: §1-filter (kan kun avvise) → gate P (fil-disjunkt) → claim B og dispatch implementer(B) sammen med A; in-flight-tabell; gate M før B sin merge; B eskalert til nivå A etter claim ⇒ frys B.
- [ ] Vakt/kommando: `tasks/parallel-disjoint.py`; `parallel_implementers.max`
- [ ] Pausepunkt: ingen egen rad — gate M-utfall og B-eskalering håndteres i stegfilen (§5d/§6)

## 6. Skriv delt state (seriell, re-kjørbar) + merge (kun koordinator)
→ `steps/6-delt-state-og-merge.md` — les hele fila FØR steget kjøres.
- [ ] Hva: fra ferdig-rapporten: CI-gate `ci=green` for pinnet head-SHA (steg 0, før delt state røres) → lessons → bugs → arkiver todo + planfil → verifiser base = `{{BASE_BRANCH}}` → todo-nr-gater (a) + (b) → merge via REST med `sha=` fra gaten → `stadium: merged` → §0b per akkumulert par → (§5d: seriell merge + CI-differensial) → steg 4b sweep (`wtsweep=`, `wtsweep_named=`) → steg 5 run-log-rad (dedup-guardet, notat-felt) → steg 6 delt-state-git-hale; selv-modifiserende PR ⇒ re-les endrede filer.
- [ ] Vakt/kommando: `python3 tasks/ci-gate.py <pr-nummer>`; `gh pr view <pr> --json baseRefName -q .baseRefName`; `gh api --method PUT "repos/{owner}/{repo}/pulls/<pr-nummer>/merge" -f merge_method=merge -f sha=<sha fra steg 0>`; `./tasks/worktree-sweep.sh`
- [ ] Pausepunkt: CI-gate ikke grønn (§6 steg 0); todo-nr-kollisjon (§6.4 gate b, se §9); Merge-konflikt (§6.4); Rebase-konflikt i delt-state-git-halen (§6/§6c/§7/§8/§8b); Teknisk risiko flagget (§4) eller truffet (§5/§6)

## 6b. Drain bug-innboks (hver syklus, kun koordinator)
→ `steps/6b-drain-bug-innboks.md` — les hele fila FØR steget kjøres.
- [ ] Hva: hver syklus: hver fil i `tasks/bugs/inbox/` → `tasks/bugs.md` / ny todo / forkast; slett innboks-fila.
- [ ] Vakt/kommando: ingen skript
- [ ] Pausepunkt: ingen

## 6c. Helsesjekk + release-rådgiver (betinget, kun koordinator)
→ `steps/6c-helsesjekk.md` — les hele fila FØR steget kjøres.
- [ ] Hva: kjør `/loop-health-check` ved Trigger 1 (kø tom, før §7) eller Trigger 2 (hver 5. merge, telleren i stegfilen); grønn → §8b + §8c; rød → PAUSEPUNKT, §8b/§8c kjøres IKKE; Del D er del av sjekken.
- [ ] Vakt/kommando: `python3 tasks/loop-cadence.py` etter hver merged-rad (exit 1 = forfalt); `/loop-health-check`
- [ ] Pausepunkt: Helsesjekk rød (§6c) — regresjon eller infra-feil

## 6d. Worktree-sweep (hver syklus, kun koordinator)
→ `steps/6d-worktree-sweep.md` — les hele fila FØR steget kjøres.
- [ ] Hva: HVA/HVORFOR for døgnsweepen; selve kjøringen skjer i §6 steg 4b; `--gate` er token-basert; redning via `tasks/worktree-landed.sh`; docker prunes aldri automatisk.
- [ ] Vakt/kommando: `tasks/worktree-sweep.sh`; `tasks/worktree-landed.sh`
- [ ] Pausepunkt: ingen (gaten er §6c Del A)

## 7. Grooming-modus (kø tom)
→ `steps/7-grooming.md` — les hele fila FØR steget kjøres.
- [ ] Hva: kø tom → §6c først → §8b/§8c → inntil 3 utkast totalt (`status: deferred` + `tags: [forslag]`), aldri auto-implementer; stopp for triage.
- [ ] Vakt/kommando: ingen skript
- [ ] Pausepunkt: ingen (stopp for triage er forventet, ikke et pausepunkt)

## 8. Mini-retro (kø-tom/stopp)
→ `steps/8-mini-retro.md` — les hele fila FØR steget kjøres.
- [ ] Hva: ved kø-tom eller pausepunkt-stopp: 5-linjers entry til `retro-log.md` (dedup på timestamp-header), deretter delt-state-git-halen (§6 steg 6).
- [ ] Vakt/kommando: `grep -qF "## $TS —" docs/superpowers/loop/retro-log.md`
- [ ] Pausepunkt: ingen

## 8b. Drain retro-logg (ved §6c-helsesjekk — begge triggere — kun koordinator)
→ `steps/8b-drain-retro-logg.md` — les hele fila FØR steget kjøres.
- [ ] Hva: ved begge §6c-triggere (kun grønn): klassifiser hver utriagert `Forbedringsforslag`-linje (adopted/promoted/obsolete), rad i `retro-triage.md`, utestående-tak 3 for promoteringer; nivå B6.
- [ ] Vakt/kommando: `sed -n '/^## Logg/,$p' docs/superpowers/loop/retro-log.md`; `decision-level.py` (B6)
- [ ] Pausepunkt: ingen (B6 er nivå B — logg, ikke stopp)

## 8c. Agér på tallene (ved §6c-helsesjekk — begge triggere — kun koordinator)
→ `steps/8c-ager-paa-tallene.md` — les hele fila FØR steget kjøres.
- [ ] Hva: rett etter §8b (kun grønn): mål (feilklasser + kostnadstrend), les handlingslinja, handle (gate innført | todo | ikke gatebar — alltid logget), mål effekten av forrige handling.
- [ ] Vakt/kommando: `python3 tasks/lesson-classes.py --days 7`; `python3 tasks/measure-cost.py "$(date -v-30d +%F)" --trend`; `tasks/vblock-lint.py`
- [ ] Pausepunkt: ingen

## 9. Todo-nummer: reservasjon, kollisjon og renummerering
→ `steps/9-todo-nummer.md` — les hele fila FØR steget kjøres.
- [ ] Hva: nytt nr via `--next` mot fersk `origin/{{BASE_BRANCH}}`; reservasjon teller først når minimal fil er pushet; ved kollisjon renummererer PR-en som ikke har merget («sist inn flytter»), med prosa-grep etterpå.
- [ ] Vakt/kommando: `sh scripts/check-todo-nr-collisions.sh --next`; `sh scripts/check-todo-nr-premerge.sh <branch>`
- [ ] Pausepunkt: ingen egen rad — kollisjon før merge stopper i §6 steg 4

## Pausepunkter (nivå A — spør + eskalér; nivå B — bestem selv, logg, mennesket kan vetoe, TODO 246)

**Klassifiser ALLTID mekanisk, aldri fra hukommelsen:**
```bash
python3 tasks/decision-level.py --event <navn> --context k=v...
```
stdout: `{"level":"A"|"B","rule":"<id>","trigger":"…","obligations":[…],"violations":[…]}`.
`rule = "A0"` er fail-closed (ukjent hendelse, manglende påkrevd kontekst, eller rundetak
overskredet) — `level` er da ALLTID `"A"`, exit-koden ≠ 0, og valget behandles som et vanlig
nivå-A-pausepunkt under. Et ikke-klassifiserbart valg blir ALDRI stilltiende et nivå-B-valg.
`--dump-rules`/`--self-test` finnes for verifisering — se `loop-health-check.md` Del D.

**Alle `A`-radene i tabellen under er nivå A** (uendret oppførsel: STOPP, release claim, eskalér) **med unntak
av kode-reviewer-revise-gate-punktet**, som nå er delt i nivå A og nivå B1 — se B-radene i tabellen under.

### Alle pausepunkter — én tabell (ID `A` uten tall = eldre nivå-A-punkt utenfor `decision-level.py`; A1–A8 og B1–B7 = `decision-level.py`)

| ID | Trigger |
|---|---|
| A | Teknisk risiko flagget (§4) eller truffet (§5/§6) |
| A | Brainstorm-påkrevd todo (hoppet over i §1) |
| A | Reviewer no-go som ikke konvergerer etter 2 runder (§4) |
| A | Kode-reviewer revise-gate — **nivå B1 innenfor taket** (koordinatoren bestemmer selv og logger, se B-radene i tabellen under); eskalerer til mennesket (nivå A, uendret pausepunkt-oppførsel) KUN når den ene ekstra fix-runden `extra_allowed`-budsjettet ga (`code_review_rounds = 3`) også er brukt og revise-gaten fortsatt ikke er tom (§5b) |
| A | Agent-probe i preflight feiler («Agent type not found», dekker §5b) → fersk koordinator-sesjon kreves |
| A | Merge-konflikt (§6.4) |
| A | CI-gaten ikke `ci=green` (§6 steg 0) — unntatt `ci=red` fra PR-ens egen diff, som går til §5b fix-mode |
| A | Rebase-konflikt i delt-state-git-halen (§6/§6c/§7/§8/§8b) |
| A | Ferskhets-gaten for en pipelinet plan er fortsatt ikke-tom etter én re-plan-runde (§5c) |
| A | `git`/working-tree ikke ren (§0) |
| A | `canary`-mismatch som ikke løses (§3) |
| A | Proporsjonalitet: planens `planned_diff` > ~5× budsjettet fra §3 (§4, før review) |
| A | Andre `plan_invalid` på samme todo (§5) |
| A | Release: scope tomt (`MÅL NÅDD` / `MÅL IKKE NÅDD`), åpne scope-todoer uten kvalifiserte, eller `release.py status` exit 2 (§1) |
| A | Helsesjekk rød (§6c) — regresjon eller infra-feil i integrert `{{BASE_BRANCH}}` |
| A1 | Skriving mot prod-miljøet (`{{PROD_ENV_ID}}`) eller kjøring av `{{RELEASE_COMMAND}}` |
| A2 | Env-variabler, secrets eller vault |
| A3 | Native/EAS-bygg, TestFlight-distribusjon eller iOS-Modal-endring |
| A4 | Push eller merge til `{{PROD_BRANCH}}` |
| A5 | Destruktiv eller irreversibel operasjon (datasletting, force-push, drop) |
| A6 | Avvik fra `CLAUDE.md` eller `docs/naming-conventions.md` som krever menneskets bekreftelse |
| A7 | Apply av migrasjon eller RLS-endring mot dev (`{{DEV_ENV_ID}}`) |
| A8 | Edge Function-deploy (dev eller prod) |
| B1 | §5b revise-gate **etter 2/2**: én ekstra målrettet fix-runde (runde 3) vs. merge m/carry-forwards vs. stopp — og de samme valgene innenfor taket |
| B2 | Splitt av en todo i del-todos |
| B3 | Valg eller hopp av neste todo innenfor mennesket-godkjent rekkefølge (§1) |
| B4 | Pipelining: valg eller drop av B-sporet (§5c) |
| B5 | Godkjenning av `technical_risk` fra **plan-rapporten** når `kind ∈ {docs_selfmod, hook_selfmod}` **og** `executable_gate = true` |
| B6 | Retro-triage: hvilke retro-observasjoner som promoteres eller lukkes (§8b) |
| B7 | §4 plan-review: ny revisjonsrunde vs. drop/`open` — **kun når `plan_review_rounds < 2`** |

<!-- mekanisk-kandidat: pausepunkt-tabellen ↔ decision-level.py (finnes: tasks/decision-level.py + D2-paritet i loop-health-check.md Del D) -->


De `A`-radene uten tall i tabellen over er egne, ELDRE pausepunkter (utenfor `decision-level.py`s
15-rads regeltabell) og forblir nivå A uansett — A1–A8 dekker et ANNET, mer spesifikt sett
hendelser (prod-skriving, secrets, native, `{{PROD_BRANCH}}`, destruktive operasjoner,
naming-avvik, migrasjon/RLS mot dev, Edge Function-deploy) som koordinatoren klassifiserer
eksplisitt før den handler (§2c, §5c).


**Pinnet (mot tvetydighet):** rundebetingelsene i B1/B7s triggertekst over («etter 2/2»,
«kun når `plan_review_rounds < 2`») er PROSA for menneskelesere og for V7-paritet mot
`--dump-rules` — de er IKKE en betingelse i selve B1/B7-regelmatchingen i `decision-level.py`.
Rundetak bor UTELUKKENDE i rundetak-vakten under; B1 matcher på `event=revise_gate_choice` +
`action ∈ {fix_round, merge_carry, stop}` alene, og B7 matcher på `event=plan_review_choice` +
`action ∈ {revise, drop}` alene. **B5 krever begge betingelser** (`kind`  OG `executable_gate`);
et `technical_risk` med `kind=migration` treffer A7 fordi B5s `kind`-betingelse er usann — IKKE
fordi A7 evalueres først (rekkefølgen A-block-før-B-block er likevel reell og bindende, se
skriptets docstring). **`technical_risk` fra en REVIEWER (ikke planneren) bærer aldri
`kind`/`executable_gate` og klassifiseres derfor ALLTID som nivå A** — B5 gjelder kun
plan-rapportens `technical_risk` (§4 «Ved `technical_risk.flagged`» over). **`hook_selfmod`s
eksakte scope** (hvilke filer i `.claude/hooks/` som teller, og at hooks som håndhever en
nivå-A-invariant som `guard-main-merge.sh`/`guard-supabase-ref.sh` ALDRI er B5 uansett
`executable_gate`) er definert i `report-schema.md` — B5-raden over gjentar den ikke, for å
unngå at D2s ordrette paritet-diff (tabellrad ↔ `TRIGGER_BY_ID`) driver fra scope-prosaen.

**Rundetak-vakt (evalueres FØR alt annet i `decision-level.py`, uavhengig av `--event`):** taket
er **2** (frosset fra §4/§5b-eskaleringene). `extra_allowed = 1` er et **FIX-RUNDE-BUDSJETT** for
`revise_gate_choice`-siden alene — IKKE et globalt rundebudsjett: å LUKKE gaten (`merge_carry`/
`stop`) er alltid B1, uansett hvor mange runder som allerede er brukt. Kun et NYTT `fix_round`-
forsøk utover budsjettet er A0.

| `code_review_rounds` | `action=fix_round` | `action ∈ {merge_carry, stop}` |
|---|---|---|
| `0`–`1` (innenfor taket) | **B1** | **B1** |
| `2` (revise-gate 2/2) | **B1** (autoriserer runde 3) | **B1** |
| `3` (den ene ekstra er brukt) | **A0** — en fjerde fix-runde krever mennesket | **B1** (lukking er fortsatt B) |
| `≥ 4` | **A0** for et NYTT fix-runde-forsøk | **B1** (lukking er fortsatt B, uansett rundetall) |

Uavhengig av tabellen over: **ved `code_review_rounds >= 2` er `--context decision_logged=yes`
PÅKREVD for ETHVERT `--event`**, ikke bare `revise_gate_choice` — en koordinator kan ikke smugle
rundekontekst forbi loggplikten via et annet hendelsesnavn (lukker et BLOKKERENDE plan-review-
funn om event-navn-lekkasje).

**Residual, navngitt — IKKE lukket, hverken av skriptet eller av Del D4 i denne PR-en:**
`decision_logged=yes` og run-loggens `code_review_rounds` skrives av SAMME aktør (koordinatoren) i
samme runde — en under-rapportering av begge likt ville passere klassifiseringen uoppdaget her, og
V14/V16 er konsistenskontroller mellom to selvrapporter, ikke verifisering mot en uavhengig kilde
(plan-review r2, VIKTIG-funn 2). Forberedt, men IKKE koblet inn: hver `[B1]`/`[A0]`-decision-log-
entry for en `revise_gate_choice`-beslutning bærer i tillegg **`Runde-SHA:`** — den samme
`pr_head_sha` §5b «Trigger-sett»-steget allerede pinner for den runden (§5b over, `gh pr view <pr>
--json headRefOid`). En fremtidig todo kan la `loop-health-check.md` Del D4 verifisere at hver slik
SHA faktisk finnes (`git cat-file -e`) og at antall DISTINKTE runde-SHA-er for todoen er
`>= code_review_rounds - 1`; **denne PR-en skriver kun feltet** — se `loop-health-check.md` Del D4
«Residual» for den eksplisitte, dokumenterte avgrensningen (ingen `git log`-avhengig gate er lagt
til Del D ennå).

**De fire logg-pliktene (alle fire, ellers er det ikke et gyldig nivå-B-valg):**

1. Decision-log-entry i frosset format (`docs/superpowers/loop/decision-log.md` § Format) — for
   `revise_gate_choice`-beslutninger ved `code_review_rounds >= 2` bærer entryen i tillegg
   `**Runde-SHA:** <sha>` (se «Residual» over).
2. `auto_decided=<rad-eier>:<antall>` i `run-log.md` felt 11, ved siden av `selector=`/`floor=`/
   `pipelined_from=` (se §6 steg 5).
3. Én linje i sluttmeldingen: `<regel-id> — <kort valg> (reversibel til <punkt>; veto: svar i
   chatten)`.
4. Regel-IDen er hentet fra `python3 tasks/decision-level.py`, ikke fra hukommelsen.

**Veto:** mennesket kan når som helst svare i chatten og overstyre et logget nivå-B-valg —
koordinatoren ruller da tilbake til «Reversibel til»-punktet i decision-log-entryen.
