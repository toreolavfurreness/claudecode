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

### A5b — Web-smoke (betinget, tetter blindsonen: ingen annen gate faktisk LASTER web-appen)

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
  `web=red` → A6 RØD (regresjon), eskalér. Dette er nøyaktig klassen denne gaten finnes for.
- Kjørte, feilet på nav-/locator-assert **urelatert** til noe som faktisk endret seg (spec-drift,
  f.eks. en gammel `getByText`-selector) → dette er IKKE en web-regresjon. Fiks spec-en (foretrekk
  testID-baserte locators) i en liten oppfølgings-PR, og behandle IKKE dette som pausepunkt for
  helsesjekken alene — men rapporter det tydelig i sammendraget.
- Kunne ikke kjøre pga. KJENT worktree-/Metro-begrensning (curl-probe-bekreftet, ikke bare antatt) →
  `web=n/a` (samme filosofi som `rls=n/a`/`e2e_not_applicable`) — eskalerer IKKE alene.
- Playwright selv ødelagt (manglende dep, config-feil — IKKE worktree-stien) → `web=infra-feil` →
  A6 RØD (infra), eskalér.

### A5c — Worktree-sweep-gate

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
  den tilstanden som lot 72 agent-worktrees og 19,4 GB hope seg opp uten at noe noensinne ble rødt.

### A5d — Vakter utenfor loopen

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

### A5e — Kostnadskalibrering

Sammenligner `measure-cost.py` sin egen sum med harnessens kostnadstall per avsluttet økt. Steget gjør
aldri helsesjekken rød.

```bash
python3 tasks/measure-cost.py --calibrate; echo "exit=$?"
```

`final` er andelen underagent-meldinger som har endelig usage. Exit 2 (ingen økt målt) →
**ADVARSEL**. Annen exit ≠ 0 uten en `over=yes`-linje (traceback, eller ingen sesjonskataloger) →
**ADVARSEL** med stderr ordrett. Per linje:
- `over=yes` uten `KJENT HULL` → **ADVARSEL**.
- `KJENT HULL` → meld som «KJENT HULL», ikke som ADVARSEL: fra Claude Code 2.1.281 mangler
  underagent-transkriptene endelig usage, så egen sum er for lav. `KJENT HULL` har ingen nedre grense
  og skjuler enhver undermåling i økta: prisfeil, avkortet hovedfil, manglende underagent-filer (når
  minst én underagent-melding er igjen) og avvik som stammer fra hovedfila.
- En linje med `final` under 50 % etterprøver ikke prisene, uansett `over=`. Har ingen linje `final` på
  50 % eller mer, meld steget som «ikke en prismåling denne runden». Prisene kan da bare etterprøves
  slik (`<fil>` i scratchpad):

```bash
curl -sL https://platform.claude.com/docs/en/about-claude/pricing.md -o <fil>
python3 tasks/measure-cost.py --prices-check <fil>
```

ADVARSEL, KJENT HULL og «ikke en prismåling denne runden» endrer ikke A6. Koordinatoren tar med én linje
per utfall til eieren i neste statusrapport, med calibrate-linja ordrett.

### A5f — Kit-drift

```bash
python3 tasks/kit-drift.py
```

Sjekker at kit-eide filer som skal være like i alle prosjekter (i dag `tasks/queue-status.py` og
Køsiden-raden i `docs/superpowers/loop/artifacts.md`) står som i `v3-agent-orchestrator/templates/`.

- Exit 0 → `kitdrift=green`.
- Exit 1 (`AVVIK`-linjer) → `kitdrift=avvik`. Endrer ikke A6: koordinatoren tar med AVVIK-linjene til
  eieren i neste statusrapport. Rettingen er `/setup` (malen inn), og prosjektspesifikke endringer
  flyttes til `tasks/queue-config.py`. Loopen redigerer aldri en kit-eid fil for å få vakten grønn.
- Exit 2 (`UKJENT`, fant ikke kit-malen) → `kitdrift=n/a`, med én linje i statusrapporten.

### A5g — Prosa-drift

Måler om linja et `fil:NNN`-sitat peker på, er endret siden sitatet ble skrevet. Steget gjør aldri
helsesjekken rød og endrer ikke A6.

```bash
python3 tasks/prose-drift.py --self-test; echo "exit=$?"
python3 tasks/prose-drift.py; echo "exit=$?"
```

