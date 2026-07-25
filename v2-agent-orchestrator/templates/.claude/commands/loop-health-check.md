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
{{CMD_TEST}} > /tmp/hc-test.log 2>&1; echo "EXIT:$?"; tail -20 /tmp/hc-test.log
```

**Rapporter faktisk output og exit-kode** — «burde funke» godkjennes ikke. (Fil-omdirigering + `$?`,
ALDRI `cmd | tail` — pipen svelger exit-koden og gate-n kan ikke blokkere.)

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

### A5b — Effektivitets-snapshot + worktree/branch-sweep (round-over-round sammenligning, ALDRI en pausetrigger)

Rent informasjonelt tillegg til helseraden — påvirker aldri GRØNN/RØD-status. Formålet er å gjøre
det billig å se om loop-optimaliseringer (se `docs/superpowers/loop/optimization-backlog.md`)
faktisk virker over tid, ved å legge noen få, billige nøkkeltall inn i samme append-only helserad
du allerede skriver i Del C. Sweepen under FJERNER faktisk (ikke bare teller) — den er backstop for
alt Lag 1 (§3/§5a i `coordinator-runbook.md`) ikke rakk å rydde selv: krasjede dispatcher,
pausepunkter, re-claims.

**Sikkerhetskriteriet er navneuavhengig** — ikke stol på branch-navnemønster (`worktree-agent-*`,
`claude/*` osv. drifter over tid og brukes også av legitime interaktive sesjoner). Et worktree
fjernes KUN hvis det er inaktivt OG innholdet er fullt reflektert i `{{BASE_BRANCH}}`.

**⚠️ Parallell-modus-vern (batch-15-funn):** UTSETT sweepen mens agenter dispatchet i INNEVÆRENDE
sesjon fortsatt lever — en aktiv reviewers rene worktree på base-branch-tipp matcher
fjerningskriteriet, og lsof-vernet dekker ikke agenter mellom verktøykall. Koordinatoren VET hvilke
agenter som kjører; sweep først når ingen egne agenter er aktive (eller ekskluder deres stier eksplisitt).

**Worktree-pass** (fjerner inaktive worktrees hvis branch allerede er fanget i `{{BASE_BRANCH}}`):

```bash
active_cwds=$(lsof -d cwd -Fn 2>/dev/null | grep '^n' | sed 's/^n//' | sort -u)
main_wt=$(git rev-parse --show-toplevel)
total=0
removed=0
while IFS= read -r wt_path; do
  total=$((total+1))
  [ "$wt_path" = "$main_wt" ] && continue

  branch=$(git -C "$wt_path" branch --show-current 2>/dev/null)
  [ -z "$branch" ] && continue

  locked=$(git worktree list --porcelain \
    | awk '/^worktree /{w=$2; lk=0} /^locked/{lk=1} w=="'"$wt_path"'" && lk{print "yes"; exit}')
  [ "$locked" = "yes" ] && continue

  if echo "$active_cwds" | grep -qxF "$wt_path"; then
    continue   # kjørende prosess har dette som cwd — rør ikke
  fi

  dirty=$(git -C "$wt_path" status --porcelain 2>/dev/null)
  [ -n "$dirty" ] && continue

  if git merge-base --is-ancestor "$branch" origin/{{BASE_BRANCH}} 2>/dev/null \
     || git diff --quiet origin/{{BASE_BRANCH}} "$branch" 2>/dev/null; then
    if git worktree remove "$wt_path" --force 2>/dev/null; then
      git branch -d "$branch" 2>/dev/null || git branch -D "$branch" 2>/dev/null
      removed=$((removed+1))
    fi
  fi
done < <(git worktree list --porcelain | grep '^worktree ' | sed 's/^worktree //')
echo "worktrees_total=$total;worktrees_stale=$removed"
```

`worktrees_stale` = antall worktrees faktisk FJERNET denne runden (betydning endret 2026-07-12 —
var tidligere kun et øyeblikksbilde-antall, se `docs/superpowers/loop/optimization-backlog.md`
tiltak #6). `lsof -d cwd`-sjekken kjøres ÉN gang for hele sweepen (ikke per worktree) — billig, og
lukker samme hull den manuelle 2026-07-12-oppryddingen måtte dekke med `lsof`/`ps aux` for hånd.

**Branch-pass** (orphans: brancher uten tilknyttet worktree — `fix/*`/`pr-*`-brancher fra
fix-mode-/kode-review-runder som allerede har mistet sitt worktree, jf. §5a-notatet om at
«agent-opprettede lokale brancher er repo-globale og overlever worktree-fjerning»). Navneuavhengig,
samme kriterium som over, minus lsof/dirty-sjekken (ingen working tree å sjekke uten worktree):

```bash
wt_branches=$(git worktree list --porcelain | grep '^branch refs/heads/' | sed 's#^branch refs/heads/##')
deleted=0
for b in $(git branch --format='%(refname:short)'); do
  [ "$b" = "{{BASE_BRANCH}}" ] && continue
  [ "$b" = "{{PROD_BRANCH}}" ] && continue
  echo "$wt_branches" | grep -qxF "$b" && continue   # har fortsatt et worktree — dekket av passet over

  if git merge-base --is-ancestor "$b" origin/{{BASE_BRANCH}} 2>/dev/null \
     || git diff --quiet origin/{{BASE_BRANCH}} "$b" 2>/dev/null; then
    if git branch -d "$b" >/dev/null 2>&1 || git branch -D "$b" >/dev/null 2>&1; then
      deleted=$((deleted+1))
    fi
  fi
done
echo "branches_stale_deleted=$deleted"
```

En branch som verken er ancestor ELLER tre-identisk med `origin/{{BASE_BRANCH}}` beholdes og nevnes
i rapporten (kan være en aktiv PR-branch eller upushet arbeid — aldri slett den automatisk). Merk:
tre-identisk-sjekken er kun pålitelig rett etter at branchen ble merget, før `{{BASE_BRANCH}}`
drifter videre — en kjent, eksisterende begrensning som gjenbrukes uendret her.

**Revisjons-rate siden forrige helsesjekk** (fanger opp om plan-kvalitet endrer seg over tid):

```bash
prev_line=$(grep -n ' | health | ' docs/superpowers/loop/run-log.md | tail -1 | cut -d: -f1)
tail -n +$((prev_line+1)) docs/superpowers/loop/run-log.md | grep ' | merged | ' > /tmp/since_last.txt
merges_since_last=$(wc -l < /tmp/since_last.txt)
needed_revision=$(awk -F' \\| ' '$7+0 >= 2' /tmp/since_last.txt | wc -l)
echo "merges_since_last=$merges_since_last;plan_revision_rate=$needed_revision/$merges_since_last"
```

`plan_revision_rate` = hvor mange av todoene siden forrige helsesjekk trengte ≥2 plan-review-runder
(dvs. fikk no-go første forsøk) av totalen. Et stigende tall over flere helsesjekk-rader tyder på at
planner enten får stadig vanskeligere todoer, eller at plan-kvaliteten svekkes — begge verdt å
undersøke, men INGEN av dem er en pausetrigger i seg selv.

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

Format for `health_payload` (fast rekkefølge, nøkkel=verdi-kjede). De fem siste feltene
(`worktrees_total`/`worktrees_stale`/`branches_stale_deleted`/`merges_since_last`/`plan_revision_rate`)
kommer fra A5b — rent informasjonelle, aldri en del av GRØNN/RØD-aggregeringen:

```
sha=<full-40-char-origin/{{BASE_BRANCH}}-HEAD-SHA>;tests=<green|red|infra-feil>;type=<green|red|infra-feil>;lint=<green|red|infra-feil>;rls=<green|red|n/a>;release=<go|no-go>;worktrees_total=<n>;worktrees_stale=<n>;branches_stale_deleted=<n>;merges_since_last=<n>;plan_revision_rate=<x/y>
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
2026-06-19T16:00 | - | loop-health-check | health | - | - | 0 | 0 | planner/reviewer/implementer/code-reviewer={{MODELS_DISPLAY}} | sha=abc123def456abc123def456abc123def456abc123;tests=green;type=green;lint=green;rls=n/a;release=go;worktrees_total=18;worktrees_stale=6;branches_stale_deleted=4;merges_since_last=5;plan_revision_rate=2/5
```

**Helseraden nullstiller merge-telleren** for N-merge-triggeren i §6c (se koordinator-runbooken).

**Round-over-round-sammenligning:** `grep ' | health | ' docs/superpowers/loop/run-log.md` gir alle
tidligere helserader i rekkefølge — les `worktrees_stale`- og `plan_revision_rate`-feltene på tvers
av radene for å se om `docs/superpowers/loop/optimization-backlog.md`-tiltakene faktisk monner over
tid (f.eks. `worktrees_stale` bør trende mot 0 etter tiltak #6; `plan_revision_rate` bør ikke trende
oppover etter tiltak #2/#7).
