# Portregler: v3-agent-orchestrator → v3-copilot-agent-orchestrator

Reglene for å porte en endring i `v3-agent-orchestrator/` (Claude Code) til
`v3-copilot-agent-orchestrator/` (GitHub Copilot-harnessen). De ble brukt til den første porten
(v3.7) og gjelder for hver senere endring. Fila ligger med vilje UTENFOR Copilot-mappa, siden den
nevner Claude.

**Arbeidsflyt for én port:**
1. `bash .github/kit-port/check-drift.sh` viser commitene og filene som er endret siden forrige synk.
2. For hver commit: `git show <sha> -- v3-agent-orchestrator/` og port endringen til tilsvarende fil
   (stikartet i §1). Ta med intensjonen, ikke bare teksten: en ny regel i en stegfil skal stå i
   Copilot-stegfila, men med Copilot-vokabularet i §3–§9.
3. Er endringen plattformnøytral (Python-skript, tester, kø-logikk), kan den ofte tas over nesten
   ordrett. Sjekk likevel ordvakta (§0) og stiene.
4. `bash .github/kit-port/validate-copilot-kit.sh` skal være grønn.
5. Sett `synket-mot` i `v3-copilot-agent-orchestrator/KIT-SYNC` til den siste porterte commiten, i
   samme PR. Kan en endring ikke portes, skriv hvorfor i `docs/PORTING-DECISIONS.md` og oppdater
   `synket-mot` likevel.

Kitet kjøres i **VS Code med Copilot-harnessen** (samme runtime som Copilot CLI / Copilot SDK).
Språk: norsk bokmål, samme stil og tetthet som originalen. Behold all logikk, alle regler, gater,
nivå A/B-beslutninger, tall og herding; endre bare det plattformen krever.

## 0. ABSOLUTT KRAV: ordet «Claude» skal ikke finnes i målmappen
- Ingen «Claude», «Claude Code», «claude-…»-modell-ID-er, «Anthropic», «Opus», «Sonnet», «Haiku»,
  ingen lenker til claude.com/claude.ai/anthropic, ingen `.claude/`-stier, ingen `CLAUDE_*`-env.
- Ingen omtale av at kitet stammer fra en annen plattform. Ikke skriv «i motsetning til …»,
  «porten», «originalen», «kilden». Kitet står på egne ben og beskriver Copilot som den naturlige
  plattformen. (Unntak: `docs/PORTING-DECISIONS.md`, se §9 — men heller ikke den nevner Claude.)
- `superpowers` (navn på en tredjeparts plugin) fjernes også: «Superpowers-kommandoer» →
  «debug-/verifiserings-skills» (se §6).
- Lenker til `toreolavfurreness/claudecode` (repo-navnet) er OK å beholde der de peker på
  MIGRATION/historikk, men foretrekk relative lenker innen mappen. Repo-navnet er ikke et problem.
- Etter arbeidet: ordvakta i `validate-copilot-kit.sh` skal være grønn (eneste unntak er repo-URL-en
  `github.com/toreolavfurreness/claudecode`).

## 1. Stikart

| v3-agent-orchestrator | v3-copilot-agent-orchestrator |
|---|---|
| `templates/.claude/agents/<x>.md` | `templates/.github/agents/<x>.agent.md` |
| `templates/.claude/commands/<x>.md` | `templates/.github/skills/<x>/SKILL.md` |
| `templates/.claude/hooks/<x>` | `templates/.github/hooks/scripts/<x>` |
| `templates/.claude/scripts/bootstrap-worktree.sh` | `templates/scripts/bootstrap-worktree.sh` |
| `templates/docs/superpowers/loop/` | `templates/docs/loop/` |
| `templates/CLAUDE.md` | `templates/AGENTS.md` |
| `docs/PORTING.md` | `docs/ARCHITECTURE.md` |
| `.claude/worktrees/`, `.claude/worktree-rescue/` | `.loop-worktrees/`, `.loop-worktree-rescue/` |
| `.claude/agent-memory/` | `tasks/agent-memory/` |
| `.claude/settings.json` (hooks) | `.github/hooks/loop-guards.json` (generert av `/setup`) |
| `$CLAUDE_PROJECT_DIR` | `$LOOP_PROJECT_DIR` (fallback `git rev-parse --show-toplevel`) |

