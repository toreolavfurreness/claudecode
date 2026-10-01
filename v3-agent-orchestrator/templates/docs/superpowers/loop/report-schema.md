<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# Loop-rapport-skjema

Seks rapporttyper er definert i denne fila. Fire av dem — `plan`, `review`, `code_review`, `done` — binder koordinator og workers sammen. De to siste binder workers til hverandre og når aldri koordinatoren direkte: `lens_observation` (kode-revieweren og dens lenser, med en litt annen bevis-kontrakt — se § Lens-observasjon under) og `scout` (planner/implementer og lokaliserings-workeren — se § Scout-rapport under). Hver returneres som ETT JSON-objekt i workerens siste melding (sluttmeldingen ER returverdien — ingen prosa rundt). Bevis-sitater (se «Bevis-regel» under) bor INNI dette JSON-objektet, som et `evidence`-felt — aldri som prosa før eller etter.

## Bevis-regel (gjelder alle seks rapporttyper — for `lens_observation` er `evidence`-nøkkelen PÅKREVD fra TODO 250B, se § Lens-observasjon)

Enhver «bekreftet/verifisert X»-påstand i en rapport MÅ følges av kommandoen + ordrett output som beviser det. En prosa-bekreftelse uten kommando+output regnes som IKKE verifisert — koordinatoren skal behandle den slik (ikke stole på den). `evidence`-feltet under er en billig FØRSTELINJE-tripwire (spesielt for feil-cwd-tilfeller der workeren ikke lyver, men siterer fra feil sted); den erstatter IKKE koordinatorens egen uavhengige sjekk (`git status --porcelain`, `wc -l`/`tail`, `gh pr view/diff`, osv.).

**Probe-modus-unntak:** når dispatch-prompten er en ren probe som KUN ber om `{"ok": true}` (planner- og code-reviewer-preflight i `run-loop.md`; code-reviewer Steg 0) — svar bart `{"ok": true}`, uten `evidence`, uten sitater. Reglene under gjelder kun i FULL modus (faktisk plan/review/implementer/code-review-arbeid).

## Språk i enumer

`severity`- og `confidence`-enumene er NORSKE (`BLOKKERENDE`/`VIKTIG`/`MINDRE`,
`sikker`/`sannsynlig`/`mulig`); alle andre nøkler og verdier i loop-rapportene er ENGELSKE
(`merged`, `e2e_green`, `report_type`, `source_agent`, …). Dette er IKKE et brudd på
norsk-UI/engelsk-backend (CLAUDE.md) — feltene er verken UI-tekst eller Supabase-data — men regelen
skrives her ÉTT sted, slik at den ikke gjettes på nytt for hver ny rapporttype (TODO 180B).

## Plan-rapport (planner → koordinator)

```json
{
  "report_type": "plan",
  "todo_nr": "41",
  "slug": "redirect-after-login-next-flyt",
  "branch": "feat/todo-41-redirect-after-login-next-flyt",
  "plan_path": "tasks/plans/todo-41-redirect-after-login-next-flyt.md",
  "summary": "Kort sammendrag av valgt tilnærming (1-3 setninger).",
  "files_touched": ["src/proxy.ts", "src/app/login/page.tsx"],
  "technical_risk": { "flagged": false, "kind": null, "executable_gate": null, "detail": null },
  "deps_ok": true,
  "verification_criteria": ["Uinnlogget bruker på dyp lenke → /login?next=<url>"],
  "planned_diff": { "lines": 40, "files": 2 },
{{SCOUT_USAGE_LINE}}  "canary": "L<linjenummeret du landet på>: <de første 8 ordene på den linja>",
  "evidence": { "toplevel": "<ordrett output av `git rev-parse --show-toplevel`>", "plan_tail": "<ordrett `tail -5` av planfilen>" },
  "status": "reviewed",
  "notes": "Forbehold eller funn."
}
```

