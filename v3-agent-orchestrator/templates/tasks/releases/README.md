# tasks/releases/ — Én fil per release

En release samler todoer rundt ett mål. Når én release er `active`, henter loopen bare todoer fra
den og stopper når målet er nådd. Uten en aktiv release jobber loopen på hele køen, som før.

Fila heter `<versjon>.md`, for eksempel `1.4.0.md`. Filnavnet er versjonen. Todoene peker på den
med `release: "1.4.0"`.

## Mal

```markdown
---
status: planned            # planned | active | shipped. Bare én kan være active.
goal: "Brukere kan invitere et teammedlem og jobbe i samme prosjekt"
cutoff: "2026-10-15"       # scope fryses denne datoen. Etterpå slipper bare release_blocker inn.
---

## done_when

Releasens definition of done. Hver linje skal kunne måles av noen som ikke var med.

- [ ] En invitert bruker kan åpne og redigere prosjektet (e2e-spec grønn på base-branchen)
- [ ] Ingen åpne bugs med høy prioritet i epicen `invitasjon`
- [ ] Release notes er skrevet

## Epics

- `invitasjon` — invitere en annen bruker til et prosjekt
- `tilganger` — lese- og skrivetilgang per medlem

## Retro

Fylles ut når releasen er levert.
```

## Feltene

- **`goal`** er én setning om hva brukeren får. Planneren får den i hver dispatch (§3), så planene
  holder seg til målet.
- **`## done_when`** er releasens definition of done, som en sjekkliste. Den er forskjellig fra
  definition of done per todo, som V-blokken, CI og kode-reviewen allerede håndhever.
  `release.py status` teller avkryssede bokser i denne seksjonen. Bokser i andre seksjoner teller
  ikke.
- **`cutoff`** er datoen scopet fryses. En todo som kommer inn i scope etter den, uten
  `release_blocker: true`, gir en ADVARSEL i `release.py status`. Datoen todoen kom inn måles som
  datoen fila først ble committet.
- **`shipped`** (valgfri) er datoen releasen gikk i prod, `"ÅÅÅÅ-MM-DD"`. Køsiden
  (`tasks/queue-status.py --html`) viser den i levert-banen sammen med `goal`. `release.py` leser den ikke.
- **`## Epics`** gir hver epic et mål på én linje. Todoene peker på epicen med `epic: <slug>`, og
  `release.py status` viser fremdrift per epic.

## Livsløp

1. **`planned`:** mennesket skriver fila og setter `release:` (og eventuelt `epic:`) på todoene.
2. **`active`:** mennesket setter `status: active` og oppretter prod-release-todoen. Det er en
   vanlig todo med `release: "<versjon>"` og `tags: [prod-release]`. Den eies av mennesket. Loopen
   claimer den aldri og teller den ikke som åpen.
3. **Loopen jobber:** §1 velger bare todoer i scope. Når scopet er tomt, stopper loopen med en av
   to dommer:
   - `MÅL NÅDD`: alle bokser i `done_when` er krysset av. Neste steg er prod-release-todoen.
   - `MÅL IKKE NÅDD`: scopet er tomt, men noen bokser mangler. Mennesket legger til todoer eller
     endrer `done_when`.
4. **`shipped`:** når releasen er i prod:
   - `python3 tasks/release.py notes <versjon>` gir release notes fra arkivet.
   - `python3 tasks/measure-cost.py <since> --release <versjon>` gir kostnaden for releasen.
   - Skriv `## Retro` i release-fila: ble målet nådd, hvor mange todoer kom inn etter cut-off, hva
     kostet releasen, og hva gjør vi annerledes neste gang.
   - Sett `status: shipped` og `shipped: "<dato>"`.

## Hvem skriver hva

| Felt | Eier |
|---|---|
| Ny release-fil, `status`, `goal`, `cutoff`, `## Epics` | Mennesket |
| `release:` / `epic:` på en u-claimet todo | Mennesket |
| Avkrysning i `## done_when` | Koordinatoren, med bevis på samme linje (`— bevis: PR #N` eller kommando og utdata). Mennesket kan krysse av selv. |
| `## Retro` | Koordinatoren skriver et utkast når releasen er levert. Mennesket godkjenner. |

## Scope-vakten

Et funn underveis (en carry-forward fra kode-reviewen, en bug fra innboksen, et grooming-forslag)
får **ikke** `release:` automatisk. Det havner i backloggen eller i neste release. Unntaket er et
funn som blokkerer en `done_when`-linje. Da får todoen `release: "<aktiv versjon>"`,
`release_blocker: true` og én linje i brødteksten om hvilken linje den blokkerer.

## Verktøy

```bash
python3 tasks/release.py status            # fremdrift og DOM for den aktive releasen
python3 tasks/release.py scope <versjon>   # todo-nr i scope
python3 tasks/release.py notes <versjon>   # release notes fra arkivet
python3 tasks/release.py --self-test
```
