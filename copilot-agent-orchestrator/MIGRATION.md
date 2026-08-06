# Migrering

Denne filen dekker to migreringsscenarier: (A) et prosjekt som allerede kjører
Claude Code sin `v2-agent-orchestrator`, og (B) et prosjekt som (som dette
repoet) allerede har en enklere, ikke-autonom Copilot-oppsett
(`.claude/commands/{start,status,todo-plan,todo-execute,todo-done}.md` +
`.claude/agents/{reviewer,plan-reviewer,lessons-writer}.md`).

## A) Fra Claude Code `v2-agent-orchestrator` → denne porten

Datamodellen er identisk — `tasks/todos/*.md`-frontmatter, `tasks/todo_archive.md`,
`tasks/lessons/*`, rapport-JSON-formatet — så det er **ingen datamigrering**.
Det som endres er hvordan koordinatoren *dispatcher* rollene.

1. **Behold `loop.config.yaml` nesten uendret.** Alle nøkler under
   `models`/`environments`/`branch_strategy`/`verification_commands`/
   `tier1_invariants`/`tech_review_agents`/`canary_source`/`lessons_topics`/
   `pause_triggers`/`release`/`loop_eval` betyr det samme. Eneste endring:
   `models.*` peker nå på Copilot-modell-IDer (se `available_models` i din
   Copilot-sesjon), ikke Claude-modellalias.
2. **Slett `.claude/agents/<project_name>-{planner,reviewer,implementer,code-reviewer,verifier}.md`.**
   Disse eksisterer ikke lenger som registrerte agenter — innholdet deres
   flyttes til `templates/roles/*.md` (allerede skrevet i dette kit-et; juster
   kun prosjektspesifikke deler som tier1-invarianter-teksten hvis den var
   hardkodet i den gamle agentfila i stedet for lest fra config).
3. **Slett `.claude/commands/{run-loop,todo-finish-worker,loop-health-check}.md`.**
   Erstattes av `templates/commands/{run-loop,loop-health-check}.md` i dette
   kit-et. `todo-finish-worker.md` sitt innhold er nå en del av
   `templates/roles/implementer.md` sin prosedyre (§ i den filen) — implementeren
   kjører selv-verifiseringen som SISTE del av samme barnesesjon, i stedet for
   en egen kommando-fil.
4. **Flytt `docs/superpowers/loop/{coordinator-runbook,report-schema,run-log}.md`
   til `docs/{coordinator-runbook,report-schema,run-log}.md`** (eller behold
   gamle sti hvis prosjektet foretrekker det — koordinatoren leser stien du
   faktisk har, juster referanser i `templates/commands/*.md` tilsvarende).
   `run-log.md`-INNHOLDET flyttes uendret — det er kun en sti-endring, ikke et
   nytt format.
5. **Kjør `scaffolding/scripts/setup.sh`** for å friske opp githooks/CI (samme
   verdier som før — skriptet er idempotent på disse filene).
6. **Tech-review-agenter** (`examples/tech-review-agents/*.example.md` eller
   prosjektets egne): flytt fra `.claude/agents/<navn>.md` til
   `templates/roles/<navn>.md`. Innholdet er uendret; kun hvor koordinatoren
   finner filen endres.
7. Start koordinator-sesjonen og be den følge det nye
   `templates/commands/run-loop.md` — ingen restart-og-probe-steg er
   nødvendig siden det ikke finnes navngitte agenter å probe lenger (se
   `docs/PORTING-DECISIONS.md` §3).

## B) Fra dette repoets eksisterende v1-oppsett → denne loopen

v1 (`.claude/commands/{start,status,todo-plan,todo-plan-review,todo-execute,todo-done,endsession}.md`
+ `.claude/agents/{reviewer,plan-reviewer,lessons-writer}.md`) er et
**menneske-i-loopen-per-steg-system**: du trigger `/todo-plan`, godkjenner,
trigger `/todo-execute` selv, osv. Denne orkestreringsloopen er et
**overbygg**, ikke en erstatning:

- Samme `tasks/todos/`-datamodell, samme frontmatter-felter — todos skrevet
  under v1 fungerer uendret som input til loopen.
- `lessons-writer`-agenten kan gjenbrukes direkte fra
  `docs/coordinator-runbook.md` §7 punkt 5 (koordinatoren dispatcher den, eller
  skriver lessons selv fra rapportens `lessons[]`-felt).
- `reviewer.md`/`plan-reviewer.md` i v1 tilsvarer konseptuelt
  `templates/roles/reviewer.md` i denne loopen, men er IKKE samme fil —
  v1-agenten er registrert og statisk; loop-rollen er en dispatch-tid-template.
  Ikke bland dem: bruk v1 for manuell, per-todo-styrt arbeid; bruk
  `copilot-agent-orchestrator/` når du vil at koordinatoren skal kjøre flere
  todos i rekke uten at du trigger hvert steg selv.
- Du kan kjøre begge systemene side om side i samme prosjekt — de deler
  datamodell og skriver ikke til de samme filene på motstridende vis, så
  lenge du ikke starter en autonom loop-runde og en manuell `/todo-execute`
  på SAMME todo samtidig (`claimed_by`-feltet er advisory, ikke en ekte lås —
  se `tasks/todos/README.md` § Regler).