- `technical_risk.flagged`: `true` hvis planen krever noe under pause-triggerne. `kind` ∈ `"migration"|"rls"|"prod_push"|"secrets"|"docs_selfmod"|"hook_selfmod"` (de to siste, TODO 246, dekker kit-selvmodifisering). `docs_selfmod` = `v3-agent-orchestrator/templates/`, `.claude/commands/setup.md` — IKKE prosjektets øvrige dokumentasjon. `hook_selfmod` = ikke-A-håndhevende hooks i `.claude/hooks/` (i dag: `typecheck-on-edit.sh`, `session-start-lint.sh`, `guard-reviewer-readonly.sh` + tilhørende test-script) — **eksplisitt UTENFOR scope:** hooks som håndhever en nivå-A-invariant (`guard-main-merge.sh` = A4 push/merge til `{{PROD_BRANCH}}`; `guard-supabase-ref.sh` = A1/A7 prod/dev-prosjektref-skille) forblir ALLTID nivå A uansett `executable_gate`, fordi B5s koordinator-selv-godkjenning ellers ville latt koordinatoren godkjenne endring av vakten som håndhever sin egen A-plikt. Tilpass ellers til prosjektets pause-triggere.
- `technical_risk.executable_gate` (TODO 246, kun relevant når `kind` er `docs_selfmod`/`hook_selfmod`): `true` hvis planen har en KJØRBAR testtabell/differensial/mutasjonstest for endringen (ikke bare prosa-verifisering). `null` for de øvrige `kind`-verdiene. Koordinatoren klassifiserer `flagged: true` med `kind ∈ {docs_selfmod, hook_selfmod}` og `executable_gate: true` som **pausepunkt-regel B5** (`tasks/decision-level.py`) — bestemmer selv og logger i stedet for å spørre. Enhver annen `technical_risk` (inkludert ALT flagget av en REVIEWER, som aldri bærer `kind`/`executable_gate` — se «Kode-review-rapport» under) forblir nivå A.
- `deps_ok`: `false` → `status: "blocked"`.
- `planned_diff`: planens anslag for diffen, i linjer og filer. §4 sammenligner det med budsjettet fra §3-dispatchen (proporsjonalitet).
- `canary`: stikkprøve på at filene faktisk ble lest. Koordinatoren oppgir et mål (fil + linje som IKKE er gjentatt i prompten); planneren returnerer linjenummeret den landet på og den eksakte teksten der. Mismatch = lesing hoppet over. NB: dette beviser at lesing *skjedde*, ikke at *alle* bootstrap-filer ble lest fullt.
- `evidence`: `toplevel` beviser at planneren skriver i EGEN worktree (feil-cwd er en observert bug-klasse — planneren skrev en gang planfilen til hovedsjekkuten); `plan_tail` beviser at planfilen faktisk ble skrevet på disk. I probe-modus (se «Bevis-regel» over): utelates helt.
- `status` ∈ `"reviewed"|"blocked"`.
- `scout_usage`: summen av `measurement`-objektene fra scout-rapportene denne rollen dispatchet
  (`dispatches` = antall scout-oppdrag, `bytes_read` = sum av deres `bytes_read`, `findings` = sum
  av deres `findings_count`). Ingen scout brukt ⇒ `{ "dispatches": 0, "bytes_read": 0, "findings": 0 }`
  — et lovlig og ofte riktig svar. Feltet er PÅKREVD når `scout.enabled` er `true` i
  `loop.config.yaml`, og utelates helt når rollen er av; koordinatoren summerer det til
  `scout=`-tokenet i `run-log.md` (se § frittekst-notatfelt under). Feltet er PÅKREVD også når
  `status: "blocked"` — normalt `{0, 0, 0}` — for å lukke den vanligste stien til `scout=unknown` ved
  kilden. Forbeholdet om hva `bytes_read`
  ER og ikke er, står i § Scout-rapport.

## Review-rapport (reviewer → koordinator)

```json
{
  "report_type": "review",
  "todo_nr": "41",
  "plan_path": "tasks/plans/todo-41-redirect-after-login-next-flyt.md",
  "findings": [
    { "severity": "BLOKKERENDE", "ref": "Steg 3", "issue": "…", "fix": "…" },
    { "severity": "VIKTIG", "ref": "Steg 5", "issue": "…", "fix": "…" },
    { "severity": "MINDRE", "ref": "Generelt", "issue": "…", "fix": "…" }
  ],
  "evidence": { "toplevel": "<ordrett output av `git rev-parse --show-toplevel` — SVAKT/sekundært, se under>", "reviewed_head": "<ordrett første 10 linjer av planfilen som ble reviewet — PRIMÆR>" },
  "verdict": "no-go",
  "notes": "Samlet vurdering."
}
```

- `severity` ∈ `"BLOKKERENDE"|"VIKTIG"|"MINDRE"`.
- `verdict` ∈ `"go"` (ingen BLOKKERENDE) | `"no-go"` (≥1 BLOKKERENDE → koordinator sender tilbake til planner, maks 2 runder).
- `evidence`: reviewer er IKKE symmetrisk med planner — revieweren SKRIVER ingenting, den LESER kun planfilen. `reviewed_head` er derfor PRIMÆRT bevis (beviser faktisk lesing av riktig artefakt); koordinatoren matcher den mot SIN EGEN kopi av planfilen (den reviewer ble dispatchet mot). `toplevel` beviser kun reviewerens egen cwd, ikke at riktig artefakt ble lest — merkes SVAKT/sekundært.
- **Dette skjemaet har ingen `technical_risk`-nøkkel** (TODO 246). En reviewer som mener planen
  bærer teknisk risiko, flagger det via `verdict: "no-go"` + `notes`, ikke via et strukturert felt.
  Koordinatorens `tasks/decision-level.py` klassifiserer ALL reviewer-initiert `technical_risk` som
  nivå A — **pausepunkt-regel B5 gjelder KUN plan-rapportens `technical_risk`**, aldri reviewerens.

## Lens-observasjon (tech-review-sub-agent → code-reviewer)

Pluggbare tech-review-agenter (`tech_review_agents` i `loop.config.yaml`) leverer IKKE en
severity-rangert rapport. De leverer **severity-frie observasjoner** — severity er
kode-reviewerens (synthesizerens) ansvar alene, aldri lensens (TODO 180B).

