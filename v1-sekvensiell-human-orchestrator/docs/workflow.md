# Arbeidsflyt

Referert fra `CLAUDE.md`. Inneholder prosess og format — ikke atferdsregler.

---

## Slash-kommandoer

| Kommando | Når brukes den |
|----------|----------------|
| `/start` | Alltid ved sesjonstart — full kontekstlasting |
| `/todo-plan` | Planlegg neste TODO, vent på bekreftelse, implementer |
| `/todo-execute` | Utfør en godkjent TODO steg for steg |
| `/todo-plan-review` | Devil's advocate — vurder en ferdig plan kritisk |
| `/todo-done` | Avslutt en TODO — code-review, arkiver, lessons, commit |
| `/endsession` | Alltid ved sesjonslutt — commit uferdig arbeid, oppdater status |
| `/status` | Lettvekts todo-oversikt uten full kontekstlasting |

---

## Branch og PR

### Branch-navnekonvensjon

| Type | Prefix | Eksempel | Typisk innhold |
|------|--------|----------|----------------|
| Feature | `feature/` | `feature/import-data` | Ny funksjonalitet |
| Bugfix | `fix/` | `fix/bug-003-auth-header` | Konkret bug fra bugs.md |
| Dokumentasjon | `docs/` | `docs/cleanup-2026-04` | Småting samles her |
| Release | `release/` | `release/2026-05-01` | Planlagt prod-release |

- Feature-branches opprettes alltid fra `<base-branch>`
- Alle PR-er har `<base-branch>` som target
- Direkte push til `main` er forbudt
- **Batching:** trivielle endringer (docs, .gitignore, småfikser) samles på én
  `docs/`-branch. Én PR med flere småfikser > fem PR-er med én linje hver.

### Når trenger en PR code-review?

**Kjør alltid** hvis PR-en endrer:
- Kjørbar kode
- Database-migrasjoner
- Avhengighetsfiler (`package.json`, `requirements.txt` osv.)
- Build- eller deploy-konfig

**Hopp over** hvis PR-en bare endrer:
- Dokumentasjon (`*.md`)
- Konfigurasjon uten kode-effekt (`.gitignore`, `.editorconfig`)
- Assets uten tilhørende kodeendring

Under 20 linjer og ingen kjørbar kode: overlat til brukeren.
Tvilstilfeller: spør brukeren før push.

### Det du ikke gjør
- Ikke merge PR automatisk
- Ikke kjør code-review på PR-er i "hopp over"-listen

---

## Bugregistrering — `tasks/bugs.md`

### Terskel for registrering
- Score ≥ 80, eller sikkerhet/datatap → registrer alltid
- Score < 80 → registrer kun hvis det gjelder sikkerhet eller data

### Alvorlighet
- Score ≥ 90, eller sikkerhet/datatap → **kritisk**
- Score 80–89, eller funksjonell feil → **høy**
- Score < 80 som likevel registreres → **lav**

### Format
```md
**BUG-[nr]**
- **Beskrivelse:** hva som er galt
- **Kilde:** code-review | manuell-test | bruker | claude-code
- **Fil:** filnavn og linje
- **Alvorlighet:** kritisk | høy | lav
- **Status:** åpen | under arbeid | lukket
- **Oppdaget:** YYYY-MM-DD
- **Løst:** YYYY-MM-DD eller —
- **Rotårsak:** fylles inn når løst
```

Nummerering er sekvensiell og gjenbrukes aldri.
Flytt til `tasks/bugs_archive.md` når lukket. Slett aldri.

---

## TODO-format — `tasks/todo.md`

```md
### TODO [nr] — [tittel]
- [ ] Gjennomført
**Hva:** Konkret beskrivelse
**Hvorfor:** Kort kontekst
**Test:** Eksakte kriterier som må være oppfylt før todoen kan markeres ferdig
**Status:** ny | plan klar — venter på review | reviewet — klar for /todo-execute | under arbeid | ferdig
```

- Marker `[x]` kun etter at testkriteriene er verifisert og godkjent
- Marker `[~]` for påbegynte todos med note om hva som gjenstår
- Når ferdig og godkjent: flytt til `tasks/todo_archive.md` via `/todo-done`
- TODO-numre er sekvensielle og gjenbrukes aldri

---

## Superpowers-integrasjon

[obra/superpowers](https://github.com/obra/superpowers) er et skill-bibliotek
som gir strukturerte kodepraksis-kommandoer. Installer via Claude Code Extensions.

### Skill-til-flyt-mapping

| Superpowers-skill | Når | Plassering i flyten |
|-------------------|-----|---------------------|
| `/brainstorm` | Utforsk tilnærminger | Før `/todo-plan` |
| `/tdd` | Ny feature | Første steg i `/todo-execute` |
| `/systematic-debugging` | Bug | Første steg i `/todo-execute` |
| `/security-review` | Auth/data-kode | Under `/todo-execute` |
| `/verification-before-completion` | Verifiser ferdig | Steg 3 i `/todo-done` |
| `/simplify` | Rydd opp kode | Steg 4 i `/todo-done` |

### TDD-syklus

```
/tdd → skriv failing test (RED)
     → minimum kode for å bestå (GREEN)
     → refaktorer uten å endre tester (REFACTOR)
     → gjenta per testkriterium fra planfilen
```

Hvert testkriterium i planfilens `## Verifisering` skal ha en korresponderende test
som dokumenterer *hvorfor* atferden er viktig (ikke bare *hva* den gjør).

### Debugging-protokoll

```
/systematic-debugging → reproduser problemet (minimaleksempel)
                      → formuler hypotese
                      → test hypotesen (logg, isoler)
                      → identifiser rot-årsak
                      → verifiser at fix løser rot-årsaken (ikke symptomet)
```

Skriv null kode før rot-årsaken er identifisert.
Etter fix: kall `@lessons-writer` med hva som var ikke-åpenbart.

---

## Prinsipp: brukerspråk i UI / engelsk under panseret

*(Fjern seksjonen hvis ikke relevant.)*

Data som lagres i database og sendes mellom systemer er på engelsk
(feltverdier, statuser, enums). Kun UI-tekst er på brukerens språk.
Ved nedtrekkslister: ha alltid eksplisitt mapping mellom visningsverdi
og databaseverdi — både ved skriving og lesing.
