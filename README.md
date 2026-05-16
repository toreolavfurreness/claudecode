# Claude Code — prosjektmal

En gjenbrukbar mal for å sette opp Claude Code i et nytt prosjekt. Bygget
på Karpathy's 12 atferdsregler, wiki-basert langtidsminne og separert
planleggings- og implementeringsflyt med modellvalg per fase.

Innholdet er på norsk. Kode, filnavn og databaseobjekter er på engelsk.

---

## Filosofi

De fleste CLAUDE.md-filer er enten for lange eller for tomme. For lange:
Claude følger dem 30% av tiden. For tomme: ingen konsistens mellom sesjoner.

Denne malen er bygget rundt tre innsikter:

**1. CLAUDE.md er en atferdskontrakt, ikke en prosjekthåndbok.**
Compliance faller kraftig etter 200 linjer fordi viktige regler drukner i
støy. Her er atferdsregler i CLAUDE.md (141 linjer), prosessinnhold i
`docs/workflow.md`. De to blandes aldri.

**2. Lessons-wikien løser kontekstproblemet.**
En flat `lessons.md` vokser til 500+ linjer etter noen måneder — og lastes
i sin helhet hver sesjon. Wikien i `tasks/lessons/` lar Claude laste kun
det som er relevant for dagens oppgave, navigert via `index.md`.
Designet er inspirert av Karpathy's LLM Wiki-mønster:
*"Obsidian is the IDE; the LLM is the programmer; the wiki is the codebase."*

**3. Planlegging og implementering er separate kontekster.**
Når `/todo-execute` kjøres etter `/todo-plan` i samme sesjon, starter
implementeringen forurenset av planleggingsdiskusjonen, forkastede
tilnærminger og tilbakemelding. Planfilen (`tasks/plans/todo-X.md`) er
API-et mellom de to fasene — implementeringsagenten leser kun den.

---

## Mappestruktur

```
prosjektrot/
│
├── CLAUDE.md                   Atferdsregler + prosjektkontekst (141 linjer)
├── README.md                   Denne filen
│
├── .claude/
│   └── agents/                 Sub-agent definisjoner (YAML frontmatter + system prompt)
│       ├── planner.md          Opus 4.7 — produserer planfil
│       ├── implementer.md      Sonnet 4.6 — implementerer fra planfil
│       ├── reviewer.md         Sonnet 4.6 — code review av git diff
│       └── lessons-writer.md   Haiku 4.5 — oppdaterer lessons-wiki
│
├── docs/
│   ├── architecture.md         Stack, miljøer, mappestruktur
│   ├── data-model.md           Tabeller, entiteter, tilgangskontroll
│   ├── design-system.md        Farger, typografi, mønstre (slett om ikke UI)
│   ├── naming-conventions.md   Navnekonvensjoner — obligatorisk lesning
│   └── workflow.md             Slash-kommandoer, branching, PR, bug- og todo-format
│
├── tasks/
│   ├── todo.md                 Aktive TODOs
│   ├── bugs.md                 Kjente bugs
│   ├── backlog.md              Idéer og fremtidige features
│   ├── plans/                  Planfiler for aktive TODOs (opprettes av /todo-plan)
│   │   └── archive/            Arkiverte planfiler (flyttes av /todo-done)
│   ├── sessions/               Session dumps fra /endsession
│   └── lessons/                Wiki — Claude Codes langtidsminne
│       ├── index.md            Innholdskatalog + navigering + lint-rutine
│       ├── log.md              Append-only kronologisk logg
│       ├── general.md
│       ├── auth.md
│       ├── database.md
│       ├── api.md
│       ├── ui.md
│       ├── testing.md
│       └── git-workflow.md
│
└── [skill-filer på rot]        Slash-kommandoer for Claude Code
    ├── start.md                /start — sesjonstart, full kontekstlasting
    ├── status.md               /status — lettvekts oversikt
    ├── todo-plan.md            /todo-plan — planlegg neste TODO
    ├── todo-plan-review.md     /todo-plan-review — devil's advocate
    ├── todo-execute.md         /todo-execute — implementer godkjent TODO
    ├── todo-done.md            /todo-done — avslutt, arkiver, lessons, commit
    └── endsession.md           /endsession — sesjonsslutt
```

---

## Komme i gang

**1. Kopier malen inn i prosjektroten:**
```bash
cp -R path/to/mal/. ditt-prosjekt/
```

**2. Fyll inn `CLAUDE.md`** — søk etter `<PLACEHOLDER>` og bytt ut:
- Prosjektnavn, målgruppe, kjerneproblem
- Stack (språk, frontend, backend, database, auth, hosting)
- Miljøbeskrivelse (dev/prod-skille, hvilken branch deployer til hva)