- Selvtest med exit ≠ 0, eller måling med exit 2 → **ADVARSEL** med stderr ordrett. Tallet meldes ikke.
- Skriptet leser `HEAD`, mens helsesjekken gjelder `origin/{{BASE_BRANCH}}` (Steg 0). `ref` i `prosa-drift:`-linja
  skal være lik `git rev-parse --short=8 origin/{{BASE_BRANCH}}`. Avvik → **ADVARSEL**, og tallet meldes ikke.
- Ellers tar koordinatoren `prosa-drift:`-linja og hver `plan …`-linje ordrett med til eieren i neste
  statusrapport. Linjene er opplysning. Om en plan skal planlegges på nytt, er eierens valg.

Hva som er bindende (ingenting) og hvorfor, står i toppkommentaren i `tasks/prose-drift.py`.

### A5h — Graf-hygiene

```bash
python3 tasks/graph-build.py --lint; echo "exit=$?"
```

Tallene gjelder arbeidstreet helsesjekken kjøres i.

- Første linje føres ordrett som `hygiene=` i Del C. Exit ≠ 0 eller ingen `hygiene=`-linje →
  `hygiene=n/a` og en **ADVARSEL** med stderr ordrett.
- `forslag_stale`-linjene går til eieren i neste statusrapport som triage-liste: åpne (`status: open`
  og fjern taggen) eller slett.
- `deps_dangling`-linjene meldes som sannsynlig skrivefeil i `deps`.
- `cf_orphans` meldes bare som tall. Det er størrelsen på oppfølgingskøen uten eier, ikke en feil.

### A5i — Lessons-konsolidering

```bash
python3 tasks/lesson-audit.py --self-test; echo "selftest=$?"
python3 tasks/lesson-audit.py | tail -1
```

Steget gjør aldri helsesjekken rød.

- `selftest` ulik 0 → **ADVARSEL** med selvtestens utdata ordrett. Siste linje meldes da ikke.
- Starter siste linje med `KONSOLIDERING:`, tar koordinatoren linja ordrett med til eieren i neste
  statusrapport. Runden følger `tasks/lessons.md` § Konsoliderings-protokoll, og eieren velger når.
- Starter siste linje med `Ingen tema over terskelen`, er det ingen melding.
- Alt annet (tom utdata, feilmelding, traceback) → **ADVARSEL** med utdataen ordrett: målingen feilet.

### A5j — Lens-effekt og graf-treff

```bash
python3 tasks/loop-metrics.py; echo "exit=$?"
python3 tasks/loop-metrics.py --graph; echo "exit=$?"
```

Vinduet er mergene siden forrige helserad. Utskriften går ordrett i rapportblokka til eieren.
Ren rapportering: endrer ikke A6 eller Del C. Exit ≠ 0 gir en **ADVARSEL** med stderr ordrett
(`--graph` trenger nett og `gh`, og en rad uten måling står som `IKKE MÅLT`).

### A6 — Helsesjekk-aggregering

A5h er ren rapportering og endrer ikke A6.
A5i er ren rapportering og endrer ikke A6.

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

### B0 — Release-mål

```bash
python3 tasks/release.py status
```

Ta med utdataene ordrett. `DOM: INGEN AKTIV RELEASE` → hopp over resten av B0. Exit 2 (`FEIL`) →
rød helsesjekk.

### B2 — Brukervendte endringer siden siste release

Med en aktiv release: `python3 tasks/release.py notes <versjon>`. Ellers: les
`tasks/todo_archive.md` og finn todos ferdigstilt siden forrige release. Oppsummer titler og hva de
gir brukere.

```bash
git diff origin/{{PROD_BRANCH}}..origin/{{BASE_BRANCH}} --name-only -- 'src/**'
```

List berørte kildefiler for å gi et teknisk bilde av omfanget.

### B3 — Release-blokkerende bug-sjekk

