# copilot-agent-orchestrator

Prosjekt-agnostisk port av [`v2-agent-orchestrator`](https://github.com/toreolavfurreness/claudecode/tree/main/v2-agent-orchestrator)
(en Claude Code loop-orkestreringsmal) til **GitHub Copilot CLI**.

Tar todos fra `tasks/todos/` gjennom planlegging → review → implementering →
kode-review → merge, med en koordinator-sesjon som eneste skriver til delt
state og et menneske som styrer retning i stedet for å trigge hvert steg.

**Les `docs/orchestration-loop.md` først** hvis du skal *bruke* loopen i et
prosjekt — det er operatør-guiden. Denne README-en er for deg som skal *ta
kit-et i bruk* eller forstå hvordan det er bygget.

## Hvorfor denne porten ser annerledes ut enn kilden

Copilot CLI og Claude Code deler nok av de samme grunnmekanismene (custom
agents snapshottes ved sesjonsstart, `task`-verktøyet tilsvarer subagent-
dispatch), men isolasjonsmodellen er forskjellig: Copilot sine in-session
`task`-bakgrunnsagenter deler filsystem/worktree med foreldresesjonen — det
finnes ingen `isolation: worktree`-frontmatter-ekvivalent. Dette er empirisk
verifisert (ikke antatt), se `docs/PORTING-DECISIONS.md` §1 for de tre
spikene som testet dette.

Konsekvensen: koordinatoren dispatcher planner/reviewer/code-reviewer som
lette in-session `task`-kall (ingen isolasjon nødvendig — de muterer ikke
kode), men implementer/verifier som ekte `create_session`-barnesesjoner (egen
worktree/branch, empirisk bekreftet isolert). Og siden agent-registeret
snapshottes ved sesjonsstart akkurat som i Claude Code, dropper denne porten
navngitte, forhåndsregistrerte rolle-agenter helt — koordinatoren leser
`templates/roles/*.md` og substituerer tokens i minnet ved hvert dispatch i
stedet. Ingen restart-syklus når du endrer `loop.config.yaml`.

Full begrunnelse, alle empiriske funn og alle avveininger: `docs/PORTING-DECISIONS.md`.

## Hva er 1:1 portert vs. tilpasset

| | Kilde (Claude Code) | Denne porten (Copilot) |
|---|---|---|
| Rapport-kontrakt (JSON, ett objekt) | ✅ | ✅ identisk skjema, se `docs/report-schema.md` |
| Én-fil-per-todo, deps-gating, todo-nr-kollisjonsgater | ✅ | ✅ portert nær verbatim (ren bash/CI) |
| Githooks (delt-checkout-vern, prod-push-varsel) | ✅ | ✅ portert nær verbatim |
| Lessons/run-log/todo-archive (append-only, single-writer) | ✅ | ✅ samme disiplin |
| Navngitte, forhåndsregistrerte rolle-agenter | ✅ (`.claude/agents/<project>-*.md`) | ❌ erstattet med runtime-substituerte prompt-templates (§3) |
| Isolasjon for ALLE workers via worktree | ✅ | ⚠️ kun implementer/verifier (via `create_session`); planner/reviewer/code-reviewer er in-session |
| Modell/effort kompilert inn i agent-frontmatter | ✅ | ❌ leses fra `loop.config.yaml` som runtime-parametre til `task`/`create_session` (§4) |
| `/setup`-kompilering av HELE kit-et | ✅ | ⚠️ kun scaffolding (githooks/CI/tasks-READMEs) — se `docs/setup.md` |

## Struktur

```
copilot-agent-orchestrator/
├── loop.config.example.yaml     # kopier til prosjektets loop.config.yaml og fyll ut
├── docs/
│   ├── PORTING-DECISIONS.md     # arkitektur + empiriske funn — les FØRST
│   ├── orchestration-loop.md    # operatør-guide (bruk loopen)
│   ├── setup.md                 # engangsoppsett i et nytt prosjekt
│   ├── coordinator-runbook.md   # koordinatorens steg-for-steg-prosedyre
│   ├── report-schema.md         # rapport-kontrakten roller/koordinator følger
│   └── run-log.md               # seed-only telemetri-fil
├── templates/
│   ├── roles/                   # planner/reviewer/implementer/code-reviewer/verifier
│   ├── commands/                # run-loop.md, loop-health-check.md
│   └── tasks/                   # tasks/todos + tasks/bugs/inbox READMEs (rendres av setup.sh)
├── scaffolding/
│   ├── githooks/                # pre-commit, pre-push
│   ├── github-workflows/        # ci.yml
│   └── scripts/                 # setup.sh + todo-nr-kollisjonsgater
└── examples/tech-review-agents/ # pluggbare domene-reviewere (security, RLS)
```

## Kom i gang

1. Les `docs/PORTING-DECISIONS.md` — forstå isolasjonsmodellen før du dispatcher noe.
2. Følg `docs/setup.md` for engangsoppsett i målprosjektet.
3. Les `docs/orchestration-loop.md` for hvordan du kjører og styrer loopen.
4. Start en koordinator-sesjon og be den følge
   `templates/commands/run-loop.md`.

## Kjente begrensninger (ikke skjult, se `docs/PORTING-DECISIONS.md` §5)

- Konvensjonene for hvor rolle-/kommando-templates skal ligge i et helt nytt
  prosjekt (uten forhistorie) er ikke testet utover dette repoet.
- Superpowers-ekvivalente skills (`systematic-debugging`,
  `verification-before-completion`) og Playwright MCP er ikke garantert
  tilgjengelig i alle Copilot CLI-oppsett — rollene skal degradere gracefully,
  ikke anta at de finnes.
- Nøyaktig overhead ved `create_session` per worker-dispatch er ikke målt
  presist, kun bekreftet funksjonelt riktig.
