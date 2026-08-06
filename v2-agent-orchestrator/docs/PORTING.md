# PORTING — blueprinten bak v2

**Formål:** tegningen for hvorfor v2 er bygget som det er — skillet mellom det
**universelle** (maskineriet, transporterbart) og det **prosjektspesifikke**
(config). Dette dokumentet er konseptuelt; den operative oppskriften ligger i
[`../README.md`](../README.md) (nytt prosjekt) og [`../MIGRATION.md`](../MIGRATION.md)
(eksisterende v1-prosjekt).

**Kjerneinnsikt:** å kopiere filene replikerer *ikke* systemet. Loopen var
opprinnelig tett bundet til ett prosjekt (én stack, miljø-IDer, ett språk,
`npm`-kommandoer, én RLS-auditor). Riktig porting = **skill det universelle fra
det prosjektspesifikke**, og eksternalisér sistnevnte til én `loop.config.yaml`.
Da blir et nytt prosjekt «fyll ut config + kjør `/setup`», ikke «skriv om fire
charter».

---

## 1. Arkitektur — det universelle (transporterbart konsept)

Uavhengig av stack:

- **Single-writer-koordinator** + flyktige workers, hver i egen worktree (`isolation: worktree`).
- **Fire worker-roller:** planner (dyp modell) → uavhengig reviewer (dyp modell) → implementer (rask modell) → uavhengig kode-reviewer (dyp modell).
- **Strukturerte rapport-kontrakter** (plan / review / code_review / done) som skjøten mellom koordinator og workers.
- **Én-fil-per-todo + frontmatter-kø** — ingen aggregert indeks (fjerner merge-fella). Status leses on-demand via glob.
- **Pausepunkter** = menneske-i-loopen: teknisk risiko, brainstorm-påkrevd, feil, ikke-konvergerende review, aldri til produksjons-branchen.
- **Uavhengig > selvgransking** på både plan og kode (egne agenter, fersk kontekst).
- **Grooming** med dobbel gating (`status: deferred` + `tags: [forslag]`) — foreslår, mennesket triagerer.
- **Run-logg** (telemetri) + **helsesjekk/release-rådgiver** (periodisk).
- Menneskets review flyttet fra per-plan → per-release.

Dette laget endrer seg ikke mellom prosjekter. Det er det v2 bevarer.

---

## 2. `loop.config.yaml` — det som MÅ eksternaliseres

Alt prosjektspesifikt samles i ÉN fil som `/setup` kompilerer inn i kit-et.
Se [`../loop.config.example.yaml`](../loop.config.example.yaml) for den
fullstendige, kommenterte malen og [`../setup.md`](../setup.md) for token-mappingen.

| Config-nøkkel | Hva | Hvor det var hardkodet |
|---|---|---|
| `project_name` | → agent-navn `<project>-planner/reviewer/implementer/code-reviewer` | Agent-filnavn + `subagent_type`-kall |
| `models` | tier per rolle (planner/reviewer/code-reviewer = dyp; implementer = rask) + `effort` | Charter-frontmatter (`model:`/`effort:`) |
| `environments` | dev-ID, prod-ID | Tier-1-invarianter i alle charter |
| `branch_strategy` | base-branch for PR, prod/«aldri rør»-branch, release-target | `gh pr create --base`, runbook |
| `verification_commands` | `build` / `type_check` / `lint` / `test` / `e2e` | `todo-finish-worker.md`, helsesjekk |
| `tier1_invariants` | språk-regel, sikkerhetsregler | Hver charters «Ufravikelige invarianter» |
| `tech_review_agents` | hvilke domene-reviewere code-reviewer dispatcher (pluggbare) | code-reviewer-charteret |
| `canary_source` | fil planner-canary leses fra (bevis på fil-lesing) | Runbook §3 |
| `lessons_topics` | gyldige tema-filnavn | `report-schema.md` + charterne |
| `pause_triggers` | hva som teller som teknisk risiko | Pausepunkt-lister |
| `release` | release-kommando, N-merges helsesjekk-intervall | Runbook §6c |

**Tommelfingerregel:** nevner en verdi en stack, et miljø-ID, en produksjons-branch
eller et språk — den hører i `loop.config`, ikke i maskineriet.

---

## 3. Filinventar — kit-et (`templates/`)

`/setup` renderer alt under `templates/` til prosjektets faktiske stier.