**Finnes ikke i Copilot-kitet** (endringer i disse portes ikke, men vurder om intensjonen skal inn
et annet sted): `guard-reviewer-readonly.sh`, `test-guard-reviewer-readonly.sh`,
`reviewer-readonly.contract` (erstattet av `scripts/readonly-check.sh`) og
`sessionstart-checkpoint.sh` (erstattet av regelen i steg 0c).

**Konvensjoner innført i den første porten:**
- `WT=$(bash scripts/bootstrap-worktree.sh <id> <rolle>)` lager `.loop-worktrees/<rolle>-<id>` på
  branch `loop/<rolle>-<id>`; uten argumenter er skriptet bootstrap i gjeldende worktree.
- Base-sha noteres med `git -C "$WT" rev-parse HEAD` rett før dispatch;
  `bash scripts/readonly-check.sh "$WT" <base-sha>` etter hver read-only-dispatch (exit 1/2 = brudd).
- Navngitt sweep: `bash tasks/worktree-sweep.sh <rolle>-<id>`.
- Dispatch-argumentene kompileres inn av `/setup`: `{{DISPATCH_ARGS_<ROLLE>}}`,
  `{{DEEP_DISPATCH_ARGS}}` (gir `model: "…"` + eventuelt `reasoning_effort: "…"`). Les aldri
  `loop.config.yaml` under kjøring.
- Rapporter har `evidence.worktree`, og `evidence.toplevel` må være lik den. Rollehukommelse
  foreslås som `memory_candidates`; koordinatoren skriver `tasks/agent-memory/`.
- Kost: `credits=<n>` i run-log-raden (AI credits), `IKKE MÅLT` når tallet mangler.
  `measure-cost.py --main-credits` erstatter `--main-usd`.
- MCP-basert e2e kjennes på ordet «MCP» i `verification_commands.e2e`; verktøy heter
  `<server>/<verktøy>`.

## 2. Agentfiler (`templates/.github/agents/*.agent.md`) — Copilot custom agent-format
Frontmatter som Copilot støtter: `name`, `description` (påkrevd), `tools` (YAML-liste), `model`
(streng ELLER prioritert liste), `user-invocable`, `disable-model-invocation`,
`include-custom-instructions`, `target`. Det finnes IKKE: `effort`, `isolation`, `memory`,
`disallowedTools`.
Mal for workers:
```yaml
---
name: {{PROJECT_NAME}}-planner
description: …uendret…
model: {{MODEL_PLANNER}}            # rendres av /setup til en YAML-liste: ["A", "B"]
tools: [read, search, execute, edit{{SCOUT_AGENT_TOOL}}]
user-invocable: false               # workers dispatches av koordinatoren, ikke fra plukkeren
include-custom-instructions: true   # ellers får subagenten IKKE AGENTS.md
---
```
Verktøy-aliaser (Copilot): `read` (lese filer), `search` (grep/glob), `execute` (shell),
`edit` (opprette/endre filer), `agent` (kalle andre custom agents som subagent), `web`, `todo`.
- Read-only-roller (reviewer, code-reviewer, scout, tech-review-agenter): `tools: [read, search, execute]`
  (+ `agent` for code-reviewer hvis den dispatcher tech-review-agenter). ALDRI `edit`.
  Copilot håndhever verktøylisten: et verktøy som ikke står der, finnes ikke for agenten.
- `{{SCOUT_AGENT_TOOL}}` rendres til `, agent` når scout er på, ellers tom.
- `{{MEMORY_X}}`-tokens i frontmatter fjernes. Rollehukommelse blir en vanlig fil (se §7).
- Tech-review-agent-navn som `Agent(a, b)` i tools-linja → `agent` i tools + navnelista i brødteksten.