```bash
test -f tasks/bugs.md && test -r tasks/bugs.md && awk 'function f(){if(h=="")return;m++;if(p==3)print "UKJENT " h;else if(p==2||(!p&&a))print h;else if(!s)print "UKJENT (ingen feltlinje) " h;else return;n++} /^## /{f();h="";p=a=s=0;if(/^## BUG-/)h=$0} {l=tolower($0)} l~/^[^a-z]*\*\*prioritet[^a-z]*:/{s=1;v=l;sub(/^[^a-z]*prioritet[ \t*:]*/,"",v);q=(v~/^(h(ø|Ø)y|kritisk)/)?2:(v~/^(lav|normal|middels)[ \t\r]*(\(|$)/)?1:3;if(q>p)p=q} l~/^[^a-z]*\*\*alvorlighet[^a-z]*:/{s=1;v=l;sub(/^[^a-z]*alvorlighet[ \t*:]*/,"",v);if(v~/^(h(ø|Ø)y|kritisk)/)a=1} END{f();print "B3: " n+0 " (av " m+0 " bugblokker)"}' tasks/bugs.md
```

Siste linje er `B3: <n> (av <m> bugblokker)`. Mangler den, er B3 ikke målt og aldri grønn (awk
feilet, eller `bugs.md` er ikke en lesbar fil). `av 0 bugblokker` er heller ikke målt: ingen
`## BUG-`-overskrift ble funnet. `B3: 0` med minst én bugblokk → bug-gaten er grønn (kun åpne bugs i
`bugs.md`; lukkede er i `bugs_archive.md`). Ellers → release-anbefaling = **no-go**, og linjene over
er lista over buggene.

Regelen er at bare en ren, kjent verdi kan senke en bug. Alt annet teller:

- **Høy:** Prioritet-verdien begynner med høy eller kritisk. Buggen teller.
- **Lav:** Prioritet-verdien er lav, normal eller middels, fulgt av linjeslutt eller en parentes
  (`lav (nedjustert 12.10)`). Buggen teller ikke, uansett Alvorlighet.
- **Ukjent:** alt annet etter Prioritet-nøkkelen, også tom verdi, tegn foran verdien
  (`~~lav~~ høy`, `(lav)`) og sammensatte verdier (`Middels-Høy`, `Normal → Høy`, `lav – utsatt`).
  Buggen står som `UKJENT <overskrift>` og teller til verdien er rettet.
- **Strengeste Prioritet-linje i blokka gjelder** (lav < høy < ukjent), ikke siste: en bug senkes ved
  å rette linja, ikke ved å legge en ny under.
- **Alvorlighet** gjelder bare når blokka ikke har noen Prioritet-linje. Buggen teller da bare når
  Alvorlighet-verdien begynner med høy eller kritisk. Lav- og ukjent-testen gjelder
  Prioritet-verdien: en annen Alvorlighet-verdi (`Middels-Høy`, `Lav`, tom) gir ikke `UKJENT`, og
  buggen teller ikke.
- **Ingen feltlinje:** en bugblokk uten noen gjenkjent Prioritet- eller Alvorlighet-linje står som
  `UKJENT (ingen feltlinje) <overskrift>` og teller til en feltlinje er satt.

En feltlinje kjennes igjen når `**` står rett foran `Prioritet` eller `Alvorlighet`, med kolon
innenfor eller utenfor feten, og med punkttegn, sitattegn (`>`) eller innrykk foran. Linja må
begynne uten bokstaver foran feten: `- [x] **Prioritet:** høy` gjenkjennes ikke, og prosa uten fet
skrift (`Prioritet: høy`) er ikke en feltlinje. Har blokka ingen annen feltlinje, gjelder
«Ingen feltlinje» over. Etter nøkkelen fjernes bare blanktegn, `*` og `:` før verdien leses. Store
og små bokstaver er like.

### B4 — Go/no-go-anbefaling

Skriv en strukturert anbefaling:

```
Release-anbefaling: go | no-go

Begrunnelse:
- Urealiserte commits: N stk
- Brukervendte endringer: [liste]
- Kritiske bugs (høy prioritet): N stk [evt. BUG-IDer]
- Release-mål: <DOM-linja fra B0, eller «ingen aktiv release»>
- Helsesjekk: grønn | rød

Neste steg (hvis go): kjør `{{RELEASE_COMMAND}}` selv.
Neste steg (hvis no-go): [konkret hva som må fikses]
```

