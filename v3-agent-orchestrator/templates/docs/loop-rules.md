{{GENERATED_HEADER}}

# {{PROJECT_NAME}} — Loop- og kunnskapsregler

> **Hvem eier denne fila:** kit-et. Den genereres av `/setup` fra
> `v3-agent-orchestrator/templates/docs/loop-rules.md` og importeres av prosjektets
> `CLAUDE.md` med `@docs/loop-rules.md`. Prosjektspesifikke regler hører hjemme i
> `CLAUDE.md` — ikke her. Operatør-guide for selve loopen: `docs/orchestration-loop.md`.

## Miljø-bekreftelse (Tier 1)

| Miljø    | ID                 | Brukes av                                  |
| -------- | ------------------ | ------------------------------------------ |
| **Dev**  | `{{DEV_ENV_ID}}`  | Daglig arbeid, all loop-aktivitet          |
| **Prod** | `{{PROD_ENV_ID}}` | Kun planlagte releaser (`{{RELEASE_COMMAND}}`) |

- **Les alltid ID-en, aldri navnet.** Prosjektvelgere viser ofte dev og prod som nabolinjer med
  kun et suffiks som skille — ett feilklikk bytter miljø uten annen bekreftelse.
- **Send ID-en EKSPLISITT i hvert kall** (CLI-flagg, `project_id` i MCP) når du står i en worktree —
  der alle loop-agenter jobber. Lokale «lenket prosjekt»-filer er som regel gitignorert og finnes
  ikke i en fersk worktree, og en fil verktøyet selv skriver som bivirkning av ditt eget kall
  bekrefter ingenting. Et kall uten eksplisitt ID i en worktree er et regelbrudd, ikke en
  forglemmelse.
- Et verktøy som ikke kan rettes mot et bestemt miljø (ingen ID-parameter), skal ikke brukes.

## Oppstart av hver sesjon

1. Les `CLAUDE.md` (og denne fila, som den importerer).
2. Les `tasks/lessons.md` — KUN katalogen (tema-scope + lese- og skriveprotokoll). Lessons ligger én
   per fil i `tasks/lessons/<tema>/` og lastes ved behov, etter leseprotokollen.
3. Les køen: `tasks/todos/todo-*.md` (én fil per todo — status i frontmatter).

**Arbeidsmodell (autonom orkestrering):** `/run-loop` lar en koordinator-agent kjøre køen
(velg todo → planner → uavhengig reviewer → implementer → uavhengig kode-reviewer → merge mot
`{{BASE_BRANCH}}`), med stopp kun ved pausepunkter. Menneskelig review flyttes fra per-plan til
per-release. For manuell, sekvensiell jobbing på enkelt-todos finnes `/todo-plan` →
`/todo-plan-review` → `/todo-execute` → `/todo-done`.

## Planlegging først

- Oppgaver med 3+ steg eller arkitekturvalg: skriv en plan og vent på bekreftelse før koding.
- Går noe galt: STOPP og lag ny plan — ikke fortsett å pushe.
- Før analyse og løsningsvalg: _«Hva ville en senior utvikler gjort her?»_ — rotårsak, ikke
  symptom, og vurder om løsningen faktisk virker på målplattformen.

## Oppgavehåndtering

**Én fil per todo** er kilden til sannhet: `tasks/todos/todo-NN-slug.md` med frontmatter (`nr`,
`slug`, `title`, `status`, `order`, `priority`, `tags`, `deps`, `claimed_by`, `plan`). Status leses
on-demand via glob — ingen monolittisk todo-liste (den er en merge-konflikt-magnet). Fullt skjema:
`tasks/todos/README.md`.

**Status-enum:** `open` | `reviewed` | `in_progress` | `done` (arkivert) | `deferred`
(`+ tags: [forslag]` = u-triagert grooming-forslag) | `split`.

- Nye todos: lag en ny fil — aldri bare i konteksten. Nummer = `sh scripts/check-todo-nr-collisions.sh --next`
  (etter `git fetch origin {{BASE_BRANCH}}`); gjenbruk aldri et arkivert nummer. Reservasjon og
  renummerering: `docs/superpowers/loop/coordinator-runbook.md` §9.
- **Koordinatoren er eneste skriver** til `claimed_by` / `status: in_progress|done`, og til
  `tasks/lessons*`, `tasks/followups/`, `tasks/bugs.md` og `tasks/todo_archive.md`. Mennesket styrer køen ved å sette
  `priority` / `order` / `status: deferred` på u-claimede todos, og slipper bugs i
  `tasks/bugs/inbox/`.
- Ferdige todos arkiveres til `tasks/todo_archive.md` (append-only) og todo-fila slettes.

## Lessons learned — én fil per lesson

Lessons er Codes langtidsminne: én fil per lesson. Filsystemet er indeksen — ingenting telles eller
genereres, så ingenting kan bli utdatert.

