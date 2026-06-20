# Datakilder

## Viktig oppdagelse
Garmin nås **ikke** direkte. Den går via **Chirona** (et Terra-basert lag som
dekker Garmin, og evt. COROS / Oura / TrainingPeaks). Strava er en egen,
direkte MCP. Dette gir en naturlig rollefordeling.

## Rollefordeling (én sannhet per datatype)
Samme økt finnes ofte i både Strava og Garmin. For å unngå dobbelttelling
velger vi én kilde som autoritativ per datatype:

| Datatype | Autoritativ kilde | Merknad |
|----------|-------------------|---------|
| Utholdenhetsøkter (distanse, HR, watt, kadens, soner) | **Strava** | Rikest på detaljer + tidsserier |
| Tidsserier / streams (HR, watt, høyde, GPS) | **Strava** | `get_activity_streams` |
| Soner, FTP, maxHR, pace-soner | **Strava** | `get_athlete_zones` |
| Styrkeøkter | **Garmin/Chirona** | Strava er tynn på styrke |
| Søvn, HRV, hvilepuls, recovery, body battery | **Garmin/Chirona** | Finnes ikke i Strava |
| Vekt / body-data | **Garmin/Chirona** | |
| Push av planlagte økter til klokke | **Garmin/Chirona** | Lukker coaching-loopen |

## Strava — relevante endepunkter
- `list_activities` — distanse, tid, høydemeter, snitt/maxHR, watt, kadens,
  kalorier, relative effort, gear. Dato-filtrering + paginering.
- `get_activity_performance` — HR/watt-snitt, perceived exertion, laps, PRs.
- `get_activity_streams` — tidsserier (HR, watt, høyde, kadens, GPS, …).
- `get_athlete_zones` — HR-/power-/pace-soner + FTP.
- `get_athlete_profile` — vekt, måleenhet, treningsfokus.
- `get_gear` — sko/sykler (utstyrsslitasje).

Enheter returneres i metrisk.

## Garmin via Chirona — relevante endepunkter
- `get-recent-activities` — alle sporter inkl. styrke. Maks 3 mnd per kall →
  iterer i 3-mnd-bolker for historikk.
- `get-latest-sleep` / søvn-data — varighet + score.
- `get-latest-body` — vekt/body-data.
- `get-period-summary` — sammendrag over en periode.
- `get-run-splits`, `get-activity-details` — detaljer.
- `get-planned-workouts` / `push-planned-workout` / `delete-planned-workout`
  — les og skriv planlagte økter på Garmin. Pace i min/km, HR i % av maxHR,
  intervaller via `repeat` + nøstede steg.

> MERK: Chirona krever `conversation-initialisation-critical-instructions`
> som første kall hver melding før øvrige Chirona-kall. Verdt å huske når
> innhenting bygges.

## Konsekvens for innhenting
- Idempotens på `(source, source_id)` slik at re-kjøring ikke duplikerer.
- Garmin-historikk hentes i 3-måneders bolker ved første backfill.
- Søvn/HRV hentes om morgenen *etter* at klokka har synket natten.
