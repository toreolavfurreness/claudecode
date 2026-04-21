# [Prosjektnavn] — CLAUDE.md

## Infrastruktur
| Service      | Detail                                      |
|--------------|---------------------------------------------|
| Supabase     | Project ID: `[din-supabase-project-id]`     |
| Supabase URL | `https://[din-supabase-project-id].supabase.co` |
| Vercel       | Project ID: `[din-vercel-project-id]` — Team: `[din-team-id]` |
| GitHub       | `https://github.com/[bruker]/[repo]`        |

**ALDRI bruk en annen project-ref for MCP-kall, migrasjoner eller Edge Function-deploys.**
Hvis du har en global `~/CLAUDE.md` som tilhører et annet prosjekt — verifiser alltid mot tabellen over før du kjører Supabase MCP-kall.

## Dokumentasjon
- Design: `docs/design-system.md`
- Arkitektur: `docs/architecture.md`
- Datamodell: `docs/data-model.md`
- Navnekonvensjoner: `docs/naming-conventions.md`

## Språk
Svar alltid på norsk, uavhengig av hva brukeren skriver.
All UI-tekst (det brukeren ser) er norsk. All kode, filnavn, databaseobjekter og Git-artefakter er engelske. Skillet er absolutt — se `docs/naming-conventions.md`.

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
- **Før analyse og løsningsvalg:** still deg alltid spørsmålet *"Hva ville en senior utvikler gjort her?"* — vurder rotårsak, ikke bare symptom, og vurder om den foreslåtte løsningen faktisk virker (f.eks. iOS-begrensninger, tilgjengelighet, vedlikeholdbarhet)

### Kodepraksis
- Forklar alltid hva koden gjør og hvorfor — ikke bare lever koden
- **Trivielle endringer** (fargejustering, tekst, enkel bug): gjør direkte uten å vente på bekreftelse
- **Arkitekturvalg og oppgaver med 3+ steg**: skriv plan og vent på bekreftelse
- Aldri lagre API-nøkler eller passord i koden
- Aldri commit direkte til `main` — alltid branch + PR
- Når noe feiler: be om feilmeldingen og feilsøk før du går videre
- Etter feil fra brukeren: oppdater `tasks/lessons.md` med hva som gikk galt og hvordan det unngås

### Navnekonvensjoner

Alle navnekonvensjoner er definert i `docs/naming-conventions.md`.
Filen er **obligatorisk lesning** før enhver oppgave som oppretter eller endrer:

- Filer eller mapper
- Variabler, funksjoner, komponenter eller typer
- Databasetabeller, kolonner, indekser eller RLS-policies
- Edge Functions eller Storage-buckets
- Git-branches eller commit-meldinger
- Env-variabler

Avvik krever eksplisitt bekreftelse fra prosjekteier og skal dokumenteres i `docs/naming-conventions.md` under seksjonen "Unntak og avvik".

### Oppgavehåndtering

`tasks/todo.md` er kilden til sannhet for hva som skal gjøres. Kontekst i chatten er midlertidig — filen overlever mellom sesjoner.