```json
{
  "report_type": "lens_observation",
  "agent": "rls-migration-reviewer",
  "scope": "hva som faktisk ble gransket",
  "observations": [
    { "ref": "supabase/migrations/20260901_x.sql:42", "issue": "…", "fix": "…", "confidence": "sikker", "basis": "postgres-rls.md 2026-05-26" }
  ],
  "checked_ok": ["hva som ble sjekket og var i orden"],
  "evidence": { "toplevel": "<git rev-parse --show-toplevel — SVAKT, se under>", "reviewed_sha": "<SHA-en du faktisk gransket>" },
  "notes": "…"
}
```

- **Ingen `severity`-nøkkel.** En lens som emitterer en har brutt kontrakten; kode-revieweren
  ignorerer verdien og rapporterer bruddet i `notes`.
- `confidence` ∈ `"sikker"|"sannsynlig"|"mulig"` er lensens EGEN sikkerhet på funnet — IKKE
  alvorlighet. Kode-revieweren bruker `severity_floor` (per agent, i `loop.config.yaml`) og hele
  diff-konteksten til å sette faktisk severity, ikke `confidence`.
- `basis` peker på lesson-dato / BUG-nr / regel som gjør observasjonen etterprøvbar for
  kode-revieweren, i stedet for å be den stole på lensens ordvalg.
- Kode-revieweren samler observasjoner fra alle dispatchede lenser inn i `code_review.findings[]`
  (se under) og setter `severity` + `source_agent` på hver av dem. Dette skjemaet er ALDRI
  koordinatorens eller implementerens returverdi direkte.
- `toplevel` er **SVAKT**. Lensens worktree-topologi er nå MÅLT ÉN gang (TODO 250C, 2026-09-07, ÉN
  harness): de fire lens-charterne har ingen `isolation`-nøkkel, og utfallet der var **arv av
  kode-reviewerens worktree** — konsistent med at nøkkelen er fraværende (fravær har minst to
  mulige utfall i prinsippet: arv av kode-reviewerens worktree, eller hovedsjekkuten; DENNE
  målingen viser det første). **Formuleringen skal fortsatt være betinget** — «kan være identisk med
  synthesizerens egen» — aldri en universell påstand om at den ALLTID ER det: målingen er
  HARNESS-AVHENGIG og generaliseres IKKE til andre prosjekter som bruker dette kit-et. Den daterte
  målingen (arkiv-stabil referanse — planfiler flyttes til `tasks/plans/archive/` ved `/todo-done`)
  står i `steps/5b-kode-review.md` «Liveness-vakt (TODO 250C)» pkt. 7.
- `reviewed_sha` er lensens PRIMÆRE bevis og kan kryss-sjekkes mot `code_review.evidence.pr_head_sha`
  (stale-diff-tripwire). `null` er lovlig og betyr «ikke oppgitt». **Oppgi FULL 40-tegns SHA, aldri
  kortform** — en kort SHA kan bli ikke-normaliserbar i mottakerens R10-sjekk.
- **Overgangsregel:** `evidence` er **PÅKREVD fra TODO 250B**. Flippen ble gjort i TODO 250B; den
  virker først i en koordinator-sesjon som oppfyller predikatet i `coordinator-runbook.md` §5b. I en
  sesjon startet FØR mergen, eller i et kit-prosjekt uten flagget, er en `lens_observation` uten
  `evidence` fortsatt `legacy`, ikke et kontraktbrudd.
- **`legacy`-stien finnes fortsatt, men kun i to tilstander:** (i) en koordinator-sesjon startet FØR
  TODO 250Bs merge (skriptet kjøres da i form A, uten `--require-attestations`), og (ii) et
  kit-prosjekt som ikke gir flagget. Fixture F11 er den frosne, falsifiserbare formen for
  flagg-AV-stien; F19/F20 dekker flagg-PÅ.

## Scout-rapport (scout → planner/implementer)

Lokaliserings-workeren (`scout` i `loop.config.yaml`) svarer på ÉTT «hvor er X»-spørsmål. Den
returnerer STEDER, aldri filinnhold, og den setter ALDRI severity — den vurderer ingenting. Den
går til oppdragsgiveren (planner eller implementer), aldri til koordinatoren.

```json
{
  "report_type": "scout",
  "query": "hvor settes claimed_by på en todo",
  "status": "answered",
  "findings": [
    { "ref": "tasks/todos/README.md:31", "symbol": "claimed_by", "why": "definisjon av feltet" },
    { "ref": "lib/todos.ts:88", "symbol": "updateTodo", "why": "eneste skrivested" }
  ],
  "unresolved": ["fant ingen skriving fra e2e-testene — søkte e2e/**/*.spec.ts etter claimed_by"],
  "measurement": {
    "files_read": 2, "bytes_read": 51234,
    "bytes_read_cmd": "wc -c tasks/todos/README.md lib/todos.ts | tail -1",
    "findings_count": 2, "truncated": false
  },
  "evidence": {
    "toplevel": "<ordrett output av `git rev-parse --show-toplevel`>",
    "searched": ["rg -n 'claimed_by' --glob '!node_modules'", "ls e2e/"]
  },
  "notes": ""
}
```

