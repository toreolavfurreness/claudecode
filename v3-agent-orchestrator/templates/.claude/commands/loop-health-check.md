---
description: "Periodisk helsesjekk + release-rådgiver for orkestreringsloopen."
---
{{GENERATED_HEADER}}

# Loop: helsesjekk + release-rådgiver

## ⚠️ Hard grense (ufravikelig)

Denne kommandoen **vurderer og anbefaler** — den **utfører aldri** en prod-release.
`{{PROD_BRANCH}}` og produksjonsmiljøet (`{{PROD_ENV_ID}}`) berøres **aldri** av loopen uten at
mennesket eksplisitt gir det som oppgave. Anbefalingen er alltid «kjør `{{RELEASE_COMMAND}}` selv» —
**aldri** auto-merge til `{{PROD_BRANCH}}` — verken via `gh pr merge` eller REST
(`gh api --method PUT …/pulls/<nr>/merge`) — og aldri `git push origin {{PROD_BRANCH}}`.

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

### A5b — Web-smoke (betinget, tetter BUG-076-blindsonen: ingen annen gate faktisk LASTER web-appen)

Betinget som A5: sjekk om klientkode (`app/`, `components/`, `lib/`) er berørt siden forrige
helsesjekk (samme `<forrige_sha>` fra A1):

```bash
git diff <forrige_sha>..origin/{{BASE_BRANCH}} --name-only -- app/ components/ lib/
```

- Tom diff → hopp over web-smoke, sett `web=n/a` (ingen klientkode endret siden forrige helsesjekk).
- Ikke-tom diff (eller ingen forrige SHA — samme regel som A5) → kjør smoke-kommandoen:

```bash
{{CMD_WEB_SMOKE}}
```

**Preferert sti (unngår `n/a`):** start/gjenbruk Metro fra HOVEDSJEKKUTEN (ikke en nøstet
`.claude/worktrees/…`-sti) — `playwright.config.ts` har `reuseExistingServer: true` og bundler
mot port {{DEV_SERVER_PORT}}, så kommandoen kjører rent derfra. Hovedsjekkuten er alltid i
«Additional working directories», så koordinatoren har tilgang. Kostnad når den faktisk kjører:
~1–2 min (inkl. Metro-oppstart hvis ingen server allerede kjører på porten).

Utfallsklasser:
- Kjørte, alle asserts passerte → `web=green`
- Kjørte, feilet på en reell web-regresjon (login/lasting krasjer, konsoll-feil, DB-side-effekt) →
  `web=red` → A6 RØD (regresjon), eskalér. Dette er nøyaktig BUG-076-klassen denne gaten finnes for.
- Kjørte, feilet på nav-/locator-assert **urelatert** til noe som faktisk endret seg (spec-drift,
  f.eks. en gammel `getByText`-selector) → dette er IKKE en web-regresjon. Fiks spec-en (foretrekk
  testID-baserte locators) i en liten oppfølgings-PR, og behandle IKKE dette som pausepunkt for
  helsesjekken alene — men rapporter det tydelig i sammendraget.
- Kunne ikke kjøre pga. KJENT worktree-/Metro-begrensning (curl-probe-bekreftet, ikke bare antatt) →
  `web=n/a` (samme filosofi som `rls=n/a`/`e2e_not_applicable`) — eskalerer IKKE alene.
- Playwright selv ødelagt (manglende dep, config-feil — IKKE worktree-stien) → `web=infra-feil` →
  A6 RØD (infra), eskalér.

### A5c — Worktree-sweep-gate (TODO 380)

```bash
./tasks/worktree-sweep.sh --gate
```

Sletter ALDRI noe — den leser kun INNHOLDET i siste ikke-helse-§6-rad i `run-log.md` (token-basert,
ikke tidsstempel-basert — fix-runde 2, B1) og krever at raden bærer `wtsweep=<n>/<n>`.
`tasks/metrics/worktree-sweep-log.jsonl` er ren diagnostikk og leses ikke av gaten.

- `GATE GRØNN` (exit 0) → `wtsweep=green`
- `GATE RØD` (exit 1) → `wtsweep=red` → A6 RØD (infra): §6 steg 4b (beskrevet i §6d) har enten ikke
  kjørt siden forrige syklus, eller kjørte men skrev et feil-formet token. Dette er ikke en kodefeil
  — det er en uteblitt driftsrutine, og skal eskaleres på samme måte: fravær av sweep er nøyaktig
  den tilstanden som lot 72 agent-worktrees og 19,4 GB hope seg opp uten at noe noensinne ble rødt
  (målt i kildeprosjektet, TODO 380).

### A5d — Vakter utenfor loopen (TODO 368)

