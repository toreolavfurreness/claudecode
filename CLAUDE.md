# <PROSJEKTNAVN> — CLAUDE.md

> Denne filen er Claude Codes hovedinstruks for prosjektet. Erstatt alle `<PLACEHOLDER>`-merker med faktiske verdier før første sesjon.

---

## Prosjektoversikt

**Hva:** <En setning om hva prosjektet er>
**Hvem:** <Målgruppe / brukere>
**Hvorfor:** <Kjerneproblem prosjektet løser>

## Infrastruktur

| Lag | Verdi |
|-----|-------|
| Språk / runtime | `<f.eks. TypeScript + Node 22>` |
| Frontend | `<f.eks. Next.js / React Native / ingen>` |
| Backend | `<f.eks. Express / Edge Functions / ingen>` |
| Database | `<f.eks. PostgreSQL / Supabase / SQLite / ingen>` |
| Auth | `<f.eks. Supabase Auth / NextAuth / Clerk / egen>` |
| Hosting | `<f.eks. Vercel / Fly / egen Docker>` |
| Kildekode | `<git-url>` |

### Miljøer

Beskriv miljøskillet hvis prosjektet har flere (dev / staging / prod). Inkluder:
- Hva hvert miljø brukes til
- Hvilken branch som deployer dit
- Hvilke ressurser (database, secrets) som er separate
- Hvordan migrasjoner / deploys håndteres mellom dem

> **Kritisk:** Hvis prosjektet har separate dev/prod-databaser eller -secrets, dokumenter eksplisitt hvordan du verifiserer at du jobber mot riktig miljø før migrasjoner eller deploys. Feil miljø er en av de vanligste kildene til datatap.

## Dokumentasjon
- Arkitektur: `docs/architecture.md`
- Datamodell: `docs/data-model.md`
- Designsystem: `docs/design-system.md` *(kun hvis UI)*
- Navnekonvensjoner: `docs/naming-conventions.md`

## Språk
Svar alltid på norsk, uavhengig av hva brukeren skriver.

---

## Atferd og arbeidsmetode

### Oppstart av hver sesjon
Gjør alltid dette først — før du gjør noe annet:
1. Les `CLAUDE.md` (denne filen)
2. Les `tasks/lessons.md`
3. Les `tasks/todo.md`
4. Finn første todo som ikke er merket `[x]`
5. Presenter en plan for den todoen — vent på bekreftelse før koding starter

Hvis `tasks/todo.md` ikke finnes: opprett den med riktig format (se nedenfor).
Hvis `tasks/lessons.md` ikke finnes: opprett den tom.

### Planlegging først
- For alle oppgaver med 3+ steg eller arkitekturvalg: skriv en plan og vent på bekreftelse før koding starter
- Hvis noe går galt: STOPP og lag ny plan — ikke fortsett å pushe
- Bruk planmodus også for verifiseringssteg, ikke bare bygging
- **Før analyse og løsningsvalg:** still deg alltid spørsmålet *"Hva ville en senior utvikler gjort her?"* — vurder rotårsak, ikke bare symptom, og vurder om den foreslåtte løsningen faktisk virker (plattform-begrensninger, tilgjengelighet, vedlikeholdbarhet)

### Kodepraksis
- Forklar alltid hva koden gjør og hvorfor — ikke bare lever koden
- **Trivielle endringer** (fargejustering, tekst, enkel bug): gjør direkte uten å vente på bekreftelse
- **Arkitekturvalg og oppgaver med 3+ steg:** skriv plan og vent på bekreftelse
- Aldri lagre API-nøkler eller passord i koden
- Aldri commit direkte til `main` — alltid branch + PR
- Når noe feiler: be om feilmeldingen og feilsøk før du går videre
- Etter feil fra brukeren: oppdater `tasks/lessons.md` med hva som gikk galt og hvordan det unngås

### Navnekonvensjoner

Alle navnekonvensjoner er definert i `docs/naming-conventions.md`.
Filen er **obligatorisk lesning** før enhver oppgave som oppretter
eller endrer:

- Filer eller mapper
- Variabler, funksjoner, komponenter eller typer
- Databaseobjekter (tabeller, kolonner, indekser, policies)
- Eksterne tjenester (functions, buckets, queues)
- Git-branches eller commit-meldinger
- Env-variabler

Avvik krever eksplisitt bekreftelse fra prosjekteier og skal dokumenteres
i `docs/naming-conventions.md` under seksjonen "Unntak og avvik".

### Oppgavehåndtering

