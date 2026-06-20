# TindraFit — prosjektoppsett

> **TindraFit** — auto-oppdatert treningsdashboard. Domene: `tindrafit.com`.
> Strukturert planmappe. **Ingenting implementeres i dette repoet.**
> Innholdet her løftes senere inn i et eget repo med egen infrastruktur.

## Hva
TindraFit er et auto-oppdatert treningsdashboard som henter data fra Strava og Garmin,
lagrer historikk i egen database, og presenterer trening på fire nivåer —
**år / måned / uke / dag** — med nøkkeltall-kort og trendgrafer, samt en
treningsassistent som gir innsikt og en justerbar treningsplan.

## Hvem
Én primærbruker (eier). Bygges flerbruker-ryddig fra start, men optimaliseres
ikke for det i V1.

## Hvorfor
Strava og Garmin viser hver sin bit. Ingen av dem regner ut egen
form-/fatigue-kurve over tid, kombinerer utholdenhet + styrke til samlet
belastning, eller kobler subjektiv følelse mot data for adaptiv coaching.
Verdien ligger i å samle rådata i egen DB → beregne egne metrics → vise trender
→ gi råd.

## Omfang V1 (besluttet)
- **Treningsformer:** utholdenhet (løp/sykkel/ski) **+** styrke/gym (hybrid).
- **Assistent:** nivå «Innsikt» — ukentlig auto-oppsummering av hva som var
  bra/dårlig. Rådgiver/chat kommer senere.
- **Tilnærming:** konsept + datamodell først (denne mappa), så eget repo.

## Dokumenter i denne mappa
| Fil | Innhold |
|-----|---------|
| `datakilder.md` | Hva Strava og Garmin/Chirona faktisk gir oss + rollefordeling |
| `datamodell.md` | Tabeller, felter og bevisste designvalg |
| `arkitektur.md` | Lag, hosting, innhentingsrutiner, sikkerhet |
| `dashboard.md` | Visninger, kort og grafer per nivå |
| `assistent.md` | Treningsassistenten — ambisjonsnivåer og hva som kreves |
| `faseplan.md` | Faseinndelt TODO for når prosjektet settes opp i eget repo |
| `beslutninger.md` | **Avklarte valg** (belastningsmetrikk, styrke/Hevy, sesongmål m.m.) |
| `apne-sporsmal.md` | Historikk over vurderte spørsmål (nå avklart) |

## Status
Planfase. Neste konkrete steg er beskrevet i `faseplan.md`.