- `status` ∈ `"answered"|"blocked"`. `"blocked"` = oppdraget var underspesifisert; `notes` sier hva
  som manglet. Et tomt `findings` med `status: "answered"` er et gyldig svar («finnes ikke») og skal
  ikke forveksles med `"blocked"`.
- `findings[].ref` er `fil:linje`. **Filinnhold hører ikke hjemme i rapporten** — maks to linjer
  ordrett sitat per funn, og kun når spørsmålet ER hvordan linja lyder. Oppdragsgiveren åpner selv
  stedene den skal planlegge eller endre (se delegerings-seksjonen i planner-/implementer-charteret):
  et scout-funn er et kart, ikke kildemateriale.
- `truncated: true` ⟹ `scout.max_findings` ble nådd og noe ble utelatt; `notes` MÅ si hva. Et stille
  kutt leses som «dekket alt» når det ikke gjorde det (runbookens «ingen stille tak»).
- `measurement.bytes_read` er MÅLT med kommandoen i `bytes_read_cmd`, aldri anslått. Åpnet scouten
  ingen filer: `0` + `bytes_read_cmd: "-"`.
- **`bytes_read` er ikke «tokens spart».** Det er en ØVRE GRENSE for filinnhold oppdragsgiveren
  slapp å holde i konteksten sin — oppdragsgiveren ville ikke nødvendigvis lest alt scouten leste.
  Tallet er brukbart som trend over mange runder, ikke som en besparelse per runde.
- `evidence.searched` er søkekommandoene ordrett. Uten dem er funn-lista ikke etterprøvbar, og
  bevis-regelen over gjelder scouten som alle andre.
- `evidence.toplevel` er scoutens `git rev-parse --show-toplevel`. Scouten har ingen
  `isolation`-nøkkel, og fravær av den har minst to mulige utfall (arv av oppdragsgiverens tre, eller
  hovedsjekkuten) — utfallet er HARNESS-AVHENGIG og generaliseres IKKE til andre prosjekter som
  bruker dette kit-et. Oppdragsgiveren MÅ derfor kryssjekke feltet mot sin egen `toplevel` før den
  stoler på linjenumre: et svar avgitt fra et annet tre ser ellers nøyaktig ut som et riktig svar.

## Kode-review-rapport (code-reviewer → koordinator)

```json
{
  "report_type": "code_review",
  "todo_nr": "41",
  "pr_url": "https://github.com/{{GITHUB_REPO}}/pull/42",
  "pr_number": "42",
  "findings": [
    { "severity": "BLOKKERENDE", "ref": "src/app/login/page.tsx:42", "issue": "…", "fix": "…", "source_agent": "{{PROJECT_NAME}}-code-reviewer" },
    { "severity": "VIKTIG", "ref": "src/lib/auth/safe-next.ts:17", "issue": "…", "fix": "…", "source_agent": "rls-migration-reviewer" },
    { "severity": "MINDRE", "ref": "src/components/ui/Button.tsx:5", "issue": "…", "fix": "…", "source_agent": "{{PROJECT_NAME}}-code-reviewer" }
  ],
  "fan_in": { "triggered": ["rls-migration-reviewer"], "dispatched": ["rls-migration-reviewer"], "returned": ["rls-migration-reviewer"], "expected_by_selector": [], "attestations": [ { "agent": "rls-migration-reviewer", "toplevel": "…", "reviewed_sha": "…" } ], "worktree_guard": { "before": "…", "after": "…" } },
  "evidence": { "toplevel": "<ordrett output av `git rev-parse --show-toplevel` — SVAKT, se under>", "pr_head_sha": "<ordrett `gh pr view <pr> --json headRefOid`-output — PRIMÆR>" },
  "tdd_check": { "required": 0, "red_commits": 0, "l2_status": "ikke utløst", "pairs_replayed": 0, "reason": null },
  "verdict": "no-go",
  "notes": "Samlet vurdering av diffen."
}
```

- **`tdd_check` er PÅKREVD** — de MÅLTE tallene fra kode-reviewerens rødt-før-grønt-sjekk:
  `required` = antall `TDD-STEG` i planen, `red_commits` = antall `test(red):`-commits i PR-en,
  `l2_status` ∈ `"kjørt"|"ikke kjørt"|"ikke utløst"`, `pairs_replayed` = par faktisk replayet (maks 3),
  `reason` = målt degraderingsgrunn (`null` ved `"kjørt"`). `"ikke utløst"` = ingen `TDD-STEG`/ingen
  røde commits; `"ikke kjørt"` = replay forsøkt og feilet, med sitert `reason`; `"kjørt"` = ≥ 1 par
  replayet. Feltet beviser **orden** (testen feilet før koden fantes) og erstatter ikke planens
  mutasjonsrader / gate F, som beviser at vakten går rød i dag. Mangler feltet: TDD-sjekken er
  ugyldig.
