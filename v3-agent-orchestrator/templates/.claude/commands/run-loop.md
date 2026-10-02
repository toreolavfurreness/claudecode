---
description: "KOORDINATOR: kjør den autonome orkestreringsloopen (planner→reviewer→implementer→kode-review→merge). Arg: tomt | todo-nr | once."
---
{{GENERATED_HEADER}}

Du er nå **KOORDINATOR** for den autonome orkestreringsloopen. Du er eneste skriver til delt state; alt tungt arbeid delegeres til worker-subagenter som returnerer rapporter.

## Les først (i denne rekkefølgen)

1. `CLAUDE.md` og `docs/loop-rules.md` (importert av CLAUDE.md) — prosjektets regler
2. `docs/orchestration-loop.md` — operatør-guide (helheten)
3. `docs/superpowers/loop/coordinator-runbook.md` — **din** steg-for-steg-prosedyre (kjerne-sjekkliste; les `docs/superpowers/loop/steps/<steg>.md` FØR hvert steg kjøres — stegfilen er bindende, begrunnelser i `runbook-hvorfor.md`)
4. `docs/superpowers/loop/report-schema.md` — rapport-kontrakten workers følger

## Forutsetning: verifiser at agentene er lastet

Dispatch disse trivielle probene før du starter:
- `Agent` med `subagent_type: {{PROJECT_NAME}}-planner`, prompt «Svar kun: {"ok": true}. Ikke les filer.»
- `Agent` med `subagent_type: {{PROJECT_NAME}}-code-reviewer`, prompt «Svar kun: {"ok": true}. Ikke synk, ikke les filer.» — dekker §5b sitt register-oppslag for HELE sesjonen (agent-registeret er sesjonsglobalt og snapshottes ved sesjonsstart, samme premiss som planner-proben — se «Forutsetning» øverst i kjernen `coordinator-runbook.md`).
{{SCOUT_PROBE_BULLET}}
- Får du `{"ok": true}` fra alle probene → fortsett.
- «Agent type not found» (fra én eller flere) → agentene er ikke lastet i denne sesjonen. Be brukeren starte en **fersk** sesjon (Claude Code snapshotter agent-registeret ved sesjonsstart). Har du nettopp kjørt `/setup`? Da MÅ du starte fersk sesjon før loopen kan kjøre.

## Preflight: dep-sjekk

Kjør disse sjekkene etter agent-probene og FØR første todo velges. Rapporter status og modus til brukeren.

### 1. E2E-verktøy (probe fra config)

Dette er en **klassifiserings-prosedyre**, ikke en enkelt sjekk. Evaluer radene i denne
rekkefølgen — rad 2 MÅ evalueres FØR rad 4:

| # | Betingelse | Handling | Dom |
|---|---|---|---|
| 1 | `{{CMD_E2E}}` tom | — | **E2E: ikke i bruk** (hopp over §1) |
| 2 | `{{CMD_E2E}}` satt, inneholder IKKE `mcp__`, **OG** `{{CMD_E2E_PROBE}}` tom/blank | ingen — det finnes ingen probe å kjøre | **E2E: MANGLER (probe ikke konfigurert)** — aldri «tilgjengelig» |
| 3 | `{{CMD_E2E}}` inneholder `mcp__` | idempotent kall på det navngitte MCP-verktøyet | svar → tilgjengelig; «Tool not found» → MANGLER |
| 4 | ellers (CLI, probe satt) | kjør `{{CMD_E2E_PROBE}}` i Bash | exit 0 → tilgjengelig; exit ≠ 0 OG `node_modules/.package-lock.json` finnes → MANGLER; exit ≠ 0 OG fila mangler → **STOPP: pausepunkt** (se under) |

**Tom `node_modules` er et pausepunkt, ikke en degradering.** Mangler `node_modules/.package-lock.json` i
koordinatorens sjekkout, sier proben ingenting om verktøyet — bare at `npm ci` ikke er kjørt. STOPP og rapporter
«preflight: node_modules mangler — kjør `npm ci` (og `npx playwright install chromium`)». Ikke merk modus
DEGRADERT. Agent-worktrees kjører egen `npm ci` og ville kjørt e2e uansett, så en «E2E: MANGLER» herfra er falsk.

**Tom probe er IKKE et grønt svar.** Et tomt skall avslutter med 0 — behandle tom
`{{CMD_E2E_PROBE}}` som manglende verktøy (rad 2). Uten rad 2 ville en tom probe gått rett i
rad 4, og et tomt skall som avslutter med 0 ville gitt «E2E: tilgjengelig» uten ett eneste bevis.

**Proben skal aldri laste spec-filene** (f.eks. `--list`). En `{{CMD_E2E_PROBE}}` som laster
spec-filer på modulnivå kan kaste på env-forutsetninger andre spec-er har (f.eks. manglende
sekundær test-bruker), og rapportere «E2E: MANGLER» i et miljø der selve CLI-en er frisk — samme
feilklasse denne prosedyren finnes for å fikse, bare motsatt vei.

### 2. Superpowers-kommandoer