**3. Fyll inn `docs/`-skjelettene:**
- `architecture.md` — stack, miljøer, mappestruktur
- `data-model.md` — tabeller og tilgangskontroll
- `naming-conventions.md` — juster til faktisk språk og stack
- Slett `design-system.md` hvis prosjektet ikke har UI

**4. La `tasks/`-filene stå tomme.** De fylles i takt med arbeidet.

**5. Start første sesjon med `/start`.** Claude leser CLAUDE.md, navigerer
lessons-wikien og presenterer en plan for første TODO.

---

## Karpathy's 12 atferdsregler

Alle 12 reglene er i `CLAUDE.md`. Her er begrunnelsen for de viktigste:

| Regel | Problemet den løser |
|-------|---------------------|
| **Tenk før du koder** | Stille feil antakelser er den hyppigste feilkilden |
| **Enkelhet først** | Over-engineering skjer uten eksplisitt forbud |
| **Kirurgiske endringer** | Claude "forbedrer" nærliggende kode den ikke ble bedt om å røre |
| **Les før du skriver** | Dupliserte funksjoner fordi eksisterende kode ikke ble lest |
| **Konflikt: velg én** | Blanding av to mønstre er verre enn begge alene |
| **Token-budsjett** | Uten budsjett spinner sesjoner ut i 50k-token kontekstdumper |
| **Sjekk etter hvert steg** | Feil på steg 4 propagerer til steg 5 og 6 uoppdaget |
| **Feil høyt** | "Fullført" er den farligste løgnen i AI-assistert utvikling |

---

## Lessons-wiki og Obsidian

### Hvordan wikien fungerer

Ved sesjonstart leser Claude `tasks/lessons/index.md` — ikke alle tema-filene.
Index.md inneholder et sammendrag per fil. Claude åpner kun de filene som
er relevante for dagens oppgave. Over tid:

```
Måned 1:   index.md (30 linjer) + 1–2 filer (20–40 linjer) = ~60 linjer
Måned 6:   index.md (50 linjer) + 1–2 filer (40–60 linjer) = ~100 linjer
Måned 18:  index.md (80 linjer) + 1–2 filer (50–80 linjer) = ~150 linjer
```

En flat `lessons.md` ville vært 900+ linjer på måned 18 og lastet i sin helhet.

### Obsidian-integrasjon

Wikien er Obsidian-kompatibel uten noen konfigurasjon — filene bruker
`[[wiki-link]]`-syntaks for kryssreferanser.

**Åpne som vault:**
```
Obsidian → File → Open Folder as Vault → velg tasks/lessons/
```

Vil du ha todos, bugs og backlog med i samme vault? Pek på `tasks/` i stedet.

**Hva du får:**
- **Graph view** — visualiser koblingene mellom tema-filer, finn orphan-lessons
- **Backlinks** — se hvilke lessons som lenker til hverandre
- **Søk** — søk på tvers av alle lessons uten å åpne hver fil

**Lint-rutinen** (én gang per måned) er dokumentert i `tasks/lessons/index.md`:
finn motsetninger, foreldede entries og orphan-sider. Graph view gjør
orphan-deteksjon visuell — isolerte noder er lessons ingen lenker til.

---

## Sub-agents og sesjonsstruktur

Sub-agents kjører i egne kontekstvinduer og returnerer kun et sammendrag
til hovedsesjonen. Brukes kun der interaktivitet ikke er nødvendig.

| Agent | Modell | Verktøy | Trigger | Hvorfor sub-agent |
|-------|--------|---------|---------|-------------------|
| `plan-reviewer` | Opus 4.7 | Read | /todo-plan (automatisk) | Frisk kontekst = avdekker antakelser fra planleggingsdiskusjonen |
| `reviewer` | Sonnet 4.6 | Read, Grep, Glob, Bash | /todo-done | Ikke-interaktiv, strukturert output |
| `lessons-writer` | Haiku 4.5 | Read, Write | /todo-done | Rutinemessig, billig |

### Sesjonsstruktur per TODO

Planlegging og implementering kjører alltid i **separate sesjoner** for å
unngå kontekstforurensing:

```
Sesjon 1 — Planlegging (Opus anbefalt)
  /todo-plan
    → PlanMode + AskUserQuestion (full interaktivitet)
    → Skriver planfil til disk
    → Spawner @plan-reviewer (Opus, leser kun planfilen — frisk kontekst)
    → Presenter funn: Critical / Important / Minor
    → Bruker godkjenner eller reviderer

Sesjon 2 — Implementering (Sonnet, standard)
  /todo-execute
    → Leser kun: CLAUDE.md + planfilen
    → Ren kontekst, ingen planleggingsdiskusjon
    → /tdd (ny feature) eller /systematic-debugging (bug)

Sesjon 2 avslutning
  /todo-done
    → @reviewer (sub-agent, leser git diff)
    → @lessons-writer (sub-agent, oppdaterer wiki)
```

