{{GENERATED_HEADER}}

# Loop: helsesjekk + release-rådgiver

## ⚠️ Hard grense (ufravikelig)

Denne kommandoen **vurderer og anbefaler** — den **utfører aldri** en prod-release.
`{{PROD_BRANCH}}` og produksjonsmiljøet (`{{PROD_ENV_ID}}`) berøres **aldri** av loopen uten at
mennesket eksplisitt gir det som oppgave. Anbefalingen er alltid «kjør `{{RELEASE_COMMAND}}` selv» —
**aldri** auto-merge til `{{PROD_BRANCH}}`, aldri `gh pr merge` mot `{{PROD_BRANCH}}`, aldri `git push origin {{PROD_BRANCH}}`.

**Koordinatoren kjører denne kommandoen** (single-writer-kontrakten) — ikke en dispatchet worker.
Helseraden i run-log skrives av koordinatoren etter at kommandoen er fullført.

---

## Steg 0 — Fetch origin

Alle git-sammenligninger bruker `origin/{{BASE_BRANCH}}` og `origin/{{PROD_BRANCH}}` — aldri lokale refs.
Kjør dette **aller først**, FØR noen diff eller log:

```bash
git fetch origin {{BASE_BRANCH}} {{PROD_BRANCH}}
```

---

## Del A — Helsesjekk (integrert `origin/{{BASE_BRANCH}}`)

### A1 — Hent forrige helsesjekk-SHA (for betinget tech-sweep)

```bash
grep ' | health | ' docs/superpowers/loop/run-log.md | tail -1 | grep -oE 'sha=[0-9a-f]{40}' | cut -d= -f2
```

Tom output → ingen tidligere helsesjekk → tech-sweep kjøres ubetinget (se A5).
Ikke-tom output → lagre SHA-en som `<forrige_sha>`.

### A2 — Tester (`{{CMD_TEST}}`)

```bash
{{CMD_TEST}}
```

**Rapporter faktisk output og exit-kode** — «burde funke» godkjennes ikke.

Utfallsklasser:
- Exit 0, 0 failures → `tests=green`
- Exit non-zero **og** testrunner rapporterte fail-count → `tests=red` (regresjon; noter fail-count)
- Exit non-zero **uten** test-runner-output (command not found, manglende dep, OOM, config-feil) →
  `tests=infra-feil` (infrastruktur; lim inn rå feilmelding; eskalér til mennesket)

### A3 — Type-sjekk (`{{CMD_TYPE_CHECK_SCRIPT}}`)

```bash
{{CMD_TYPE_CHECK_SCRIPT}}
```

Utfallsklasser:
- Exit 0 → `type=green`
- Exit non-zero + type-feil i koden → `type=red` (regresjon; noter antall feil)
- Exit non-zero + config/tool-feil → `type=infra-feil`

### A4 — Lint (`{{CMD_LINT}}`)

```bash
{{CMD_LINT}}
```

Utfallsklasser:
- Exit 0 → `lint=green`
- Exit non-zero + lint-regler brutt i koden → `lint=red` (regresjon; noter fil/linje)
- Exit non-zero + lint-config-feil → `lint=infra-feil`

### A5 — Tech-sweep (betinget, pluggbar)

Hvis prosjektet har en migrasjons-/domene-triggered tech-review-agent (se `tech_review_agents`
i loop.config — f.eks. `rls-auditor` ved `supabase/migrations/`): sjekk om de relevante stiene er
berørt siden forrige helsesjekk:

```bash
# Erstatt <forrige_sha> med verdien fra A1 (eller utelat for ubetinget sweep)
# Erstatt <sti> med tech-agentens trigger-sti (f.eks. supabase/migrations/)
git diff <forrige_sha>..origin/{{BASE_BRANCH}} --name-only -- <sti>
```

- Tom diff → hopp over sweep, sett `rls=n/a`
- Ikke-tom diff (eller ingen forrige SHA) → dispatch den relevante tech-review-agenten og
  rapporter funnene. Sett `rls=green` (ingen åpne hull) eller `rls=red` (funn som krever eskalering).
