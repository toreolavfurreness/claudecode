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
| `outcome` | enum | `merged` \| `paused` \| `failed` \| `blocked` \| `health` \| `hotfix` \| `loop-eval` | Koordinatorens kontekst: utledet fra hvilken §-gate som traff; `health` for §6c-helsesjekk-rader; `hotfix` for kode merget utenfor loopen (se `docs/hotfix-runbook.md`); `loop-eval` for §6f-selvevalueringsrader (dobler som §6f-tellerens reset-markør — samme rolle som `health` har for §6c-telleren). **Enumen er kjent ufullstendig mot praksis** — se run-log-spec-drift-oppføringen i `tasks/bugs.md` for målt drift og kommandoen som reproduserer den. |
| `pause_event` | enum / `-` | `teknisk-risiko` \| `brainstorm` \| `reviewer-no-go` \| `revise-gate` \| `probe-feil` \| `merge-konflikt` \| `canary-mismatch` \| `helsesjekk-rød` \| `-` | Koordinatorens kontekst — sett iff `outcome=paused`; `-` for health-rader (grønn) eller `helsesjekk-rød` (rød + eskalert); ellers `-` |
| `pr` | URL / `-` | | Ferdig-rapport `pr_url`; `-` ved paused-før-PR og health-rader |
| `plan_review_rounds` | heltall / `-` | `1`, `2`, ... , `-` (hotfix-rader) | Koordinatorens kontekst — §4-telleren; `0` for health-rader; `-` for `outcome=hotfix` |
| `code_review_rounds` | heltall / `-` | `0`, `1`, `2`, ... , `-` (hotfix-rader) | Koordinatorens kontekst — §5b-telleren (`0` ved paused-før-implementering og health-rader; `-` for `outcome=hotfix`) |
| `models` | streng | | Statisk fra Modeller-tabellen i `docs/orchestration-loop.md` ved skrivetidspunktet — tidsstemplet snapshot av hvilke modeller som faktisk var konfigurert |
| `health_payload` | streng / `-` | Se format under | Fast nøkkel=verdi-kjede for `outcome=health`-rader; fritekstnotat på øvrige rader når koordinatoren har ett; `-` ellers (eneste invariant for kolonnen er nøkkel-kjeden på health-rader) |
| `degradation` | streng / `-` | `-` \| `e2e_skipped` | Kilde: ferdig-rapportens `verification.e2e_skipped` / `playwright_available`; koordinatoren mapper; `-` ved ingen aktiv degradering eller `outcome=health` |

**`health_payload`-format (kun `outcome=health`-rader):**

Fast rekkefølge — alle nøkler obligatoriske:

