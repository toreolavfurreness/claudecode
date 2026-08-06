# Oppsett — ta loopen i bruk i et prosjekt

> **Mye mindre steg enn Claude Code-originalens `/setup`** — se
> `docs/PORTING-DECISIONS.md` §3-4 for hvorfor. Rolle- og kommando-templates
> kompileres ALDRI til disk; kun scaffolding (githooks, CI, tasks/-READMEs)
> rendres én gang.

## Prinsipper (ufravikelige, samme disiplin som kilden)

1. **Deterministisk substitusjon for sikkerhetsverdier.** Branch-navn,
   miljø-IDer og verifiseringskommandoer settes av `setup.sh` — ikke ved at
   noen «redigerer inn» verdier med skjønn.
2. **Valideringsgate — feil høyt.** Skriptet stopper hardt hvis en påkrevd
   config-nøkkel mangler, eller hvis et `{{TOKEN}}` blir stående usubstituert
   i en generert fil.
3. **Idempotent, med ett unntak.** De fleste genererte filene overskrives rent
   ved re-kjøring. **Unntak:** `docs/run-log.md` er seed-only — koordinatoren
   eier og appender til den under loop-kjøring, så skriptet seeder den KUN
   når den mangler og overskriver den aldri.
4. **Kilde vs. generert adskilt.** Templates med tokens blir liggende i
   `copilot-agent-orchestrator/scaffolding/` og `copilot-agent-orchestrator/templates/tasks/`.
   Skriptet skriver generert output til prosjektets `.githooks/`,
   `.github/workflows/`, `scripts/`, `tasks/`, `docs/run-log.md`.
5. **Ingen restart nødvendig for roller/kommandoer** — i motsetning til kilden.
   `templates/roles/*.md` og `templates/commands/*.md` leses av koordinatoren
   direkte ved hvert dispatch/sesjonsstart; de er ikke registrerte agenter.

## Steg

1. Kopier `copilot-agent-orchestrator/loop.config.example.yaml` til prosjektets
   rot som `loop.config.yaml` og fyll ut alle nøkler (se token-tabellen under).
2. Kjør substitusjonsskriptet fra prosjektroten:
   ```bash
   bash copilot-agent-orchestrator/scaffolding/scripts/setup.sh
   ```
   Det validerer config-en, renderer scaffolding (githooks, CI, tasks-READMEs),
   seeder `docs/run-log.md`/`tasks/todo_archive.md` hvis de mangler, og
   rapporterer hva som ble skrevet vs. hoppet over.
3. Les skriptets sluttrapport. Feil om manglende nøkkel eller gjenværende
   token → fiks `loop.config.yaml` (eller en scaffolding-mal hvis du har
   redigert den) og kjør på nytt. Fortsett aldri med et delvis generert kit.
4. **Aktiver githooks:** `git config core.hooksPath .githooks` (idempotent,
   trygt å kjøre flere ganger — aktiverer både pre-commit- og pre-push-vernet).
5. **Tech-review-agenter (valgfritt):** kopier innholdet fra
   `copilot-agent-orchestrator/examples/tech-review-agents/*.example.md` inn i
   en ny `templates/roles/<navn>.md` (fjern `.example`), tilpass sjekklisten,
   og legg til en entry i `loop.config.yaml: tech_review_agents`. Tom liste
   `[]` er gyldig hvis prosjektet ikke trenger noen.
6. Commit de genererte filene (`.githooks/`, `.github/workflows/ci.yml`,
   `scripts/`, `tasks/todos/README.md`, `tasks/bugs/inbox/README.md`,
   `docs/run-log.md`, `tasks/todo_archive.md`).
7. Start en koordinator-sesjon og be den kjøre
   `copilot-agent-orchestrator/templates/commands/run-loop.md` — se
   `docs/orchestration-loop.md` for hvordan du styrer og følger loopen videre.

## Token-tabell (kanonisk vokabular for scaffolding-substitusjon)

Kun tokens som faktisk brukes i `scaffolding/` og `templates/tasks/` er
listet — rolle-/kommando-templatene har flere tokens, men de substitueres av
koordinatoren i minnet (se `docs/coordinator-runbook.md`), ikke av dette
skriptet.

| Token | Config-nøkkel |
|---|---|
| `{{PROJECT_NAME}}` | `project_name` |
| `{{GITHUB_REPO}}` | `github_repo` |
| `{{BASE_BRANCH}}` | `branch_strategy.base_branch` |
| `{{RELEASE_BRANCH}}` | `branch_strategy.release_branch` |
| `{{PROD_BRANCH}}` | `branch_strategy.prod_branch` |
| `{{DEV_ENV_ID}}` / `{{PROD_ENV_ID}}` | `environments.dev_id` / `environments.prod_id` |
| `{{CMD_TEST}}` / `{{CMD_TYPE_CHECK}}` / `{{CMD_LINT}}` | `verification_commands.test` / `.type_check_script` / `.lint` |
| `{{RELEASE_COMMAND}}` | `release.command` |

`base_branch="dev"` og `protected_branch="main"` i `.githooks/pre-commit`/
`pre-push` er reelle shell-defaults (ikke `{{TOKEN}}`-plassholdere) som
`setup.sh` retter med en egen, dokumentert `sed`-linje — samme mønster som
kildens hooks.