Noen vakter kan loopen ikke kjøre selv, fordi de leser et miljø loopen aldri skal lese (typisk prod).
De kjører som planlagte GitHub-workflows og bærer markørlinja `# loop-guard: max-age-hours=<N>`.
A5d leser aldri miljøet vakten vokter. Den sjekker bare at vakten kjører, og om den melder rødt.

```bash
git grep -l '^# loop-guard: max-age-hours=' origin/{{PROD_BRANCH}} -- .github/workflows/
```

- Exit 1 og tom output → ingen vakter → `vakt=n/a`. Exit ≥ 2 → `vakt=infra-feil`.
- Per treff (fjern `origin/{{PROD_BRANCH}}:`-prefikset): `<wf>` = filnavnet, `<N>` = tallet i markøren.

```bash
gh api "repos/{owner}/{repo}/actions/workflows/<wf>" --jq .state
gh run list --workflow <wf> --branch {{PROD_BRANCH}} --event schedule --status completed --limit 1 \
  --json createdAt,conclusion \
  --jq 'if length == 0 then "none" else (.[0] | "\(((now - (.createdAt | fromdateiso8601)) / 3600) | floor) \(.conclusion)") end'
git log -1 --first-parent --format=%ct origin/{{PROD_BRANCH}} -- .github/workflows/<wf>
```

`--first-parent` er påkrevd. Uten det gir `git log` tidspunktet for den opprinnelige feature-commiten,
ikke for mergen som brakte fila til `{{PROD_BRANCH}}` (målt på `ci.yml`: ~25 t forskjell). Alder i timer:
`echo $(( ($(date +%s) - <ct>) / 3600 ))`.

Per vakt, første regel som treffer:
1. `state` er ikke `active` → `vakt=red` (vakten er slått av).
2. Ingen fullført planlagt kjøring (`none`): fila landet på `{{PROD_BRANCH}}` for ≤ N timer siden →
   `vakt=n/a` (ny vakt); ellers → `vakt=red` (vakten har aldri kjørt).
3. Siste fullførte planlagte kjøring er eldre enn N timer → `vakt=red` (vakten har sluttet å kjøre).
4. Den er `success` → `vakt=green`.
5. Den er `failure` → `vakt=report-red`: vakten lever og melder rødt om miljøet den vokter. Det eies
   av eieren, ikke av loopen. Mangler kjøringen jobblogg, er det som regel GitHub som nektet å starte
   jobben (les ANNOTATIONS), ikke vaktens funn.
6. Annen konklusjon (`cancelled`, `timed_out`, `startup_failure` …) → `vakt=red`.

`vakt=red` og `vakt=infra-feil` → A6 RØD (infra). `vakt=report-red` endrer ikke A6: koordinatoren tar
med én linje til eieren i neste statusrapport, med kjøringens URL
(`gh run list --workflow <wf> --branch {{PROD_BRANCH}} --event schedule --limit 1 --json url --jq '.[0].url'`).
Flere vakter: verste utfall vinner (`infra-feil`/`red` > `report-red` > `n/a`/`green`).

### A6 — Helsesjekk-aggregering