## 3. Dispatch-vokabular (koordinator → worker)
| v3-begrep | Copilot |
|---|---|
| `Agent`-verktøyet med `subagent_type: X` | `task`-verktøyet med `agent_type: "X"` |
| `model:` i Agent-kallet | `model:` i `task`-kallet (modell fra config, se §8) |
| effort i frontmatter | valgfritt `reasoning_effort:` i `task`-kallet, fra `models.<rolle>_effort` hvis satt |
| `run_in_background: true` | `mode: "background"`; resultat hentes med `read_agent` |
| synkron dispatch | `mode: "sync"` |
| `SendMessage` til en worker | `write_agent(agent_id=…, message=…)` — virker BARE mens workeren fortsatt kjører (bakgrunnsmodus). En worker som har levert rapport og avsluttet, kan IKKE vekkes: dispatch en FERSK `task` for samme rolle med forrige rapport + funnene + worktree-stien i prompten. Skriv reglene så de er riktige for begge tilfeller; standard er fersk dispatch. |
| «Agent type not found» | `Unknown agent_type: X` |
| agent-registeret snapshottes ved sesjonsstart | samme i Copilot: nye/endrede `.agent.md` krever ny sesjon |
| `TaskCreate`/todo-verktøy | `todo` |
| `/compact`, auto-komprimering | Copilot komprimerer også kontekst (`/compact`, auto) |
| hovedsesjonen | koordinator-sesjonen (Copilot-sesjon i VS Code, Session Target = Copilot) |
| verktøynavn `Read/Grep/Glob/Bash/Write/Edit/MultiEdit` i prosa | `read/search/execute/edit` (eller beskriv handlingen) |

## 4. Worktree-isolasjon (VIKTIG arkitekturendring)
Copilot har INGEN `isolation: worktree` per subagent: en `task`-subagent deler filsystem og
arbeidskatalog med koordinatoren (målt). Derfor:
- Koordinatoren lager worktree FØR dispatch: `bash scripts/bootstrap-worktree.sh <todo-nr> <rolle>`
  (lager `.loop-worktrees/<rolle>-<todo-nr>` på en egen branch fra `origin/<base>`, skriver stien
  til stdout). Stien sendes i prompten som `WORKTREE: <sti>`.
- Hver worker sitt Steg 0: `cd "<WORKTREE>"` og verifiser `git rev-parse --show-toplevel` == WORKTREE;
  ALLE kommandoer og fil-endringer skjer der. Avvik → avbryt med feil-rapport.
- Scout har ingen egen worktree: den kjører i oppdragsgiverens WORKTREE (gis i prompten).
- Read-only-roller får også egen worktree (billig, og gjør read-only-sjekken mulig, §5).
- Rydding: eksisterende `worktree-sweep.sh` / `worktree-landed.sh` / steg 0b/6d gjelder
  `.loop-worktrees/`. Stinavn `.claude/worktrees/agent-*` i tester → `.loop-worktrees/<rolle>-<nr>`.

## 5. Hooks (`templates/.github/hooks/`)
Copilot-hooks konfigureres i `.github/hooks/*.json` (versjon 1). /setup GENERERER
`.github/hooks/loop-guards.json` (kit-eid, overskrives — ingen merge med prosjektets egne filer;
prosjektet legger egne hooks i andre filer i samme mappe). Format:
```json
{ "version": 1,
  "hooks": {
    "preToolUse": [ { "type": "command", "bash": "bash .github/hooks/scripts/guard-main-merge.sh",
                      "cwd": ".", "timeoutSec": 30 } ] } }
```
Hendelser (camelCase): `sessionStart` (input: sessionId, timestamp, cwd, source: startup|resume|new,
initialPrompt), `preToolUse` (sessionId, timestamp, cwd, toolName, toolArgs), `postToolUse`,
`preCompact` (sessionId, timestamp, cwd, transcriptPath, trigger: manual|auto, customInstructions —
kun varsel, kan ikke påvirke), `subagentStart`/`subagentStop` (agentName, agentType, agentId),
`agentStop`, `sessionEnd`.
- `toolArgs` kan komme som JSON-STRENG eller objekt. Parse robust i jq:
  `.toolArgs | if type=="string" then (fromjson? // {}) else (. // {}) end`.