```
sha=<full-40-char-origin/{{BASE_BRANCH}}-HEAD-SHA>;tests=<green|red|infra-feil>;type=<green|red|infra-feil>;lint=<green|red|infra-feil>;rls=<green|red|n/a>;release=<go|no-go>;worktrees_total=<n>;worktrees_stale=<n>;branches_stale_deleted=<n>;merges_since_last=<n>;plan_revision_rate=<x/y>
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
- `worktrees_total` — antall registrerte git-worktrees ved sweepens start (§A5b i
  `.claude/commands/loop-health-check.md`).
- `worktrees_stale` — antall worktrees FJERNET denne sweeprunden (semantikk endret 2026-07-12: var
  tidligere et rent øyeblikksbilde-antall av «trolig trygge å fjerne»-worktrees — §A5b fjerner nå
  faktisk i stedet for kun å telle, se `docs/superpowers/loop/optimization-backlog.md` tiltak #6.
  Historiske rader fra før 2026-07-12 brukte den gamle betydningen; de endres ikke, append-only).
- `branches_stale_deleted` — antall orphan-brancher (uten tilknyttet worktree) slettet denne runden.
- `merges_since_last` — antall `outcome=merged`-rader siden forrige helserad.
- `plan_revision_rate` — brøk `<trengte≥2 runder>/<totalt>` blant merges siden forrige helserad.

**Invarianter:**
- `outcome=paused` ⟹ `pause_event` MÅ være ett av de lovlige pausepunkt-verdiene (ikke `-`).
- `outcome=health` ⟹ `pause_event = -` (grønn) eller `pause_event = helsesjekk-rød` (rød + eskalert). `pr = -`. `plan_review_rounds = 0`. `code_review_rounds = 0`. `todo_nr = -`. `slug = loop-health-check`. `health_payload` MÅ ha alle elleve nøkler i fast rekkefølge (`sha/tests/type/lint/rls/release` + `worktrees_total/worktrees_stale/branches_stale_deleted/merges_since_last/plan_revision_rate`). `degradation = -`.
- `outcome=merged|failed|blocked` ⟹ `pause_event` SKAL være `-`. `health_payload` bærer et
  fritekstnotat for ikke-health-rader NÅR koordinatoren har ett å bokføre (samme kolonne-praksis
  som `hotfix`-invarianten under); `-` når notat mangler. **Ikke** en fast `= -`-invariant — praksis
  i den levende loggen (f.eks. release-radene) bærer notater i denne kolonnen på `merged`-lignende
  rader, og spec-en beskriver nå det faktiske mønsteret i stedet for å motsi det.
- `outcome=hotfix` ⟹ `todo_nr = -`. `plan_review_rounds = -`. `code_review_rounds = -`.
  `models = utenfor-loopen`. `pr` = PR-URL. `health_payload` bærer notatet (symptom+rotårsak+fiks
  +filer), samme kolonne-praksis som alle andre ikke-health-rader (se `docs/hotfix-runbook.md`).
- **Kun `outcome=merged` telles av §6c/§6f** — alle andre verdier (`paused`/`failed`/`blocked`/
  `health`/`hotfix`/`loop-eval`) er usynlige for begge tellerne, og det er tilsiktet: en etterfylt
  hotfix-rad skal ALDRI blåse opp en teller den ikke faktisk hørte til (loggen appendes ikke
  strengt kronologisk — en etterfylt rad kan stå før nyere rader den ble oppdaget etter). **Kjent
  unntak, IKKE tilsiktet:** de udokumenterte `pr1-merged`/`pr2-merged`-verdiene i den levende loggen
  (se run-log-spec-drift-oppføringen i `tasks/bugs.md`) er også usynlige for begge tellerne, men
  representerer ekte loop-merger — «tilsiktet» over gjelder kun de seks listede verdiene, ikke disse
  to. Målt: 7 `pr1-merged`/`pr2-merged`-rader tellerne ikke ser.
- `models`-feltet skrives som et fast kjede-uttrykk på formen `planner/reviewer/implementer/code-reviewer=<modell>/<modell>/<modell>/<modell>` — hentes fra Modeller-tabellen, ikke fra rapporten — unntatt `outcome=hotfix`, som bruker `utenfor-loopen`.
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

## Avstemming — klassifiserte PR-er uten rad

**Formål:** idempotent demping av `### 0c`-avstemmingen i `.claude/commands/run-loop.md`. De
fleste PR-er den finner er legitimt uten rad (todo-filer, docs, bugs-drops) — uten et sted å
bokføre «trenger ingen rad» rapporterer sjekken de samme PR-ene på nytt hver sesjon og blir støy.

**Format:** én linje per klassifisert PR, alltid med full `pull/<nr>`-URL (den er selve
grepen-ankeret sjekken leser): `- <dato> [PR #<nr>](<full pull/<nr>-URL>): <klasse> — <begrunnelse>`,
`<klasse>` ∈ `ingen kode` (kun `tasks/`/`docs/`-filer) \| `kode utenfor loopen` (kildefiler, se
`docs/hotfix-runbook.md`) \| `release-merge` (PR mot `{{PROD_BRANCH}}`-basen som er en
dev→main-release, ikke en hotfix — sveipet dekker nå begge baser, se `### 0c`).
En **main-port av en allerede logget fiks** (samme kode landet via to PR-er, dev + main)
klassifiseres her som `kode utenfor loopen` med henvisning til dev-PR-ens logg-rad i
begrunnelsen — den får ALDRI egen `outcome=hotfix`-rad (én fiks = én rad; se
`docs/hotfix-runbook.md`).

**Plassering:** egen `##`-seksjon, append-only, koordinator er eneste skriver — samme mønster som
`## Eier-beslutningskø` (§6g i `coordinator-runbook.md`). **Koordinatorens rad-appends fra §6 går
ALDRI inn i denne seksjonen** — de går til `## Logg`-tabellen over. Denne seksjonen er ren
klassifisering, ikke telemetri.