**Format for todos:**
```md
### TODO [nr] — [tittel]
**Status:** ikke påbegynt
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

#### Prinsipp: norsk UI / engelsk backend
All data som sendes til og lagres i Supabase skal være på engelsk (feltverdier, statuser, roller osv.). Kun tekst som vises i UI-et skal være norsk. Ved bruk av nedtrekkslister eller valgknapper med norske labels må det alltid ligge en eksplisitt mapping mellom norsk visningsverdi og engelsk databaseverdi — både ved skriving og lesing.

### Slash-kommandoer
| Kommando       | Når brukes den |
|----------------|----------------|
| `/start`       | Alltid ved sesjonstart — full kontekstlasting |
| `/todo-plan`   | Planlegg neste TODO, vent på bekreftelse, implementer og oppdater todo.md fortløpende |
| `/todo-execute`| Utfør en godkjent TODO steg for steg — oppdater todo.md fortløpende |
| `/todo-done`   | Avslutt en TODO — kjør review, arkiver, lessons, commit |
| `/endsession`  | Alltid ved sesjonslutt — commit uferdig arbeid, oppdater todo-status |
| `/status`      | Lettvekts todo-oversikt uten full kontekstlasting |

### Lessons learned — `tasks/lessons.md`

Denne filen er Claude Code sitt langtidsminne. Den leses ved oppstart og skrives til når noe går galt eller løses på en ikke-åpenbar måte.

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
- Bruk alltid Playwright til funksjonell verifisering — **aldri manuell `npm run web`**
- Playwright spinner opp egen server automatisk via `webServer` i `playwright.config.ts`
- Testbruker og passord hentes fra `.env.test` — aldri hardkod passord i tester
- Både `playwright` (CLI) og `@playwright/test` (test-API) må være installert og på samme versjon
- Sjekk alltid `package.json` før du installerer noe — verifiser med `npx playwright --version` ved tvil
- Aldri kjør `npm install` for pakker som allerede finnes i prosjektet
- Kjør testene med `npm run test:e2e` og rapporter resultatet før PR opprettes
- For endringer som ikke kan testes med Playwright (database, auth-flyt, Supabase-migrasjoner): sjekk Supabase-logg og kjør SQL for å bekrefte

**`.env.test` — lokal konfigurasjon for Playwright:**
Filen ligger i prosjektroten og er gitignored (skal aldri committes). Opprett lokalt med:
```
TEST_USER_EMAIL=[din-testbruker@epost.no]
TEST_USER_PASSWORD=[hent fra passordbehandler]
```
Valgfritt for å kjøre mot Vercel preview i stedet for lokal dev-server:
```
PLAYWRIGHT_BASE_URL=https://[din-preview].vercel.app
```
Når `PLAYWRIGHT_BASE_URL` ikke er satt, starter Playwright lokal dev-server automatisk.

---

## Faste regler — lessons fra forrige prosjekt

Disse er lært på harde måten. Følges alltid — avvik krever eksplisitt bekreftelse fra prosjekteier.

### Supabase Edge Functions
- **Deploy alltid med `verify_jwt: false` + gjør manuell `auth.getUser()` i funksjonen.** Automatisk JWT-verifisering i Supabase-plattformen er upålitelig på tvers av klient-versjoner. Gjør autentisering eksplisitt i koden.
- **Verifiser `schema_migrations` etter hvert MCP `apply_migration`-kall.** MCP-responsen kan gi suksess selv når migrasjonen ikke ble registrert. Sjekk `select * from supabase_migrations.schema_migrations order by version desc limit 5` for å bekrefte.

### Supabase RLS
- **Bruk `SECURITY DEFINER`-funksjoner for RLS-sjekker — aldri inline subquery mot samme tabell.** Inline-subquery mot samme tabell gir uendelig rekursjon eller skjulte ytelsesproblemer. Definer hjelpefunksjoner i `public`-skjemaet (f.eks. `is_member(team_id)`) og bruk dem i policies.
- **Aldri anta at en lokal skjemafil er sannhet.** Den kan være generert fra en gammel dump. Sjekk alltid `pg_policy`, `pg_constraint`, og `information_schema` direkte når du skal verifisere faktisk skjema.

### Migrasjoner
- **Engangs-datarydding skal aldri committes som migrasjon.** Migrasjoner skal være idempotente og representere skjemaendringer, ikke engangs-fikser av data. Data-opprydding kjøres ad-hoc via SQL-editor eller MCP `execute_sql`, og dokumenteres i `tasks/lessons.md` hvis relevant.

### Next.js og Web

- **Server Components som default.** Bruk `'use client'` kun når du trenger interaktivitet (state, events, hooks). Les som regel data på serveren.
- **app/-routeren, ikke pages/.** Alle nye ruter legges i `app/` med App Router-mønster.
- **`accessibilityLabel` på alle ikon-knapper.** Gir skjermlesere meningsfull etikett og fungerer som stabil test-selector i Playwright.
- **Minimum `fontSize: 16px` på tekstinputter.** iOS Safari zoomer automatisk inn på inputs med mindre skrift — det ødelegger layouten.
- **Unngå `window.confirm()` når mulig.** Bruk state-basert modal/UI i stedet for native browser-dialogs. Native dialoger blokkerer hele siden.
- **TypeScript på alle React-komponenter.** Ingen `.jsx` uten typer.

---

## Arbeidsflyt — branch og PR

### Regler
- Aldri push direkte til `main`
- **Branches knyttes til arbeidsenheter, ikke sesjoner.** Ved sesjonsstart spør `/start` om formålet og foreslår enten å fortsette en eksisterende branch eller opprette en ny
- Branch-navnekonvensjon etter type arbeidsenhet:

  | Type | Branch-prefix | Eksempel | Typisk innhold |
  |------|---------------|----------|----------------|
  | Feature | `feat/` | `feat/ny-funksjonalitet` | Ny funksjonalitet, multi-sesjons arbeid |
  | Bugfix | `fix/` | `fix/bug-003-beskrivelse` | Konkret bug fra `tasks/bugs.md` |
  | Dokumentasjon / rydding | `docs/` | `docs/april-cleanup` | Småting batches — loggføringer, doc-fikser og ryddeoppgaver |

- **Batching-regel for småting:** Dokumentasjon, bug-loggføring, `.gitignore`-endringer og lignende trivielle endringer skal samles på én felles `docs/`-branch i stedet for å opprette én branch per endring.
- Når arbeidsenheten er ferdig: åpne en PR mot `main` med `gh pr create`
- Vurder om PR-en trenger code-review (se nedenfor)
- Spør brukeren om de ønsker å merge PR-en til main (via `gh pr merge --squash`) — **ikke merge automatisk**

### Når trenger en PR code-review?

**Kjør code-review automatisk** hvis PR-en endrer noe av følgende:
- Kjørbar kode: `.ts`, `.tsx`, `.js`, `.jsx`
- SQL og Supabase-migrasjoner: `supabase/migrations/**`, `*.sql`
- Edge Functions: `supabase/functions/**`
- Avhengigheter: `package.json`, `package-lock.json`
- Build-/deploy-config: `vercel.json`, `app.json`, `tsconfig.json`, `babel.config.js`

**Hopp over** (rapporter PR som klar og overlat valget til brukeren) hvis PR-en bare endrer:
- Dokumentasjon: `*.md` (CLAUDE.md, README, `tasks/**`)
- Konfigurasjon uten kode-effekt: `.gitignore`, `.env.example`, `.editorconfig`, `.prettierrc`
- Bilder/assets uten tilhørende kode-endring

**Egen unntaksregel — små differ:** Hvis hele diffen er **under 20 linjer OG ikke berører noen av "kjør automatisk"-filene over**, hopp over.

**Tvilstilfeller → spør brukeren før push.**

### Bugregistrering
Alle funn fra code-review med score ≥ 80 registreres alltid i `tasks/bugs.md`.
Funn med score < 80 vurderes slik:
- Handler det om sikkerhet eller data? → Registrer uansett score
- Handler det om formattering eller navnekonvensjon? → Ignorer, eller samle til ryddeoppgave

Alvorlighet settes basert på code-review-score:
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

Bugs nummereres sekvensielt (BUG-001, BUG-002 ...). Flytt til "## Lukkede bugs" når løst. Slett aldri.

### Det du ikke gjør
- Ikke merge PR automatisk til main
- Ikke kjør code-review på PR-er som faller under "hopp over"-listen — overlat valget til brukeren

---

## Svarformat

- Korte, konsise svar — ingen unødvendig fylltekst
- Forklar tekniske begreper første gang de dukker opp
- Bruk alltid kodeblokker med riktig markering:
  - React/JSX → ` ```jsx `
  - TypeScript → ` ```typescript `
  - Bash/terminal → ` ```bash `
  - SQL → ` ```sql `

### Oppsummering etter hver endring
Avslutt alltid med:
- **Hva ble gjort** — kort beskrivelse
- **Før** — hvordan det så ut før
- **Etter** — hvordan det ser ut nå
- **Kodeoppsummering** — relevante kodelinjer

Gjelder særlig for endringer som ikke dekkes av Playwright-tester (f.eks. visuelle justeringer, dokumentasjon, konfigurasjon).

---

## Det du ikke gjør
- Ikke introduser nye teknologier uten å forklare tydelig hvorfor
- Ikke anta at brukeren kjenner terminologi
- Ikke gi lange kodeblokker uten forklaring
- Ikke fortsett til neste steg uten bekreftelse
- Ikke late som du vet noe du ikke vet — si fra tydelig