Med en aktiv release er anbefalingen **no-go** til DOM er `MÅL NÅDD`. Mennesket kan likevel
velge å release, men loopen anbefaler det ikke.

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
sha=<full-40-char-origin/{{BASE_BRANCH}}-HEAD-SHA>;tests=<green|red|infra-feil>;type=<green|red|infra-feil>;lint=<green|red|infra-feil>;rls=<green|red|n/a>;web=<green|red|n/a|infra-feil>;release=<go|no-go>;hygiene=<cf_orphans:N,deps_dangling:N,forslag_stale:N|n/a>
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
2026-06-19T16:00 | - | loop-health-check | health | - | - | 0 | 0 | planner/reviewer/implementer/code-reviewer={{MODELS_DISPLAY}} | sha=abc123def456abc123def456abc123def456abc123;tests=green;type=green;lint=green;rls=n/a;web=green;release=go;hygiene=cf_orphans:0,deps_dangling:0,forslag_stale:0
```

**Helseraden nullstiller merge-telleren** for N-merge-triggeren i §6c (se koordinator-runbooken).

---

## Del D — Nivå A/B-regelmotor (read-only mot repoet)

Del D kjøres FØR «Del C» over evalueres inn i pause/fortsett-beslutningen (dvs. et rødt Del D-funn
er samme klasse som Del A6 RØD — ⚠️ PAUSEPUNKT). Del D skriver INGENTING til repoet selv utenom D4-rettingene — kun til
koordinatorens rapportblokk; helseraden (Del C) bærer `release=go|no-go` som vanlig, upåvirket av
Del D's format.

### D1 — Regelmotor-selvtest

```bash
python3 tasks/decision-level.py --self-test
```

Krav: exit 0 **og** `61/61` **og** `logg-parser: PASS` **og** `avstemming: PASS` i stderr-oppsummeringen. Ikke-grønn ⇒ **RØD** (regelmotoren selv er i
utakt med sine egne fixtures — ALDRI stol på klassifiseringer denne runden).

### D1b — Regelmotor ekte-kall-sjekk (runbookens DOKUMENTERTE `--context`-kall virker, ikke bare `--self-test`)

`--self-test`/`--dump-rules` bevisste at fixturene og tabellen stemmer, men fanger IKKE en
regresjon i selve `--event`-kalleformen runbooken instruerer koordinatoren om å skrive (kode-review
r1, BLOKKERENDE-funn: komma-sammenslått `--context` ga A0 på begge dokumenterte kall). Kjør
kalleformene ordrett slik de står i runbook-stegfilene `docs/superpowers/loop/steps/4-dispatch-reviewer.md` (avsnittet «Ved `technical_risk.flagged`») og `docs/superpowers/loop/steps/5b-kode-review.md` (revise-gate-punktet under «Gate») mot LEVENDE tre:

```bash
python3 tasks/decision-level.py --event technical_risk --context source=planner --context kind=docs_selfmod --context executable_gate=yes
python3 tasks/decision-level.py --event revise_gate_choice --context code_review_rounds=2 --context action=fix_round --context decision_logged=yes --context blocking_prev=3 --context blocking_now=1 --context new_class=no --context content=no --context cost_over=no
python3 tasks/decision-level.py --event revise_gate_choice --context code_review_rounds=2 --context action=fix_round --context decision_logged=yes --context blocking_prev=2 --context blocking_now=2 --context new_class=no --context content=no --context cost_over=no
python3 tasks/decision-level.py --event plan_review_choice --context plan_review_rounds=2 --context action=revise --context blocking_prev=2 --context blocking_now=2 --context new_class=no --context content=no --context cost_over=no
python3 tasks/decision-level.py --event revise_gate_choice --context code_review_rounds=2 --context action=fix_round --context decision_logged=yes --context blocking_prev=3 --context blocking_now=1 --context new_class=no --context content=yes --context cost_over=no
python3 tasks/decision-level.py --event revise_gate_choice --context code_review_rounds=1 --context action=fix_round --context cost_over=yes
python3 tasks/decision-level.py --event revise_gate_choice --context code_review_rounds=2 --context action=fix_round --context decision_logged=yes --context blocking_prev=3 --context blocking_now=1 --context new_class=no --context content=no --context cost_over=few
python3 tasks/decision-level.py --event plan_review_choice --context plan_review_rounds=2 --context action=revise --context blocking_prev=2 --context blocking_now=1 --context new_class=no --context content=no --context cost_over=few
python3 tasks/decision-level.py --event plan_review_choice --context plan_review_rounds=2 --context action=revise --context blocking_prev=2 --context blocking_now=1 --context new_class=no --context content=yes --context cost_over=no
python3 tasks/decision-level.py --event technical_risk --context source=planner --context kind=native --context native_dep=no --context native_permission=no
python3 tasks/decision-level.py --event revise_gate_choice --context code_review_rounds=4 --context action=fix_round --context decision_logged=yes --context blocking_prev=3 --context blocking_now=1 --context new_class=no --context content=no --context cost_over=no
```

Krav, i rekkefølge:

1. exit 0 og `"rule": "B5"`. Den dokumenterte kalleformen virker.
2. exit 0 og `"rule": "B1"`. En fix-runde der funnene går ned, er nivå B.
3. exit 0 og `"rule": "B1"`. Gate-funnene går ikke ned (2→2) i §5b: nivå B.
   Gir det A0, er flyttingen borte.
4. exit 0 og `"rule": "B7"`. Samme tall i §4: nivå B.
   Gir det A0, er flyttingen borte.
5. exit 1, `"rule": "A0"` og `content='yes'` i `violations`. Innholdsfunn er nivå A også i §5b.
6. exit 1, `"rule": "A0"` og `cost_brake` i `violations`. Kostnadsbremsen gjelder fra runde 1.
7. exit 1, `"rule": "A0"` og `cost_over='few'` i `violations`. For få sammenlignbare todoer stopper
   §5b fra runde 2.
8. exit 1, `"rule": "A0"` og `cost_over='few'` i `violations`. For få sammenlignbare todoer stopper
   også §4 fra runde 2.
9. exit 1, `"rule": "A0"` og `content='yes'` i `violations`. Innholdsfunn er nivå A også i §4.
10. exit 0 og `"rule": "B8"`. Native kodearbeid uten ny avhengighet og uten ny tillatelse er nivå B.
11. exit 1, `"rule": "A0"` og `round_stop` som eneste oppføring i `violations`. Rundestoppet gjelder fra
    runde 4.

Ett avvik ⇒ **RØD**. Gir kall 1–4 og 10 `"level": "A"`, er nivå B inert i drift uansett hva D1/D2 sier.
Gir kall 5–9 og 11 nivå B,
bestemmer koordinatoren selv noe eieren skal spørres om.

### D2 — Regel-paritet (skript ↔ runbook-prosa)

```bash
python3 tasks/decision-level.py --dump-rules > /tmp/decision-rules-script.tsv
grep -E '^\| [AB][0-9] \| ' docs/superpowers/loop/coordinator-runbook.md \
  | sed -E 's/^\| ([AB])([0-9]) \| (.*) \|$/\1\2\t\1\t\3/' > /tmp/decision-rules-runbook.tsv
