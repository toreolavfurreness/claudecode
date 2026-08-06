# Koordinator-runbook

Du er koordinatoren — eneste skriver til delt state (`tasks/lessons*`, `tasks/bugs*`,
`tasks/todo_archive.md`, todo-frontmatter, `docs/run-log.md`). Workers gjør tungt arbeid og
returnerer rapporter (`docs/report-schema.md`); du dispatcher dem med to ulike mekanismer
avhengig av rolle (se `docs/PORTING-DECISIONS.md` §2):

| Rolle | Dispatch-mekanisme |
|---|---|
| planner, reviewer, code-reviewer | `task`-verktøyet, in-session (`agent_type: general-purpose`, `mode: sync`, `model`/`reasoning_effort` fra `loop.config.yaml`) |
| implementer, verifier | `create_session` (egen barnesesjon, `kickoff.model`/`kickoff.reasoning_effort` fra config), koordinert med `send_session_message`/`get_session`/`get_changes_overview`, ryddet opp med `archive_session` når ferdig |

## 0. Sesjonsstart

1. Les `loop.config.yaml` (prosjekt-roten eller `copilot-agent-orchestrator/loop.config.yaml`
   — se README for hvor prosjektet ditt har lagt den). Dette gir deg alle `{{TOKEN}}`-verdier
   for resten av runden.
2. Les `docs/orchestration-loop.md` (operatør-guiden) hvis du ikke allerede kjenner loopen.
3. Fetch + synk: `git fetch origin {{BASE_BRANCH}} && git reset --hard origin/{{BASE_BRANCH}}`.
   Working tree ikke ren (`git status --porcelain` ikke-tom FØR reset) → rapporter til
   mennesket og stopp i stedet for å reset.
4. **Run-log-avstemming:** sjekk om noe er merget til `{{BASE_BRANCH}}`/`{{PROD_BRANCH}}` uten
   en tilhørende rad i `docs/run-log.md` siden forrige kjøring:
   ```bash
   for b in {{BASE_BRANCH}} {{PROD_BRANCH}}; do
     gh pr list --state merged --base "$b" --limit 30 --json number -q '.[].number' \
     | while read n; do
         grep -qE "pull/$n([^0-9]|$)" docs/run-log.md || echo "UKLASSIFISERT: PR #$n (base=$b)"
       done
   done
   ```
   Uklassifiserte treff → klassifiser dem (hotfix/release-merge/glemt logg-rad) i én omgang
   før du går videre.

## 1. Kø-utvelgelse (deps-gating)

```bash
python3 copilot-agent-orchestrator/scaffolding/scripts/select-next-todo.py
```

Kjøres fra prosjektroten. Scriptet parser frontmatter (`nr`, `status`, `deps`, `order`,
`priority`, `tags`) fra alle `tasks/todos/todo-*.md` og printer FØRSTE kandidat som består alle
filtrene:

1. Ekskluder: `status != open`, `tags` inneholder `forslag` (u-triagert grooming-forslag) eller
   `utredning` (krever websøk du ikke har verktøy for — håndter disse selv, ikke dispatch).
2. Ekskluder todos der `deps` ikke alle har `status: done` (fil mangler i `tasks/todos/` = antatt
   done/arkivert).
3. Sorter: `priority: prioritert` først, deretter `order` stigende.

Exit 1 + tomt stdout → rapporter "kø tom" og stopp runden.

## 2. Todo-nr-kollisjonsgate (gate a — arbeidstre)

```bash
sh scripts/check-todo-nr-collisions.sh
```

Blokkerer runden hvis den finner interne duplikater eller gjenbruk av pensjonerte nr. Fiks før
du går videre.

## 3. Dispatch: planner

Bygg prompt fra `templates/roles/planner.md`: substituer `{{PROJECT_NAME}}`, `{{TODO_NR}}`,
`{{TODO_SLUG}}`, `{{TIER1_INVARIANTS}}`, `{{CANARY_TARGET}}` (fil+linje du velger, IKKE gjentatt
andre steder i prompten), `{{PAUSE_TRIGGERS}}` fra `loop.config.yaml` og todoen.

```
task(agent_type: "general-purpose", mode: "sync", model: <models.planner>,
     reasoning_effort: <models.planner_effort>, prompt: <substituert tekst>)
```

