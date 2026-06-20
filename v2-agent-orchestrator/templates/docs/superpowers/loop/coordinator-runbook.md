<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# Koordinator-runbook (fase 0, live-sesjon)

Du er koordinatoren. Du er eneste skriver til delt state. Workers gjør tungt arbeid i isolerte worktrees og returnerer rapporter (`report-schema.md`).

> ⚠️ **Forutsetning:** koordinatoren MÅ kjøre i en sesjon som ble startet ETTER at `.claude/agents/{{PROJECT_NAME}}-*.md` finnes på disk. Claude Code snapshotter agent-registeret ved sesjonsstart — nyopprettede custom agenter er ikke tilgjengelige i en allerede kjørende sesjon. Verifiser med en triviell probe-dispatch (`subagent_type: {{PROJECT_NAME}}-planner`) før du starter en runde; «Agent type not found» betyr at du må starte en fersk sesjon.

## 0. Synk

```bash
git fetch origin {{BASE_BRANCH}} && git switch {{BASE_BRANCH}} && git pull --ff-only
```
Working tree ikke ren → rapporter til mennesket og stopp.

## 1. Kø-utvelgelse (med ekte deps-gating)

Kjør dette python-skriptet — det resolver `deps`, ekskluderer claimed/brainstorm, og sorterer prioritert-først:

```bash
python3 - <<'PY'
import glob, re
def fm(p):
    t = open(p).read()
    m = re.search(r'^---\n(.*?)\n---', t, re.S)
    d = {}
    if m:
        for line in m.group(1).splitlines():
            mm = re.match(r'(\w+):\s*(.*)', line)
            if mm: d[mm.group(1)] = mm.group(2).strip().strip('"')
    d['_brainstorm'] = bool(re.search(r'krever[^.\n]*brainstorm|brainstorm\s+f.?r\s+plan|spec\s+f.?r\s+plan', t, re.I))
    d['_path'] = p
    return d
def as_int(v, default=9999):
    try: return int(v)
    except (ValueError, TypeError): return default
todos = {}
for p in glob.glob('tasks/todos/todo-*.md'):
    d = fm(p); nr = d.get('nr','')
    if not nr:
        print(f"ADVARSEL: mangler nr i {p}"); continue
    todos[nr] = d                                    # parse hver fil ÉN gang
def dep_done(nr):
    f = todos.get(nr)
    return f is None or f.get('status') == 'done'    # mangler fil ⟹ arkivert
rows = []
for nr, d in todos.items():
    deps = re.findall(r'"([^"]+)"', d.get('deps','') or '')
    tags_raw = d.get('tags', '')
    eligible = (d.get('status')=='open' and (d.get('claimed_by','null') in ('null','',None))
                and not d['_brainstorm'] and all(dep_done(x) for x in deps)
                and not re.search(r'\bforslag\b', tags_raw))
    pr = 0 if d.get('priority')=='prioritert' else 1
    rows.append((pr, as_int(d.get('order')), nr, d.get('status','?'), 'YES' if eligible else 'no', d['_path']))
for r in sorted(rows):
    print(f"elig={r[4]:3} pri={r[0]} order={r[1]:5} TODO {r[2]:5} {r[3]:10} {r[5]}")
PY
```

Velg øverste rad med `elig=YES`. Ingen → §7 (grooming).

## 2. Claim + pre-løs lessons-tema

Sett `claimed_by: <din-sesjon>` i todo-fila. Grep `tasks/lessons.md` for 1–3 tema relevant for todoens domene (gyldige tema: {{LESSONS_TOPICS}}).

**Claim-release:** I ENHVER stopp-sti senere (teknisk risiko, blocked, failed, merge-konflikt) → sett `claimed_by: null` tilbake før du stopper, så todoen ikke lekker ut av køen.

## 3. Dispatch planner

Velg et **canary-mål** workeren ikke kan gjette: en fil+linje som ikke er en invariant og ikke gjentas i prompten (f.eks. `{{CANARY_FILE}}` linje N — varier N per dispatch). Noter den faktiske teksten selv (`sed -n 'Np' {{CANARY_FILE}}`).

`Agent`: `subagent_type: {{PROJECT_NAME}}-planner`. Prompt:
> TODO <nr> (`tasks/todos/todo-<nr>-<slug>.md`). Relevante lessons-tema: <liste>. Canary: returner de første 8 ordene på linje <N> i `{{CANARY_FILE}}`. Følg charteret ditt. Returner plan-rapport som JSON.