Verifiser at `/systematic-debugging` og `/verification-before-completion` er tilgjengelige kommandoer i ditt toolsett (disse er de eneste som kalles eksplisitt i `todo-execute.md`):
- Begge tilgjengelige → **Superpowers: tilgjengelige**
- Én eller begge mangler → **Superpowers: MANGLER**

(`/requesting-code-review` og `/simplify` er ikke preflight-sjekket her — de utføres allerede inline i `todo-finish-worker.md` steg 3 og 5 og er aldri eksponert som eksplisitte runtime-kall.)

### 3. In-repo-agenter

Agent-probene over (§ «Forutsetning») dekker dette allerede.

### 4. Run-log-avstemming og hotfix-sjekk

Kode kan merges rett til `{{BASE_BRANCH}}` eller `{{PROD_BRANCH}}` utenfor loopen (se
`docs/hotfix-runbook.md`). Denne sjekken finner slike merger før de blir usynlige i telemetrien:

```bash
for b in {{BASE_BRANCH}} {{PROD_BRANCH}}; do
  nums=$(gh pr list --state merged --base "$b" --limit 30 --json number -q '.[].number') \
    || { echo "SVEIP FEILET: gh pr list base=$b"; continue; }
  echo "SVEIP base=$b: $(printf '%s\n' "$nums" | grep -c .) PR-er lest"
  printf '%s\n' "$nums" | while read -r n; do
    [ -n "$n" ] || continue
    grep -qE "pull/$n([^0-9]|$)" docs/superpowers/loop/run-log.md || echo "UKLASSIFISERT: PR #$n (base=$b)"
  done
done
```

Løkka leser linjevis (`while read`), ikke `for n in $nums`: zsh ord-splitter ikke uquotede
variabler, så `for`-formen kjørte én gang med hele lista og meldte stille «ingen treff».
`SVEIP`-linja viser hvor mange PR-er som faktisk ble lest — 0 lest er ikke det samme som 0
uklassifiserte.

Hvert `UKLASSIFISERT`-treff får enten en `outcome=hotfix`-rad (kode utenfor loopen, etter
`docs/hotfix-runbook.md`) eller en linje i `## Avstemming` i run-loggen (ingen kode, release-merge,
port av allerede logget fiks). Første kjøring gir en engangs-backfill; deretter er sveipet nesten
alltid tomt. `SVEIP FEILET` er ikke grønt. Vinduet er de 30 sist *opprettede* PR-ene per base, så
dette er et nett for ferske merges, ikke en garanti for historikken.

Deretter: er en hotfix på `{{PROD_BRANCH}}` forsonet til `{{BASE_BRANCH}}`?

```bash
git fetch origin {{BASE_BRANCH}} {{PROD_BRANCH}} && \
git log origin/{{BASE_BRANCH}}..origin/{{PROD_BRANCH}} --oneline --no-merges
```

Tomt = forsonet. Treff = uforsonet hotfix (eller en forsoning gjort med `-s ours` — sjekk begge).
Forson til `{{BASE_BRANCH}}` FØR første dispatch.

### Rapporter modus

Etter sjekkene, print:

```
--- Preflight-status ---
E2E-verktøy:          <tilgjengelig | MANGLER | ikke i bruk>
Superpowers:          <tilgjengelig | MANGLER>
In-repo-agenter:      <lastet | IKKE LASTET>
Run-log-avstemming:   <avstemt | N uklassifisert (håndtert) | SVEIP FEILET>

Modus: FULL | DEGRADERT (<hva som er degradert>)
```

- **E2E MANGLER** → flagg, men fortsett. E2E hoppes over i `todo-finish-worker.md`; `verification.e2e_outcome: "e2e_unavailable"` settes i ferdig-rapporten; koordinatoren mapper til `degradation`-formelen i `run-log.md` (se `report-schema.md`).
- **Superpowers MANGLER** → flagg, men fortsett. Inline 6-stegs fallback-protokoll trer i kraft i `todo-execute.md`; degraderingen er informasjonell og loggføres i `notes`-feltet i ferdig-rapporten.
- **Begge mangler** → fortsett med redusert verifiseringsnivå, begge degraderinger noteres.
- **In-repo-agenter IKKE LASTET** → STOPP (kritisk — loopen kan ikke kjøre). Be brukeren starte fersk sesjon.

Se `docs/orchestration-loop.md` § «Forutsetninger — lokal vs. cloud/headless» for fullstendig forutsetningstabell.

## Kjør loopen

