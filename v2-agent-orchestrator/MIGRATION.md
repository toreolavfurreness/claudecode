# MIGRATION — fra v1 til v2 i et eksisterende prosjekt

Denne playbooken er for et prosjekt som allerede kjører **v1** (sekvensiell
human-orchestrator: commands på rot, monolittisk `tasks/todo.md`, punktvise
sub-agenter) og vil over til **v2** (autonom agent-orchestrator).

> **Kilden til denne oppskriften er Kornerflagget selv.** Det prosjektet ble
> migrert v1→v2 i to trinn som speiler stegene under: først en strukturell
> refaktor `tasks/todo.md` → én-fil-per-todo (todo-system-refaktoren), så
> bygging av loop-maskineriet (koordinator + fire workers + rapport-kontrakter
> + run-logg + helsesjekk) oppå det refaktorerte stillaset. Rekkefølgen er ikke
> tilfeldig: maskineriet forutsetter én-fil-per-todo, så stillaset må på plass
> først. Se git-historikken i `toreolavfurreness/kornerflagget` for den faktiske
> sekvensen.

**To inngangsstier til v2:** er prosjektet *nytt* (ikke v1 ennå) → bruk
[`README.md`](README.md) i stedet. Denne fila er for et levende v1-prosjekt med
historikk og kanskje in-flight arbeid.

---

## Prinsipper for en trygg migrering

- **Reversibelt før irreversibelt.** Steg 1 (strukturell refaktor) endrer ikke
  atferd og kan rulles tilbake. Først når v2 er validert (steg 4) kutter du over.
- **Migrer bare når køen er ren.** In-flight arbeid (en todo midt i
  `/todo-execute`, en åpen feature-branch) skal landes eller parkeres FØR du
  refaktorerer todo-systemet. Ellers mister du sporbarhet i overgangen.
- **v1 og v2 lever side om side til cut-over.** Du sletter ikke v1-kommandoene
  før loopen har kjørt grønt på minst én ekte todo.

---

## Steg 0 — Forutsetning: ren kø

Bekreft før du rører noe:

```bash
git status                      # working tree ren?
git branch                      # noen uflettet feature-branch?
```

- Åpne PR-er / feature-branches → flett eller lukk dem først.
- En todo med `[~]`/«påbegynt» i `tasks/todo.md` → fullfør den med v1-flyten
  (`/todo-execute` → `/todo-done`) eller marker den eksplisitt som utsatt.
- Mål: `tasks/todo.md` inneholder kun *ikke-påbegynte* todos når du går til steg 1.

> Hvorfor: steg 1 splitter `tasks/todo.md` i mange filer. En halvferdig todo med
> tilstand spredt mellom chat, branch og todo.md-linje overlever ikke splitten rent.

---

## Steg 1 — Strukturell refaktor (reversibel, endrer ikke atferd)

Dette er ren omstrukturering. Ingen ny loop-logikk ennå.

### 1a. `tasks/todo.md` → én-fil-per-todo

For hver todo i den monolittiske `tasks/todo.md`, opprett
`tasks/todos/todo-NN-slug.md` med frontmatter etter skjemaet i
`templates/tasks/todos/README.md`:

```yaml
---
nr: "NN"
slug: kebab-case-slug
title: "Tittel"
status: open          # [x] ferdig → arkivér i stedet (se under); [ ] → open; [~] → deferred
order: NN0            # bevar rekkefølgen fra todo.md (nr × 10)
priority: normal
tags: []
deps: []              # eksplisitte avhengigheter du kjenner
claimed_by: null
plan: null
---

<original todo-tekst som body>
```

- Allerede ferdige (`[x]`) todos: ikke lag fil — append dem til
  `tasks/todo_archive.md` (append-only). Done-todos *finnes ikke* i `tasks/todos/`
  (deps-gating tolker «fil mangler» som arkivert).
- Behold `tasks/todo.md` midlertidig som referanse under migreringen; slett den
  i cut-over (steg 5).

> **Hvorfor én-fil-per-todo:** den monolittiske fila er en merge-konflikt-magnet
> så snart flere agenter (eller du + koordinatoren) skriver samtidig. Én fil per
> todo + status lest on-demand via glob fjerner hele konflikt-klassen. Dette er
> selve forutsetningen for at koordinatoren kan eie delt state alene.

### 1b. Flytt commands til `.claude/commands/`

v1 har slash-kommandoene som `.md`-filer på rot (`start.md`, `todo-plan.md` …).
Flytt v1-kommandoene du beholder under migreringen inn i `.claude/commands/`
(reversibelt — bare git mv). Dette gjør plass til v2-kommandoene og samler alt
ett sted.

### 1c. Lessons-struktur

v1 har `tasks/lessons/<tema>.md` + `index.md`. v2 forventer `tasks/lessons.md`
(indeks) + `tasks/lessons/<tema>.md`. Hvis navnene avviker: lag `tasks/lessons.md`
som indeks (kan gjenbruke v1s `index.md`-innhold). Behold tema-filene.