Verifiser at `canary` matcher den faktiske teksten du noterte. Mismatch → re-dispatch eller eskalér (workeren leste sannsynligvis ikke filene). Koordinatoren (du) setter `plan:`-stien fra rapportens `plan_path` i todo-frontmatteren — workeren rører den ikke.

## 4. Dispatch reviewer + gate

`Agent`: `subagent_type: {{PROJECT_NAME}}-reviewer`. Prompt:
> TODO <nr>. Plan: `<plan_path>`. Relevante lessons-tema: <liste>. Følg charteret ditt. Returner review-rapport som JSON.

Gate på `verdict`:
- `"no-go"` (≥1 BLOKKERENDE) → send funnene tilbake til planner (§3, revisjons-runde). **Hold en eksplisitt teller** («revisjonsrunde X/2») i kontekst. Etter **2** runder uten `go` → ⚠️ eskalér til mennesket, release claim.
- `"go"` → fortsett.

Ved `technical_risk.flagged` (plan- eller review-rapport) → ⚠️ STOPP, release claim, rapporter risikoen, vent på menneskets go.

## 5. Dispatch implementer

`Agent`: `subagent_type: {{PROJECT_NAME}}-implementer`. Prompt:
> TODO <nr>. Plan: `<plan_path>`. Relevante lessons-tema: <liste>. Følg charteret ditt. Returner ferdig-rapport som JSON.

`status: "failed"|"blocked"` → ⚠️ STOPP, release claim, rapporter.

## 5b. Uavhengig kode-review

### Probe (obligatorisk FØR review-dispatch)

Før du dispatcher selve reviewen, kjør en triviell probe for å verifisere at `{{PROJECT_NAME}}-code-reviewer` er lastet i denne sesjonen:

`Agent`: `subagent_type: {{PROJECT_NAME}}-code-reviewer`, prompt: «Svar kun: {"ok": true}. Ikke synk, ikke les filer.»

- Får du `{"ok": true}` → fortsett til review-dispatch.
- «Agent type not found» (eller manglende `ok`) → ⚠️ STOPP, release claim, eskalér til mennesket: «§5b krever en koordinator-sesjon startet ETTER at `.claude/agents/{{PROJECT_NAME}}-code-reviewer.md` ble merget til `{{BASE_BRANCH}}`; start en fersk sesjon».

### Review-dispatch

`Agent`: `subagent_type: {{PROJECT_NAME}}-code-reviewer`. Prompt:
> TODO <nr>. PR: `<pr_url>` (fra ferdig-rapporten). Relevante lessons-tema: <liste>. Følg charteret ditt. Returner code_review-rapport som JSON.

### Gate (revise-gate på severity, ikke kun på verdict)

Les `code_review`-rapporten:

- Inneholder rapporten **≥1 BLOKKERENDE eller ≥1 VIKTIG** → **revise-gate**: send funnene tilbake til implementeren via fix-mode-dispatch (se fix-mode-mal under). **Hold en eksplisitt teller** («kode-review-runde X/2», samme mønster som §4). Etter **2** runder uten at revise-gaten er tom → ⚠️ eskalér til mennesket, release claim.
- Kun MINDRE eller ingen funn (`verdict = "go"`, revise-gate ikke trigget) → fortsett til §6.
- Teknisk risiko som dukker opp i rapporten → ⚠️ STOPP, release claim, rapporter (samme som §4-gaten).

**NB:** `verdict = "no-go"` trigges kun ved ≥1 BLOKKERENDE (identisk med plan-review). Revise-gaten er strengere — den trigges også ved ≥1 VIKTIG selv om `verdict = "go"`. Koordinatoren leser severity-arrayet direkte, ikke kun `verdict`.

### Fix-mode-dispatch-mal (revise-runde)

`Agent`: `subagent_type: {{PROJECT_NAME}}-implementer`. Prompt:

