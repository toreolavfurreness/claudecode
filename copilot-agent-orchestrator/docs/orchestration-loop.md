<!--
  Denne filen er en STATISK guide, ikke generert av setup-scriptet — kildens
  "GENERATED, do not edit"-mekanisme er droppet for kommandoer/docs i denne porten
  (se docs/PORTING-DECISIONS.md §3). Rediger den direkte når arkitekturen endres.
-->
# Orkestreringsloopen — operatør-guide

Denne guiden forklarer **hvordan den autonome utviklingsloopen fungerer i praksis**, og —
viktigst — **hvor du som menneske passer inn**. Den er for deg som kjører loopen, ikke for deg
som bygger den.

- **Arkitektur og empiriske funn:** `docs/PORTING-DECISIONS.md`
- **Koordinator-runbook:** `docs/coordinator-runbook.md`
- **Rapport-kontrakt:** `docs/report-schema.md`

---

## Hva loopen er

Et system som tar todos fra `tasks/todos/` og kjører dem gjennom planlegging → review →
implementering → kode-review → merge **uten at du må trigge hvert steg**. Du går fra å være den
som setter i gang alt, til å være den som styrer retning og svarer på unntak.

**Kjernidé:** en **koordinator**-sesjon dispatcher kortlevde **roller** («workers») som gjør det
tunge arbeidet og returnerer korte rapporter. Koordinatoren er **eneste skriver** til delt state
(lessons, arkiv, bugs, status, run-log), så flere workers tråkker aldri på hverandre.

**Viktig forskjell fra Claude Code-originalen:** roller er ikke navngitte, forhåndsregistrerte
agenter — koordinatoren leser `templates/roles/*.md` og substituerer tokens ved HVERT dispatch.
Det betyr ingen restart-syklus når du endrer `loop.config.yaml`. Til gjengjeld er isolasjonen
ulik per rolle (se tabellen under) — dette er en bevisst avveining, ikke en begrensning du
trenger å tenke på i det daglige.

---

## Hvordan en runde fungerer

```
DU starter loopen (kjør skillet "run-loop" i en koordinator-sesjon)
   │
   ▼
KOORDINATOR  ── velger neste todo (prioritert → order, deps oppfylt, ikke claimet)
   │
   ├─→ PLANNER        (in-session task, {{MODELS.planner}})       skriver en plan for todoen
   ├─→ REVIEWER       (in-session task, {{MODELS.reviewer}})      uavhengig djevelens advokat
   ├─→ IMPLEMENTER     (egen barnesesjon, {{MODELS.implementer}})  koder, verifiserer, lager PR
   ├─→ CODE REVIEWER  (in-session task, {{MODELS.code_reviewer}}) uavhengig review av PR-diffen
   │      └─→ VERIFIER (egen barnesesjon, betinget)                beviser at vakter kan gå røde
   ▼
KOORDINATOR  ── skriver lessons, arkiverer todo, merger til {{BASE_BRANCH}}, går til neste
```

| Rolle | Dispatch-mekanisme | Hvorfor |
|---|---|---|
| planner, reviewer, code-reviewer | `task`, in-session | Leser/vurderer, muterer ikke kode/git — ingen isolasjon nødvendig |
| implementer, verifier | `create_session` (barnesesjon) | Muterer faktisk kode/git — trenger egen worktree/branch (empirisk bekreftet i spike, se `docs/PORTING-DECISIONS.md` §1) |

Du ser fremdriften rulle forbi (koordinator-sesjonen er synlig hele veien), og blir kun stoppet
ved ekte veiskiller (se under).

---

## Hvor du passer inn (human in the loop)

Du har tre roller. Ingen av dem krever at du sitter og venter.

### 1. Du starter og stopper loopen

Loopen kjører sekvensielt (én todo om gangen i første versjon) og **du bestemmer når den
kjører**. Start den ved å be koordinator-sesjonen kjøre `templates/commands/run-loop.md`
(kopiert inn som skill/instruks i prosjektet, se README for oppsett) — f.eks.:

- "Kjør loopen til køen er tom" — kontinuerlig
- "Kjør nøyaktig én todo, så stopp" — forsiktig oppstart / validering
- "Start med todo 41" — spesifikk oppgave

### 2. Du styrer køen (rattet)

Du trenger ikke røre koordinatoren for å endre hva som blir gjort. Rediger **ett felt i én fil**
under `tasks/todos/`:

| Vil du… | Gjør dette |
|---|---|
| Prioritere en oppgave | Sett `priority: prioritert` på todo-fila |
| Finjustere rekkefølge | Endre `order` |
| Ta noe ut av køen midlertidig | Sett `status: deferred` |
| Legge til ny oppgave | Lag en ny `tasks/todos/todo-NN-slug.md` |
| Tvinge en rekkefølge | Sett `deps: ["NN"]` |

Koordinatoren leser dette på nytt ved hver runde, så endringene slår inn umiddelbart.

### 3. Du svarer på pausepunkter

Loopen stopper og spør deg kun ved ekte veiskiller: `pause_triggers` i `loop.config.yaml`
(f.eks. skjemaendringer, nye avhengigheter, sikkerhets-/tilgangslogikk), 2 mislykkede
revisjonsrunder, eller en `status: blocked`-rapport fra en barnesesjon. Ellers går den av seg selv.

---

## Kvalitetssikring (uten å lese hver plan)

Kvaliteten sikres i tre lag, og dine øyne flyttes fra «hver plan» til «hver release»:

**Loopens egne lag (automatisk):**
- Uavhengig plan-reviewer (devil's advocate) før implementering
- Uavhengig kode-review på PR-diffen etter implementering, før merge (adversariell, read-only,
  maks 2 revisjonsrunder)
- **Verifikasjons-gate (betinget):** når PR-en leverer *vakter* (tester som finnes for å gå røde
  ved drift), dispatcher kode-revieweren en verifier-barnesesjon som **beviser at hver vakt
  faktisk KAN gå rød** ved å injisere en mutasjon i sin egen isolerte kopi. Poenget er ikke
  flere tester; det er at en test som ikke kan feile kjøper tillit uten å levere noe.
- Implementer-selvgransking + CI (build/type-check/lint/test) på hver PR
- **Periodisk helsesjekk** (`templates/commands/loop-health-check.md`): koordinatoren kjører
  tester, type-check, lint og en betinget tech-sweep mot integrert `origin/{{BASE_BRANCH}}` —
  enten etter et konfigurert antall merges eller når køen tømmes. Resultatet skrives som en
  helserad i `docs/run-log.md`.

**Ditt lag (periodisk, ikke per todo):**
- Se på `docs/run-log.md` innimellom — det er den fulle telemetrien
- Svar på pausepunkter når de kommer
- Kjør release (`{{RELEASE_COMMAND}}`) selv når helsesjekken anbefaler det — loopen anbefaler,
  utfører aldri, en prod-release (se hard grense i `docs/coordinator-runbook.md`)

---

## Kostnad og modellvalg

`loop.config.yaml: models` lar deg sette ulik modell/reasoning-effort per rolle — f.eks. en
rimeligere modell for planner/reviewer (mye lesing, lite generering) og en sterkere for
implementer (den som faktisk skriver koden). Dette leses av koordinatoren ved hvert dispatch,
så du kan justere det uten restart.
