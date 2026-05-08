# Datamodell

> Skjelett. Erstatt `<PLACEHOLDER>`-merker med faktiske tabeller, kolonner og policies.
> Slett denne filen hvis prosjektet ikke har en database.

Database: `<f.eks. PostgreSQL via Supabase / SQLite>`. `<Beskriv kort hvordan tilgangskontroll håndheves — RLS, app-lag, e.l.>`

---

## Tilgangsmodell

`<Forklar hvordan brukere får tilgang til data:`
`- Brukere → tenants/familier/orgs (1-til-mange? mange-til-mange?)`
`- Hvilken tabell er autoritativ for tilgangskontroll?`
`- Hvordan håndheves det — RLS-policies, applikasjonslag, begge?>`

---

## Hjelpefunksjoner *(slett hvis ikke relevant)*

`<Hvis prosjektet bruker SQL-funksjoner for tilgangskontroll, list dem her:`

| Funksjon | Argument | Returnerer | Formål |
|----------|----------|------------|--------|
| `<navn>` | `<arg>` | `<type>` | `<hva den sjekker>` |

---

## Tabeller

### `<tabell_navn>`

`<En setning om hva tabellen representerer.>`

| Kolonne | Type | Notater |
|---------|------|---------|
| `id` | `<uuid / bigserial>` | PK |
| `<kolonne>` | `<type>` | `<constraints, default, FK>` |
| `created_at` | `timestamptz` | default `now()` |

**Indekser:**
- `idx_<tabell>_<kolonne>` — `<begrunnelse>`

**Tilgangsregler:**
- SELECT: `<beskrivelse>`
- INSERT: `<beskrivelse>`
- UPDATE: `<beskrivelse>`
- DELETE: `<beskrivelse>`

---

`<Repeter for hver tabell. Grupper relaterte tabeller med markdown-overskrifter>`
`<- ### Brukere og auth>`
`<- ### Domeneobjekter>`
`<- ### Logging og audit>`

---

## Relasjonsdiagram *(valgfritt)*

`<Sett inn et tekst-diagram, Mermaid-graf eller link til ekstern figur som viser hvordan tabellene henger sammen.>`

---

## Migrasjonshistorikk

`<Slett denne seksjonen hvis migrasjonsverktøyet ditt logger dette automatisk.
Ellers før kort liste over store skjema-endringer her med dato og PR/migrasjonsnummer.>`
