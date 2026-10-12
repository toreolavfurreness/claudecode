# ARCHITECTURE — det universelle og det prosjektspesifikke

**Formål:** tegningen bak kitet. Den viser skillet mellom det **universelle** (maskineriet, likt i
alle prosjekter) og det **prosjektspesifikke** (config). Dokumentet er konseptuelt. Den operative
oppskriften står i [`../README.md`](../README.md) (nytt prosjekt) og
[`../MIGRATION.md`](../MIGRATION.md) (eksisterende prosjekt). Hvorfor kitet er bygget som det er
på GitHub Copilot, står i [`PORTING-DECISIONS.md`](PORTING-DECISIONS.md).

**Kjerneinnsikt:** å kopiere filene replikerer *ikke* systemet. Loopen var opprinnelig tett bundet
til ett prosjekt (én stack, miljø-ID-er, ett språk, `npm`-kommandoer, én RLS-auditor). Riktig
oppsett er å **skille det universelle fra det prosjektspesifikke** og samle det siste i én
`loop.config.yaml`. Da blir et nytt prosjekt «fyll ut config og kjør `/setup`», ikke «skriv om fire
charter».

Kitet gjør tre grep for å håndheve reglene, ikke bare beskrive dem:

1. **Vakter i stedet for prosa.** «Rør aldri prod-branchen» og «implementeren kjører på modellen fra
   config» er Copilot-hooks med regresjonsharness, ikke bare setninger i et charter. At
   read-only-rollene ikke skriver, håndheves av verktøylisten i agentfila og kontrolleres etterpå
   av `scripts/readonly-check.sh` mot rollens egen worktree.
2. **Kit-eid vs. prosjekt-eid.** Loop-reglene ligger i generert `docs/loop-rules.md`. Prosjektets
   `AGENTS.md` er seedet én gang og peker til dem. `/setup` kan da kjøres på nytt uten å trå på
   prosjektets egne regler.
3. **Tre filklasser:** generert (overskrives), seed (skrives bare hvis fila mangler) og merget
   (`.gitignore` og pekeren i `AGENTS.md`: legg til, slett aldri). Se README «Mappestruktur».

---

## 1. Arkitektur — det universelle

Uavhengig av stack:

- **Én koordinator som eneste skriver** og kortlevde workers. Koordinatoren lager en egen git-worktree
  per worker med `scripts/bootstrap-worktree.sh` og sender stien i dispatchen.
- **Fire worker-roller:** planner (dyp modell) → uavhengig reviewer (dyp modell) → implementer (kodemodell)
  → uavhengig kode-reviewer (dyp modell). Valgfri scout (billig modell) for lokalisering.
- **Strukturerte rapport-kontrakter** (plan / review / code_review / done) er skjøten mellom
  koordinator og workers.
- **Én fil per todo og en kø i frontmatter.** Ingen samlet indeks, og dermed ingen merge-felle.
  Status leses ved behov med glob.
- **Pausepunkter** er der mennesket kommer inn: teknisk risiko, påkrevd brainstorm, feil,
  review som ikke konvergerer, og aldri mot produksjons-branchen.
- **Uavhengig review slår selvgransking** på både plan og kode: egne agenter med fersk kontekst, og
  gjerne en annen modellfamilie enn den som skrev arbeidet.
- **Grooming** med dobbel gating (`status: deferred` + `tags: [forslag]`). Loopen foreslår, mennesket
  triagerer.
- **Run-logg** (telemetri) og **helsesjekk/release-rådgiver** (periodisk).
- Menneskets review flyttes fra per plan til per release.

Dette laget er likt i alle prosjekter.

---

## 2. `loop.config.yaml` — det som MÅ ligge i config

Alt prosjektspesifikt samles i ÉN fil som `/setup` kompilerer inn i kitet. Se
[`../loop.config.example.yaml`](../loop.config.example.yaml) for den fullstendige, kommenterte malen
og [`../setup.md`](../setup.md) for token-tabellen.

