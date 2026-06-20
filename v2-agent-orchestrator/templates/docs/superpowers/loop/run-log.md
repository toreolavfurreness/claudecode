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
| `outcome` | enum | `merged` \| `paused` \| `failed` \| `blocked` \| `health` | Koordinatorens kontekst: utledet fra hvilken §-gate som traff; `health` for §6c-helsesjekk-rader |
| `pause_event` | enum / `-` | `teknisk-risiko` \| `brainstorm` \| `reviewer-no-go` \| `revise-gate` \| `probe-feil` \| `merge-konflikt` \| `canary-mismatch` \| `helsesjekk-rød` \| `-` | Koordinatorens kontekst — sett iff `outcome=paused`; `-` for health-rader (grønn) eller `helsesjekk-rød` (rød + eskalert); ellers `-` |
| `pr` | URL / `-` | | Ferdig-rapport `pr_url`; `-` ved paused-før-PR og health-rader |
| `plan_review_rounds` | heltall | `1`, `2`, ... | Koordinatorens kontekst — §4-telleren; `0` for health-rader |
| `code_review_rounds` | heltall | `0`, `1`, `2`, ... | Koordinatorens kontekst — §5b-telleren (`0` ved paused-før-implementering og health-rader) |
| `models` | streng | | Statisk fra Modeller-tabellen i `docs/orchestration-loop.md` ved skrivetidspunktet — tidsstemplet snapshot av hvilke modeller som faktisk var konfigurert |
| `health_payload` | streng / `-` | Se format under | Fast nøkkel=verdi-kjede for `outcome=health`-rader; `-` for alle andre rader (invariant) |
| `degradation` | streng / `-` | `-` \| `e2e_skipped` | Kilde: ferdig-rapportens `verification.e2e_skipped` / `playwright_available`; koordinatoren mapper; `-` ved ingen aktiv degradering eller `outcome=health` |

**`health_payload`-format (kun `outcome=health`-rader):**

Fast rekkefølge — alle nøkler obligatoriske:

```
sha=<full-40-char-origin/{{BASE_BRANCH}}-HEAD-SHA>;tests=<green|red|infra-feil>;type=<green|red|infra-feil>;lint=<green|red|infra-feil>;rls=<green|red|n/a>;release=<go|no-go>
```

- `sha=` — `origin/{{BASE_BRANCH}}`-HEAD-SHA på tidspunktet for helsesjekken. Brukes av neste helsesjekk for
  å avgrense tech-sweep-gaten. Les med:
  `grep ' | health | ' run-log.md | tail -1 | grep -oE 'sha=[0-9a-f]{40}' | cut -d= -f2`
  Tom → ingen tidligere helsesjekk → tech-sweep kjøres ubetinget.
- `tests/type/lint` — `green` (ok), `red` (regresjon: runner rapporterte feil i koden),
  `infra-feil` (kommando feilet å starte: manglende dep, config-feil, OOM — IKKE regresjon).
- `rls` — `green` (ingen åpne hull), `red` (funn som krever eskalering), `n/a` (ingen
  tech-relevante endringer siden forrige helsesjekk, eller ingen tech-review-agenter konfigurert).
- `release` — `go` (alt grønt + ingen høy-prioriterte bugs) eller `no-go` (minst ett hinder).

**Invarianter:**
- `outcome=paused` ⟹ `pause_event` MÅ være ett av de lovlige pausepunkt-verdiene (ikke `-`).
- `outcome=health` ⟹ `pause_event = -` (grønn) eller `pause_event = helsesjekk-rød` (rød + eskalert). `pr = -`. `plan_review_rounds = 0`. `code_review_rounds = 0`. `todo_nr = -`. `slug = loop-health-check`. `health_payload` MÅ ha alle seks nøkler i fast rekkefølge. `degradation = -`.
- `outcome=merged|failed|blocked` ⟹ `pause_event` SKAL være `-`. `health_payload = -` (invariant).
- `models`-feltet skrives som et fast kjede-uttrykk på formen `planner/reviewer/implementer/code-reviewer=<modell>/<modell>/<modell>/<modell>` — hentes fra Modeller-tabellen, ikke fra rapporten.
- `degradation` settes alltid; `-` betyr ingen aktiv degradering.

---

## Eksempel-logglinje (merged-rad)

```
2026-06-19T14:30 | 69 | loop-run-log | merged | - | https://github.com/{{GITHUB_REPO}}/pull/214 | 1 | 1 | planner/reviewer/implementer/code-reviewer={{MODELS_DISPLAY}} | - | -
```

## Eksempel-logglinje (health-rad)

```
2026-06-19T16:00 | - | loop-health-check | health | - | - | 0 | 0 | planner/reviewer/implementer/code-reviewer={{MODELS_DISPLAY}} | sha=1a7f4a5b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f;tests=green;type=green;lint=green;rls=n/a;release=go | -
```

---

## Logg

| timestamp | todo_nr | slug | outcome | pause_event | pr | plan_review_rounds | code_review_rounds | models | health_payload | degradation |
|---|---|---|---|---|---|---|---|---|---|---|