- **`tasks/lessons.md`** — statisk tema-katalog med lese- og skriveprotokollen. Leses ved oppstart.
- **`tasks/lessons/<tema>/<YYYY-MM-DD>-<slug>.md`** — én lesson per fil. Temaene er mappene
  (`ls tasks/lessons/`). Lastes kun ved behov i `/todo-plan`, `/todo-plan-review`, `/todo-execute` og
  `/todo-done`, etter leseprotokollen.
- **`tasks/followups/`** — oppfølgingskøen (carry-forwards), én fil per oppfølging. Ikke lessons: en
  fil slettes når oppfølgingen er lukket.

**Tema (fra `lessons_topics` i loop.config.yaml — et nytt tema er bare en ny mappe):**

{{LESSONS_TOPICS_BULLETS}}

**Skriv en lesson når:** en bug ble fikset på en ikke-åpenbar måte · en antakelse viste seg å være
feil · noe tok vesentlig lengre tid enn forventet pga. en fallgruve · mennesket måtte korrigere Code.

**Format (én fil):**

```md
---
tags: [rls, security-definer]
scope: project
kilder: [TODO-12, BUG-003]
---

# Kort tittel

**Problem:** Hva som gikk galt eller var uventet
**Årsak:** Rotårsaken (valgfri — utelates når problemet er selvforklarende)
**Løsning:** Hva som faktisk fungerte
**Unngå:** Konkret regel Code skal følge fremover
```

`tags` er fritt vokabular og erstatter `## Se også`: relevans for et annet tema er en tag, ikke en
peker. `scope` er `project`. `kilder` er `TODO-NN` / `BUG-NNN` (tom liste tillatt).

**Regler:**

- Skriv etter skriveprotokollen i `tasks/lessons.md` (algoritme i `/todo-done`). Ingen indeks å
  oppdatere og ingen telling.
- Dekker en eksisterende lesson samme mønster: utvid den og legg kilden til i `kilder` — ikke lag
  duplikat.
- Hold det konkret — handlingsbare regler, ikke generelle refleksjoner.
- Etter at noe er skrevet: vurder om det også bør inn i `CLAUDE.md` som en generell regel.

Kommer du fra temafiler (`tasks/lessons/<tema>.md` med `## <dato> — <tittel>`-blokker): kjør
`python3 v3-agent-orchestrator/scripts/split-lessons.py` én gang (se `MIGRATION.md`).

## Tre kunnskapsbaser

Tre kunnskapsbaser lever side om side, med ulike roller:

- **Auto-minne / MEMORY.md** (Claude Codes brukerminne) — atferds- og prosessregler og
  samarbeidspreferanser fra mennesket.
- **`tasks/lessons.md` + `tasks/lessons/`** — teknisk prosjektkunnskap og fallgruver. **Varig.**
- **`.claude/agent-memory/<agent>/MEMORY.md`** (Claude Codes `memory: project`-frontmatter —
  injiseres ved agent-oppstart, sjekkes inn i git) — rolle-spesifikk arbeidsmetode for én subagent.
  Påslått for: {{AGENT_MEMORY_ROLES}}. **Forbruksvare.**

**Brukerminne vs. de to andre:** _«Er dette knyttet til prosjektkode/data, eller til min måte å
samarbeide med Claude?»_ Prosjektkode/data → en lesson i riktig tema-mappe under `tasks/lessons/`.
Samarbeidspreferanse → brukerminnet.

**Grensen mellom `tasks/lessons/` og agent-minne kan IKKE avgjøres med samme tommelfingerregel.**
En prosjektregel er som regel også en sjekk en agent kjører selv — «er dette sant om prosjektet,
eller om hvordan jeg jobber?» gir «begge» på nettopp det vanligste tilfellet. Bruk i stedet fire
ordnede tester, første treff vinner:

**Forutsetning: testene anvendes på ÉN atomisk påstand.** Bærer en setning flere påstander, SPLITT
den først — ellers dømmer T0 hele setningen på ett enkelt signalord, og splitten som er hele poenget
skjer aldri.

- **T0 — Observasjonshistorikk-filteret** (rent mekanisk, kjøres først). Inneholder påstanden et
  rundetall, en treffrate, en frekvens eller en tidsserie over EGNE kjøringer? Signalord: «de siste
  N rundene», «gir oftest», «har aldri gitt», «to av tre ganger», «pleier å». → **agent-minne**,
  uten videre test.
- **T1 — Transferability** (primær for alt T0 ikke fanger). Omskriv i to trinn: (a) fjern
  førstepersons-subjektet, (b) generaliser til en påstand om systemet (kodebasen, plattformen,
  verktøyet) — ikke om observasjonshistorikken. Overlever resultatet som en fullstendig, sann
  påstand om systemet? → **lessons.** Kollapser den til nonsens, en bar preferanse, eller en usann
  generalisering? → **agent-minne.**