diff /tmp/decision-rules-script.tsv /tmp/decision-rules-runbook.tsv
```

Krav: `diff` tom, begge filer 16 linjer (8 A + 8 B). Ikke-tom diff ⇒ **RØD** — regeltabellen har
driftet mellom kode og prosa etter merge av en senere PR (R3).

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
ikke bruker `pipefail`. **En bevisst periode-splitt av decision-loggen gjør D3 rød ÉN
GANG ved første helsesjekk etter splitten** (entry-tallet i den NYE fila starter på 0/lavt) — dette
er IKKE en reell SEED_ONLY-svikt; splitt-todoen MÅ oppdatere `SEED_ONLY` (begge `setup.md`-
tvillinger) OG dette D3-referansepunktet i SAMME PR, og den påfølgende røde helsesjekken kvitteres
manuelt av mennesket som forventet engangs-støy.

### D4 — Nivå-B-oppsummering + avstemming (mot run-loggen)

```bash
# Avstemming: hver run-log-rad siden siste helsesjekk mot oppføringene som hører til raden.
python3 tasks/decision-level.py --reconcile

# Run-log-krysssjekk — tre deler. Ankeret er hardkodet 246 (ikke en `<todo_nr>`-plassholder):
# 246 sin merge-rad er der auto_decided-kontrakten trådte i kraft, og raden selv er med i vinduet.
awk '/\| 246 \|/{f=1} f' docs/superpowers/loop/run-log.md \
  | awk -F' \| ' '$4 ~ /^(merged|paused)$/ && $7+0 > 2 {print $1, $2, "prr="$7}'   # V16a