| Fil | Klasse |
|---|---|
| `.claude/agents/PROJECT_NAME-{planner,reviewer,implementer,code-reviewer,verifier}.md` | **Universal struktur + config** (verifier er pluggbar — kun relevant hvis registrert i `tech_review_agents`) |
| `.claude/commands/run-loop.md` | **Universal + config** |
| `.claude/commands/todo-finish-worker.md` | **Universal + config** |
| `.claude/commands/loop-health-check.md` | **Universal + config** |
| `.claude/commands/{todo-plan,todo-plan-review,todo-execute,todo-done,start,status,endsession}.md` | **Prereq-stillas + config** |
| `docs/superpowers/loop/coordinator-runbook.md` | **Universal + config** (kø-skript universelt) |
| `docs/superpowers/loop/report-schema.md` | **Universal** (kun `lessons_topics` fra config) |
| `docs/superpowers/loop/run-log.md` | **Universal** (telemetri-format; tom logg ved generering) |
| `docs/orchestration-loop.md` | **Universal + config** (operatør-guide) |
| `docs/hotfix-runbook.md` | **Universal + config** (protokoll for kode merget utenfor loop-sesjonen) |
| `tasks/todos/README.md`, `tasks/bugs/inbox/README.md` | **Prereq-stillas** |
| `examples/tech-review-agents/*` | **Pluggbar** — leveres per prosjekt bak code-reviewer-grensesnittet |

---

## 4. Prerequisite-stillas (må finnes FØR loopen virker)

Loopen sitter oppå et todo-/workflow-system. v2 leverer dette i `templates/` og
`scaffolding/`, men prosjektet må ha (eller få):

- **Én-fil-per-todo:** `tasks/todos/todo-NN-slug.md` + frontmatter-skjema + `tasks/todo_archive.md`.
- **Workflow-commands:** `todo-plan`, `todo-plan-review`, `todo-execute` (charterne peker hit).
- **Lessons:** `tasks/lessons.md` (indeks) + `tasks/lessons/<tema>.md`.
- **`CLAUDE.md`** (charterne sier «les og adlyd»).
- **Konvensjons-docs:** naming-conventions, (loading-patterns, data-model hvis relevant).
- **CI som blokkerende port** på PR (se `scaffolding/`).

---

## 5. Eksterne / plattform-avhengigheter

| Avhengighet | Universal eller tech-spesifikk |
|---|---|
| **Claude Code-plattform** (custom subagents med `model`/`effort`/`isolation: worktree`, miljø-arv for `gh`-auth, agent-registeret) | Universal — kreves. Annet runtime må re-implementere subagent-isolasjon + modell-ruting |
| **Superpowers-plugin** (`/systematic-debugging` m.fl. via `todo-execute`) | Universal for denne loopen (grasiøs degradering finnes) |
| **git + `gh` (GitHub)** | Universal her; GitLab/annet krever tilpasning |
| E2E-verktøy (Playwright MCP) / DB-MCP | Tech-spesifikke (web-/DB-prosjekter) |

---

## 6. Porting-sjekkliste

1. **Stillas på plass?** Verifiser én-fil-per-todo + workflow-commands + lessons + CLAUDE.md + konvensjons-docs + CI. Hvis ikke: port disse først (se README/MIGRATION).
2. **Fyll `loop.config.yaml`** (§2).
3. **Kjør `/setup`** — renderer `templates/` → prosjektets stier, renamer agentene, validerer at ingen tokens gjenstår.
4. **Lever tech-review-agentene** (§3 pluggbar) — kopier fra `examples/`, tilpass, registrer i config, kjør `/setup` på nytt.
5. **Plattform-deps** (§5) — Claude Code + Superpowers + git/`gh` + evt. tech-MCP.
6. **Valider:** start fersk sesjon, kjør `/run-loop once` på én liten lavrisiko-todo, bekreft planner→reviewer→implementer→code-review→merge + at workers ikke rører delt state + at modell-pinning virker. Skriv et valideringsnotat.
7. **Backlog-hygiene:** sett betingede/post-MVP-todos `deferred`, brainstorm-gate design-tunge.

---

## 7. Kjent fremtidig herding (ikke gjort ennå)

Dokumentert ærlig så template-et ikke later som det er komplett:

- **Worktree-backstop** — periodisk prune av orphans; per-todo-rydding finnes.
- **Kostnadstak + synlighet** — 3 dype + 1 rask modell-kall per todo; ingen budsjett-grense ennå.
- **Self-mod-gate** — todos som endrer loopens egen maskineri (eller `loop.config`/`/setup`) bør tvinges til menneskelig review.
- **Secret-scan i CI** — for autonom kodegenerering.
- **Fase 1 (Workflow-port)** — fra live-sesjon til deterministisk bakgrunns-script m/resume.
- **Cloud/headless-kjøring** — krever Superpowers/MCP tilgjengelig der (preflight + degradering finnes).
- **`/setup`-robusthet** — krever `python3` + `pyyaml`; ingen pre-validering av at config-*verdiene* (ikke bare nøklene) er meningsfulle.

---

**Oppsummert:** kit-et i §3 + stillaset i §4 + `loop.config` i §2 er det som skal
til. Det egentlige template-arbeidet er å parameterisere §3-filene mot §2-config-en
via `/setup`, så replikering blir «fyll config + kompiler», ikke «skriv om».
Konseptet i §1 er det som overlever uansett stack.
