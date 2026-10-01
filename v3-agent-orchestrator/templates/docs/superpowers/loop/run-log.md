<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her (kun format-spec).
  Endre loop.config.yaml og kjør /setup på nytt.
  MERK: Logg-tabellen nederst er append-only data som koordinatoren skriver
  under kjøring — /setup overskriver IKKE eksisterende logg-rader ved re-kjøring
  hvis du beholder dem. Ved første generering er den tom (kun header).
-->

# Loop run-log (koordinator-telemetri)

**Single-writer-kontrakt:** Kun koordinatoren skriver til denne filen. Workers returnerer
telemetri som data i ferdig-rapportens `notes` og `lessons` — koordinatoren leser og appender.
Workers rører ALDRI run-log.md.

---

## Format-spec

Én linje per runde. Alle felt er obligatoriske; `pause_event` settes til `-` når `outcome=merged`.

| Felt | Type | Lovlige verdier | Kilde |
|---|---|---|---|
| `timestamp` | `YYYY-MM-DDTHH:MM` | ISO 8601 (minutter) | Koordinatorens kontekst — tidspunkt for §6-skriving |
| `todo_nr` | streng | e.g. `"69"`, `"6C3a"`, `-` (health-rader) | Ferdig-rapport `todo_nr` (eller plan-rapport ved paused-før-impl.; `-` for health-rader) |
| `slug` | streng | | Ferdig-/plan-rapport `slug`; `loop-health-check` for health-rader |
| `outcome` | enum | `merged` \| `paused` \| `failed` \| `blocked` \| `health` \| `hotfix` | Koordinatorens kontekst: utledet fra hvilken §-gate som traff; `health` for §6c-helsesjekk-rader |
| `pause_event` | enum / `-` | `teknisk-risiko` \| `brainstorm` \| `reviewer-no-go` \| `revise-gate` \| `probe-feil` \| `merge-konflikt` \| `canary-mismatch` \| `proporsjon` \| `plan-invalid` (andre på samme todo) \| `release` (§1: scope tomt eller blokkert, eller `release.py` exit 2) \| `helsesjekk-rød` \| `ci-rød` (alle ikke-grønne CI-utfall: red/cancelled/pending/missing/error — `ci=` i notatet skiller dem) \| `-` | Koordinatorens kontekst — sett iff `outcome=paused`; `-` for health-rader (grønn) eller `helsesjekk-rød` (rød + eskalert); ellers `-` |
| `pr` | URL / `-` | | Ferdig-rapport `pr_url`; `-` ved paused-før-PR og health-rader |
| `plan_review_rounds` | heltall / `-` | `1`, `2`, ... , `-` (hotfix-rader) | Koordinatorens kontekst — §4-telleren; `0` for health-rader |
| `code_review_rounds` | heltall / `-` | `0`, `1`, `2`, ... , `-` (hotfix-rader) | Koordinatorens kontekst — §5b-telleren (`0` ved paused-før-implementering og health-rader) |
| `models` | streng | | Statisk fra Modeller-tabellen i `docs/orchestration-loop.md` ved skrivetidspunktet — tidsstemplet snapshot av hvilke modeller som faktisk var konfigurert |
| `health_payload` | streng / `-` | Se format under | Fast nøkkel=verdi-kjede for `outcome=health`-rader; `-` for alle andre rader (invariant) |
| `degradation` | streng / `-` | `-` \| `e2e=<verdi>;web_smoke=<verdi>` | Kilde: ferdig-rapportens `verification.e2e_outcome` + `verification.web_smoke_outcome` (fem-verdi-enum, se `report-schema.md`). Formel: `outcome=health` ⟹ `-` (carve-out). `outcome=paused` uten ferdig-rapport ⟹ `-` (carve-out). `e2e_outcome == e2e_green` OG `web_smoke_outcome == e2e_green` ⟹ `-`. Ellers `"e2e=<e2e_outcome>;web_smoke=<web_smoke_outcome>"`. Manglende felt i en rad som HAR en ferdig-rapport ⟹ `e2e_blocked:missing_outcome_field` for det manglende feltet. `e2e_not_applicable` er IKKE en degradering, men logges eksplisitt. |

**`health_payload`-format (kun `outcome=health`-rader):**

Fast rekkefølge — alle nøkler obligatoriske:

```
sha=<full-40-char-origin/{{BASE_BRANCH}}-HEAD-SHA>;tests=<green|red|infra-feil>;type=<green|red|infra-feil>;lint=<green|red|infra-feil>;rls=<green|red|n/a>;web=<green|red|n/a|infra-feil>;release=<go|no-go>
```

- `sha=` — `origin/{{BASE_BRANCH}}`-HEAD-SHA på tidspunktet for helsesjekken. Brukes av neste helsesjekk for
  å avgrense tech-sweep-gaten. Les med:
  `grep ' | health | ' run-log.md | tail -1 | grep -oE 'sha=[0-9a-f]{40}' | cut -d= -f2`
  Tom → ingen tidligere helsesjekk → tech-sweep kjøres ubetinget.
