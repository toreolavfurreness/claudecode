# v2 — agent-orchestrator

Et **parameterisert, selvstendig template** av den autonome
orkestreringsloopen: en koordinator-agent som kjører en kø av todos gjennom
planlegging → uavhengig review → implementering → uavhengig kode-review →
merge, uten at du trigger hvert steg. Destillert fra et live-prosjekt og gjort
prosjekt-agnostisk via `loop.config.yaml` + `/setup`.

> Bakgrunn og designresonnement: [`docs/PORTING.md`](docs/PORTING.md).

---

## Hva er nytt vs. v1

| | v1 — sekvensiell human-orchestrator | v2 — agent-orchestrator |
|---|---|---|
| **Orkestrator** | Mennesket, én kommando om gangen | Koordinator-agent, autonomt |
| **Plan-godkjenning** | Du godkjenner hver plan | Uavhengig reviewer-agent; du godkjenner per *release* |
| **Kode-review** | Punktvis `@reviewer` | Uavhengig kode-reviewer på PR-diff, revise-gate (maks 2 runder) |
| **Todos** | Monolittisk `tasks/todo.md` | Én-fil-per-todo (ingen merge-konflikt-felle) |
| **Workers** | — | Planner/reviewer/implementer/code-reviewer i isolerte worktrees |
| **Delt state** | Du skriver alt | Koordinator er eneste skriver (lessons/arkiv/bugs/run-log) |
| **Telemetri** | — | Run-logg + periodisk helsesjekk + release-rådgiver |
| **Menneske-i-loopen** | Hvert steg | Kun pausepunkter (teknisk risiko, ikke-konvergerende review, rød helsesjekk …) |

v2 er ikke «v1 fast» — det er en annen kontrollmodell. Velg bevisst (se rot-README).

---

## Forutsetninger

v2 sitter oppå et todo-/workflow-stillas og en plattform. Før loopen virker:

- **Plattform:** Claude Code med custom subagents (`model`/`effort`/`isolation: worktree`), miljø-arv for `gh`-auth, og agent-registeret. git + `gh`.
- **Stillas:** én-fil-per-todo + workflow-commands + `tasks/lessons.md` + `CLAUDE.md` + konvensjons-docs + blokkerende CI. v2 leverer disse i `templates/` og `scaffolding/`.
- **Valgfritt (degraderer grasiøst hvis fraværende):** Superpowers-plugin (`/systematic-debugging` m.fl.), e2e-verktøy (Playwright MCP), tech-MCP (DB e.l.).

Mangler stillaset i et eksisterende prosjekt? Se [`MIGRATION.md`](MIGRATION.md).

---

## Mappestruktur

```
v2-agent-orchestrator/
├── README.md                  Denne filen
├── MIGRATION.md               v1→v2-migrering av et eksisterende prosjekt
├── loop.config.example.yaml   Den ENESTE filen du fyller (kopier → loop.config.yaml)
├── setup.md                   /setup — kompilerer config inn i kit-et (token-tabell + skript)
├── docs/
│   └── PORTING.md             Blueprinten (universal vs. config)
├── templates/                 KILDE — tokeniserte filer; /setup renderer disse
│   ├── .claude/agents/        PROJECT_NAME-{planner,reviewer,implementer,code-reviewer}.md
│   ├── .claude/commands/      run-loop, todo-finish-worker, loop-health-check,
│   │                          todo-plan(+review), todo-execute, todo-done, start, status, endsession
│   ├── docs/                  orchestration-loop.md + superpowers/loop/{coordinator-runbook,report-schema,run-log}.md
│   └── tasks/                 todos/README.md, bugs/inbox/README.md
├── examples/
│   └── tech-review-agents/    rls-auditor / security-reviewer (pluggbare EKSEMPLER)
└── scaffolding/
    ├── githooks/pre-push      Produksjons-branch-beskyttelse
    └── github-workflows/ci.yml Blokkerende CI-port
```