**Modellvalg per sesjon:**
- Planlegging: bytt til Opus med `/model claude-opus-4-7`
- Implementering: Sonnet er standard — ingen bytte nødvendig

**Sub-agents arver ikke CLAUDE.md automatisk.** Relevante atferdsregler
er inkludert direkte i hver agents system prompt.

---

## Hooks

Hooks håndheves av Claude Code-harness — ikke av Claude selv. Det betyr
at de er 100% pålitelige, i motsetning til CLAUDE.md-regler (~80%).

Alt som *må* holde, ikke bare *bør* holde, hører hjemme i en hook.

**Eksempel — blokker commit direkte til main:**
```json
// .claude/settings.json
{
  "hooks": {
    "PreToolCall": [{
      "matcher": "Bash",
      "hooks": [{
        "type": "command",
        "command": "bash -c 'if echo \"$CLAUDE_TOOL_INPUT\" | grep -q \"git commit\" && [ \"$(git branch --show-current)\" = \"main\" ]; then echo \"BLOKKERT: commit til main er forbudt\" && exit 1; fi'"
      }]
    }]
  }
}
```

Se `docs/workflow.md` for flere hook-eksempler og konfigurasjonsguide.

---

## Superpowers-plugin

[obra/superpowers](https://github.com/obra/superpowers) er et skill-bibliotek
for Claude Code som gir strukturerte kodepraksis-kommandoer. Det er
**komplementært** til dette oppsettet — ikke konkurrerende.

| Nivå | Dette oppsettet | Superpowers |
|------|-----------------|-------------|
| **Spørsmål** | Hva bygger vi, i hvilken rekkefølge? | Hvordan skriver vi god kode? |
| **Verktøy** | Agents, plan-filer, lessons-wiki | Skills per oppgave |
| **Persistens** | Langtidsminne på tvers av sesjoner | Aktiveres per kommando |

### Integrasjonskart

```
/todo-plan (@planner)
  └── Valgfritt: /brainstorm FØR planner kalles
      → Utforsk 3-5 tilnærminger, gi den beste til planner

/todo-execute (@implementer)
  ├── Ny feature    → START med /tdd (red-green-refactor)
  ├── Bug           → START med /systematic-debugging (diagnose rot-årsak FØR kode)
  └── Sikkerhetskode → /security-review inline

/todo-done
  ├── /verification-before-completion  ← Superpowers
  ├── /simplify på endrede filer       ← Superpowers
  ├── @reviewer (Critical/Important/Minor)  ← Native agent
  └── @lessons-writer                       ← Native agent
```

### TDD-arbeidsflyt

1. `@planner` skriver testkriterier inn i `## Verifisering` i planfilen
2. `@implementer` starter med `/tdd` — tvinger red-green-refactor
3. Hvert testkriterium fra planfilen dokumenterer *hvorfor* atferden er viktig
4. `/todo-done` → `/verification-before-completion` kjører testene, bekrefter faktisk output

### Systematisk debugging

1. Bug oppdages → logg i `tasks/bugs.md`
2. Kjør `/systematic-debugging` **FØR** du rører kode — identifiser rot-årsak
3. Er buggen kompleks nok for TODO? → `/todo-plan`. Liten og forstått? → Fiks direkte
4. Etter fix: `@lessons-writer` dokumenterer hva som var ikke-åpenbart

### Installasjon

```bash
# Åpne Claude Code → Extensions, eller følg instruksjoner på:
# https://github.com/obra/superpowers
```

Pluginen er anbefalt men ikke påkrevd. Fallback-instruksjon er dokumentert
direkte i `todo-done.md` og `todo-execute.md`.

---

## Hva dette ikke er

- **Ikke et CI/CD-oppsett** — ingen GitHub Actions, ingen deploy-scripts
- **Ikke prosjektdokumentasjon** — `docs/`-skjelettene er tomme maler
- **Ikke stack-spesifikt** — ingen referanser til React, Supabase, Vercel
- **Ikke en chatbot-konfigurasjon** — malen forutsetter Claude Code CLI

---

## Etter første uke

**Lessons begynner å vokse:** Kjør lint-rutinen i `tasks/lessons/index.md`
én gang per måned. Slett foreldede entries, flytt feilplasserte lessons,
fiks orphan-noder.

**En TODO er for stor:** Del den i to. Planfiler som har mer enn 8–10 steg
er et tegn på at scope er for bredt for én PR.

**Agent-flyten er overkill:** For trivielle endringer (tekst, fargejustering,
enkel bug) — bruk Claude Code direkte uten skill-filer. Flyten er designet
for oppgaver med 3+ steg og arkitekturvalg.

**Stack-spesifikke tilpasninger:** Legg prosjektspesifikke regler *under*
de 12 atferdsreglene i CLAUDE.md. Ikke over 200 linjer totalt.