awk '/\| 246 \|/{f=1} f' docs/superpowers/loop/run-log.md \
  | awk -F' \| ' '$4 ~ /^(merged|paused)$/ && $8+0 == 3 {print $1, $2, "crr="$8}'  # V16b
awk '/\| 246 \|/{f=1} f' docs/superpowers/loop/run-log.md \
  | awk -F' \| ' '$4 ~ /^(merged|paused)$/ && $8+0 >= 4 {print $1, $2, "crr="$8}'  # V16c
```

Krav til avstemmingen: exit 0 ⇒ `OK`. Exit 1 ⇒ rett selv: sett `auto_decided=<nr>:<n>` på hver
`AVVIK`-, `FEIL_FORM`- og `MANGLER_TOKEN`-rad til `logg=`-tallet fra linja, skriv én oppføring
`### <tid> — loop [D4]: rettet <n> rader` i decision-log med `<radtid> <nr> før→etter` per rad, og kjør
`--reconcile` én gang til. Exit 0 ⇒ `OK (rettet <n>)`. Er det fortsatt exit 1 (også `etter merged-rad`), er
det **RØD**: gjengi linjene i rapportblokken og eskalér. Ved `rad > logg` kan det være loggen som mangler
en beslutning. Oppføringen navngir da hvilken beslutning som mangler logg-oppføring, eller sier at ingen
mangler. `run-log.md` er append-only. Å rette `auto_decided`-tokenet på en rad i D4 er det eneste tillatte unntak.
D4-rettinger gjengis i rapportblokken, fordi `--recent-b` bare viser `[B…]`. Navngir en `[D4]`-oppføring en beslutning som mangler i loggen, står den i rapportblokken på egen linje `ulogget nivå B-valg: <nr> <hva>`, så eieren kan vetoe den. En rad som fører et annet tall enn loggen
gir, eller et nivå-B-valg uten rad, er brudd på en av de fire logg-pliktene. Exit 2 (en fil kan
ikke leses, eller markøren mangler) ⇒ **RØD**. `rader=0` er et tomt vindu og skrives slik.

`FEIL_FORM` er en rad der nøkkelen foran kolon ikke er radens todo (f.eks. `koordinator:3`), og rettes som `AVVIK`.
`<tid> A0 MANGLER_TYPE` og `<tid> A0 UKJENT_TYPE <ledd>` er en `[A0]`-oppføring skrevet etter 516s `merged`-rad uten
`Type` i `SLAG`: sett `Type`-linja i oppføringen, og før den i `[D4]`-oppføringen som `<tid> Type: <verdi>`.
Sumlinja teller dem i `a0_feil=<n>`.

Regelen (`attribute()` i skriptet, samme funksjon som `--auto-decided` i §6 steg 5): en
`[B<siffer>]`-oppføring eies av første `TODO <nr>` i overskriften og telles på eierens første rad
med radtid ≥ oppføringstid. `venter på merge` (eieren har ingen rad ennå, eller siste rad er ikke
`merged`) og `uten todo` gjengis i rapportblokken og gir ikke rødt. **Eierløse B-valg (`— loop
[Bn]`) står ikke på noen rad og avstemmes ikke.** De telles bare. Run-log-rader med `-` i todo-feltet (felt 2) hoppes over av `attribute()` og avstemmes heller ikke. `etter merged-rad` kan bli rødt for
en todo som er åpnet igjen etter merge. Linja forsvinner når todoen får ny rad.

**B8-kontrollen.** En todo godkjent under B8 skal ha rad på eierens iPhone-liste:

```bash
L=docs/superpowers/loop/decision-log.md; R=docs/superpowers/loop/run-log.md; E=tasks/releases
for n in $(awk -F' \\| ' '$4=="health"{s=""; next} $4=="merged"{s=s" "$2} END{print s}' "$R"); do
  grep -qE "^### .{16} — TODO $n \[B8\]" "$L" || continue
  awk '/^## Eierpunkter/{f=1;next} /^## /{f=0} f' "$E"/*.md | grep -qiE "iPhone[^:]*-lista[^:]*: $n([^0-9A-Za-z]|\$)" || echo "MANGLER iPhone-rad: $n"
done
```

