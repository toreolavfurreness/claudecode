# Claude Code Skills

En samling slash-kommandoer for strukturert utvikling med Claude Code. Kommandoene implementerer en sesjonsbasert arbeidsflyt der Claude alltid vet hvor prosjektet står, hva som skal gjøres, og hva som er lært underveis.

Utviklet for bruk med [Next.js](https://nextjs.org/), [Supabase](https://supabase.com/) og [Vercel](https://vercel.com/), men kjerneprinsippene fungerer for ethvert prosjekt med en `tasks/`-mappestruktur.

---

## Filosofi

Kontekst i chatten er midlertidig. Filer overlever mellom sesjoner.

Workflowen er bygget rundt noen få filer som Claude leser ved oppstart og skriver til underveis:

| Fil | Formål |
|-----|--------|
| `CLAUDE.md` | Prosjektregler, infrastruktur og atferdsregler |
| `tasks/todo.md` | Kilden til sannhet for hva som skal gjøres |
| `tasks/bugs.md` | Oversikt over kjente feil og status |
| `tasks/lessons.md` | Langtidsminne — feil, fallgruver og løsninger |
| `tasks/plans/todo-<nr>-<slug>.md` | Detaljert planfil per TODO |
| `tasks/sessions/todo-<nr>-<slug>.md` | Sesjonsnotat ved avbrudd |

Claude gjør ingenting uten å ha lest relevant kontekst. Claude gjør ingenting uten å presentere en plan og vente på bekreftelse.

---

## Kommandoer

### `/start`
Brukes alltid ved sesjonstart. Laster full kontekst ved å lese `CLAUDE.md`, `tasks/lessons.md`, `tasks/bugs.md` og `tasks/todo.md`. Kjører git-orientering (`branch`, `log`, `status`), sjekker for avbrutte sesjoner og ucommittede endringer, finner første uløste TODO, og presenterer en plan — uten å starte koding.

### `/status`
Lettvekts alternativ til `/start`. Gir en rask oversikt over branch, ucommittede endringer, todo-status og åpne bugs — uten full kontekstlasting. Endrer ingenting, starter ingenting.

### `/todo-plan`
Planlegger neste TODO i PlanMode — ingen filer endres. Leser `todo.md`, `lessons.md` og `bugs.md`, analyserer oppgaven grundig (filer som berøres, avhengigheter, risiko, verifiseringskriterier), og presenterer planen for bekreftelse. Etter godkjenning opprettes planfilen `tasks/plans/todo-<nr>-<slug>.md`, committes umiddelbart, og status settes til `plan klar — venter på review`.

### `/todo-plan-review`
Devil's advocate-gjennomgang av en ferdig plan. Ingen filer endres før brukeren godkjenner. Sjekker hva som er oversett, hvilke risikoer ikke er adressert, om avhengighetene faktisk er oppfylt, og om testkriteriene er gode nok. Trekker eksplisitt på `lessons.md` og `bugs.md`. Etter godkjenning oppdateres planfil og `todo.md` med status `reviewet — klar for /todo-execute`.

### `/todo-execute`
Utfører en reviewet TODO steg for steg basert på planfilen. Sjekker ucommittede endringer og avhengigheter før start. Markerer hvert steg i planfilen som fullført etter hvert som det er verifisert. Gir bruker en statusmelding etter hvert steg. Markerer ikke hele TODO-en som ferdig — det gjøres av `/todo-done`.

### `/todo-done`
Avslutter en fullført TODO i 13 definerte steg: rydder kjørende prosesser, verifiserer testkriterier med faktisk output, rydder koden, kjører code review, markerer TODO som ferdig, arkiverer TODO og planfil, lukker relevante bugs, oppdaterer `lessons.md`, committer og pusher — og gir bruker en komplett sluttrapport. Venter på eksplisitt bekreftelse før neste TODO påbegynnes.

### `/endsession`
Brukes alltid ved sesjonslutt. Rydder kjørende prosesser (`playwright`, `expo`, `next dev`), committer uferdig arbeid, oppdaterer todo-status (`[x]` for ferdig, `[~]` for påbegynt), og skriver et sesjonsnotat til `tasks/sessions/` med branch, hvor man er, viktig kontekst og fallgruver. Starter ikke på nytt arbeid.

---

## Arbeidsflyt

```
sesjonstart
    │
    ▼
 /start
 Les CLAUDE.md + lessons.md + bugs.md + todo.md
 Git-orientering — sjekk avbrutte sesjoner
 Presenter plan for første uløste TODO
 Vent på bekreftelse
    │
    ▼
 /todo-plan                        (PlanMode — ingen filer endres)
 Les todo.md + lessons.md + bugs.md
 Analyser oppgaven grundig
 Presenter plan — vent på bekreftelse
 Opprett planfil → commit → oppdater status
    │
    ▼
 /todo-plan-review                 (devil's advocate — ingen filer endres)
 Les planfil + lessons.md + bugs.md
 Pek på svakheter og mangler
 Etter godkjenning: oppdater planfil og todo.md
    │
    ▼
 /todo-execute
 Sjekk avhengigheter og git-status
 Implementer steg for steg
 Marker hvert steg [x] etter verifisering
    │
    ▼
 /todo-done
 Rydd prosesser → verifiser → code review
 Arkiver TODO og planfil → lukk bugs
 Oppdater lessons.md → commit → push
 Vent på bekreftelse
    │
    ▼
 /endsession                       (ved sesjonslutt)
 Rydd prosesser → commit uferdig arbeid
 Oppdater todo-status
 Skriv sesjonsnotat til tasks/sessions/
```

---

## TODO-format

Hver TODO i `tasks/todo.md` følger dette formatet:

```md
### TODO [nr] — [tittel]
**Status:** ikke påbegynt
- [ ] Gjennomført
**Hva:** Konkret beskrivelse av oppgaven
**Hvorfor:** Kort kontekst
**Test:** Eksakte kriterier som må være oppfylt før todoen kan markeres ferdig
```

Statusverdier i rekkefølge:

```
ikke påbegynt → plan klar — venter på review → reviewet — klar for /todo-execute → under arbeid → ferdig
```

Fullførte TODOs flyttes til `tasks/todo_archive.md`. Planfiler flyttes til `tasks/plans/archive/`. Den aktive listen holdes kort.

---

## Mappestruktur

```
tasks/
├── todo.md               # Aktive TODOs
├── todo_archive.md       # Fullførte TODOs
├── bugs.md               # Åpne bugs
├── bugs_archive.md       # Lukkede bugs
├── lessons.md            # Lessons learned
├── plans/
│   ├── todo-01-slug.md   # Planfil per TODO
│   └── archive/          # Arkiverte planfiler
└── sessions/
    └── todo-01-slug.md   # Sesjonsnotat ved avbrudd
```

---

## Installasjon

Kopier kommandofilene til `.claude/commands/` i prosjektroten din:

```bash
git clone https://github.com/[bruker]/claude-skills.git
cp claude-skills/*.md ditt-prosjekt/.claude/commands/
```

Kommandoene er tilgjengelige i Claude Code med `/` etterfulgt av filnavnet uten `.md`.

---

## Forutsetninger

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installert
- En `CLAUDE.md` i prosjektroten med prosjektspesifikke regler
- Mappen `tasks/` med `todo.md`, `bugs.md` og `lessons.md`

Se [Anthropic sin dokumentasjon](https://docs.anthropic.com/en/docs/claude-code) for mer om slash-kommandoer og `CLAUDE.md`-formatet.
