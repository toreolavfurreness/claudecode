# Project-Agnostic Claude Code-mal

Dette er en gjenbrukbar mal for å sette opp Claude Code i et nytt prosjekt — uavhengig av programmeringsspråk, rammeverk eller database. Innholdet er destillert fra et faktisk produksjonsprosjekt og holdt på norsk.

## Hva er med

```
assets/projectagnostic/
├── README.md                       — denne filen
├── CLAUDE.md                       — prosjektets atferds- og samarbeidsregler
├── .claude/
│   └── commands/                   — slash-kommandoer for arbeidsflyt
│       ├── start.md                — sesjonsstart, full kontekstlasting
│       ├── status.md               — lettvekts oversikt uten kontekstlasting
│       ├── todo-plan.md            — planlegg neste TODO
│       ├── todo-plan-review.md     — devil's advocate-review av plan
│       ├── todo-execute.md         — gjennomfør godkjent TODO steg for steg
│       ├── todo-done.md            — avslutt TODO: review, arkiver, lessons, commit
│       └── endsession.md           — sesjonsslutt: commit, oppdater status, session dump
├── docs/
│   ├── architecture.md             — skjelett: stack, miljøer, mappestruktur
│   ├── data-model.md               — skjelett: tabeller, tilgangskontroll
│   ├── design-system.md            — skjelett: farger, typografi, mønstre (slett om ikke UI)
│   └── naming-conventions.md       — agnostisk struktur, juster per språk/stack
└── tasks/
    ├── todo.md                     — aktive oppgaver med format-mal
    ├── lessons.md                  — langtidsminne, format-mal
    ├── bugs.md                     — kjente bugs, format-mal
    ├── backlog.md                  — funksjonsidéer, format-mal
    ├── plans/                      — planfiler for aktive TODOs
    │   └── archive/                — arkiverte planfiler (flyttet av /todo-done)
    └── sessions/                   — session dumps fra /endsession
```

## Slik tar du det i bruk i et nytt prosjekt

1. **Kopier strukturen** inn i prosjektroten:
   ```bash
   cp -R assets/projectagnostic/. <nytt-prosjekt>/
   ```
   (Punktum etter skråstrek tar med skjulte mapper som `.claude/`.)

2. **Fyll inn `CLAUDE.md`** — søk etter `<PLACEHOLDER>`-merker og bytt med faktiske verdier (prosjektnavn, stack, database, hosting, branches, testverktøy osv.).

3. **Fyll inn `docs/`-skjelettene:**
   - `architecture.md` — beskriv stack, miljøer, mappestruktur
   - `data-model.md` — beskriv tabeller/entiteter og tilgangskontroll
   - `design-system.md` — kun hvis prosjektet har UI; ellers slett
   - `naming-conventions.md` — juster avsnitt 2–14 til faktisk språk/stack

4. **La `tasks/`-filene stå tomme.** De fylles etter hvert som du jobber.

5. **Verifiser kommandoene:** Åpne hver fil i `.claude/commands/` og bekreft at referanser til miljøvariabler, testverktøy og deploy-flyt passer for prosjektet ditt. Slett kommandoer du ikke trenger.

## Designvalg

- **Norsk innhold** — UI-tekst og samtale forblir på norsk; engelsk kan beholdes for kode/databaseidentifikatorer (se `naming-conventions.md`).
- **Agnostisk for stack** — ingen referanser til React Native, Supabase, Vercel, Playwright e.l. Originalen var bygget rundt disse, men er renset her.
- **Ikke inkludert** — `release-prod.md` (for stack-spesifikk), `tools.md` (eget MCP-oppsett), historisk innhold i `tasks/`-filene.

## Avhengigheter (valgfritt)

Kommandoene refererer til skills som ofte kommer med Claude Code-installasjonen:
- `/verification-before-completion`
- `/simplify`
- `/requesting-code-review`
- `/systematic-debugging`

Hvis disse ikke er installert, fungerer kommandoene fortsatt — instruksjonene er bare litt mindre rike. Du kan også fjerne referansene i `todo-done.md` og `todo-execute.md` om ønskelig.
