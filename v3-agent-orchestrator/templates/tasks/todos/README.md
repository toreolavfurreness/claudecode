<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->
# tasks/todos/ — Én fil per todo

Hver aktiv todo har én fil: `todo-NN-slug.md` (f.eks. `todo-12-kort-beskrivelse.md`).

Ferdige todos flyttes ikke hit — de arkiveres i `tasks/todo_archive.md` (append-only).

---

## Frontmatter-skjema

```yaml
---
nr: "66"                          # STRING — stabil nøkkel; håndterer 6, 6A, 6C3a
slug: todos-one-file-per-todo     # kebab-case, norsk tillatt (tracking-unntak)
title: "Refaktor: todo.md → én fil per todo"
status: open                      # se Status-enum nedenfor
order: 660                        # kuratert rekkefølge (nr × 10, sub: 6A=61, 6C3a=631)
priority: normal                  # normal | prioritert
tags: []                          # [domene-tag] | []
deps: []                          # ["18","60"] — nr-strenger til avhengige todos
claimed_by: null                  # branch/worktree som jobber med den (ADVISORY i MVP)
phase: null                       # valgfri — fasen til en claimet todo, settes av koordinatoren (se «Fase»)
plan: null                        # tasks/plans/todo-NN-slug.md (settes når en plan finnes — også for en pipelinet, u-claimet todo)
effort: M                         # valgfri — S | M | L, implementeringskost (se Verdifelter)
saves: "≈2 opus-dispatcher per todo"   # valgfri — hva den sparer, i loopens egne enheter
observed: "run-log: 22/49 pause_event" # valgfri — observasjonen som motiverer todoen
bugs:    ["BUG-001", "BUG-002"]   # valgfri — kantbærende, se «Kantbærende felt»
files:   ["components/AddItemModal.tsx"]     # valgfri — repo-relativ sti, kantbærende
lessons: ["react-native-web", "postgres-rls"]  # valgfri — tema-basenavn uten .md, kantbærende
pr:      ["465"]                  # valgfri — LISTE (ikke skalar), kantbærende
release: "1.4.0"                  # valgfri — versjonen i tasks/releases/<versjon>.md
epic: invitasjon                  # valgfri — epic-slug fra release-filas «## Epics»
release_blocker: true             # valgfri — kom inn etter cut-off fordi den blokkerer done_when
---
```

### Status-enum

| Verdi | Betyr |
|---|---|
| `open` | Klar for planlegging — eller pipelinet: plan finnes og `plan:` er satt, men todoen er ikke claimet (se `coordinator-runbook.md` §5c) |
| `reviewed` | Plan skrevet og godkjent, klar for `/todo-execute` |
| `in_progress` | `/todo-execute` er startet |
| `done` | Ferdig — flyttes til `tasks/todo_archive.md` |
| `deferred` | Utsatt til videre — tilsvarer `[~]`. `deferred` + `tags: [forslag]` = u-triagert grooming-forslag (se `docs/orchestration-loop.md`) |
| `split` | Overordnet container splittet i sub-todos |

### Tagging

- `[domene-tag]` — valgfri tag som grupperer todos rundt et avgrenset domene/delsystem
  (erstatt med prosjektets egne domene-tags). Todos uten tag = generelle app-features.
- `[forslag]` — u-triagert grooming-forslag (universell; brukes av grooming-flyten).
- `[prod-release]` — releasens prod-todo. Eies av mennesket; §1 velger den aldri.

### Regler

- **`nr` er alltid string** — håndterer sammensatte IDer som `6A`, `6C3a`.
- **`order`** bevarer kuratert rekkefølge: heltall. Regel: enkle tall `nr × 10` (todo-8 → 80, todo-66 → 660). 6-serien: `6 + alfabetisk posisjon` (A=1…H=8) → 61–68 (6A=61, 6H=68). Siffer-sub: `6C3 = 63` (ingen videre multiplikasjon).
- **`deps`-gating:** `/todo-execute` verifiserer at alle `deps`-todos har `status: done` FØR start.
- **`claimed_by`** er advisory i MVP — TOCTOU-race er mulig. Atomisk lås hører til loopen (egen spec).
- **ALDRI** committ en aggregert indeksfil som aggregerer status fra alle todos — det gjenskaper konflikt-fellen. Status leses on-demand via glob + frontmatter.
- **Slug-konsistens:** bruk samme slug i `todos/todo-NN-slug.md`, `plans/todo-NN-slug.md` og branches.

### Release-felt (valgfrie)

`release`, `epic` og `release_blocker` kobler todoen til en release. Skjema, livsløp og eierskap:
`tasks/releases/README.md`.

- **`release`** må matche et filnavn i `tasks/releases/` (uten `.md`). En verdi som ikke finnes er
  en feil: `release.py status` gir exit 2 og §1 stopper. Ellers ville en skrivefeil tatt todoen
  stille ut av scope.
