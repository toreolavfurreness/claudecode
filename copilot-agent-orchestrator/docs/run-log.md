# run-log.md — koordinatorens append-only telemetri

**Seed-only-fil.** Opprettes tom (kun denne headeren) når prosjektet tar i bruk loopen.
Koordinatoren er eneste skriver — append alltid, slett aldri en rad.

## Format

Én rad per hendelse:

```
| dato | type | todo | detaljer |
|---|---|---|---|
```

`type` ∈:
- `plan` — planner dispatchet/fullført
- `review` — reviewer-verdikt (go/no-go)
- `implement` — implementer dispatchet (barnesesjon-id notert)
- `code_review` — code-reviewer-verdikt
- `merged` — PR merget mot base_branch (inkluder PR-nummer)
- `health` — helsesjekk kjørt (inkluder sha=<origin/base_branch-sha> for betinget tech-sweep)
- `loop-eval` — selvevaluering av loopens egen ytelse (kadens: hver N. merge, se loop.config)
- `blocked` — todo stoppet på pause-trigger, eskalert til menneske
- `hotfix` — kode merget utenfor en loop-sesjon (se docs/hotfix-runbook.md hvis den finnes)

## Avstemming

Seksjon for å dempe falske positiver i koordinatorens run-log-avstemming ved sesjonsstart
(se `docs/coordinator-runbook.md` §0c) — f.eks. PR-er som er `release-merge` mot
`prod_branch` og derfor bevisst ikke har en `merged`-rad mot `base_branch`.

## Logg

<!-- Koordinatoren appender rader under denne linjen. Ikke rediger eksisterende rader. -->