- `findings[]`-objektet har **identisk shape som plan-review-rapportens `findings[]` PLUSS
  `source_agent`**, som er unikt for `code_review` (`severity`/`ref`/`issue`/`fix`/`source_agent`);
  for kode-review er `ref` = `file:line`. Plan-review-funn skal IKKE ha feltet. Ingen omdøping av
  de øvrige feltene.
- `source_agent` (TODO 180B) er **påkrevd** på hvert funn, satt av kode-revieweren (aldri av
  lensen) — ett av `tech_review_agents[].name` eller `"{{PROJECT_NAME}}-code-reviewer"` for
  kode-reviewerens egne funn. Aldri `null`, aldri utelatt. Feltet er limet som gjør
  `severity_floor`-gulvet håndhevbart i kode (`tasks/review-severity-floor.py`) i stedet for i
  prosa — uten agent-attribusjon per funn kan ikke koordinatoren regne ut om et gulv ble
  respektert. **`tasks/review-severity-floor.py` ekskluderer bevisst funn med manglende/ukjent
  `source_agent` (eller ugyldig `severity`) fra sin `findings[]`-output og feiler høyt (exit ≠ 0,
  ikke-tom `violations[]`) i stedet** — se `coordinator-runbook.md` §5b for hvordan koordinatoren
  skal lese denne exit-koden. Et funn som mangler `source_agent` her oppdages der, ikke i dette
  skjemaet alene.
- `floor_exempt` (TODO 321) er **valgfritt** og settes av kode-revieweren, aldri av lensen. Utelatt
  eller `null` = ingen merking. Ellers nøyaktig `"comment_doc_wording"`, bare på funn fra en agent
  med «Gulvunntak» i kode-reviewer-charteret, med `ref` `fil:N`/`fil:N-M` på kommentarlinjer eller
  en linje i en `.md`-fil under `docs/` (også `docs/` krever `:N`). Merkingen senker aldri severity:
  `tasks/review-severity-floor.py` godtar den bare etter en mekanisk ref-sjekk (ellers
  `exempt_rejected[]` og vanlig gulv), og koordinatoren leser `issue`/`fix` mot hovedkriteriet
  (eneste kontroll av selve funnet) og sjekker fra r≥2 at forrige fix-runde bare endret ordlyd i
  ref-fila — rettelsen av det unntatte funnet selv verifiseres aldri (`coordinator-runbook.md`
  §5b). Enhver annen verdi gir `violations[]` og usignert rapport.
- `fan_in` (TODO 180A — erstatter den tidligere `tech-review fan-in: n/n/n`-linja i `notes`, ikke en tilføyelse til den): et objekt med FEM felt (seks med `worktree_guard`, se under) — de fire PÅKREVDE arrayene pluss `attestations`, som er PÅKREVD når `returned` er ikke-tom (TODO 250B) — i rapporten din, PÅKREVD i full modus. **Mangler `fan_in` helt i en full-modus-rapport → kontraktbrudd, behandles som usignert** — samme prinsipp som 179s vakt (fravær er utvetydig bevis på at vakten ble ignorert, aldri stilltiende «alt er fint»).
  - `triggered` (reviewer-fylt): agenter kode-revieweren selv vurderer at `trigger:`-prosaen treffer for denne diffen.
  - `dispatched` (reviewer-fylt): agenter kode-revieweren faktisk sendte til som frisk sub-agent.
  - `returned` (reviewer-fylt): agenter som faktisk svarte.
  - `expected_by_selector` (**koordinator-fylt, ALDRI av revieweren**): revieweren SKAL levere dette feltet som en TOM array (`"expected_by_selector": []`, se eksempelet over) — ALDRI utelate nøkkelen. Koordinatorens egen utregning via `tasks/review-lens-select.py` (`trigger_globs`-gulvet i `loop.config.yaml`) fylles inn i feltet ETTER at rapporten er mottatt, ALDRI av revieweren selv. «Utfylt» betyr her en IKKE-TOM array: en `code_review`-rapport som ankommer med en ikke-tom `expected_by_selector` er et **kontraktbrudd** og behandles som usignert. En tom array er forventet og korrekt fra revieweren.
  - `attestations` (**ATTESTASJONSPÅBUD, revieweren, TODO 250B**): for hver agent i `returned` — SKAL — en entry med `agent` (streng, påkrevd) + `toplevel`/`reviewed_sha` (streng eller `null`), sitert fra lensens egen `evidence`. Når nøkkelen finnes, gjelder form-regelen `{a.agent for a in attestations} == set(returned)`. Er session-predikatet i `coordinator-runbook.md` §5b usant (form A), er manglende nøkkel fortsatt `legacy` og ikke et kontraktbrudd — se `coordinator-runbook.md` §5b og `tasks/review-fan-in-verify.py`.
  - `worktree_guard` (**revieweren, TODO 292** — sjette felt, PÅKREVD når `dispatched` er ikke-tom): `{ "before": "<ordrett>", "after": "<ordrett>" }` — utskriften av arbeidstre-snapshotet i kode-reviewer-charterets «Arbeidstre-vakt», tatt rett før og rett etter lens-fanouten. Ulike verdier (sammenlignet ord for ord) ⇒ arbeidstreet ble endret under lens-runden ⇒ rapporten behandles som usignert (`steps/5b-kode-review.md` «Arbeidstre-vakt (TODO 292)»). Manglende felt stopper ingenting, men logges (`wtguard=missing`).
  - Alle fire PÅKREVDE arrayer skal finnes (kan være tomme) i **full modus**; hele `fan_in`-feltet utelates i **probe-modus**. `attestations` er PÅKREVD når session-predikatet i `coordinator-runbook.md` §5b er sant og `returned` er ikke-tom (manglende nøkkel ⇒ `attest=attestations-missing`, stoppende). Er predikatet usant, er manglende nøkkel `attest=legacy` og IKKE et kontraktbrudd — se `coordinator-runbook.md` §5b.
