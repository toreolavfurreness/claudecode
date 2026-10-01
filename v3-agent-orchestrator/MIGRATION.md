# MIGRATION — til v3 i et eksisterende prosjekt

Inngangsstier:

- **Prosjektet kjører v3.2** → kjør `/setup` på nytt. To endringer merkes utenfor kit-filene:
  plan-rapporten har et nytt felt, `planned_diff`, og kanarien har nytt format, `L<N>: <tekst>`.
  Har du egne verktøy som leser plan-rapporter, oppdater dem. Har du skrevet om plan-malen, sjekk at
  planene fortsatt har en `## Steg`-seksjon: `python3 tasks/vblock-lint.py <plan>` sier fra.
- **Prosjektet kjører v3.1** → kjør `/setup` på nytt. v3.2 legger bare til nytt innhold og en
  valgfri nøkkel, `hooks.compaction_checkpoint` (av som standard). Har du kopiert eksempel-lensene
  inn i `.claude/agents/`, ta med den nye seksjonen «Tilgang til koden under review» og regelen om
  ett funn per mekanisme selv. `/setup` rører ikke tech-review-agentene dine.
- **Prosjektet kjører v3.0** → [Fra v3.0 til v3.1](#fra-v30-til-v31), så `/setup`.
- **Prosjektet kjører v2** (har `v2-agent-orchestrator/` og en fungerende loop) → [Fra v2](#fra-v2-til-v3).
- **Prosjektet kjører v1** (sekvensiell human-orchestrator) → [Fra v1](#fra-v1-til-v3). Stegene der
  er skrevet for v2 og gjelder uendret med v3-kit-et; v3-nøklene har defaults.
- **Nytt prosjekt** → [`README.md`](README.md).

---

## Fra v3.0 til v3.1

v3.1 endrer to ting som `/setup` ikke kan gjøre for deg:
- Lessons blir én fil per lesson.
- Oppfølgingskøen flytter til `tasks/followups/`.

Resten er en vanlig rekompilering. Commit alt før du starter. Da er git-historikken backupen.

1. **Erstatt kit-et:** kopier inn det nye `v3-agent-orchestrator/` og `setup.md` →
   `.claude/commands/setup.md`.
   - Sjekk først om du har redigert genererte filer direkte. Bruk diff-oppskriften i
     [steg 2 under](#2-finn-lokale-endringer-før-du-overskriver).
   - Merk: runbooken er nå delt i en kjerne og stegfiler. En lokal endring i
     `coordinator-runbook.md` hører nå hjemme i riktig `steps/<steg>.md`.
2. **Config:**
   - `lessons_topics` er nå navn på tema-*mapper*. Bruk temanavnet uten periode-suffiks
     (`workflow-process`, ikke `workflow-process-sep2026`).
   - Fjern `open-followups` fra `lessons_topics` (oppfølgingskøen er ikke et tema lenger).
   - Ny valgfri vakt: `hooks.implementer_model_guard`. Den er på som standard og trenger `jq`.
3. **Kjør `/setup`.** Den seeder `tasks/lessons/<tema>/` for hvert tema og
   `tasks/followups/README.md`. Finnes en gammel `tasks/lessons/<tema>.md`, sier rapporten fra.
4. **Splitt lessons:** kjør fra prosjektroten:
   ```bash
   python3 v3-agent-orchestrator/scripts/split-lessons.py
   ```
   - Les planen. Antall blokker inn må være lik antall filer ut.
   - Sub-tema-filer blir egne mapper. Slå dem sammen med `--map gammel=ny` hvis du vil.
   - Kjør på nytt med `--apply`. Skriptet skriver filene og sletter de gamle temafilene.
     `open-followups.md` går til `tasks/followups/`.
5. **Etterarbeid** (skriptet skriver ut det som gjenstår):
   - Gi hver lesson minst én emne-tag.
   - Gjør gamle `## Se også`-pekere om til tagger.
   - Fyll scope-linja per tema i `tasks/lessons.md`.
6. **Valider:**
   - Kjør harnessene i README steg 6, alle grønne.
   - Commit, og start en **fersk** sesjon. Nye hooks lastes ved sesjonsstart.

---

## Fra v2 til v3

Kontrollmodellen er lik, så dette er en rekompilering, ikke en ombygging. Det som krever
oppmerksomhet er at `/setup` **overskriver genererte filer** — har prosjektet redigert dem direkte
(slik opphavsprosjektet har gjort med runbooken, måleskriptene og køvisningen), går de endringene tapt
om du ikke tar dem med først.

### 0. Forutsetning

Loopen står stille: ingen koordinator-sesjon kjører, ingen todo er `in_progress`, arbeidstreet er
rent. Gjør migreringen på en egen branch mot base-branchen.

### 1. Legg v3 ved siden av v2

```bash
cp -R <sti>/v3-agent-orchestrator .
cp v2-agent-orchestrator/loop.config.yaml v3-agent-orchestrator/loop.config.yaml
cp v3-agent-orchestrator/setup.md .claude/commands/setup.md
```

Legg til v3-nøklene du vil ha i `v3-agent-orchestrator/loop.config.yaml` (se «Valgfrie nøkler
(v3)» i `loop.config.example.yaml`). Utelatt: vaktene PÅ, komfort-hookene AV, scout AV, ingen
worktree-bootstrap. Sett `lessons_topics` til prosjektets lessons-temaer. Hvert tema blir en mappe
`tasks/lessons/<tema>/`. Har prosjektet tema-filer fra v2, splitter du dem etterpå med
`scripts/split-lessons.py` (se [Fra v3.0 til v3.1](#fra-v30-til-v31), steg 4–5).

### 2. Finn lokale endringer FØR du overskriver

Render v3 i et engangs-tre og diff mot prosjektets levende filer:

```bash
mkdir -p <tmp>/v3render && cd <tmp>/v3render && git init -q
cp -R <prosjekt>/v3-agent-orchestrator .
awk '/^python3 - <<.PY.$/{f=1;next} /^PY$/{f=0} f' v3-agent-orchestrator/setup.md > ../setup-body.py
python3 ../setup-body.py
for f in $(find .claude docs tasks scripts -type f | sort); do
  [ -f "<prosjekt>/$f" ] && ! diff -q "$f" "<prosjekt>/$f" >/dev/null && echo "AVVIK $f"
done
```

For hver `AVVIK`: er det prosjektets egen forbedring, ta den inn i
`v3-agent-orchestrator/templates/` (tokenisert) før du går videre — ellers forsvinner den i steg 3.
Er prosjektets versjon bevisst prosjektspesifikk og rikere (f.eks. en `queue-status.py` med `--html`,
modellforsøk-seksjonene i `measure_cost_html.py`), gjenopprett den etter steg 3 med
`git checkout HEAD -- <fil>`. Merk at neste `/setup` overskriver den igjen.

### 3. Kjør `/setup`

Den skriver kit-et, lar seed-filer som finnes være i fred (`CLAUDE.md`, lessons, agent-minne,
konvensjons-docs), og merger:

- **`.claude/settings.json`** — hook-registreringer legges til bare hvis akkurat den
  kommandostrengen mangler. Prosjektets egne hooks (f.eks. en miljø-vakt) bevares. Har prosjektet
  allerede vaktene registrert med samme kommando (som opphavsprosjektet), er dette en no-op.
- **`.gitignore`** — runtime-loggene og worktree-mappene.
- **`CLAUDE.md`** — `@docs/loop-rules.md` legges til nederst hvis importen mangler.

Har prosjektet v2-ens `scripts/check-todo-nr-collisions.sh` / `check-todo-nr-premerge.sh`,
overskrives de nå av de genererte v3-versjonene. De leser både `## TODO-N` og `## TODO N` i arkivet,
så eksisterende arkiv trenger ingen endring. `models.display` kan fjernes fra config — den utledes.

### 4. Rydd `CLAUDE.md`

`docs/loop-rules.md` eier nå loop-, lessons- og kunnskapsbase-reglene. Fjern seksjonene i
`CLAUDE.md` som dupliserer den (typisk «Oppgavehåndtering», «Lessons learned»,
«Tre kunnskapsbaser», loop-delen av «Branching-regler»). To kopier av samme regel driver fra
hverandre — samme grunn som ingen-kopi-regelen for agent-minne. Behold alt som er prosjektets
eget (infrastruktur, miljø-ID-er, prosjektspesifikke vakter, språk).

### 5. Valider

1. Kjør harnessene (README steg 6) — alle grønne.
2. Commit, start en **fersk** sesjon (nye hooks og agenter lastes ved sesjonsstart).
3. Agent-proben i `run-loop.md`, så `/run-loop once` på én lavrisiko-todo.

### 6. Fjern v2-kilden

Når steg 5 er grønt: slett `v2-agent-orchestrator/` i en egen commit. To kit-kilder i samme repo
er to sannheter.

**Rollback:** alt over er vanlige commits — `git revert` av migrerings-committene gir v2 tilbake
(v2-kilden finnes til steg 6).

---

## Fra v1 til v3

Denne playbooken er for et prosjekt som allerede kjører **v1** (sekvensiell
human-orchestrator: commands på rot, monolittisk `tasks/todo.md`, punktvise
sub-agenter) og vil over til den autonome agent-orchestratoren. Den er skrevet
da målet var v2; les «v2» som «v3» og `v2-agent-orchestrator/` som
`v3-agent-orchestrator/` under.

> **Denne oppskriften er destillert fra en faktisk v1→v2-migrering,** utført i
> to trinn som speiler stegene under: først en strukturell refaktor
> `tasks/todo.md` → én-fil-per-todo (todo-system-refaktoren), så bygging av
> loop-maskineriet (koordinator + fire workers + rapport-kontrakter + run-logg
> + helsesjekk) oppå det refaktorerte stillaset. Rekkefølgen er ikke tilfeldig:
> maskineriet forutsetter én-fil-per-todo, så stillaset må på plass først.

### Prinsipper for en trygg migrering

- **Reversibelt før irreversibelt.** Steg 1 (strukturell refaktor) endrer ikke
  atferd og kan rulles tilbake. Først når v2 er validert (steg 4) kutter du over.
- **Migrer bare når køen er ren.** In-flight arbeid (en todo midt i
  `/todo-execute`, en åpen feature-branch) skal landes eller parkeres FØR du
  refaktorerer todo-systemet. Ellers mister du sporbarhet i overgangen.
- **v1 og v2 lever side om side til cut-over.** Du sletter ikke v1-kommandoene
  før loopen har kjørt grønt på minst én ekte todo.

---

### Steg 0 — Forutsetning: ren kø

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

### Steg 1 — Strukturell refaktor (reversibel, endrer ikke atferd)

Dette er ren omstrukturering. Ingen ny loop-logikk ennå.

#### 1a. `tasks/todo.md` → én-fil-per-todo

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

#### 1b. Flytt commands til `.claude/commands/`

v1 har slash-kommandoene som `.md`-filer på rot (`start.md`, `todo-plan.md` …).
Flytt v1-kommandoene du beholder under migreringen inn i `.claude/commands/`
(reversibelt — bare git mv). Dette gjør plass til v2-kommandoene og samler alt
ett sted.

#### 1c. Lessons-struktur

v1 har `tasks/lessons/<tema>.md` + `index.md`. v3 bruker én fil per lesson i
`tasks/lessons/<tema>/` og en katalog i `tasks/lessons.md`. Behold tema-filene under steg 1.
`/setup` seeder katalogen, og `scripts/split-lessons.py` splitter tema-filene (se
[Fra v3.0 til v3.1](#fra-v30-til-v31), steg 4–5).

**Commit steg 1 som én reversibel «refactor: todo-system + struktur»-commit.**
Verifiser at v1-flyten fortsatt virker (kjør `/status`) — atferd skal være uendret.

---

### Steg 2 — Bygg v2-maskineriet oppå

Nå legger du loopen på det refaktorerte stillaset.

1. **Kopier kit-et:** legg `v2-agent-orchestrator/` i prosjektroten, og
   `setup.md` → `.claude/commands/setup.md`.
2. **Fyll `loop.config.yaml` fra prosjektets eksisterende dokumentasjon** —
   dette er gull-kilden, ikke gjett:
   - `project_name`, `github_repo`, `language` ← `CLAUDE.md`-toppen
   - `environments` (dev/prod-ID), `branch_strategy` ← `CLAUDE.md` Infrastruktur/Branch-strategi
   - `verification_commands` ← `CLAUDE.md` «Vanlige kommandoer» / `package.json`-scripts
   - `tier1_invariants` ← `CLAUDE.md` Atferd/Sikkerhet (språk-regel, RLS-fra-første-migrasjon o.l.)
   - `lessons_topics` ← temanavnene i `tasks/lessons/` (uten periode-suffiks)
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

### Steg 3 — Tech-review-agenter

v1 hadde kanskje en `reviewer`/`security`-agent. I v2 er domene-reviewere
**pluggbare** bak code-reviewer-grensesnittet:

1. Kopier prosjektets domene-reviewere (eller maler fra `examples/`) til
   `.claude/agents/`.
2. Registrer dem i `loop.config.yaml` under `tech_review_agents` (trigger-stier +
   severity-map).
3. Kjør `/setup` på nytt så code-reviewer-charteret får dispatch-reglene.

Ingen DB/auth-domene? Sett `tech_review_agents: []`.

---

### Steg 4 — Valider med `/run-loop once`

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

### Steg 5 — Cut over og deprecate v1

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

### Rollback

- **Før steg 5:** v2 lever ved siden av v1 — slutt å bruke `/run-loop`, fortsett
  med v1-kommandoene. Ingen datatap.
- **Steg 1 alene:** den strukturelle refaktoren er reversibel via `git revert` av
  refactor-commiten (todo-filene → tilbake til `tasks/todo.md`).
- **Etter steg 5:** rull tilbake cut-over-commiten for å gjenopprette v1-oppstart;
  én-fil-per-todo-strukturen kan beholdes uavhengig (v1 kan leve med den, men var
  bygget for `tasks/todo.md`).