- Copilot-verktøynavn i payload: `bash` (args.command), `task` (args.agent_type, args.model,
  args.prompt, args.mode), `edit`/`create`/`apply_patch`/`str_replace_editor` (filsti i
  args.path — les `.path // .file_path // .filePath`), `view`, `grep`, `glob`.
- Blokkering i `preToolUse`: skriv `{"permissionDecision":"deny","permissionDecisionReason":"…"}`
  på stdout og `exit 0`. (Exit 2 eller krasj blokkerer også — fail-closed.) Timeout er fail-OPEN.
- `sessionStart`/`postToolUse` kan injisere kontekst: stdout `{"additionalContext":"…"}`.
- Prosjektrot i skript: `LOOP_PROJECT_DIR="${LOOP_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"`.
- preToolUse-payloaden har INGEN agent-identitet (hvilken subagent kaller). Derfor er
  `guard-reviewer-readonly` fjernet. Erstatning (dokumenteres der den gamle vakta ble nevnt):
  (1) read-only-rollene har ikke `edit` i `tools` (håndhevet av Copilot), (2) etter hver
  read-only-dispatch kjører koordinatoren `bash scripts/readonly-check.sh <WORKTREE> <base-sha>`
  som feiler hvis `git status --porcelain` ikke er tom eller HEAD har flyttet seg → rapporten
  forkastes, nivå A. Config-nøkkelen
  `hooks.reviewer_readonly_guard` fjernes; `/setup` avviser den som ukjent nøkkel med en melding
  om at vakta er erstattet av `readonly-check.sh`.
- `sessionstart-checkpoint.sh` er fjernet: Copilot har ingen sessionStart-kilde «compact».
  Sjekkpunkt-mekanismen (steg 0c) beholdes, men gjenopplesing etter komprimering blir en regel i
  koordinatorens runbook («les sjekkpunktfila før hvert steg / når du ikke husker tilstanden»).
  `precompact-checkpoint.sh` (logger ferskhet ved `preCompact`) beholdes, portert.
- `guard-fix-round-model.sh`: preToolUse, filtrer `toolName == "task"`, les agent_type/model/prompt
  fra toolArgs.
- `guard-main-merge.sh`: preToolUse, filtrer `toolName == "bash"`, les `command`.
- `typecheck-on-edit.sh`: postToolUse på edit/create/apply_patch.
- `session-start-lint.sh`: sessionStart.
- Testharnessene (`test-*.sh`) må mates med Copilot-payloads (camelCase, toolName/toolArgs) og
  forvente Copilot-utdata (permissionDecision deny). Alle tester skal KJØRES og gi `AVVIK: 0`.

## 6. Skills (`templates/.github/skills/<navn>/SKILL.md`) — tidligere slash-kommandoer
Frontmatter:
```yaml
---
name: run-loop                      # = mappenavn, kun [a-z0-9-]
description: "…(fra gammel description)…"
argument-hint: "tomt | todo-nr | once"   # hvis kommandoen tok argumenter
disable-model-invocation: true      # kjøres bare når brukeren skriver /run-loop
---
```
Kalles som `/run-loop` i Copilot-chatten (som før). `$ARGUMENTS` finnes ikke: skriv «argumentet
brukeren ga etter `/run-loop`». Debug-/verifiseringsflyt: der v3 krever `/systematic-debugging` og
`/verification-before-completion` (Superpowers), bruk skills med samme navn under
`.github/skills/` HVIS de finnes i prosjektet, ellers den innebygde fallback-beskrivelsen som
allerede står i teksten (grasiøs degradering). Preflight sjekker om mappene finnes.

## 7. Rollehukommelse (tidligere `memory:`-frontmatter)
Copilot har ingen agent-minne-frontmatter. `agent_memory`-config beholdes: for roller med minne
på seedes `tasks/agent-memory/<agent>/MEMORY.md`; agentens Steg 0 sier «les
`tasks/agent-memory/<agent>/MEMORY.md` hvis den finnes»; workeren foreslår nye linjer i
rapporten (`memory_candidates`), og KOORDINATOREN skriver fila (single-writer). Ingen
bruker-/prosjekt-scope-forskjell lenger: bare prosjekt-scope (fila sjekkes inn). Andre scope-verdier
avvises av /setup med forklaring.