Motta plan-rapporten (JSON). `deps_ok: false` eller `status: blocked` → eskalér til mennesket,
ikke gå videre. Ellers: **du** skriver `plan_body` til `tasks/plans/todo-<nr>-<slug>.md`, commit
("plan: legg til planfil for todo <nr>"), oppdater todo-frontmatter (`status: reviewed` settes
FØRST etter at reviewer har godkjent — sett foreløpig ingenting eller en intern
"planning"-markør hvis prosjektet ditt trenger det).

## 4. Dispatch: reviewer

Bygg prompt fra `templates/roles/reviewer.md`, med plan-teksten limt inn. Samme
`task`-mekanisme som planner (egne model/effort-verdier). `verdict: no-go` → send funnene
tilbake til planner (§3, revisjonsrunde) — maks 2 runder totalt, deretter eskalér til mennesket.
`verdict: go` → sett todo-frontmatter `status: reviewed`, gå videre til §5.

## 5. Dispatch: implementer (barnesesjon)

```
create_session(project_id: <dette prosjektet>, name: "todo-<nr>-<slug>",
  kickoff: { prompt: <templates/roles/implementer.md substituert med plan_body>,
             model: <models.implementer>, reasoning_effort: <models.implementer_effort>,
             mode: "autopilot" | "plan" (velg etter prosjektets risikoprofil) })
```

Sett todo-frontmatter `status: in_progress`, `claimed_by: <barnesesjonens branch>`.

Vent på ferdig-rapporten via `send_session_message` fra barnesesjonen (den blir idle når
prompten er ferdig behandlet — les turer med `get_session`/vent på cross-session-melding).
`status: blocked` → eskalér til mennesket, IKKE arkiver sesjonen ennå (mennesket vil ofte ville
se den). `status: done` uten `pr_url` → opprett PR-en selv fra din egen sesjon
(`gh pr create --base {{BASE_BRANCH}} ...` mot branchen implementeren rapporterte).

## 6. Dispatch: code-reviewer

Bygg prompt fra `templates/roles/code-reviewer.md` med `{{PR_URL}}` fylt inn. Samme
`task`-mekanisme (in-session). `verdict: no-go` → send funnene til implementer-barnesesjonen
via `send_session_message` (fix-mode, se rolle-instruksjonen) — maks 2 revisjonsrunder, deretter
eskalér. `verdict: go` → gå videre til §7.

**Tech-review-armer:** for hver `tech_review_agents`-entry som er relevant for diffen: dispatch
in-session `task`-kall (armen leser sin egen `.claude/agents/<navn>.md`-instruks). Er armen en
**verifier** (muterer kode) → dispatch den i stedet som en EGEN barnesesjon (`create_session`),
samme begrunnelse som implementer.

## 7. Merge + opprydding

1. **Gate b (pre-merge):** `sh scripts/check-todo-nr-premerge.sh <branch>` — siste handling før
   merge. Exit ≠ 0 → ikke merge, følg feilmeldingen.
2. `gh pr merge <pr> --squash` (eller prosjektets foretrukne merge-strategi) mot
   `{{BASE_BRANCH}}`.
3. Arkiver implementer-/verifier-barnesesjonene: `archive_session(id: <session_id>)`.
4. Oppdater todo: fjern filen fra `tasks/todos/`, append til `tasks/todo_archive.md`.
5. Skriv lessons fra ferdig-rapportens `lessons[]`-felt til `tasks/lessons/<topic>.md` +
   `index.md` + `log.md` (eller dispatch `lessons-writer`-agenten hvis prosjektet har en, se
   dette repoets `.claude/agents/lessons-writer.md` for et eksempel som allerede fungerer).
6. Append rad(er) til `docs/run-log.md` (`plan`, `review`, `implement`, `code_review`, `merged`).

## 8. Neste todo eller helsesjekk

Går videre til neste todo i køen (§1), eller kjører `docs/coordinator-runbook.md`-helsesjekken
(se separat `templates/commands/loop-health-check.md`) hvis merge-intervallet i
`loop.config.yaml` (`release.health_check_merge_interval` / `loop_eval.merge_interval`) er nådd.

## Hard grense (ufravikelig, alle roller)

`{{PROD_BRANCH}}` og produksjonsmiljøet (`{{PROD_ENV_ID}}`) berøres **aldri** av loopen uten at
mennesket eksplisitt gir det som oppgave — verken via `create_session`, `gh pr merge`, eller
direkte git-kommandoer.