Krav: tom utdata. Vinduet er merged-radene siden forrige helsesjekk, som i avstemmingen. Raden står under
`## Eierpunkter` i releasefila og har formen `iPhone-lista: <nr> …` (også `iPhone/iPad-lista`), med todo-nummeret rett etter kolonet (ett nummer per rad, ikke intervall).
`MANGLER iPhone-rad` rettes som et D4-avvik: legg raden til, før det i `[D4]`-oppføringen og kjør blokken
på nytt. Gir den fortsatt utdata ⇒ **RØD**.

Hver V16a/b-treffende rad MÅ ha en tilsvarende
decision-log-entry (`[B7]` eller `[A0]`/`[A…]` for V16a, `[B1]` eller `[A0]`/`[A…]` for V16b — det
finnes ikke noe fast rundetak, så runde 3+ kan være en B-runde). En V16c-treffende rad (`crr >= 4`) MÅ ha
enten `[B1]` (lukking — den vanlige klassen: `merge_carry`/`stop` ved `crr>=4` er B1 uansett
rundetall) eller `[A0]` (et forkastet nytt fix-runde-forsøk: fra runde 4 er en ny fix-runde alltid A0) — IKKE strengt `[A0]`. Rad uten NOEN
av de tillatte entry-typene ⇒ **RØD**.

**Residual (navngitt, ikke lukket av Del D4 alene):** `decision_logged=yes` og run-loggens
`code_review_rounds`-felt skrives av SAMME aktør i samme runde — se «Residual» i
`coordinator-runbook.md` § Pausepunkter for mitigeringen (`Runde-SHA:`-feltet + `git cat-file -e`).
Del D4 verifiserer IKKE `Runde-SHA:` mekanisk i denne PR-en (ingen `git log`-avhengig gate er lagt
til Del D — kun kommandoene over); det er en dokumentert, bevisst avgrensning, ikke en
påstått lukket gate.

### D5 — Treffsikkerhet per type

```bash
python3 tasks/decision-level.py --agreement
```

TSV-en (`type n fulgt avvek forslag`) går inn i rapportblokken. En rad med `flytt-til-B` gir ett
nivå A-spørsmål (`Type: calibration`, se `coordinator-runbook.md` § Kalibrering). Exit ≠ 0 ⇒ **RØD**.
En type som alt har en `[B, calibration]`-oppføring med samme `Type`, får `-` og foreslås ikke på
nytt. `-` demper også et nytt `flytt-til-B` for samme type, så en videre utvidelse av en flyttet
type (f.eks. `content=yes` for `revise_gate_choice`) må tas opp manuelt. Dempingen varer for alltid, også etter en VETO mot flyttingen; en tilbakeføring
må da også tas opp manuelt.

En type foreslås bare når leddet foran kolon står i `SLAG` i `tasks/decision-level.py`. I slaget
`eiervalg` foreslås en rad bare med kort-navnet `mekanisk` (f.eks. `eiervalg:mekanisk`,
`release_scope:mekanisk`): et eiervalg som er uklassifisert, `struktur` eller `produkt`, får alltid `-`.

**Minste N:** en rad leses ikke som en rate før n ≥ 10. `flytt-til-B` krever i tillegg at de ti
siste svarene er fulgt. Kolonnen `avvek` betyr «ikke i fulgt-form», så fritekstsvar teller mot
delegering.

Kalibreringsspørsmålet for en rad med kort-navnet `mekanisk` i eiervalg-slaget (f.eks.
`eiervalg:mekanisk`, `release_scope:mekanisk`) lister overskriftene til de ti siste oppføringene, så eieren kan underkjenne klassifiseringen. En godkjenning gjelder bare det navngitte underområdet
regel-PR-en beskriver, ikke hele klassen. Etter godkjenningen viser raden `-`, og flere underområder
tas opp manuelt.

Rapportblokken oppgir også antall tellende oppføringer i eiervalg-slaget uten klasse:
summen av `n` for rader der leddet hører til slaget `eiervalg` i `SLAG` i `tasks/decision-level.py`,
og kort-navnet ikke er `mekanisk`, `struktur` eller `produkt`.

Rødt i D1-D5 ⇒ helsesjekk RØD (samme eskalering som Del A6) — §8b kjøres IKKE (se
`coordinator-runbook.md` «Etter §6c»).
