{{GENERATED_HEADER}}

# Loop: helsesjekk + release-rådgiver

## ⚠️ Hard grense (ufravikelig)

Denne kommandoen **vurderer og anbefaler** — den **utfører aldri** en prod-release.
`{{PROD_BRANCH}}` og produksjonsmiljøet (`{{PROD_ENV_ID}}`) berøres **aldri** uten at mennesket
eksplisitt gir det som oppgave. Anbefalingen er alltid «kjør `{{RELEASE_COMMAND}}` selv» —
**aldri** auto-merge til `{{PROD_BRANCH}}`, aldri `gh pr merge`/`git push origin {{PROD_BRANCH}}`.

**Koordinatoren kjører denne kommandoen selv** (single-writer-kontrakten) — ikke en dispatchet
worker. Helseraden i `docs/run-log.md` skrives av koordinatoren etter at kommandoen er fullført.

---

## Steg 0 — Fetch origin

Alle git-sammenligninger bruker `origin/{{BASE_BRANCH}}` og `origin/{{PROD_BRANCH}}` — aldri
lokale refs. Kjør dette først:

```bash
git fetch origin {{BASE_BRANCH}} {{PROD_BRANCH}}
```

## Del A — Helsesjekk (mot `origin/{{BASE_BRANCH}}`)

### A1 — Forrige helsesjekk-SHA (for betinget tech-sweep)

```bash
grep ' | health | ' docs/run-log.md | tail -1 | grep -oE 'sha=[0-9a-f]{40}' | cut -d= -f2
```

Tom output → ingen tidligere helsesjekk → tech-sweep kjøres ubetinget (se A4).

### A2 — Test / type-sjekk / lint (`verification_commands` i `loop.config.yaml`)

```bash
{{CMD_TEST}} > /tmp/hc-test.log 2>&1; echo "EXIT:$?"; tail -20 /tmp/hc-test.log
{{CMD_TYPE_CHECK}} > /tmp/hc-type.log 2>&1; echo "EXIT:$?"; tail -20 /tmp/hc-type.log
{{CMD_LINT}} > /tmp/hc-lint.log 2>&1; echo "EXIT:$?"; tail -20 /tmp/hc-lint.log
```

**Rapporter faktisk output og exit-kode** — bruk alltid fil-omdirigering + `$?`, aldri
`cmd | tail` (pipen svelger exit-koden). For hver kommando, klassifiser:
- Exit 0 → `green`
- Exit ≠ 0 med faktiske feil/testfeil i koden → `red` (regresjon, noter antall)
- Exit ≠ 0 uten domene-output (command not found, manglende dep, config-feil) → `infra-feil`
  (eskalér til mennesket, teller ikke som kode-regresjon)

### A3 — Tech-sweep (betinget, pluggbar)

Hvis `tech_review_agents` i `loop.config.yaml` har entries med en trigger-sti (f.eks. migrations/
domenespesifikke mapper): sjekk om stien er berørt siden forrige helsesjekk-SHA.

```bash
git diff <forrige_sha>..origin/{{BASE_BRANCH}} --name-only -- <trigger_sti>
```

Tom diff → hopp over, sett `<arm>=n/a`. Ikke-tom (eller ingen forrige SHA) → dispatch
tech-review-armen in-session (`task`), rapporter funn: `green` (ingen åpne funn) eller `red`
(funn som krever eskalering). Ingen tech-review-agenter konfigurert → alltid `n/a`.

### A4 — Barnesesjon-opprydding (Copilot-spesifikk, erstatter kildens worktree/lsof-sweep)

Siden implementer/verifier kjører som `create_session`-barnesesjoner (ikke rå git-worktrees),
er oppryddingsproblemet et annet enn i kilden: en krasjet/pauset dispatch kan la en idle
barnesesjon stå igjen uarkivert.

```
list_agents(scope: "children", include_completed: true)
```

For hver barnesesjon merket `completed`/`idle` der branchen allerede er fullt reflektert i
`origin/{{BASE_BRANCH}}` (dvs. PR-en er merget, ingen ukommiterte endringer gjensto): kjør
`archive_session`. **Unnta** barnesesjoner opprettet i INNEVÆRENDE runde eller markert
`blocked` (mennesket skal se dem) — arkiver aldri en `blocked`-sesjon automatisk.

## Del B — Release-anbefaling

Sammenlign `origin/{{BASE_BRANCH}}` mot `origin/{{PROD_BRANCH}}`:

```bash
git log origin/{{PROD_BRANCH}}..origin/{{BASE_BRANCH}} --oneline
```

Ikke-tom + Del A all-green → anbefal `{{RELEASE_COMMAND}}` til mennesket, med commitlisten som
begrunnelse. Én eller flere `red`/`infra-feil` i Del A → anbefal IKKE release, list hva som må
fikses først.

## Del C — Skriv helserad

Append til `docs/run-log.md`:

```
| <dato> | health | - | test=<green\|red\|infra-feil> type=<...> lint=<...> tech=<...\|n/a> sha=<origin/{{BASE_BRANCH}}-sha> |
```

Er `loop_eval.merge_interval`-tellingen (§6f i `docs/coordinator-runbook.md`) nådd samtidig:
kjør selvevalueringen og append en `| loop-eval |`-rad også.
