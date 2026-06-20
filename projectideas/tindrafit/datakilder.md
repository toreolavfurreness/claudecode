# Datakilder

## Viktig oppdagelse
Garmin nås **ikke** direkte. Den går via **Chirona** (et Terra-basert lag som
dekker Garmin, og evt. COROS / Oura / TrainingPeaks). Strava er en egen,
direkte MCP. Dette gir en naturlig rollefordeling.

## Rollefordeling (Garmin/Chirona er primærkilde)
**Garmin er kilden, Strava er speilet.** Treningsdata bor samme sted som
restitusjonsdata (HRV/søvn/puls), som kun finnes i Garmin/Chirona. Derfor er
Garmin/Chirona primær for alt. **Strava = fullverdig fallback** (ikke bare
berikelse): brukes når Garmin/Chirona-data mangler, og for evt. fremtidige
brukere som kun har Strava. Begge kilder ligger bak ett provider-grensesnitt
(se `beslutninger.md`), så appen er kilde-agnostisk.

| Datatype | Primærkilde | Merknad |
|----------|-------------|---------|
| Utholdenhetsøkter (distanse, HR, watt, kadens) | **Garmin/Chirona** | `get-recent-activities` / `get-activity-details` |
| Søvn, HRV, hvilepuls, recovery, body battery | **Garmin/Chirona** | Finnes ikke i Strava |
| Styrkeøkter | **Garmin/Chirona** (+ Hevy) | |
| Vekt / body-data | **Garmin/Chirona** | `get-latest-body` |
| Push av planlagte økter til klokke | **Garmin/Chirona** | Lukker coaching-loopen |
| Detaljerte HR-streams | **Garmin/Chirona** → ev. **Strava** | Berikelse hvis Chirona er tynn |
| Soner, FTP, maxHR, pace-soner | **Garmin/Chirona** → ev. **Strava** | `get_athlete_zones` som fallback |

### MÅ verifiseres tidlig (avgjør om Strava trengs)
1. Gir Chirona **HR-tidsserier (streams)** per økt? (Til stream-TRIMP + sonefordeling.)
2. Gir Chirona **maxHR + hvilepuls / soner**? (Til TRIMP.)
3. Gir Chirona Garmins egne **Training Load / Readiness / VO2max**? (Referanse.)

Mangler 1 eller 2 → hent akkurat det fra Strava som supplement.

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

## TRIMP beregnes — hentes ikke (kun utholdenhet)
Verken Strava eller Garmin/Chirona gir et ferdig TRIMP-tall. Vi beregner det
selv (Banister): `TRIMP = varighet_min × r × 0,64·e^(1,92·r)`, der
`r = (snittpuls − hvilepuls)/(maxpuls − hvilepuls)`.
- **Kun for utholdenhetsøkter.** Styrke får IKKE TRIMP (puls måler ikke
  mekanisk last) — styrke = tonnasje/antall i egen `strength_load`.
- Råstoff hentes fra **Garmin/Chirona** (primær). Snitt-HR til å starte;
  stream-vektet hvis Chirona gir streams, ellers Strava som fallback.
- `maxHR` + `hvilepuls` settes på `athletes` fra Garmin/Chirona (Strava
  `get_athlete_zones` som fallback hvis Chirona ikke eksponerer dem).
- Aldri TRIMP fra begge kilder for samme økt → unngå dobbelttelling.

## Konsekvens for innhenting
- Idempotens på `(source, source_id)` slik at re-kjøring ikke duplikerer.
- Garmin-historikk hentes i 3-måneders bolker ved første backfill.
- Søvn/HRV hentes om morgenen *etter* at klokka har synket natten.