- `tests/type/lint` — `green` (ok), `red` (regresjon: runner rapporterte feil i koden),
  `infra-feil` (kommando feilet å starte: manglende dep, config-feil, OOM — IKKE regresjon).
- `rls` — `green` (ingen åpne hull), `red` (funn som krever eskalering), `n/a` (ingen
  tech-relevante endringer siden forrige helsesjekk, eller ingen tech-review-agenter konfigurert).
- `web` — web-lastings-/login-smoke (A5b, tetter BUG-076-blindsonen): `green` (kjørte, passerte),
  `red` (kjørte, reell web-regresjon — eskalér), `n/a` (kjent worktree-/Metro-begrensning,
  curl-probe-bekreftet — eskalerer IKKE, samme filosofi som `rls=n/a`), `infra-feil` (Playwright selv
  ødelagt, ikke worktree-stien — eskalér).
- `release` — `go` (alt grønt + ingen høy-prioriterte bugs) eller `no-go` (minst ett hinder).

**Invarianter:**
- `outcome=paused` ⟹ `pause_event` MÅ være ett av de lovlige pausepunkt-verdiene (ikke `-`).
- `outcome=health` ⟹ `pause_event = -` (grønn) eller `pause_event = helsesjekk-rød` (rød + eskalert). `pr = -`. `plan_review_rounds = 0`. `code_review_rounds = 0`. `todo_nr = -`. `slug = loop-health-check`. `health_payload` MÅ ha alle sju nøkler i fast rekkefølge (health-rader skrevet før 2026-07-12 har legacy 6-nøkkel-form uten `web=` — de regnes IKKE om i ettertid). `degradation = -`.
- `outcome=merged|failed|blocked` ⟹ `pause_event` SKAL være `-`. `health_payload = -` (invariant).
- `outcome=hotfix` ⟹ `todo_nr = -`. `pause_event = -`. `plan_review_rounds = -`. `code_review_rounds = -`.
  `models = utenfor-loopen`. `pr` = PR-URL. `health_payload` bærer notatet (symptom+rotårsak+fiks+filer),
  `degradation = -`. Se `docs/hotfix-runbook.md`.
- **Kun `outcome=merged` telles av §6c** — `hotfix` og de andre er usynlige for merge-tellerne, med
  vilje: en etterfylt hotfix-rad skal aldri blåse opp en teller den ikke hørte til.
- `models`-feltet skrives som et fast kjede-uttrykk på formen `planner/reviewer/implementer/code-reviewer=<modell>/<modell>/<modell>/<modell>` — hentes fra Modeller-tabellen, ikke fra rapporten.
- `degradation` bærer e2e-utfallsparet og settes alltid. `-` betyr at både full suite og web-smoke
  kjørte grønt — eller at raden er unntatt per carve-out over (`outcome=health` eller
  `outcome=paused` uten ferdig-rapport). `e2e_not_applicable` er IKKE en degradering, men logges
  eksplisitt for sporbarhet.

---

## Eksempel-logglinje (merged-rad)

```
2026-06-19T14:30 | 69 | loop-run-log | merged | - | https://github.com/{{GITHUB_REPO}}/pull/214 | 1 | 1 | planner/reviewer/implementer/code-reviewer={{MODELS_DISPLAY}} | - | -
```

## Eksempel-logglinje (health-rad)

```
2026-06-19T16:00 | - | loop-health-check | health | - | - | 0 | 0 | planner/reviewer/implementer/code-reviewer={{MODELS_DISPLAY}} | sha=1a7f4a5b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f;tests=green;type=green;lint=green;rls=n/a;web=green;release=go | -
```

---

## Avstemming — klassifiserte PR-er uten rad

**Formål:** idempotent demping av run-log-avstemmingen i `.claude/commands/run-loop.md`
(§ Preflight 4). De fleste PR-er den finner er legitimt uten rad (todo-filer, docs, bug-drops) —
uten et sted å bokføre «trenger ingen rad» rapporteres de samme PR-ene hver sesjon.

**Format:** én linje per klassifisert PR, alltid med full `pull/<nr>`-URL (den er grep-ankeret
sjekken leser): `- <dato> [PR #<nr>](<full pull/<nr>-URL>): <klasse> — <begrunnelse>`, `<klasse>` ∈
`ingen kode` (kun `tasks/`/`docs/`) \| `kode utenfor loopen` (kildefiler, se `docs/hotfix-runbook.md`)
\| `release-merge` (PR mot `{{PROD_BRANCH}}` som er en vanlig release, ikke en hotfix). En port til
`{{PROD_BRANCH}}` av en allerede logget fiks klassifiseres her som `kode utenfor loopen` med henvisning
til logg-raden — den får aldri egen `outcome=hotfix`-rad (én fiks = én rad).

**Plassering:** står OVER `## Logg` med vilje — §6 appender rader til filslutt, så `## Logg` må
være siste seksjon. Append-only, koordinator er eneste skriver. §6-radene går ALDRI hit. Denne seksjonen er klassifisering, ikke telemetri.

## Logg

| timestamp | todo_nr | slug | outcome | pause_event | pr | plan_review_rounds | code_review_rounds | models | health_payload | degradation |
|---|---|---|---|---|---|---|---|---|---|---|