Samlet helsesjekk-status:
- Alle sjekker `green` (eller `n/a`) → **GRØNN** — fortsett til Del B
- Minst én `red` (regresjon) → **RØD (regresjon)** — ⚠️ PAUSEPUNKT, eskalér til mennesket
- Minst én `infra-feil` (inkl. `wtsweep=red` og `vakt=red`) → **RØD (infra)** — ⚠️ PAUSEPUNKT, eskalér til
  mennesket med rå feilmelding

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
sha=<full-40-char-origin/{{BASE_BRANCH}}-HEAD-SHA>;tests=<green|red|infra-feil>;type=<green|red|infra-feil>;lint=<green|red|infra-feil>;rls=<green|red|n/a>;web=<green|red|n/a|infra-feil>;release=<go|no-go>
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
2026-06-19T16:00 | - | loop-health-check | health | - | - | 0 | 0 | planner/reviewer/implementer/code-reviewer={{MODELS_DISPLAY}} | sha=abc123def456abc123def456abc123def456abc123;tests=green;type=green;lint=green;rls=n/a;web=green;release=go
```

**Helseraden nullstiller merge-telleren** for N-merge-triggeren i §6c (se koordinator-runbooken).

---

## Del D — Nivå A/B-regelmotor (TODO 246, read-only mot repoet)

Del D kjøres FØR «Del C» over evalueres inn i pause/fortsett-beslutningen (dvs. et rødt Del D-funn
er samme klasse som Del A6 RØD — ⚠️ PAUSEPUNKT). Del D skriver INGENTING til repoet selv — kun til
koordinatorens rapportblokk; helseraden (Del C) bærer `release=go|no-go` som vanlig, upåvirket av
Del D's format.

### D1 — Regelmotor-selvtest

```bash
python3 tasks/decision-level.py --self-test
```

Krav: exit 0 **og** `30/30` i stderr-oppsummeringen. Ikke-grønn ⇒ **RØD** (regelmotoren selv er i
utakt med sine egne fixtures — ALDRI stol på klassifiseringer denne runden).

### D1b — Regelmotor ekte-kall-sjekk (runbookens DOKUMENTERTE `--context`-kall virker, ikke bare `--self-test`)

`--self-test`/`--dump-rules` bevisste at fixturene og tabellen stemmer, men fanger IKKE en
regresjon i selve `--event`-kalleformen runbooken instruerer koordinatoren om å skrive (kode-review
r1, BLOKKERENDE-funn: komma-sammenslått `--context` ga A0 på begge dokumenterte kall). Kjør de to
kalleformene ordrett slik de står i runbook-stegfilene `docs/superpowers/loop/steps/4-dispatch-reviewer.md` (avsnittet «Ved `technical_risk.flagged`») og `docs/superpowers/loop/steps/5b-kode-review.md` (revise-gate-punktet under «Gate») mot LEVENDE tre:

```bash
python3 tasks/decision-level.py --event technical_risk --context source=planner --context kind=docs_selfmod --context executable_gate=yes
python3 tasks/decision-level.py --event revise_gate_choice --context code_review_rounds=2 --context action=fix_round --context decision_logged=yes
```

Krav: begge exit 0 **og** `"level": "B"` (hhv. `"rule": "B5"` og `"rule": "B1"`) i JSON-outputen.
Enten kall som gir `"level": "A"`/`"rule": "A0"` ⇒ **RØD** — nivå B er da inert i drift uansett hva
D1/D2 sier, samme feilklasse som ble reprodusert og rettet i kode-review r1.

### D2 — Regel-paritet (skript ↔ runbook-prosa)

```bash
python3 tasks/decision-level.py --dump-rules > /tmp/decision-rules-script.tsv
grep -E '^\| [AB][0-9] \| ' docs/superpowers/loop/coordinator-runbook.md \
  | sed -E 's/^\| ([AB])([0-9]) \| (.*) \|$/\1\2\t\1\t\3/' > /tmp/decision-rules-runbook.tsv
diff /tmp/decision-rules-script.tsv /tmp/decision-rules-runbook.tsv
```

Krav: `diff` tom, begge filer 15 linjer (8 A + 7 B). Ikke-tom diff ⇒ **RØD** — regeltabellen har
driftet mellom kode og prosa etter merge av en senere PR (R3). *(Denne kommandoformen ble dry-run
verifisert i planleggingen av TODO 246 — 15/15 rader, tom diff, mot den ferdig substituerte
runbooken.)*

### D3 — Monoton decision-log (SEED_ONLY-beskyttelsen holder over tid)

```bash
# <forrige_sha> fra Del A1 over. Tom <forrige_sha> (ingen tidligere helsesjekk) ⇒ hopp over D3, ikke rødt.
FØR=$(git show <forrige_sha>:docs/superpowers/loop/decision-log.md 2>/dev/null | { grep -cE '^#{2,3} 20[0-9][0-9]-' || true; })
NÅ=$(grep -cE '^#{2,3} 20[0-9][0-9]-' docs/superpowers/loop/decision-log.md)
echo "FØR=$FØR NÅ=$NÅ"
```

Krav: `NÅ >= FØR`. `NÅ < FØR` ⇒ **RØD** (SEED_ONLY-beskyttelsen har sviktet — loggen ble
overskrevet eller forkortet). `2>/dev/null` dekker tilfellet der `<forrige_sha>` er FRA FØR
`decision-log.md` ble opprettet (fila fantes ikke i den commiten) — uten den gir `git show` en
`fatal:`-linje i output i stedet for et rent tall; `|| echo 0` dekker samme tilfelle for skall som
ikke bruker `pipefail`. **En bevisst periode-splitt av decision-loggen (CF-246-3) gjør D3 rød ÉN
GANG ved første helsesjekk etter splitten** (entry-tallet i den NYE fila starter på 0/lavt) — dette
er IKKE en reell SEED_ONLY-svikt; splitt-todoen MÅ oppdatere `SEED_ONLY` (begge `setup.md`-
tvillinger) OG dette D3-referansepunktet i SAMME PR, og den påfølgende røde helsesjekken kvitteres
manuelt av mennesket som forventet engangs-støy.

### D4 — Nivå-B-oppsummering + avstemming (mot run-loggen)

```bash
# 1. Tidsstempel for siste helsesjekk
awk -F' \| ' '/\| health \|/ {ts=$1} END {print ts}' docs/superpowers/loop/run-log.md