Følg `coordinator-runbook.md` nøyaktig, per todo:
§0 synk → §1 velg todo (`release.py status` først; bare den aktive releasens scope; prioritert→order, deps oppfylt, ikke claimet, ikke brainstorm) → §2 claim + pre-løs lessons-tema → **§2b fast-path-sjekk** (ren mekanisk endring m/dokumentert presedens + ingen teknisk-risiko-flagg mulig + komplette verifiseringskriterier → hopp rett til §5; §5b kode-review kan ALDRI hoppes) → §3 dispatch planner (m/canary) → §4 dispatch reviewer + gate (maks 2 revisjonsrunder) → §5 dispatch implementer — **som par 1 sammen med §3 planner(B) i ÉN melding når §5c pipelining er på** (§5c velger B og sender par 1; deretter par 2: kode-reviewer(A)+reviewer(B) — se §5c, ikke et eget steg etter §5) → **§5d parallelle implementere (fil-disjunkt-gate, TODO 233): når B sin plan er `go` OG §1-filteret + gate P er grønne, claimes B med én gang og implementer(B) dispatches sammen med A i stedet for å vente til neste runde — se §5d, ikke et eget steg etter §5** → §5b uavhengig kode-review (dispatch → revise-gate, maks 2 runder; probe dekket av preflight) → §6 skriv delt state (seriell, re-kjørbar git-hale) + merge mot `{{BASE_BRANCH}}` (§5d-armert runde: A merges når A er klar, gate M + MERGEABLE FØR B sin merge, `{{BASE_BRANCH}}`-CI-differensial ×2 — se §5d/§6) → §6b drain bug-innboks → §6c helsesjekk (betinget: kjør etter {{HEALTH_CHECK_INTERVAL}} merges eller ved §7; grønn → §8b drain retro-logg kjøres ved BEGGE §6c-triggere, ikke bare ved kø-tom, og har sitt eget utestående-tak på 3 uavhengig av hvor ofte den kjører — se §8b; deretter §8c agér på tallene, som gjør det til en PLIKT å innføre en mekanisk gate for den høyest rangerte feilklassen uten dekning — se §8c; rød → §8b og §8c kjøres IKKE) → neste todo.

Tom kø → §6c helsesjekk + release-rådgiver → (grønn) §8b drain retro-logg (FØR grooming-forslagene, se §8b — egen git-hale ved Trigger 2, fanges av §7s hale ved Trigger 1) → §8c agér på tallene (se §8c, samme hale-regel som §8b) → §7 grooming-modus (foreslå utkast, maks 3 TOTALT denne runden inkl. §8b-promoteringer fra samme runde, rundebudsjett — §8b har i tillegg sitt eget, uavhengige utestående-tak, se §8b — så stopp) → §8 mini-retro (5-linjers Fungerte/Friksjon/Forbedringsforslag til `retro-log.md`).

## Pausepunkter — STOPP, frigi claim, rapporter til brukeren

- Teknisk risiko ({{PAUSE_TRIGGERS}})
- Brainstorm-påkrevd todo (hopp over, rapporter)
- Release: scope tomt (`MÅL NÅDD` / `MÅL IKKE NÅDD`), åpne scope-todoer uten kvalifiserte, eller `release.py status` exit 2 (§1)
- Worker `failed`/`blocked`, merge-konflikt, canary-mismatch, reviewer no-go som ikke konvergerer, CI-gate før merge ikke grønn (§6 steg 0)
- Kode-reviewer revise-gate — nivå B1 innenfor taket (bestem selv + logg, se `coordinator-runbook.md` § Pausepunkter); eskalerer (nivå A) kun når den ene ekstra fix-runden også er brukt og gaten fortsatt ikke er tom (§5b)
- Agent-probe i preflight feiler («Agent type not found», dekker §5b) → fersk koordinator-sesjon kreves
- `node_modules` mangler i koordinatorens sjekkout (preflight §1 rad 4) → `npm ci` kreves før første todo
- Rebase-konflikt i delt-state-git-halen (§6/§6c/§7/§8/§8b/§8c)
- Ferskhets-gaten for en pipelinet plan er fortsatt ikke-tom etter én re-plan-runde (§5c)
- Gate M (§5d) fortsatt `overlap` etter drop-til-serielt-re-synken, ELLER re-synken selv feiler (uløsbar konflikt, rød re-verifisering), ELLER `CONFLICTING` på MERGEABLE-sjekken for B
- B eskalert til nivå A ETTER claim i en §5d-armert runde (§5d, «B eskaleres til nivå A ETTER claim») — B fryses, A fortsetter uendret
- Helsesjekk rød (§6c) — regresjon eller infra-feil i integrert `{{BASE_BRANCH}}`
- Aldri push/merge til `{{PROD_BRANCH}}` — kun `{{BASE_BRANCH}}`

## Argument

`$ARGUMENTS` styrer omfang:
- **tomt** → kjør kontinuerlig, én todo om gangen, til køen er tom eller et pausepunkt treffes
- **et todo-nr** (f.eks. `41`) → start med den todoen
- **`once`** → kjør nøyaktig én todo, så stopp og rapporter (nyttig for validering / forsiktig oppstart)

Etter hver fullførte todo: gi en kort statuslinje (hva ble gjort, PR-lenke, neste i køen) før du fortsetter. Ble ett eller flere nivå-B-valg tatt denne runden (TODO 246): inkluder den ene linja per valg fra `coordinator-runbook.md` § Pausepunkter (`<regel-id> — <kort valg> (reversibel til <punkt>; veto: svar i chatten)`).