> FIX-MODE for TODO `<nr>`. Du har ALLEREDE implementert denne og laget PR `<pr_url>` på branch `<branch>`. IKKE re-implementer og IKKE kjør `todo-execute.md` på nytt. Gjør KUN dette: (1) `git fetch origin <branch> && git checkout <branch>` og `git fetch origin {{BASE_BRANCH}} && git merge origin/{{BASE_BRANCH}}` for å bygge på ferskeste delt state før re-push; (2) rett UTELUKKENDE disse kode-review-funnene: `<liste med severity + file:line + issue + fix>`; (3) kjør `{{CMD_BUILD}}` + `{{CMD_TYPE_CHECK}}` + relevante tester på nytt; (4) `git push` til samme branch (samme PR — IKKE ny PR, IKKE ny `gh pr create`); (5) returner oppdatert ferdig-rapport. Rør ingenting utenom de oppgitte funnene.

## 6. Skriv delt state SERIELT (kun koordinator)

Fra ferdig-rapporten, `status: "implemented"`:
1. **Lessons:** for hver `lessons[]`, legg Pattern/Sjekkliste/Kilder i `tasks/lessons/<topic>.md` + én-linjes bullet i `tasks/lessons.md`. Konsolider om 2+ dekker samme mønster.
2. **Bugs:** `bugs_new[]` → `tasks/bugs.md`; `bugs_closed[]` → `tasks/bugs_archive.md` (opprett fila hvis den ikke finnes).
3. **Arkiver todo:** flytt til `tasks/todo_archive.md` (format: se eksisterende oppføringer). Slett `tasks/todos/todo-<nr>-<slug>.md`. Flytt planfil → `tasks/plans/archive/`.
4. **Merge:** `gh pr merge <pr> --merge` — ALDRI `{{PROD_BRANCH}}` (base er satt ved PR-oppretting av workeren, ikke ved merge-kommandoen; `--base`-flagget finnes ikke i `gh pr merge`). Verifiser base FØR merge: `gh pr view <pr> --json baseRefName -q .baseRefName` → `{{BASE_BRANCH}}`. Merge-konflikt → ⚠️ STOPP, release claim, rapporter.

   **Worktree-rydding etter merge** (erstatt `<branch>` med ferdig-rapportens `branch`-felt):
   ```bash
   wt_path=$(git worktree list --porcelain \
     | awk -v b="refs/heads/<branch>" '/^worktree /{w=$2} /^branch /{if($2==b){print w; exit}}')
   if [ -n "$wt_path" ]; then
     locked=$(git worktree list --porcelain \
       | awk '/^worktree /{w=$2; lk=0} /^locked/{lk=1} w=="'"$wt_path"'" && lk{print "yes"; exit}')
     if [ "$locked" != "yes" ]; then
       dirty=$(git -C "$wt_path" status --porcelain 2>/dev/null)
       if [ -z "$dirty" ]; then
         if git worktree remove "$wt_path" --force 2>/dev/null; then
           git branch -d <branch> 2>/dev/null || true
         else
           echo "ADVARSEL: git worktree remove feilet for $wt_path" >&2
         fi
       else
         echo "ADVARSEL: $wt_path har ucommittede endringer — sletter ikke, eskalér manuelt" >&2
       fi
     fi
   fi
   ```
   *Kommentar:* awk bruker streng-match (`$2==b`) — trygt for branch-navn med `/`. `git branch -d`
   kjøres KUN etter vellykket `worktree remove` (exit 0). Locked-deteksjon er alltid dynamisk.
5. **Append til run-log:** les telemetrien fra (a) ferdig-rapportens `todo_nr`, `slug`, `pr_url`; (b) egne kontekst-tellere (§4-revisjonsrunder, §5b-kode-review-runder); (c) Modeller-tabellen i `docs/orchestration-loop.md` (planner/reviewer/implementer/code-reviewer); (d) `verification.e2e_skipped` og `verification.playwright_available` fra ferdig-rapporten — map til `degradation`-kolonnen per format-spec i `run-log.md`: `e2e_skipped=true` → `e2e_skipped`; ellers `-`. Default `-`. Append én linje til `docs/superpowers/loop/run-log.md` etter format-spec-en i samme fil. Workers rører ALDRI run-log.md — de returnerer telemetrien som rapport-data, koordinatoren appender.
6. Commit delt-state-endringene på `{{BASE_BRANCH}}`, så `git push origin {{BASE_BRANCH}}`.

## 6b. Drain bug-innboks (hver syklus, kun koordinator)