`tasks/todo.md` er kilden til sannhet for hva som skal gjøres. Kontekst i chatten er midlertidig — filen overlever mellom sesjoner.

**Format for todos:**
```md
### TODO [nr] — [tittel]
- [ ] Gjennomført
**Hva:** Konkret beskrivelse av oppgaven
**Hvorfor:** Kort kontekst
**Test:** Eksakte kriterier som må være oppfylt før todoen kan markeres ferdig
```

**Regler:**
- Skriv alltid nye todos til `tasks/todo.md` — aldri bare i konteksten
- Marker `[x]` kun etter at testkriteriene er verifisert og godkjent av bruker
- Oppdater filen etter hver fullført og godkjent todo
- Når en todo er ferdig og godkjent: flytt den til `tasks/todo_archive.md` for å holde den aktive listen kort
- Legg til under eksisterende innhold i arkivfilen — ikke slett tidligere todos
- TODO-numre er **sekvensielle og gjenbrukes aldri** — bruk neste ledige basert på `todo.md` + `todo_archive.md`

#### Prinsipp: brukerspråk i UI / engelsk under panseret
*(Tilpass til prosjektet — slett seksjonen hvis ikke relevant.)*

Anbefalt mønster: data som lagres i database og sendes mellom systemer er på engelsk (feltverdier, statuser, roller, enums). Kun tekst som vises i UI-et er på brukerens språk. Ved nedtrekkslister med lokaliserte labels: ha alltid en eksplisitt mapping mellom visningsverdi og databaseverdi — både ved skriving og lesing.

### Slash-kommandoer
| Kommando | Når brukes den |
|----------|----------------|
| `/start` | Alltid ved sesjonstart — full kontekstlasting |
| `/todo-plan` | Planlegg neste TODO, vent på bekreftelse, implementer og oppdater todo.md fortløpende |
| `/todo-execute` | Utfør en godkjent TODO steg for steg — oppdater todo.md fortløpende |
| `/todo-plan-review` | Devil's advocate — vurder en ferdig plan kritisk før implementering |
| `/todo-done` | Avslutt en TODO — code-review, arkiver, lessons, commit |
| `/endsession` | Alltid ved sesjonslutt — commit uferdig arbeid, oppdater todo-status |
| `/status` | Lettvekts todo-oversikt uten full kontekstlasting |

### Lessons learned — `tasks/lessons.md`

Denne filen er Claude Codes langtidsminne for prosjektet. Den leses ved oppstart og skrives til når noe går galt eller løses på en ikke-åpenbar måte.

**Les filen ved oppstart** — sammen med `CLAUDE.md` og `tasks/todo.md`. Hvis filen ikke finnes, opprett den tom.

**Skriv til filen når:**
- En bug ble fikset på en ikke-åpenbar måte
- En antakelse viste seg å være feil
- Noe tok vesentlig lengre tid enn forventet pga. en fallgruve
- Brukeren måtte korrigere Claude

**Format:**
```md
## [dato] — [kort tittel]
**Problem:** Hva som gikk galt eller var uventet
**Løsning:** Hva som faktisk fungerte
**Unngå:** Konkret regel Claude skal følge fremover
```

**Regler:**
- Ikke slett eksisterende innhold — append alltid nederst
- Hold det konkret — ikke generelle refleksjoner, men handlingsbare regler
- Etter at noe er skrevet hit: vurder om det også bør inn i `CLAUDE.md` hvis det er en generell regel

### Verifisering
- Merk aldri en oppgave som ferdig uten å bevise at den virker
- Spør deg selv: "Ville en erfaren utvikler godkjent dette?"
- Bruk prosjektets primære testverktøy for funksjonell verifisering — `<f.eks. Playwright / Cypress / Vitest / pytest>`
- Beskriv testoppsettet konkret: hvordan startes serveren, hvordan kjøres tester, hvor ligger testbruker-credentials
- For endringer som ikke kan dekkes av automatiserte tester (database, auth-flyt, migrasjoner): logg ut hva som ble verifisert manuelt og hvordan

> **Tips:** Hold credentials og testdata i en lokal, gitignored konfig-fil (`.env.test` e.l.). Hardkod aldri passord i tester eller dokumentasjon.

---

## Branching-regler
- Feature-branches opprettes alltid fra `<base-branch, f.eks. dev>`
- Alle PR-er har `<base-branch>` som base branch
- Direkte push eller merge til `main` er forbudt uten eksplisitt bekreftelse
- `main` representerer produksjonsmiljø og røres kun ved planlagte releaser

---

## Arbeidsflyt — branch og PR