- `evidence`: kode-revieweren leser PR-diffen via `gh`, ikke via workerens worktree-filer — `toplevel` beviser derfor kun egen cwd og merkes SVAKT. `pr_head_sha` (fra `gh pr view <pr> --json headRefOid`) er PRIMÆRT bevis og tetter stale-worktree-tech-review-funn (én PR kan bli oppdatert mellom dispatch og review). **Probe-modus (Step 0 i code-reviewer-charteret):** når prompten KUN ber om `{"ok": true}`, returneres bart `{"ok": true}` — ingen `evidence`, ingen `gh pr view`, ingen `fan_in`.
- `severity` ∈ `"BLOKKERENDE"|"VIKTIG"|"MINDRE"`, satt av kode-revieweren (synthesizeren) ut fra hele
  diff-konteksten — ALDRI kopiert fra en lens, som per kontrakt ikke leverer severity i det hele
  tatt (se «Lens-observasjon» over). Koordinatoren håndhever et mekanisk MINSTEKRAV per agent,
  `tech_review_agents[].severity_floor` i `loop.config.yaml` (`tasks/review-severity-floor.py`,
  TODO 180B, erstatter den tidligere per-agent-mappingen) — kode-revieweren kan HEVE en observasjon
  til gulvet, aldri levere et funn under det (unntak: et verifisert `floor_exempt`-funn heves ikke,
  TODO 321).
- `verdict` ∈ `"go"` (ingen BLOKKERENDE) | `"no-go"` (≥1 BLOKKERENDE). Identisk terskel som plan-review.
- `verification.review_findings` i ferdig-rapporten er implementerens **selvgransking** (§5 / `/todo-finish-worker` steg 5). `code_review.findings[]` er den **uavhengige §5b-reviewen** og er en separat rapport. Disse er to distinkte kilder.

**Revise-gate (§5b) vs. `verdict` — viktig skille:**

```
verdict = "no-go"  ⟺  minst én BLOKKERENDE  (samme som plan-review og §4)
revise-gate (§5b)  ⟺  minst én BLOKKERENDE ELLER minst én VIKTIG  (= Critical/Important)

→ Rapport med 0 BLOKKERENDE + 1 VIKTIG: verdict = "go", men revise-gate trigges (1 runde tilbake til implementer).
→ Rapport med 0 BLOKKERENDE + 0 VIKTIG (kun MINDRE / ingen funn): verdict = "go", revise-gate trigges ikke → merge.
```

`verdict` alene er ikke revise-gaten. Koordinatorens §5b-gate leser severity-arrayet direkte og sender tilbake til implementer ved ≥1 BLOKKERENDE **eller** ≥1 VIKTIG. MINDRE-funn blokkerer verken `verdict` eller revise-gaten.

## Ferdig-rapport (implementer → koordinator)

```json
{
  "report_type": "done",
  "todo_nr": "41",
  "slug": "redirect-after-login-next-flyt",
  "branch": "feat/todo-41-redirect-after-login-next-flyt",
  "pr_url": "<gh pr-url mot {{BASE_BRANCH}}>",
  "status": "implemented",
  "evidence": { "toplevel": "<ordrett output av `git rev-parse --show-toplevel`>", "branch": "<ordrett output av `git branch --show-current`>" },
  "verification": {
    "build_green": true, "type_check_green": true, "tests_passed": true,
    "e2e_outcome": "e2e_green", "web_smoke_outcome": "e2e_green",
    "security_findings": [], "review_findings": [],
    "min_diff_net": 0, "min_diff_findings": 0,
    "tdd": { "required_steps": 1,
             "pairs": [{ "step": "Steg 3", "red_commit": "<sha>", "test": "<fil> :: <testnavn>",
                        "failure": "<ordrett feillinje>", "green_commit": "<sha>" }],
             "deviations": [] }
  },
  "lessons": [
    { "topic": "workflow-process", "pattern": "…", "checklist": "…", "sources": "TODO 41" }
  ],
  "bugs_closed": [],
  "bugs_new": [],
{{SCOUT_USAGE_LINE}}  "deviations": "ingen",
  "notes": "Fritekst til koordinatoren."
}
```