Sjekk `tasks/bugs/inbox/` for nye `bug-*.md` (mennesker slipper dem her — én fil per bug, ingen konflikt). For hver:
- **Reell, ikke-planlagt bug** → legg en oppføring i `tasks/bugs.md` (format: se eksisterende).
- **Bug som bør fikses nå** → forfremm til en ny todo (`tasks/todos/todo-NN-fix-<slug>.md`, sett `priority` etter innboks-filens vurdering).
- **Ugyldig/duplikat** → noter og forkast.
Slett den drainede innboks-fila etterpå. Dette er koordinatorens skriving (single-writer) — mennesker rører aldri `bugs.md` selv.

## 6c. Helsesjekk + release-rådgiver (betinget, kun koordinator)

**Koordinatoren** kjører `/loop-health-check` (`.claude/commands/loop-health-check.md`) når én av
to deterministiske triggere slår inn. Workers dispatches aldri til denne oppgaven — single-writer-
kontrakten gjelder.

### Triggerlogikk

**Trigger 1 — Kø tom / grooming (§7):** Kjør §6c FØR grooming-forslag, slik at mennesket får
en samlet statusrapport samtidig. Helseraden som skrives nullstiller merge-telleren (Trigger 2).

**Trigger 2 — Hver N-te merge (N={{HEALTH_CHECK_INTERVAL}}):** Tell rader med `outcome=merged` etter den *siste* raden
med `outcome=health` i `docs/superpowers/loop/run-log.md`:

```bash
awk '
  /\| health \|/ { count=0; next }
  /\| merged \|/ { count++ }
  END { print count }
' docs/superpowers/loop/run-log.md
```

Count ≥ {{HEALTH_CHECK_INTERVAL}} → kjør §6c nå (før neste dispatch). Helseraden som §6c skriver blir den nye
nullstillings-markøren. Ingen health-rad ennå → tell fra toppen av fila.

**Begge triggere skriver en health-rad** → telleren nullstilles alltid uansett hvilken som fyrer.

### Etter §6c

- Grønn helsesjekk → fortsett normalt (til grooming eller neste todo).
- Rød helsesjekk (regresjon eller infra-feil) → ⚠️ PAUSEPUNKT: eskalér til mennesket med detaljer,
  sett `pause_event=helsesjekk-rød` i health-raden, release evt. aktiv claim og stopp loopen.

## 7. Grooming-modus (kø tom)

Kjør §6c-helsesjekk FØR grooming-forslag (se §6c over).

Ingen kvalifisert todo → IKKE stopp tomt. Foreslå inntil **3** nye todos/bugs som UTKAST med `status: deferred` + `tags: [forslag]`, basert på backlog/arkiv/observasjoner. Auto-implementer ALDRI selvgenerert arbeid. Etter 3 forslag: STOPP og rapporter til mennesket for triage. (Exit-kriterium hindrer uendelig grooming.)

**Forslag-konvensjon:** Hvert grooming-forslag opprettes med disse to feltene i frontmatteren:
```yaml
status: deferred
tags: [forslag]
```
Kombinasjonen er dobbel gating: `status: deferred` holder forslaget ute av §1-køen (som kun plukker `status: open`), og `tags: [forslag]` holder det ute selv om noen ved uhell flipper statusen uten å fjerne taggen.

**Triage (gjøres av mennesket):** Et forslag godkjennes ved å flippe `status: deferred → open` OG fjerne `forslag`-taggen (`tags: []`). Begge endringer er nødvendige — kun én av dem er ikke tilstrekkelig for å gjøre forslaget kvalifisert (`elig=YES`). Avviste forslag beholder `status: deferred` og kan slettes eller beholdes som referanse.

## Pausepunkter (alltid eskalér + release claim)

- Teknisk risiko flagget (§4) eller truffet (§5/§6)
- Brainstorm-påkrevd todo (hoppet over i §1)
- Reviewer no-go som ikke konvergerer etter 2 runder (§4)
- Kode-reviewer revise-gate som ikke konvergerer etter 2 runder (§5b)
- §5b-probe feiler («Agent type not found») → fersk koordinator-sesjon kreves
- Merge-konflikt (§6.4)
- `git`/working-tree ikke ren (§0)
- `canary`-mismatch som ikke løses (§3)
- Helsesjekk rød (§6c) — regresjon eller infra-feil i integrert `{{BASE_BRANCH}}`