**Commit steg 1 som én reversibel «refactor: todo-system + struktur»-commit.**
Verifiser at v1-flyten fortsatt virker (kjør `/status`) — atferd skal være uendret.

---

## Steg 2 — Bygg v2-maskineriet oppå

Nå legger du loopen på det refaktorerte stillaset.

1. **Kopier kit-et:** legg `v2-agent-orchestrator/` i prosjektroten, og
   `setup.md` → `.claude/commands/setup.md`.
2. **Fyll `loop.config.yaml` fra prosjektets eksisterende dokumentasjon** —
   dette er gull-kilden, ikke gjett:
   - `project_name`, `github_repo`, `language` ← `CLAUDE.md`-toppen
   - `environments` (dev/prod-ID), `branch_strategy` ← `CLAUDE.md` Infrastruktur/Branch-strategi
   - `verification_commands` ← `CLAUDE.md` «Vanlige kommandoer» / `package.json`-scripts
   - `tier1_invariants` ← `CLAUDE.md` Atferd/Sikkerhet (språk-regel, RLS-fra-første-migrasjon o.l.)
   - `lessons_topics` ← de faktiske filnavnene i `tasks/lessons/`
   - `canary_source` ← en stabil doc (data-model/arkitektur)
   - `tech_review_agents` ← prosjektets domene-reviewere (se steg 3)
3. **Kjør `/setup`.** Den renderer `templates/` → `.claude/agents/`,
   `.claude/commands/`, `docs/`, `tasks/`. Den validerer at ingen tokens gjenstår.
4. **Stillas:** mangler prosjektet `.githooks/pre-push` eller CI-port → kopier fra
   `scaffolding/` og tilpass.

> Merk: `/setup` *legger til* v2-kommandoer (`run-loop`, `todo-finish-worker`,
> `loop-health-check`) og v2-versjoner av workflow-kommandoene ved siden av v1.
> v1-kommandoene røres ikke ennå — du kutter over i steg 5.

---

## Steg 3 — Tech-review-agenter

v1 hadde kanskje en `reviewer`/`security`-agent. I v2 er domene-reviewere
**pluggbare** bak code-reviewer-grensesnittet:

1. Kopier prosjektets domene-reviewere (eller maler fra `examples/`) til
   `.claude/agents/`.
2. Registrer dem i `loop.config.yaml` under `tech_review_agents` (trigger-stier +
   severity-map).
3. Kjør `/setup` på nytt så code-reviewer-charteret får dispatch-reglene.

Ingen DB/auth-domene? Sett `tech_review_agents: []`.

---

## Steg 4 — Valider med `/run-loop once`

**Start en fersk sesjon** (agent-registeret lastes ved sesjonsstart — de
nygenererte `<project>-*`-agentene er ikke synlige i sesjonen som kjørte `/setup`).

1. Kjør agent-proben fra `run-loop.md` (`{"ok": true}`-dispatch). «Agent type not
   found» → bekreft at agent-filene ligger i `.claude/agents/` og start på nytt.
2. Velg én **liten, lavrisiko** todo (ingen migrasjon/secrets/prod) som
   validerings-kandidat.
3. Kjør `/run-loop once`. Bekreft hele kjeden:
   planner → uavhengig reviewer → implementer → uavhengig kode-review → merge mot
   base-branch, at workers ikke rørte delt state, og at modell-pinningen traff
   (planner/reviewer/code-reviewer = dyp modell, implementer = rask).
4. Skriv et kort valideringsnotat (go/no-go for å kutte over).

> Gikk noe galt? Du har ikke kuttet over ennå — v1 er fortsatt intakt. Fiks
> config/agenter og kjør `/run-loop once` på nytt før du går videre.

---

## Steg 5 — Cut over og deprecate v1

Først når steg 4 er grønt:

1. **Slett `tasks/todo.md`** (den monolittiske) — kilden til sannhet er nå
   `tasks/todos/*.md`.
2. **Fjern v1-kommandoene** som er erstattet (v1s rot-`*.md` / duplikate
   `.claude/commands/`-varianter). Behold kun v2-settet.
3. **Oppdater `CLAUDE.md`s «Oppstart»-seksjon** til å peke på `/run-loop` (og
   v2-workflow-kommandoene) i stedet for v1-flyten.
4. **Commit cut-over** som en egen, tydelig commit («chore: cut over to v2
   orchestration loop»). Etter denne er v1 deprecert i prosjektet.

---

## Rollback

- **Før steg 5:** v2 lever ved siden av v1 — slutt å bruke `/run-loop`, fortsett
  med v1-kommandoene. Ingen datatap.
- **Steg 1 alene:** den strukturelle refaktoren er reversibel via `git revert` av
  refactor-commiten (todo-filene → tilbake til `tasks/todo.md`).
- **Etter steg 5:** rull tilbake cut-over-commiten for å gjenopprette v1-oppstart;
  én-fil-per-todo-strukturen kan beholdes uavhengig (v1 kan leve med den, men var
  bygget for `tasks/todo.md`).