- **`epic`** er en slug fra release-filas `## Epics`. Den brukes bare til fremdrift per epic.
- **`release_blocker: true`** settes bare når todoen blokkerer en `done_when`-linje. Skriv hvilken
  i brødteksten. Uten feltet gir en todo som kommer inn i scope etter cut-off en ADVARSEL.
- `/todo-done` skriver `**Release:**` og `**Epic:**` i arkivoppføringen, så fremdrift og release
  notes også teller arkiverte todoer.

### Verdifelter (valgfrie)

`effort`, `saves` og `observed` er alle **valgfrie**. De finnes for at et
menneske skal kunne rangere loop-forbedringer mot hverandre og for §7-grooming-triagen — ikke
for automatisk sortering. Ingen kø-skript skal bygge auto-prioritering på dem.

- **`effort`** — `S | M | L`, eller den sammensatte formen `<kode>/<verifisering>` (f.eks. `S/M`).
  - **Enkel form** (`S`) = grovt anslag skrevet ved opprettelsen, før noen har lest koden. Det er en
    **påstand, ikke en måling**.
  - **Sammensatt form** (`S/M`) = MÅLT mot en ferdig plan som har fått `go` i §4, og skrevet av
    koordinatoren der. Venstre halvdel er kodekost, høyre er verifiseringskost. De to divergerer
    ofte: en todo kan være ~28 linjer i én fil (`S`) med ny e2e-spec, suite-kjøring og en iOS-runde
    (`M`). Ett tall kan ikke bære begge.
  - Ved oppdatering: behold det opprinnelige anslaget i brødteksten («opprettet som `S`»), så
    driften er synlig og kan kalibreres mot `todo_archive.md`.
  - Størrelsen oppdateres **kun etter `go`**. Et `no-go` betyr at størrelsen er nettopp det som
    ikke er avklart — 267s reviewer anbefalte en splitt som ville endret den fundamentalt.
  - Merk at S/M/L måler linjer, ikke **runder**. En `S` som trenger tre fix-runder er dyrere enn en
    `M` som går rett gjennom. Feltet er fortsatt kun til menneskelig rangering; ingen kø-skript
    skal auto-sortere på det.
- **`saves`** — fri tekst: hva todoen sparer, uttrykt i loopens egne enheter (f.eks.
  «≈2 opus-dispatcher per todo», «1 pausepunkt-runde mindre per uke»).
- **`observed`** — fri tekst: observasjonen som motiverer todoen (f.eks. et run-log-utdrag).
  Kalles bevisst **ikke** `evidence` — det ordet er allerede reservert til anti-fabrikasjons-
  objektet i ferdig-rapportene (se `report-schema.md`); å gjenbruke det her ville skapt
  tvetydighet for agenter som leser begge.

**Ikke kantbærende:** `saves` og `observed` er fri tekst og kan nevne andre todo-/bug-/PR-numre
i prosa. De skal ALDRI brukes som kilde for automatisk utledede kanter (f.eks. en regex som
`TODO \d+` mot frontmatter-felt) — en slik utleder ville produsert falske kanter fra en
tilfeldig omtale i prosa. Enhver ekte referanse til en annen todo/bug/PR/fil hører hjemme i et
eget, typet felt (`deps`, eller tilsvarende), ikke i disse to.

### Kantbærende felt (valgfrie) — graf-integrasjon

`bugs`, `files`, `lessons` og `pr` speiler kanter som ellers kun står skrevet i prosa. De leses av
`tasks/graph-build.py` (generert av `/setup`, se `docs/orchestration-loop.md` for eierskap) og gjøres
oppslåbare via `tasks/graph-query.py` — se `docs/superpowers/loop/coordinator-runbook.md` §2.

1. **Alle fire er valgfrie.** Ingen eksisterende todo trenger dem, og en todo uten dem bygges og
   leses helt normalt av alle andre skript (§1-køskriptet, `/todo-execute`, `/todo-done`).
2. **De er kantbærende** — i skarp kontrast til `saves`/`observed` rett over, som ALDRI skal brukes
   som kantkilde. Skriv en ekte todo-/bug-/PR-/fil-referanse i ett av disse fire feltene, ikke i fri
   tekst, hvis den skal være maskinlesbar.
3. **Inline-listeform er påkrevd** — `bugs: ["BUG-001", "BUG-002"]`, én linje, doble anførselstegn.
   En YAML-blokkliste (`files:` på egen linje + `  - sti` under) brekker ikke §1-køskriptet, men
   `graph-build.py` ser den ikke — feltet rapporteres i `stats.blocklist_form_fields` i stedet for å
   tapes stille.
   - `bugs` — liste av `BUG-nnn`-strenger.
   - `files` — liste av repo-relative stier (samme form som `git ls-files`, f.eks.
     `components/AddItemModal.tsx`).
   - `lessons` — liste av tema-basenavn UTEN `.md` (f.eks. `react-native-web`, ikke
     `react-native-web.md`).
   - `pr` — **liste**, ikke skalar (`pr: ["465"]`, ikke `pr: 465`) — en todo kan lande som flere PR-er.