# 2. Antall [B*]-entries i decision-log ETTER FORMAT-V2-markøren og etter det tidspunktet
awk -v since="<TS fra steg 1, mellomrom i stedet for T>" '/FORMAT-V2/ { m=1; next } m && /^### 20[0-9][0-9]-/ { h=substr($0,5); if (substr(h,1,16) >= since && h ~ /\[B[0-9]+\]/) n++ } END { print n+0 }' docs/superpowers/loop/decision-log.md

# 3. Sum av auto_decided= + rader som mangler tokenet — ANKER-SCOPET på TODO 246s EGEN
#    merge-rad (180B-mønsteret, runbook-templaten 545-548), IKKE på siste helserad. 246 er
#    hardkodet (ikke en `<todo_nr>`-plassholder) fordi 246 er merge-raden der auto_decided-
#    kontrakten trådte i kraft — en helsesjekk er ikke scopet til «denne todoen», så en
#    plassholder her ville anker på feil rad (VIKTIG-funn, kode-review r1). ANKERRADEN
#    INKLUDERES i vinduet (ingen `next` etter `f=1`) — ekskludert next-form (180B-mønsteret for
#    selector=-tellingen over) rørte kun 180As FØR-kontrakt-rad; 246s egen rad bærer derimot
#    selve auto_decided-kontraktens FØRSTE gyldige token, så den skal telles med, ellers er
#    steg 2/3-vinduene forskjøvet med 246s egen runde (BLOKKERENDE-funn, kode-review r1).
awk '/\| 246 \|/{f=1} f' docs/superpowers/loop/run-log.md \
  | awk '/\| health \|/ { s=0; c=0; b=0; next } /^20[0-9][0-9]-/ { c++; if (match($0, /auto_decided=[^ |]*:[0-9]+/)) { t=substr($0, RSTART, RLENGTH); sub(/.*:/, "", t); s+=t } else b++ } END { print "sum=" s+0, "rader=" c+0, "mangler_token=" b+0 }'

# 4. Run-log-krysssjekk — tre deler, samme anker som steg 3 (hardkodet 246, se begrunnelsen over):
awk '/\| 246 \|/{f=1} f' docs/superpowers/loop/run-log.md \
  | awk -F' \| ' '$4 ~ /^(merged|paused)$/ && $7+0 > 2 {print $1, $2, "prr="$7}'   # V16a
awk '/\| 246 \|/{f=1} f' docs/superpowers/loop/run-log.md \
  | awk -F' \| ' '$4 ~ /^(merged|paused)$/ && $8+0 == 3 {print $1, $2, "crr="$8}'  # V16b
awk '/\| 246 \|/{f=1} f' docs/superpowers/loop/run-log.md \
  | awk -F' \| ' '$4 ~ /^(merged|paused)$/ && $8+0 >= 4 {print $1, $2, "crr="$8}'  # V16c
```

Krav: **steg 2 == sum (steg 3)** OG **mangler_token = 0** ⇒ `OK`. Avvik ⇒ **RØD** («AVVIK» i
rapportblokken), eskalér — en koordinator som logget et nivå-B-valg uten `auto_decided=` (eller
omvendt) har brutt en av de fire logg-pliktene. Hver V16a/b-treffende rad MÅ ha en tilsvarende
decision-log-entry (`[A0]` for V16a, `[B1]` for V16b). En V16c-treffende rad (`crr >= 4`) MÅ ha
enten `[B1]` (lukking — den vanlige klassen: `merge_carry`/`stop` ved `crr>=4` er B1 uansett
rundetall) eller `[A0]` (et forkastet nytt fix-runde-forsøk) — IKKE strengt `[A0]`. Rad uten NOEN
av de tillatte entry-typene ⇒ **RØD**.

**Residual (navngitt, ikke lukket av Del D4 alene):** `decision_logged=yes` og run-loggens
`code_review_rounds`-felt skrives av SAMME aktør i samme runde — se «Residual» i
`coordinator-runbook.md` § Pausepunkter for mitigeringen (`Runde-SHA:`-feltet + `git cat-file -e`).
Del D4 verifiserer IKKE `Runde-SHA:` mekanisk i denne PR-en (ingen `git log`-avhengig gate er lagt
til Del D — kun de fire kommandoene over); det er en dokumentert, bevisst avgrensning, ikke en
påstått lukket gate.

Rødt i D1-D4 ⇒ helsesjekk RØD (samme eskalering som Del A6) — §8b kjøres IKKE (se
`coordinator-runbook.md` «Etter §6c»).