- `status` ∈ `"implemented"|"blocked"|"failed"|"plan_invalid"`.
- `plan_invalid` = **planen selv holdt ikke**: en antakelse den bygger på stemmer ikke med koden
  slik den faktisk er. Skilles fra `failed` (planen var god, implementeringen strandet) og `blocked`
  (planen er god, men et steg krever eier-fullmakt). `pr_url: null`. `notes` MÅ navngi HVILKEN
  antakelse som brast og HVILKET målt funn som felte den; uten det er rapporten ugyldig, fordi den
  ber om en ny plan uten å levere fakta til den. Koordinatoren ruter den tilbake til planlegging (§5).
- `verification.tdd`: `required_steps` = antall `TDD-STEG` i planen (ikke implementerens skjønn);
  `deviations[]` = merkede steg uten rødt-par, med målt grunn. Tomt felt = «ingen», manglende felt =
  «ikke gjort». Ingen `TDD-STEG` ⇒ `{"required_steps": 0, "pairs": [], "deviations": []}`. Hele
  blokken limes også inn i PR-bodyen.
- `scout_usage`: summen av `measurement`-objektene fra scout-rapportene denne rollen dispatchet
  (`dispatches` = antall scout-oppdrag, `bytes_read` = sum av deres `bytes_read`, `findings` = sum
  av deres `findings_count`). Ingen scout brukt ⇒ `{ "dispatches": 0, "bytes_read": 0, "findings": 0 }`
  — et lovlig og ofte riktig svar. Feltet er PÅKREVD når `scout.enabled` er `true` i
  `loop.config.yaml`, og utelates helt når rollen er av; koordinatoren summerer det til
  `scout=`-tokenet i `run-log.md` (se § frittekst-notatfelt under). Feltet er PÅKREVD også i
  rapporter med `status: "blocked"`/`"failed"` — normalt `{0, 0, 0}` i disse tilfellene, siden
  arbeidet stanset før noen scout ville vært aktuell — nettopp for å lukke den vanligste stien til
  `scout=unknown` ved kilden. Forbeholdet om hva `bytes_read`
  ER og ikke er, står i § Scout-rapport.
- `evidence`: slanket sammenlignet med planner/reviewer — koordinatorens uavhengige `gh pr view`/`gh pr diff` er OFFISIELT bevis for PR-innholdet (verifiseres eksternt uansett), så implementeren siterer kun `toplevel` (egen worktree) + `branch` (riktig PR-branch). Ingen ordrett bygg-/testoutput kreves i selve rapporten.
- `topic` MÅ være en tema-mappe under `tasks/lessons/` (`ls tasks/lessons/`); passer ingen, foreslå et nytt kebab-case-navn. Carry-forwards er ikke lessons — legg dem i `notes`.
- `security_findings`/`review_findings`: kun KRITISK/HØY/Important som IKKE ble fikset (tom = alt fikset).
- `min_diff_net`/`min_diff_findings`: resultatet av `/todo-finish-worker` steg 3 (minste diff). `min_diff_net` er netto
  linjer fjernet i steget, og `min_diff_findings` er antall funn. 0/0 er gyldig. Koordinatoren kan føre dem i
  run-loggens notatfelt for å følge effekten over tid.
- `e2e_outcome` — utfallet av å kjøre den konfigurerte `{{CMD_E2E}}` (full e2e-suite). **Ingenting
  annet.** En grønn web-smoke gir ALDRI `e2e_green` for `e2e_outcome`.
- `web_smoke_outcome` — utfallet av å kjøre den konfigurerte `{{CMD_WEB_SMOKE}}` (web-smoke-gaten).
  Egen kommando, egen verdi — skrives ALDRI sammen med `e2e_outcome` fra samme steg.
- Begge feltene bruker samme fem-verdi-enum, og er BEGGE påkrevd i hver ferdig-rapport (manglende
  felt ⟹ koordinatoren skriver `e2e_blocked:missing_outcome_field` for rader som HAR en
  ferdig-rapport — aldri stille `-`):

  | Verdi | Betyr |
  |---|---|
  | `e2e_green` | kommandoen kjørte og passerte |
  | `e2e_red` | kommandoen kjørte og feilet reelt |
  | `e2e_unavailable` | verktøyet fantes ikke etter korrekt probe |
  | `e2e_blocked:<reason>` | forsøkt, blokkert — `<reason>` påkrevd |
  | `e2e_not_applicable` | gaten er ikke relevant for denne diffen |

  `<reason>` MÅ være én av: `metro_bundling | browser_binary | env_missing |
  missing_outcome_field | other`. Forbudt i `<reason>`: `|` (kolonneseparator), mellomrom, og
  norske tegn (`æ ø å`). Trenger du noe annet enn de fem — bruk `other` og skriv detaljen i
  `notes`.

  Koordinatoren avleder `degradation`-kolonnen i run-log fra BEGGE feltene sammen — se
  `run-log.md` for den fullstendige formelen (begge carve-outs).