4. `nr` er global nøkkel på tvers av `tasks/todos/`, `tasks/todo_archive.md` **og** åpne, umergede
   PR-er. Duplikate `nr:` gir tvetydige node-ID-er i grafen.
5. **Hvem fyller dem:** den som **oppretter** todoen fyller `files:` og `lessons:` når de er kjent —
   det er de to feltene ingen annen kilde (frontmatter, git, arkiv, bug-fil) kan produsere for en
   todo som verken er arkivert eller har commits ennå. `bugs:` og `pr:` er valgfri berikelse:
   `todo_archive.md` blir uansett kantkilde for begge ved arkivering, så et manuelt utfylt felt her
   dupliserer en kant grafen får automatisk. Systematisk produsent-integrasjon (§6b/§7/`/todo-done`)
   og backfill av eksisterende todos er trinn 2 — se `tasks/followups/`, ikke løst av trinn 1.

---

## Opplisting (glob + frontmatter)

```bash
# Vis alle aktive todos sortert på order (zsh-kompatibel):
for f in tasks/todos/todo-*.md; do
  nr=$(grep '^nr:' "$f" | sed 's/nr: *"\(.*\)"/\1/')
  st=$(grep '^status:' "$f" | awk '{print $2}')
  title=$(grep '^title:' "$f" | sed 's/title: *"\(.*\)"/\1/')
  order=$(grep '^order:' "$f" | awk '{print $2}')
  echo "$order|$nr|$st|$title"
done | sort -t'|' -k1,1n | awk -F'|' '{printf "TODO %-6s %-12s %s\n", $2, $3, $4}'
```

Ikke bruk variabelnavnet `status` i shell-løkker — det er read-only i zsh. Bruk `st`.

## Deps-gating

```bash
# Sjekk at alle deps for en todo er done (zsh-kompatibel):
# deps_array er et space-separert liste av nr-strenger, f.eks. "6D 6F"
# OBS: nr-strenger i deps er uppercase (6D, 6F), men filnavn er lowercase (todo-6d-...).
# Bruk `tr '[:upper:]' '[:lower:]'` — IKKE `${dep,,}` (bash-only, virker ikke i zsh).
for dep in $deps_array; do
  dep_lower=$(echo "$dep" | tr '[:upper:]' '[:lower:]')
  f=$(ls tasks/todos/todo-${dep_lower}-*.md 2>/dev/null | head -1)
  if [ -n "$f" ]; then
    s=$(grep '^status:' "$f" | awk '{print $2}')
    if [ "$s" != "done" ]; then
      echo "BLOKKERT: dep $dep har status $s"
    fi
  fi
  # Fil ikke funnet = todo er done og arkivert (done-todos slettes fra tasks/todos/)
done
```

**Regel:** Fil ikke funnet ⟹ antatt done (arkivert). Done todos slettes fra `tasks/todos/` av `/todo-done`.

Commands (`/start`, `/status`, `/todo-execute`, `/todo-done`) bruker glob + frontmatter-lesing.
Se CLAUDE.md for kanonisk dokumentasjon av kommando-protokollen.

## Fase (`phase`)

Koordinatoren setter `phase` på en claimet todo ved hvert steg, i samme commit som resten av delt
state. Køsiden (`tasks/queue-status.py`) viser fasen i stedet for plan-status. Første ord er nøkkelen,
resten er fritekst: `phase: kode-review r2 PR 112`. ` #` i en ukvotert verdi kutter resten: sett verdien i doble anførselstegn for å bruke `#`. Feltet gjelder bare mens todoen er `in_progress`.

| `phase`          | Vises som         | Settes når                                    |
| ---------------- | ----------------- | --------------------------------------------- |
| `plan`           | planlegges        | claim, planner dispatchet (§3)                |
| `plan-review`    | plan til review   | plan committet, reviewer dispatchet (§4)      |
| `plan-revisjon`  | plan revideres    | no-go, tilbake til planner                    |
| `implementering` | implementeres     | plan `go`, implementer dispatchet (§5)        |
| `kode-review`    | kode-review       | PR åpnet, kode-reviewer dispatchet (§5b)      |
| `fix`            | fix-runde         | revise-gate, tilbake til implementer          |
| `merge-klar`     | venter CI / merge | kode-review `go` (§6 steg 0)                  |
| `venter-eier`    | venter på deg     | pausepunkt eller nivå A-spørsmål              |

Feltet er bare visning: ingen gate leser det. Mangler det, viser siden «fase ikke satt».
