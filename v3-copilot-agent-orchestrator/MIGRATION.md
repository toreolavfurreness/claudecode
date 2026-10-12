# MIGRATION — ta kitet i bruk i et eksisterende prosjekt

Inngangsstier:

- **Prosjektet har ingen loop ennå** → følg [`README.md`](README.md#ta-i-bruk-nytt-prosjekt). Har det
  allerede todoer, les [Grunnstillas](#grunnstillas-for-et-prosjekt-med-egne-todoer) først.
- **Prosjektet kjører `copilot-agent-orchestrator`** (det enklere Copilot-kitet med rollemaler i
  `templates/roles/` og `setup.sh`) → [Fra copilot-agent-orchestrator](#fra-copilot-agent-orchestrator).

---

## Fra copilot-agent-orchestrator

Kontrollmodellen er den samme: én koordinator som eneste skriver, uavhengige workers og mennesket
ved pausepunktene. Forskjellene som krever oppmerksomhet:

| | `copilot-agent-orchestrator` | Dette kitet |
|---|---|---|
| Roller | Maler i `templates/roles/`, fylt ut av koordinatoren ved hver dispatch | Registrerte custom agents i `.github/agents/<project>-*.agent.md`, generert av `/setup` |
| Isolasjon | Implementer og verifier i egne Copilot-sesjoner | Egen git-worktree per worker fra `scripts/bootstrap-worktree.sh` |
| Planfila | Koordinatoren skriver den fra planner-rapporten | Planneren skriver den i sin egen worktree; koordinatoren merger |
| Vakter | Bare githooks | Copilot-hooks i `.github/hooks/loop-guards.json` + githooks + `readonly-check.sh` |
| Oppsett | `setup.sh` (bare stillas) | `/setup` (hele kitet, fra `loop.config.yaml`) |
| Modeller | Én modell per rolle | Prioritert liste per rolle + valgfri `*_effort` |
| Run-logg | `docs/run-log.md` | `docs/loop/run-log.md` |

### 0. Forutsetning

Loopen står stille: ingen koordinator-sesjon kjører, ingen todo er `in_progress`, ingen
worker-sesjoner er åpne, og arbeidstreet er rent. Gjør migreringen på en egen branch mot
base-branchen.

### 1. Legg kitet ved siden av det gamle

```bash
cp -R <sti>/v3-copilot-agent-orchestrator .
cp v3-copilot-agent-orchestrator/loop.config.example.yaml v3-copilot-agent-orchestrator/loop.config.yaml
mkdir -p .github/skills/setup
cp v3-copilot-agent-orchestrator/setup.md .github/skills/setup/SKILL.md
```

Overfør verdiene fra den gamle `loop.config.yaml` til den nye fila. Nøklene for prosjekt, miljøer,
branch-strategi, verifiseringskommandoer, invarianter og tech-review-agenter har samme betydning.
Modellene skrives som lister (`planner: ["<modell>"]`). `verifier`-rollen finnes ikke her. Har
prosjektet en verifier blant tech-review-agentene, gjør den om til en read-only tech-review-agent
(se `examples/tech-review-agents/`).

### 2. Ta vare på prosjektets egne endringer

Har prosjektet redigert de gamle rollemalene (`templates/roles/*.md`) eller kommandomalene
(`templates/commands/*.md`), noter endringene. Ta prosjektspesifikke regler inn i `AGENTS.md`, og
kitforbedringer inn i `v3-copilot-agent-orchestrator/templates/` (tokenisert) før steg 3.

### 3. Kjør `/setup`

Start en Copilot-sesjon i VS Code (Session Target = Copilot) og kjør `/setup`. Den skriver kitet,
lar seed-filer som finnes være i fred (`AGENTS.md`, lessons, agent-minne, konvensjonsdokumenter) og
legger til det som mangler i `.gitignore` og pekeren til `docs/loop-rules.md` i `AGENTS.md`.

`scripts/check-todo-nr-collisions.sh` og `check-todo-nr-premerge.sh` overskrives av de genererte
versjonene. De leser både `## TODO-N` og `## TODO N` i arkivet, så eksisterende arkiv trenger ingen
endring.

### 4. Flytt telemetrien

```bash
git mv docs/run-log.md docs/loop/run-log.md
```

Har `/setup` seedet en tom `docs/loop/run-log.md`, erstatt den med den gamle loggen. Kolonnene er de
samme. Rader skrevet før migreringen mangler kostnadsfelt i AI credits og teller som `IKKE MÅLT`.

### 5. Valider

1. Kjør harnessene (README steg 6). Alle skal være grønne.
2. Commit og start en **ny** Copilot-sesjon. Agenter og hooks leses ved sesjonsstart.
3. Agent-proben i `/run-loop`, så `/run-loop once` på én lavrisiko-todo. Sjekk at hver worker jobbet i
   sin egen `.loop-worktrees/<rolle>-<nr>`.

### 6. Fjern det gamle kitet

Når steg 5 er grønt: slett `copilot-agent-orchestrator/` og de gamle rolle- og kommandomalene i en egen
commit. To kit-kilder i samme repo er to sannheter.

**Rollback:** alt over er vanlige commits. `git revert` av migrerings-committene gir det gamle
oppsettet tilbake (kilden finnes til steg 6).

---

## Grunnstillas for et prosjekt med egne todoer

Loopen forutsetter én fil per todo med frontmatter (se `templates/tasks/todos/README.md`). Har
prosjektet todoer i én samlet fil eller i et sakssystem:

1. **Stopp nytt arbeid** til migreringen er ferdig, og sørg for at ingen todo er halvferdig.
2. **Del opp:** én fil per todo i `tasks/todos/todo-NN-slug.md`. Behold numrene. Ferdige todoer går til
   `tasks/todo_archive.md` som `## TODO-NN — tittel`.
3. **Sjekk numrene:** `bash scripts/check-todo-nr-collisions.sh` (etter `/setup`) skal ikke gi
   kollisjoner.
4. **Lessons:** én fil per lesson i `tasks/lessons/<tema>/`. Har prosjektet lessons i temafiler, splitt
   dem med `python3 v3-copilot-agent-orchestrator/scripts/split-lessons.py`.
5. Fortsett med README «Ta i bruk», fra steg 3.

Hvert steg er en egen commit, så det kan rulles tilbake for seg.