- Implementeren skriver `lessons`/`bugs_*` som DATA. Den skriver ALDRI til `tasks/lessons*`, `tasks/followups/`, `tasks/bugs.md` eller `tasks/todo_archive.md`, og rører ikke todo-frontmatteren — det gjør koordinatoren.

## `run-log.md`s frittekst-notatfelt (kalt «felt 11» i `coordinator-runbook.md`, TODO 246)

`run-log.md` har et siste, ikke-navngitt frittekst-felt (den udokumenterte fritekstkolonnen
`coordinator-runbook.md` refererer til flere steder) som bærer nøkkel=verdi-notater koordinatoren
appender selv: `selector=<agenter>` (TODO 180A), `floor=<n> viol=<n>` (TODO 180B),
`floor_exempt=<g>:godtatt,<a>:avvist` (TODO 321),
`pipelined_from=<todo>` (§5c), `auto_decided=<rad-eier>:<antall>` (TODO 246), `attest=<verdi>`
(TODO 250A), `vblock=<ok|stale|missing|legacy|stuck>` (TODO 252, med F5s valgte V-ID i parentes:
`vblock=ok(F5:V4)`), `wtguard=<none|missing|ok|violation>` (TODO 292), og `scout=<dispatches>d/<KB>kb` (lokaliserings-workeren). Feltets EKSAKTE
nummer i forhold til spec-tabellens navngitte kolonner er omstridt (nummereringen avklares i
TODO 210, deferred) — denne setningen dokumenterer kun INNHOLDET, ikke posisjonen.

**`scout=`-tokenet.** Formen er `scout=<dispatches>d/<KB>kb`, der begge tallene er summen over ALLE
rollene som dispatchet en scout denne runden (plan-rapportens + ferdig-rapportens `scout_usage`,
inkludert fix-runder). `<KB>` er `bytes_read` delt på 1024, avrundet til nærmeste heltall. Ingen
scout brukt: `scout=0` (kortformen — ikke `scout=0d/0kb`). Tokenet hører til gruppen der FRAVÆR ER
ET KONTRAKTBRUDD så lenge `scout.enabled` er `true` i `loop.config.yaml` — nettopp fordi feltet
finnes for å måle om rollen lønner seg: en manglende `scout=` kan ikke skilles fra en runde uten
scout-bruk, og da måler serien ingenting. Er `scout.enabled` `false`, skal tokenet utelates helt.

**`scout=unknown`-sentinelen.** Brukes NÅR workeren ikke kan spørres i det hele tatt: sesjonen ble
avsluttet uten en rapport, eller rapporten har `status: "blocked"`/`"failed"` og mangler
`scout_usage` (se under — dette skal normalt ikke skje, men er den eneste lovlige veien til
`scout=unknown` når det skjer likevel). Skill BEVISST fra `scout=0` («spurt, fikk svar, ingen scout
brukt»): kollapser koordinatoren de to til samme verdi, mister serien nøyaktig det tokenet finnes
for å måle — om fravær av scout-bruk er reelt eller bare ikke-rapportert. `vblock=` og `attest=` har
begge tilsvarende sentinel-verdier (`stale`/`missing`/`legacy` osv.); `scout=unknown` er den samme
mekanismen for `scout=`.

**Ikke les `<KB>` som spart kontekst.** Det er summen av filer scouten åpnet i stedet for
oppdragsgiveren — en øvre grense, ikke en besparelse (§ Scout-rapport). Serien er brukbar som TREND
over mange runder sammenlignet med rundenes øvrige form (antall fix-runder, `plan_review_rounds`),
aldri som et regnskap per runde.

`attest=` er, sammen med `pipelined_from=`, `vblock=` og `wtguard=`, blant tokenene i registeret over hvis
FRAVÆR IKKE er et kontraktbrudd — i motsetning til `floor=`, `floor_exempt=`, `auto_decided=` og
`scout=` (sistnevnte kun når `scout.enabled` er `true`), som ALLE gjør fravær til et kontraktbrudd:

| Token | Fravær = kontraktbrudd? | Betingelse |
|---|---|---|
| `floor=` | Ja | alltid, på ikke-`health`-rader |
| `floor_exempt=` | Ja | på ikke-`health`-rader med `floor=`, skrevet etter TODO 321 |
| `auto_decided=` | Ja | alltid, på ikke-`health`-rader |
| `scout=` | Ja | kun når `scout.enabled` er `true` |
| `attest=` | Nei (`observe`) | — |
| `pipelined_from=` | Nei | — |
| `vblock=` | Nei | — |
| `wtguard=` | Nei | — |

Verdienes semantikk for `vblock=` står i `steps/5b-kode-review.md` Gate F-
seksjonen («Telemetri») — den dokumenteres KUN som enum her, slik at de to filene ikke får hver sin
definisjon som kan drifte fra hverandre. Samme
«dokumenterer INNHOLD, ikke posisjon»-forbehold gjelder: dette dokumenterer at tokenet finnes i
feltet, ikke hvilken posisjon det har i den frie teksten.
