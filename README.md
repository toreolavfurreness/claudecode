# Claude Code — arbeidsflyt-template

Et prosjekt-agnostisk template-repo for å kjøre Claude Code i et nytt
prosjekt. Repoet er **versjonert**: hver toppnivå-mappe er en selvstendig,
komplett arbeidsflyt. Du drar inn ÉN mappe og har alt — ingen delt
`shared/`, ingen skjulte avhengigheter mellom versjonene.

| Versjon | Mappe | I ett ord |
|---|---|---|
| **v1** | [`v1-sekvensiell-human-orchestrator/`](v1-sekvensiell-human-orchestrator/) | Mennesket orkestrerer, sekvensielt |
| **v2** | [`v2-agent-orchestrator/`](v2-agent-orchestrator/) | En koordinator-agent orkestrerer, autonomt |

---

## Hvilken velger du?

### v1 — sekvensiell human-orchestrator

Mennesket er orkestratoren. Du kjører én slash-kommando om gangen
(`/start` → `/todo-plan` → `/todo-execute` → `/todo-done`), godkjenner
hver plan, og driver flyten fremover manuelt. Sub-agenter brukes punktvis
(plan-review, code-review, lessons). Todos ligger i én monolittisk
`tasks/todo.md`.

**Velg v1 når:**
- Du vil ha full kontroll og godkjenne hvert steg.
- Prosjektet er lite, eller du er ny i Claude Code-arbeidsflyten.
- Du vil ha minst mulig maskineri og ingen avhengighet til custom
  subagents / worktree-isolasjon.

### v2 — agent-orchestrator

En **koordinator-agent** er orkestratoren. Den velger neste todo,
dispatcher kortlevde workers (planner → uavhengig reviewer → implementer →
uavhengig kode-reviewer) i isolerte worktrees, skriver delt state som
eneste skriver, og merger til integrasjonsbranchen — **uten at du må
trigge hvert steg**. Du flyttes fra «godkjenn hver plan» til «godkjenn hver
release», og trekkes kun inn ved ekte veiskiller (pausepunkter). Todos er
én-fil-per-todo (ingen merge-konflikt-felle).

**Velg v2 når:**
- Du vil kjøre en kø av todos autonomt og kun gripe inn ved unntak.
- Prosjektet har stillaset på plass (én-fil-per-todo, workflow-commands,
  lessons, CLAUDE.md, konvensjons-docs, CI) — eller du er villig til å
  sette det opp.
- Du kjører på Claude Code-plattformen med custom subagents
  (`model`/`effort`/`isolation: worktree`) og git + `gh`.

> v2 er ikke «v1 fast». Det er en annen kontrollmodell. v1 fryses som
> referanse når v2 overtar — den røres ikke utover å ligge i sin mappe.

---

## Ta i bruk

Hver versjonsmappe har sin egen `README.md` med fullstendig oppsett.

- **v1:** kopier mappens innhold inn i prosjektroten, fyll `CLAUDE.md` og
  `docs/`-skjelettene, start med `/start`. Se
  [`v1-sekvensiell-human-orchestrator/README.md`](v1-sekvensiell-human-orchestrator/README.md).
- **v2:** to inngangsstier —
  - **Nytt prosjekt:** fyll `loop.config.yaml`, kjør `/setup`, start loopen.
    Se [`v2-agent-orchestrator/README.md`](v2-agent-orchestrator/README.md).
  - **Eksisterende v1-prosjekt:** følg
    [`v2-agent-orchestrator/MIGRATION.md`](v2-agent-orchestrator/MIGRATION.md)
    for en reversibel v1→v2-migrering.

---

## Designprinsipp

**Selvstendige versjonsmapper.** Når du porterer til et nytt prosjekt skal
du dra inn ÉN mappe og ha alt — kit, stillas og config-eksempel. Det er
bevisst at v1 og v2 dupliserer noe (lessons-mønster, naming-konvensjoner):
kostnaden ved litt duplisering er lavere enn kostnaden ved en delt `shared/`
som binder versjonene sammen og gjør porting til et plukk-og-velg-puslespill.
