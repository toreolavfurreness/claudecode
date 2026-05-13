# <PROSJEKTNAVN> — CLAUDE.md

> Erstatt alle `<PLACEHOLDER>`-merker med faktiske verdier før første sesjon.

## Prosjektoversikt
**Hva:** <En setning om hva prosjektet er>
**Hvem:** <Målgruppe / brukere>
**Hvorfor:** <Kjerneproblem prosjektet løser>

## Infrastruktur
| Lag | Verdi |
|-----|-------|
| Språk / runtime | `<f.eks. TypeScript + Node 22>` |
| Frontend | `<f.eks. Next.js / ingen>` |
| Backend | `<f.eks. Express / Edge Functions / ingen>` |
| Database | `<f.eks. PostgreSQL / Supabase / ingen>` |
| Auth | `<f.eks. Supabase Auth / ingen>` |
| Hosting | `<f.eks. Vercel / Fly>` |
| Kildekode | `<git-url>` |

**Miljøer:** <Beskriv dev/prod-skille, hvilken branch deployer til hva, og
hvordan du verifiserer at du jobber mot riktig miljø før migrasjoner eller
deploys. Feil miljø er en av de vanligste kildene til datatap.>

## Språk
Svar alltid på norsk, uavhengig av hva brukeren skriver.

---

## Atferdsregler

Disse reglene gjelder for alle oppgaver med mindre eksplisitt overstyrt.

### Tenk før du koder
Si eksplisitt hva du antar. Spør istedenfor å gjette. Presenter flere
tolkninger når tvetydighet finnes. Push tilbake når en enklere løsning
eksisterer. Stopp når du er usikker — navngi hva som er uklart.

### Enkelhet først
Minimum kode som løser problemet. Ingen spekulative features. Ingen
abstraksjoner for engangsbruk. Ingen features utover det som ble bedt om.
Ville en erfaren utvikler kalt dette overkomplicert? Hvis ja — forenkle.

### Kirurgiske endringer
Berør bare det du må. Ikke "forbedre" nærliggende kode, kommentarer eller
formatering. Ikke refaktorer det som ikke er ødelagt. Match eksisterende stil.

### Mål-drevet utførelse
Definer suksesskriterier. Loop til verifisert. Definer hva suksess ser ut
som og iterer — ikke følg steg mekanisk. Marker aldri en oppgave ferdig
uten å bevise at den virker.

### Les før du skriver
Før du legger til kode i en fil: les filens eksporter, direkte kallere og
åpenbare delte utilities. Hvis du ikke forstår hvorfor eksisterende kode
er strukturert som den er — spør før du legger til.

### Konflikt: velg én, ikke bland
Hvis to mønstre i kodebasen er i konflikt: velg ett (det nyere / mest
testede), forklar hvorfor, og flagg det andre for opprydding.
Bland aldri konflikterenede mønstre — gjennomsnittskode er det verste utfallet.

### Tester verifiserer intensjon, ikke bare atferd
Hver test skal kode HVORFOR atferden er viktig, ikke bare HVA den gjør.
En test som ikke kan feile når forretningslogikken endres, er feil.

### Sjekk etter hvert steg
Etter hvert betydelig steg i en fler-stegsoppgave: oppsummer hva som er
gjort, hva som er verifisert, hva som gjenstår. Ikke fortsett fra en
tilstand du ikke kan beskrive tilbake til brukeren. Mister du oversikten
— stopp og restate.

### Match konvensjoner — selv om du er uenig
Konformitet > smak innenfor kodebasen. Navnekonvensjoner i
`docs/naming-conventions.md` er obligatorisk lesning før enhver oppgave
som oppretter eller endrer filer, variabler, komponenter, databaseobjekter,
branches eller env-variabler. Avvik: si fra eksplisitt, ikke fork stille.

### Feil høyt
"Fullført" er feil hvis noe ble hoppet over stille.
"Tester passerer" er feil hvis noen ble hoppet over.
"Fungerer" er feil hvis kanttilfellene du ble bedt om ikke ble verifisert.
Default til å synliggjøre usikkerhet — ikke skjul den.

---

## Sesjonstart

Gjør alltid dette først — før du gjør noe annet:
1. Les `CLAUDE.md` (denne filen)
2. Les `tasks/lessons/index.md`
3. Les lessons-filene som er relevante for dagens oppgave
4. Les `tasks/todo.md`
5. Finn første todo som ikke er merket `[x]`
6. Presenter en plan — vent på bekreftelse før koding starter

Hvis `tasks/todo.md` ikke finnes: opprett med format fra `docs/workflow.md`.
Hvis `tasks/lessons/` ikke finnes: opprett mappestrukturen (se `docs/workflow.md`).

---

## Langtidsminne — `tasks/lessons/`

Les `tasks/lessons/index.md` ved oppstart. Last kun relevante tema-filer.

Skriv til riktig tema-fil når:
- En bug ble fikset på en ikke-åpenbar måte
- En antakelse viste seg å være feil
- Brukeren måtte korrigere Claude

Ved ny lesson — tre steg:
1. Append til riktig tema-fil (`auth.md`, `database.md` osv.) med format:
   ```md
   ## [YYYY-MM-DD] — [tittel]
   **Problem:** ...
   **Løsning:** ...
   **Unngå:** ...
   **Trigger:** TODO-[nr] | BUG-[nr]
   → se også: [[relatert-fil]] hvis relevant
   ```
2. Oppdater sammendraget for filen i `tasks/lessons/index.md` (én setning)
3. Append én linje i `tasks/lessons/log.md`

Append alltid — slett aldri.

---

## Sikkerhet
- Aldri lagre API-nøkler eller passord i koden
- Aldri commit direkte til `main` — alltid branch + PR
- Når noe feiler: be om feilmeldingen og feilsøk før du går videre

## Dokumentasjon
- Arkitektur: `docs/architecture.md`
- Datamodell: `docs/data-model.md`
- Designsystem: `docs/design-system.md` *(kun hvis UI)*
- Navnekonvensjoner: `docs/naming-conventions.md`

## Arbeidsflyt og prosess
Se `docs/workflow.md` for: slash-kommandoer, branching, PR-prosess,
bug-registrering og todo-format.