| Config-nøkkel | Hva | Hvor det ellers ville vært hardkodet |
|---|---|---|
| `project_name` | → agent-navn `<project>-planner/reviewer/implementer/code-reviewer` | Agent-filnavn og `agent_type` i `task`-kall |
| `models` | prioritert modelliste per rolle (dyp / kode / billig) + valgfri `*_effort` | Agentenes `model:`-frontmatter og `task`-kallets `model`/`reasoning_effort` |
| `environments` | dev-ID, prod-ID | Tier 1-invarianter i alle charter |
| `branch_strategy` | base-branch for PR, prod-branch («aldri rør»), release-mål | `gh pr create --base`, runbook |
| `verification_commands` | `build` / `type_check` / `lint` / `test` / `e2e` | `todo-finish-worker`, helsesjekk |
| `tier1_invariants` | språkregel, sikkerhetsregler | Hver charters «Ufravikelige invarianter» |
| `tech_review_agents` | hvilke domene-reviewere code-revieweren dispatcher (pluggbare) | code-reviewer-charteret |
| `canary_source` | fila planner-kanarien leses fra (bevis på at fila er lest) | Runbook §3 |
| `lessons_topics` | gyldige tema-mapper (`tasks/lessons/<tema>/`) | `report-schema.md` og charterne |
| `pause_triggers` | hva som teller som teknisk risiko | Pausepunkt-listene |
| `release` | release-kommando, antall merger mellom helsesjekker | Runbook §6c |
| `pipelining` | tak for antall todos i pipeline (plan uten claim) samtidig; **valgfri**, fravær ⇒ `0` ⇒ av | Runbook §5c |
| `retro_file_classes` | filklassene retro-tallene fordeler tillagte linjer på; **valgfri** | `tasks/retro-numbers.py` |
| `parallel_implementers` | tak for antall samtidige implementere; **valgfri**, fravær ⇒ `1` ⇒ sekvensielt | Runbook §5d |
| `hooks` | hvilke vakter og komfort-hooks som registreres i `.github/hooks/loop-guards.json` | Hook-konfigurasjonen |
| `agent_memory` | hvilke roller som har rollehukommelse i `tasks/agent-memory/` | Agentenes Steg 0 |
| `compliance` | org-modus: organisasjonens agentstandard i `AGENTS.md`, godkjenning av plan og merge, høyrisiko-stier, godkjente MCP-servere, dataklassifisering; **valgfri**, fravær ⇒ av | `docs/loop/compliance.md`, `tasks/compliance-check.py`, stegfilene §4 og §6 |

**Tommelfingerregel:** nevner en verdi en stack, et miljø-ID, en produksjons-branch, et språk eller
en modell, hører den i `loop.config.yaml`, ikke i maskineriet.

---

## 3. Filinventar — kitet (`templates/`)

`/setup` renderer alt under `templates/` til prosjektets faktiske stier.

| Fil | Klasse |
|---|---|
| `.github/agents/PROJECT_NAME-{planner,reviewer,implementer,code-reviewer,scout}.agent.md` | **Universell struktur + config** |
| `.github/skills/run-loop/SKILL.md` | **Universell + config** |
| `.github/skills/todo-finish-worker/SKILL.md` | **Universell + config** |
| `.github/skills/loop-health-check/SKILL.md` | **Universell + config** |
| `.github/skills/{todo-plan,todo-plan-review,todo-execute,todo-done,start,status,endsession,handover,todo-new,lesson-new}/SKILL.md` | **Grunnstillas + config** |
| `.github/hooks/scripts/*.sh` + generert `.github/hooks/loop-guards.json` | **Universell + config** (vakter og harnesser) |
| `scripts/bootstrap-worktree.sh`, `scripts/readonly-check.sh` | **Universell + config** (worktree per worker, read-only-kontroll) |
| `docs/loop/coordinator-runbook.md` + `steps/*.md` + `runbook-hvorfor.md` | **Universell + config** (kjerne-sjekkliste, én fil per steg, begrunnelser) |
| `docs/loop/report-schema.md` | **Universell** (bare `lessons_topics` fra config) |
| `docs/loop/run-log.md` | **Universell** (telemetriformat; tom logg ved generering) |
| `docs/orchestration-loop.md` | **Universell + config** (operatørguide) |
| `tasks/todos/README.md`, `tasks/bugs/inbox/README.md` | **Grunnstillas** |
| `examples/tech-review-agents/*` | **Pluggbar**: leveres per prosjekt bak code-reviewer-grensesnittet |

---

## 4. Grunnstillas (må finnes FØR loopen virker)

Loopen sitter oppå et todo- og arbeidsflytsystem. Kitet leverer dette i `templates/` og
`scaffolding/`, men prosjektet må ha (eller få):