- Ingen tech-review-agenter konfigurert → `rls=n/a` alltid.

### A6 — Helsesjekk-aggregering

Samlet helsesjekk-status:
- Alle sjekker `green` (eller `n/a`) → **GRØNN** — fortsett til Del B
- Minst én `red` (regresjon) → **RØD (regresjon)** — ⚠️ PAUSEPUNKT, eskalér til mennesket
- Minst én `infra-feil` → **RØD (infra)** — ⚠️ PAUSEPUNKT, eskalér til mennesket med rå feilmelding

---

## Del B — Release-readiness-rådgiver

### B1 — Urealiserte commits

```bash
git log origin/{{PROD_BRANCH}}..origin/{{BASE_BRANCH}} --oneline
```

List ut alle commits.

### B2 — Brukervendte endringer siden siste release

Les `tasks/todo_archive.md` — finn todos ferdigstilt siden forrige release. Oppsummer titler og hva de gir brukere.

```bash
git diff origin/{{PROD_BRANCH}}..origin/{{BASE_BRANCH}} --name-only -- 'src/**'
```

List berørte kildefiler for å gi et teknisk bilde av omfanget.

### B3 — Release-blokkerende bug-sjekk

```bash
grep -ci '^\*\*Prioritet:\*\* høy' tasks/bugs.md
```

`> 0` → release-anbefaling = **no-go**. Vis BUG-ID-ene:

```bash
grep -B 20 '^\*\*Prioritet:\*\* høy' tasks/bugs.md | grep '^## BUG-'
```

`= 0` → bug-gaten er grønn (kun åpne bugs i `bugs.md`; lukkede er i `bugs_archive.md`).

### B4 — Go/no-go-anbefaling

Skriv en strukturert anbefaling:

```
Release-anbefaling: go | no-go

Begrunnelse:
- Urealiserte commits: N stk
- Brukervendte endringer: [liste]
- Kritiske bugs (høy prioritet): N stk [evt. BUG-IDer]
- Helsesjekk: grønn | rød

Neste steg (hvis go): kjør `{{RELEASE_COMMAND}}` selv.
Neste steg (hvis no-go): [konkret hva som må fikses]
```

**Utfør aldri releasen** — anbefal kun at mennesket kjører `{{RELEASE_COMMAND}}`.

---

## Del C — Skriv helserad til run-log

Etter at Del A og Del B er fullført, appender **koordinatoren** én rad til
`docs/superpowers/loop/run-log.md`.

Hent `origin/{{BASE_BRANCH}}`-HEAD-SHA:

```bash
git rev-parse origin/{{BASE_BRANCH}}
```

Format for `health_payload` (fast rekkefølge, nøkkel=verdi-kjede):

```
sha=<full-40-char-origin/{{BASE_BRANCH}}-HEAD-SHA>;tests=<green|red|infra-feil>;type=<green|red|infra-feil>;lint=<green|red|infra-feil>;rls=<green|red|n/a>;release=<go|no-go>
```

Helseraden i run-log følger disse **felt-invariantene**:

| Felt | Verdi for health-rad |
|---|---|
| `timestamp` | Tidspunkt for §6c-skriving (ISO 8601, minutter) |
| `todo_nr` | `-` |
| `slug` | `loop-health-check` |
| `outcome` | `health` |
| `pause_event` | `-` (grønn) eller `helsesjekk-rød` (rød + eskalert) |
| `pr` | `-` |
| `plan_review_rounds` | `0` |
| `code_review_rounds` | `0` |
| `models` | *(samme modell-streng som foregående rader — statisk fra Modeller-tabellen)* |
| `health_payload` | Se format over |

Eksempel:
```
2026-06-19T16:00 | - | loop-health-check | health | - | - | 0 | 0 | planner/reviewer/implementer/code-reviewer={{MODELS_DISPLAY}} | sha=abc123def456abc123def456abc123def456abc123;tests=green;type=green;lint=green;rls=n/a;release=go
```

**Helseraden nullstiller merge-telleren** for N-merge-triggeren i §6c (se koordinator-runbooken).