### Regler
- Aldri push direkte til `main`
- Branches knyttes til arbeidsenheter, ikke sesjoner. Ved sesjonsstart spør `/start` om formålet og foreslår enten å fortsette en eksisterende branch eller opprette en ny
- Branch-navnekonvensjon etter type arbeidsenhet:

  | Type | Branch-prefix | Eksempel | Typisk innhold |
  |------|---------------|----------|----------------|
  | Feature | `feature/` | `feature/import-data` | Ny funksjonalitet, multi-sesjons arbeid |
  | Bugfix | `fix/` | `fix/bug-003-auth-header` | Konkret bug fra `tasks/bugs.md` |
  | Dokumentasjon / rydding | `docs/` | `docs/cleanup-2026-04` | Småting samles på én branch |
  | Release | `release/` | `release/2026-05-01` | Planlagt prod-release, ingen kodeendringer |

- **Batching-regel for småting:** Dokumentasjon, bug-loggføring, `.gitignore`-endringer og lignende trivielle endringer samles på én felles `docs/`-branch i stedet for én branch per endring. Én PR med flere småfikser > fem PR-er med én linje hver.
- Når arbeidsenheten er ferdig: åpne en PR mot base-branch
- Vurder om PR-en trenger code-review (se "Når trenger en PR code-review?" nedenfor)
- Hvis bugs funnet: registrer hvert funn i `tasks/bugs.md` (se "Bugregistrering" nedenfor), fiks dem, kjør review på nytt

### Når trenger en PR code-review?

**Kjør automatisk** hvis PR-en endrer noe av følgende:
- Kjørbar kode (alle språkfiler)
- Database-migrasjoner og skjemaendringer
- Eksterne funksjoner / serverless handlers
- Avhengighetsfiler (`package.json`, `requirements.txt`, `Cargo.toml` osv.)
- Build-/deploy-config

**Hopp over** hvis PR-en bare endrer:
- Dokumentasjon (`*.md`)
- Konfigurasjon uten kode-effekt (`.gitignore`, `.editorconfig`, `.prettierrc`)
- Bilder/assets uten tilhørende kode-endring

**Egen unntaksregel — små differ:** Hvis hele diffen er **under 20 linjer OG ikke berører kjørbar kode**, hopp over og overlat til brukeren.

**Tvilstilfeller → spør brukeren før push.**

### Bugregistrering

Funn fra code-review registreres i `tasks/bugs.md` etter alvorlighet:
- **Score ≥ 80, eller sikkerhet/datatap** → registrer alltid
- **Score < 80** → vurder: handler det om sikkerhet/data, registrer; handler det om formattering, ignorer eller samle til ryddeoppgave

Alvorlighet:
- Score ≥ 90, eller sikkerhet/datatap → **kritisk**
- Score 80–89, eller funksjonell feil → **høy**
- Score < 80 som likevel registreres → **lav**

Hvert bug-innslag skal ha disse feltene:
- **Beskrivelse:** hva som er galt
- **Kilde:** code-review | manuell-test | bruker | claude-code
- **Fil:** filnavn og linje
- **Alvorlighet:** kritisk | høy | lav
- **Status:** åpen | under arbeid | lukket
- **Oppdaget:** YYYY-MM-DD
- **Løst:** YYYY-MM-DD eller —
- **Rotårsak:** fylles inn når løst

Bugs nummereres sekvensielt (`BUG-001`, `BUG-002` …). Flytt til `bugs_archive.md` når lukket. Slett aldri.

### Det du ikke gjør
- Ikke merge PR automatisk til base-branch
- Ikke kjør code-review på PR-er som faller under "hopp over"-listen — overlat valget til brukeren

---

## Svarformat

- Korte, konsise svar — ingen unødvendig fylltekst
- Forklar tekniske begreper første gang de dukker opp
- Bruk alltid kodeblokker med riktig markering for prosjektets språk

### Oppsummering etter hver endring
Avslutt alltid med:
- **Hva ble gjort** — kort beskrivelse
- **Før** — hvordan det så ut før
- **Etter** — hvordan det ser ut nå
- **Kodeoppsummering** — relevante kodelinjer

Gjelder særlig for endringer som ikke dekkes av automatiserte tester.

---

## Det du ikke gjør
- Ikke introduser nye teknologier uten å forklare tydelig hvorfor
- Ikke anta at brukeren kjenner terminologi
- Ikke gi lange kodeblokker uten forklaring
- Ikke fortsett til neste steg uten bekreftelse
- Ikke late som du vet noe du ikke vet — si fra tydelig