## 8. Modeller (`loop.config.yaml` → `models:`)
- Hver rolle tar en LISTE av modellnavn i prioritert rekkefølge (Copilot prøver neste hvis den
  første ikke er tilgjengelig). En enkelt streng godtas og gjøres om til liste.
- Eksempelfila bruker plassholdere `<DYP_MODELL>`, `<KODE_MODELL>`, `<BILLIG_MODELL>` med en
  kommentar om hva rollen krever (dyp: lange resonnement / finne feil i andres arbeid; kode:
  følge en godkjent plan med mange verktøykall; billig: bare lokalisering). Kommentar: velg
  modellene fra Copilot-modellvelgeren / `/model`, bruk eksakte navn; vurder en ANNEN
  modellfamilie for reviewer/code-reviewer enn for planner/implementer (uavhengig blikk).
- `/setup` STOPPER hvis en verdi inneholder `<` eller `>` (plassholder igjen).
- `*_effort` er valgfrie (low|medium|high|xhigh); sendes som `reasoning_effort` i `task`-kallet.
- Modellnavn i hooks/tester/eksempler: bruk nøytrale testverdier som `deep-model-a`,
  `code-model-b`, `cheap-model-c`. Visningsstreng `display` utledes som før.

## 9. Kostnad (`tasks/measure-cost.py`, `measure_cost_html.py`, retro-tall)
Copilot fakturerer i AI credits. `assistant.usage`-hendelser (model, inputTokens, outputTokens,
cost=premium-multiplikator, + cache-felt) er FLYKTIGE og lagres normalt ikke i
`~/.copilot/session-state/<sessionId>/events.jsonl`. Totaler per sesjon vises med `/usage`
(tokens og AI credits per modell). Ny modell for skriptet:
- Les `~/.copilot/session-state/<sid>/events.jsonl` (eller `$COPILOT_HOME/session-state/…`) og summer
  `assistant.usage`-linjer HVIS de finnes (tolerant parsing, ukjente felt ignoreres).
- Ellers: godta manuelle tall: `--credits <n>` (fra `/usage`) per sesjon / per todo, lagret i
  run-loggen. Mangler begge → `IKKE MÅLT` (aldri 0, aldri gjetting).
- Kostnadsbremsen (`--brake`) virker på AI credits når tall finnes; uten tall: varsle «IKKE MÅLT»
  og la nivå-A-regelen for manglende data gjelde (som v3 allerede gjør for manglende data).
- Fjern Anthropic-priser og `cache_creation`-vekting som ikke finnes i Copilot.
- `CLAUDE_CODE_SESSION_ID` → sesjons-ID fra hook-payload / `COPILOT_SESSION_ID` hvis satt, ellers
  argument `--session <id>`.

## 10. Diverse
- `docs/PORTING.md` skrives om til `docs/ARCHITECTURE.md`-aktig innhold (universelt vs. config) for
  Copilot; nevner ikke annen plattform. `docs/PORTING-DECISIONS.md` (ny) forklarer Copilot-valgene
  (worktree via skript, read-only-sjekk, write_agent vs fersk dispatch, kostnad, ingen post-compact
  hook, modellister) som egne begrunnelser — uten å nevne Claude.
- `/setup` = skill `.github/skills/setup/SKILL.md` (rot-`setup.md` holdes byte-lik med den).
- `.gitignore`-linjer: `.loop-worktrees/`, `.loop-worktree-rescue/`, `tasks/.loop-state/` osv.
- Integrasjonsbranch/`gh`-bruk er uendret (GitHub).
- MCP: prosjektets `.mcp.json` i repo-roten (Copilot-format). E2E-probe med `mcp__`-prefiks i
  v3 → MCP-verktøynavn i Copilot er `<server>/<verktøy>` (f.eks. `playwright/browser_navigate`).
- Når du er usikker på en Copilot-detalj som ikke står her: velg den konservative løsningen,
  og merk det med `UVERIFISERT:` i teksten i stedet for å gjette stille.