- **T2 — Falsifiseringskilde** (sekundær, ved uavgjort på T1). Hva gjør påstanden usann?
  Kode/DB/plattform endrer seg → **lessons**. Egen treffrate endrer seg over runder →
  **agent-minne**.
- **T3 — Uavgjort ⇒ lessons vinner.** Agent-minnet kan da holde maksimalt en **peker**
  (`se tasks/lessons/<tema>/<fil>.md`), aldri en kopi.

**To harde regler som gjør grensen håndhevbar:**

- **Ingen-kopi-regelen (ufravikelig).** En linje i en agent-`MEMORY.md` som gjengir _substansen_ i en
  lesson er en **defekt** og skal erstattes av en peker. Når en lesson rettes, finnes det da ingen
  kopi som kan bli stående utdatert. Normen alene holder ikke — før en ny minnelinje skrives, kjøres
  `grep -rn "<nøkkelord>" tasks/lessons/` (se charterets § Rollehukommelse).
- **Akseptansetesten.** _Å slette `.claude/agent-memory/` helt skal aldri miste prosjektkunnskap._
  Ville slettingen mistet noe prosjektet trenger, hørte det innholdet hjemme i lessons.

**Eksempel på splitt-forutsetningen:** «Migrasjons-differ gir oftest BLOKKERENDE på manglende
`REVOKE EXECUTE … FROM anon`; jeg sjekker grants før RLS-predikater fordi det er billigere» er to
påstander. (i) revoke-regelen overlever T1 som en sann systempåstand → **lessons**. (ii)
rekkefølgen har T0-signalordet «gir oftest» → **agent-minne**, med en peker til lessons-fila. Uten
splitten ville T0 sendt hele setningen til minne, og revoke-regelen ville forsvunnet fra lessons.

Kontrakten for form, hardt linjetak og kurering av agent-minnet står i vedkommende agents charter
(§ Rollehukommelse), ikke her.

## Branching-regler

- Aldri direkte commit/merge til `{{PROD_BRANCH}}` — alltid branch + PR mot `{{BASE_BRANCH}}`.
- Lander noe likevel på `{{RELEASE_BRANCH}}` (release eller hotfix): back-merge
  `{{RELEASE_BRANCH}} → {{BASE_BRANCH}}` umiddelbart med merge-commit (ikke squash), ellers driver
  `{{BASE_BRANCH}}` bak.
- Kode merget utenfor loopen (hotfix): følg `docs/hotfix-runbook.md` — én run-log-rad, ellers
  blir den usynlig i telemetrien.
- Slett feature-branchen etter merge.
- Prod-release er menneske-kjørt (`{{RELEASE_COMMAND}}`); loopen anbefaler kun.

## Vakter (hooks)

Registrert i `.claude/settings.json` av `/setup` (kun det `hooks:` i loop.config.yaml slår på).
En hook-endring krever **fersk sesjon** før den gjelder — hook-konfig lastes ved sesjonsstart.

| Hook | Hendelse | Håndhever |
|---|---|---|
| `guard-main-merge.sh` | PreToolUse (Bash) | Push, PR og merge mot `{{PROD_BRANCH}}` blokkeres; mennesket kjører det selv i terminal |
| `guard-reviewer-readonly.sh` | PreToolUse (alle) | Read-only-rollene i `.claude/hooks/reviewer-readonly.contract` kan faktisk ikke skrive |
| `session-start-lint.sh` | SessionStart | Myk typecheck/lint-status (blokkerer aldri) |
| `typecheck-on-edit.sh` | PostToolUse (Edit/Write) | Typesjekk etter endring av kildefiler |

Hver vakt har en testharness ved siden av seg (`test-guard-*.sh`). Endrer du en vakt: kjør
harnessen, og behandle endringen som `hook_selfmod` (se `docs/superpowers/loop/report-schema.md`).

## Kit-regelen

En PR som endrer en kitfil (en loop-fil som også finnes i kit-repoet), har en egen `Kit:`-linje i
PR-teksten. En direktecommit uten PR har linja i commit-meldingen.

- `Kit: claudecode#NN` navngir kit-PR-en.
- `Kit: ingen endring – <begrunnelse>` sier at kitet ikke trenger endringen.
- `Kit: porteres …` sier at porten lages etter merge. Den godtas i kode-review, men er et brudd i
  releasevakten til linja er byttet til en av de to første.

Kode-revieweren kjører `python3 scripts/kit-release-check.py --pr <nr>`. Releasevakten er
`python3 scripts/kit-release-check.py` (exit 1 = brudd, exit 2 = sjekken kunne ikke kjøres).
Kitfil-lista utledes fra kit-repoets tre. Unntak (`EXCEPTIONS`) og frafall for direktecommits
(`WAIVED`, full sha og begrunnelse) står i skriptet. `WAIVED` er tom i kitet: en rad der er
prosjektets egen og porteres ikke.