- **Én fil per todo:** `tasks/todos/todo-NN-slug.md` + frontmatter-skjema + `tasks/todo_archive.md`.
- **Arbeidsflyt-skills:** `todo-plan`, `todo-plan-review`, `todo-execute` (charterne peker hit).
- **Lessons:** `tasks/lessons.md` (katalog) + én fil per lesson i `tasks/lessons/<tema>/`.
- **`AGENTS.md`** (charterne sier «les og adlyd»; workers får den fordi agentene har
  `include-custom-instructions: true`).
- **Konvensjonsdokumenter:** naming-conventions, (loading-patterns, data-model hvis relevant).
- **CI som blokkerende port** på PR (se `scaffolding/`).

---

## 5. Plattformavhengigheter

| Avhengighet | Universell eller teknologispesifikk |
|---|---|
| **GitHub Copilot-harnessen** (VS Code med Session Target = Copilot, eller Copilot CLI): custom agents i `.github/agents/`, `task`-verktøyet med `agent_type`/`model`/`mode`, skills i `.github/skills/`, hooks i `.github/hooks/`, `gh`-autentisering i miljøet | Universell, kreves |
| **Debug- og verifiseringsskills** (`systematic-debugging`, `verification-before-completion`, kalt fra `todo-execute`) | Valgfrie; workerne har en innebygd fallback |
| **git + `gh` (GitHub)** | Universell her; GitLab eller annet krever tilpasning |
| E2E-verktøy (Playwright MCP) / DB-MCP i `.mcp.json` | Teknologispesifikke (web- og DB-prosjekter) |

---

## 6. Sjekkliste for et nytt prosjekt

1. **Stillas på plass?** Sjekk én fil per todo, arbeidsflyt-skills, lessons, `AGENTS.md`,
   konvensjonsdokumenter og CI. Mangler noe, legg det inn først (se README og MIGRATION).
2. **Fyll `loop.config.yaml`** (§2). Bytt alle modellplassholdere med modeller fra Copilots
   modellvelger.
3. **Kjør `/setup`.** Den renderer `templates/` til prosjektets stier, gir agentene prosjektnavn,
   genererer `.github/hooks/loop-guards.json` og stopper hvis et token eller en plassholder står igjen.
4. **Lever tech-review-agentene** (§3, pluggbar): kopier fra `examples/`, tilpass, registrer i config,
   kjør `/setup` på nytt.
5. **Plattformavhengigheter** (§5): Copilot-harnessen, git og `gh`, eventuelt MCP i `.mcp.json`.
6. **Valider:** start en ny Copilot-sesjon, kjør `/run-loop once` på én liten lavrisiko-todo, og bekreft
   planner → reviewer → implementer → kode-review → merge, at workers ikke rører delt state, at hver
   worker jobbet i sin egen worktree, og at modellvalget virker. Skriv et valideringsnotat.
7. **Backlog-hygiene:** sett betingede og post-MVP-todoer til `deferred`, og brainstorm-gate de
   designtunge.

---

## 7. Kjent fremtidig herding (ikke gjort ennå)

Dokumentert ærlig, så kitet ikke later som det er komplett:

- **Kostnadstak:** synligheten finnes (`tasks/measure-cost.py`, AI credits), men ingen budsjettgrense
  stopper loopen. Uten målte tall er bremsen `IKKE MÅLT` og faller til nivå A.
- **Self-mod-gate:** todoer som endrer loopens eget maskineri (eller `loop.config.yaml`/`/setup`) bør
  tvinges til menneskelig review.
- **Secret-scan i CI** for autonom kodegenerering.
- **Read-only-vakt før verktøykallet:** Copilots `preToolUse`-hook vet ikke hvilken subagent som
  kaller. Read-only håndheves derfor av verktøylisten og kontrolleres etterpå, ikke stoppes før.
- **Kjøring i skyen (Copilot cloud agent):** én oppgave blir én PR, så skyen passer for en
  implementer, ikke for koordinatoren.
- **`/setup`-robusthet:** krever `python3` + `pyyaml`; validerer at config-*nøklene* finnes og at
  ingen plassholdere står igjen, men ikke at verdiene er meningsfulle.

---

**Oppsummert:** kitet i §3, stillaset i §4 og `loop.config.yaml` i §2 er det som skal til. Arbeidet
i et nytt prosjekt er «fyll config og kompiler», ikke «skriv om». Konseptet i §1 overlever uansett
stack.
