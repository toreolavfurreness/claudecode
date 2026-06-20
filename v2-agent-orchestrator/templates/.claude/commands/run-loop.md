{{GENERATED_HEADER}}

Du er nå **KOORDINATOR** for den autonome orkestreringsloopen. Du er eneste skriver til delt state; alt tungt arbeid delegeres til worker-subagenter som returnerer rapporter.

## Les først (i denne rekkefølgen)

1. `CLAUDE.md` — prosjektets regler
2. `docs/orchestration-loop.md` — operatør-guide (helheten)
3. `docs/superpowers/loop/coordinator-runbook.md` — **din** steg-for-steg-prosedyre
4. `docs/superpowers/loop/report-schema.md` — rapport-kontrakten workers følger

## Forutsetning: verifiser at agentene er lastet

Dispatch en triviell probe før du starter: `Agent` med `subagent_type: {{PROJECT_NAME}}-planner`, prompt «Svar kun: {"ok": true}. Ikke les filer.»
- Får du `{"ok": true}` → fortsett.
- «Agent type not found» → agentene er ikke lastet i denne sesjonen. Be brukeren starte en **fersk** sesjon (Claude Code snapshotter agent-registeret ved sesjonsstart). Har du nettopp kjørt `/setup`? Da MÅ du starte fersk sesjon før loopen kan kjøre.

## Preflight: dep-sjekk

Kjør disse sjekkene etter agent-proben og FØR første todo velges. Rapporter status og modus til brukeren.

### 1. E2E-verktøy (Playwright MCP)

Hvis prosjektet bruker e2e (`verification_commands.e2e` er satt): forsøk `mcp__playwright__browser_snapshot` (idempotent — returnerer tomt snapshot hvis ingen side er åpen):
- Verktøyet svarer (selv med tomt snapshot) → **E2E: tilgjengelig**
- «Tool not found» / verktøyet finnes ikke i toolsettet → **E2E: MANGLER**
- `verification_commands.e2e` tom → **E2E: ikke i bruk** (hopp over denne sjekken)

### 2. Superpowers-kommandoer

Verifiser at `/systematic-debugging` og `/verification-before-completion` er tilgjengelige kommandoer i ditt toolsett (disse er de eneste som kalles eksplisitt i `todo-execute.md`):
- Begge tilgjengelige → **Superpowers: tilgjengelige**
- Én eller begge mangler → **Superpowers: MANGLER**

(`/requesting-code-review` og `/simplify` er ikke preflight-sjekket her — de utføres allerede inline i `todo-finish-worker.md` steg 3 og 5 og er aldri eksponert som eksplisitte runtime-kall.)

### 3. In-repo-agenter

Agent-proben over (§ «Forutsetning») dekker dette allerede.

### Rapporter modus

Etter sjekkene, print:

```
--- Preflight-status ---
E2E-verktøy:          <tilgjengelig | MANGLER | ikke i bruk>
Superpowers:          <tilgjengelig | MANGLER>
In-repo-agenter:      <lastet | IKKE LASTET>

Modus: FULL | DEGRADERT (<hva som er degradert>)
```

- **E2E MANGLER** → flagg, men fortsett. E2E hoppes over i `todo-finish-worker.md`; `verification.e2e_skipped: true` + `verification.playwright_available: false` settes i ferdig-rapporten; koordinatoren mapper til `degradation: e2e_skipped` i run-log.
- **Superpowers MANGLER** → flagg, men fortsett. Inline 6-stegs fallback-protokoll trer i kraft i `todo-execute.md`; degraderingen er informasjonell og loggføres i `notes`-feltet i ferdig-rapporten.
- **Begge mangler** → fortsett med redusert verifiseringsnivå, begge degraderinger noteres.
- **In-repo-agenter IKKE LASTET** → STOPP (kritisk — loopen kan ikke kjøre). Be brukeren starte fersk sesjon.

Se `docs/orchestration-loop.md` § «Forutsetninger — lokal vs. cloud/headless» for fullstendig forutsetningstabell.

## Kjør loopen

Følg `coordinator-runbook.md` nøyaktig, per todo:
§0 synk → §1 velg todo (prioritert→order, deps oppfylt, ikke claimet, ikke brainstorm) → §2 claim + pre-løs lessons-tema → §3 dispatch planner (m/canary) → §4 dispatch reviewer + gate (maks 2 revisjonsrunder) → §5 dispatch implementer → §5b uavhengig kode-review (probe → dispatch → revise-gate, maks 2 runder) → §6 skriv delt state serielt + merge mot `{{BASE_BRANCH}}` → §6b drain bug-innboks → §6c helsesjekk (betinget: kjør etter {{HEALTH_CHECK_INTERVAL}} merges eller ved §7) → neste todo.

Tom kø → §6c helsesjekk + release-rådgiver → §7 grooming-modus (foreslå utkast, maks 3, så stopp).

## Pausepunkter — STOPP, frigi claim, rapporter til brukeren

- Teknisk risiko ({{PAUSE_TRIGGERS}})
- Brainstorm-påkrevd todo (hopp over, rapporter)
- Worker `failed`/`blocked`, merge-konflikt, canary-mismatch, reviewer no-go som ikke konvergerer
- Kode-reviewer revise-gate som ikke konvergerer etter 2 runder (§5b)
- §5b-probe feiler («Agent type not found») → fersk koordinator-sesjon kreves
- Helsesjekk rød (§6c) — regresjon eller infra-feil i integrert `{{BASE_BRANCH}}`
- Aldri push/merge til `{{PROD_BRANCH}}` — kun `{{BASE_BRANCH}}`

## Argument

`$ARGUMENTS` styrer omfang:
- **tomt** → kjør kontinuerlig, én todo om gangen, til køen er tom eller et pausepunkt treffes
- **et todo-nr** (f.eks. `41`) → start med den todoen
- **`once`** → kjør nøyaktig én todo, så stopp og rapporter (nyttig for validering / forsiktig oppstart)

Etter hver fullførte todo: gi en kort statuslinje (hva ble gjort, PR-lenke, neste i køen) før du fortsetter.
