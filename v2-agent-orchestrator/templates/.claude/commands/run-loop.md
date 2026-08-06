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

Er en **verifikator-arm** konfigurert i `tech_review_agents`, prob den også
(`subagent_type: {{PROJECT_NAME}}-verifier`, samme `{"ok": true}`-prompt). Den dispatches av
kode-revieweren, ikke av deg — men uteblir den i §5b, er det koordinatoren som må dispatche den
direkte, og da må den finnes i registeret. «Agent type not found» her stopper ikke loopen: den
gjør §5b-verifikasjonsgaten UTILGJENGELIG, som skal rapporteres eksplisitt, aldri gås stille forbi.

## Preflight: dep-sjekk

### 0. §6f-teller (selvevaluering — sjekk VED SESJONSSTART, ikke bare per merge)

```bash
awk '/\| loop-eval \|/ { count=0; next } /\| merged \|/ { count++ } END { print count }' docs/superpowers/loop/run-log.md
```

≥ 5 → kjør §6f-selvevalueringen FØR første nye dispatch (kadensen glapp 3,4× da telleren kun ble
sjekket ved egne merges — korte/eier-fokuserte sesjoner hoppet over den; batch-14-funn).

### 0c. Run-log-avstemming (sesjonsstart)

Kode kan merges rett til `{{BASE_BRANCH}}` eller `{{PROD_BRANCH}}` utenfor en loop-sesjon (se
`docs/hotfix-runbook.md`). Denne sjekken finner slike merger før de blir usynlige i telemetrien.

```bash
for b in {{BASE_BRANCH}} {{PROD_BRANCH}}; do
  gh pr list --state merged --base "$b" --limit 30 --json number -q '.[].number' \
  | while read n; do
      grep -qE "pull/$n([^0-9]|$)" docs/superpowers/loop/run-log.md || echo "UKLASSIFISERT: PR #$n (base=$b)"
    done
done
```

Begge baser dekkes — en `{{PROD_BRANCH}}`-basert PR (hotfix ELLER release-merge, se
`## Avstemming`-seksjonen i `docs/superpowers/loop/run-log.md`) listes aldri av
`--base {{BASE_BRANCH}}` alene. Grepen matcher `pull/$n` HVOR SOM HELST i fila, ikke bare
`## Logg`-tabellen — en dempning i `## Avstemming`-seksjonen slukker treffet like godt som en
faktisk logg-rad, med vilje (det er poenget med den seksjonen); demping beviser altså IKKE at det
finnes en `## Logg`-rad for PR-en.

Tom output er KUN grønt hvis `gh pr list` faktisk lyktes — sjekk exit-koden (legg
`|| echo "SVEIP FEILET: gh pr list base=$b"` på gh-kallet) før du konkluderer; en feilet gh gir
ellers null linjer, visuelt identisk med «alt avstemt».

Første kjøring gir en engangs-backfill (målt 2026-08-02: 25 historiske `{{PROD_BRANCH}}`-PR-er,
nesten alle `release-merge`). Klassifiser dem i én omgang; deretter er sveipet nesten alltid tomt.

Hull etterfylles/klassifiseres FØR første dispatch. Vinduet er de 30 sist OPPRETTEDE av de mergede
PR-ene per base — `gh pr list` sorterer på opprettelsestidspunkt, ikke mergetidspunkt (målt
2026-08-02: #588 opprettet før #587, men merget etter) — **vinduet glemmer**: en gammel branch som
merges i dag kan falle utenfor de 30 nyeste; sjekken er et nett for ferske merges, ikke en garanti
for historikken.

Deretter main-hotfix-sjekken (fanger en hotfix som gikk direkte til `{{PROD_BRANCH}}` uten å bli
forsonet til `{{BASE_BRANCH}}`):

```bash
git fetch origin {{BASE_BRANCH}} {{PROD_BRANCH}} && \
git log origin/{{BASE_BRANCH}}..origin/{{PROD_BRANCH}} --oneline --no-merges
```

Tomt = ingen uforsonet main-hotfix (målt 2026-08-02: tom, #517 er forsonet). Treff betyr enten en
ekte main-hotfix ELLER at forsoningen ble gjort med `-s ours` — sjekk begge før du handler. Forson
til `{{BASE_BRANCH}}` før første dispatch.

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

(`/simplify` kalles eksplisitt i `todo-finish-worker.md` steg 3 av workeren selv (som har `Skill` i toolsettet) med inline-fallback hvis skillen mangler, og `/requesting-code-review` utføres inline i steg 5 — derfor preflight-sjekkes ingen av dem her.)

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
- **tomt** → kjør kontinuerlig, alle tags (ingen sesjon-filter)
- **tomt** → SLETT ev. eksisterende `tasks/session-queue-filter.md` FØR §1 (`rm -f tasks/session-queue-filter.md` + commit hvis den var committet) — et foreldet filter fra en tidligere sesjon har styrt køen stille før (2026-07-19)
- **domene-tag** (`ai`, `design`, `sync`, `fundament`, `metrics`) → skriv `tasks/session-queue-filter.md` med `tags_filter: [<arg>]`, kjør deretter kontinuerlig innenfor det domenet
- **et todo-nr** (f.eks. `41`) → start med den todoen (ingen tag-filter)
- **`once`** → kjør nøyaktig én todo, så stopp og rapporter (nyttig for validering / forsiktig oppstart)

**Domene-filter eksempel:** `/run-loop design` → setter filter automatisk og starter design-sesjonen.

Etter hver fullførte todo: gi en kort statuslinje (hva ble gjort, PR-lenke, neste i køen) før du fortsetter.