**Kilde vs. generert:** `templates/` (med `{{TOKEN}}`) er kilden. `/setup`
skriver de *genererte* filene til prosjektets `.claude/`, `docs/`, `tasks/`.
Hver generert fil bærer en «GENERERT — ikke rediger her»-header. Du kan alltid
diffe template mot generert.

---

## Ta i bruk (nytt prosjekt)

1. **Kopier** `v2-agent-orchestrator/` inn i prosjektroten (behold mappen — den er kilden).
2. **Kopier** `setup.md` → `.claude/commands/setup.md` (så `/setup` blir kjørbar).
3. **Fyll config:** `cp v2-agent-orchestrator/loop.config.example.yaml v2-agent-orchestrator/loop.config.yaml` og rediger alle nøkler.
4. **Kjør `/setup`.** Den validerer config, renamer agentene til `<project>-*`, substituerer tokens, og skriver kit-et til prosjektets stier. Stopper hardt hvis en nøkkel mangler eller et token gjenstår.
5. **Tech-review-agenter:** kopier prosjektets egne fra `examples/` til `.claude/agents/`, registrer i `loop.config` under `tech_review_agents`, kjør `/setup` på nytt. Ingen DB/auth? Sett `tech_review_agents: []`.
6. **Stillas:** kopier `scaffolding/` (pre-push, CI) hvis prosjektet mangler det; tilpass branch-navn/kommandoer.
7. **Restart + valider:** start en **fersk** sesjon (agent-registeret lastes ved sesjonsstart), kjør agent-proben, så `/run-loop once` på én liten lavrisiko-todo.

> **Hvorfor fersk sesjon?** Claude Code snapshotter agent-registeret ved
> sesjonsstart. De nygenererte `<project>-*`-agentene er ikke synlige i sesjonen
> som kjørte `/setup`. Dette er den vanligste oppstarts-fellen — proben i
> `run-loop.md` fanger den.

---

## Parameteriserings-mekanismen (ren A — én mekanisme)

`loop.config.yaml` er kilden; `/setup` er kompilatoren. **Ingen runtime
config-read.** Begrunnelsen:

- Plattformen tvinger setup-tid for det viktigste: agent-navn (`subagent_type`
  må matche en *registrert* streng) og `model:`/`effort:` (leses ved
  sesjonsstart, ikke av agenten). Et rent «les config ved runtime» er *umulig* der.
- Når setup-tid er påkrevd for kjernen, gir en runtime-mekanisme for resten to
  mekanismer + arver «leste agenten den egentlig?»-risikoen (Tier-3) som hele
  canary-mønsteret ble bygget for å avdekke. Å legge «rør aldri prod» bak
  «vennligst les config» er selvmotsigende.

Endrer du config: kjør `/setup` på nytt. «Rekompilering» er eksplisitt og sporbar.

Substitusjonen er **deterministisk** (sed/python over en eksplisitt
token→verdi-map), med en validerings-gate som feiler høyt på gjenværende
`{{...}}` eller manglende nøkler. Se [`setup.md`](setup.md).

---

## Kjent fremtidig herding (ikke gjort ennå)

Ærlig liste så template-et ikke later som det er komplett (utdypet i
[`docs/PORTING.md §7`](docs/PORTING.md)):

- **Worktree-backstop** — periodisk prune av orphans (per-todo-rydding finnes).
- **Kostnadstak + synlighet** — 3 dype + 1 rask modell-kall per todo; ingen budsjett-grense.
- **Self-mod-gate** — todos som endrer loopens egen maskineri, `loop.config` eller `/setup` bør tvinges til menneskelig review.
- **Secret-scan i CI** — for autonom kodegenerering.
- **Fase 1 (Workflow-port)** — fra live-sesjon til deterministisk bakgrunns-script m/resume.
- **Cloud/headless-kjøring** — krever Superpowers/MCP tilgjengelig der (preflight + degradering finnes).
- **`/setup`-robusthet** — krever `python3` + `pyyaml`; validerer config-*nøkler*, ikke at *verdiene* er meningsfulle.
