# Datamodell

Postgres (Supabase). Tabellnavn i flertall, snake_case. Alle tider i UTC,
visning lokaliseres i frontend.

## Oversikt
```
athletes            – profil, soner, FTP, maxHR (sjelden endring)
activities          – én rad per utholdenhetsøkt (autoritativ: Strava)
strength_sessions   – styrkeøkter (autoritativ: Garmin/Chirona)
daily_metrics       – én rad per dag: søvn, HRV, hvilepuls, vekt
load_metrics        – én rad per dag: CTL / ATL / TSB (beregnes av oss)
feedback            – subjektiv daglig logg
plans / plan_items  – treningsplan, justerbar pr nivå, kan synces til Garmin
insights            – cache av assistentens AI-oppsummeringer
sync_state          – sist synkede cursor/tid per kilde (idempotent innhenting)
```

## Tabeller (skisse)

### athletes
`id, navn, kjønn, fødselsdato, vekt_kg, max_hr, hvilepuls_baseline,
ftp_watt, hr_soner (jsonb), pace_soner (jsonb), maleenhet, opprettet`

### activities
`id, athlete_id, source ('strava'|'garmin'), source_id, sport,
start_tid (utc), start_tid_lokal, varighet_s, distanse_m, hoydemeter_m,
snitt_hr, max_hr, snitt_watt, normalized_power, snitt_kadens, kalorier,
relative_effort, trimp, tss, polyline (nullable), rådata (jsonb), opprettet`
- **UNIQUE (source, source_id)** → idempotent innhenting.
- `trimp`/`tss` beregnes ved innhenting fra HR/watt + soner.

### strength_sessions
`id, athlete_id, source, source_id, start_tid, varighet_s, øvelser (jsonb:
[{navn, sett:[{reps, vekt_kg}]}]), totalvolum_kg, beregnet_belastning,
opprettet`
- Egen tabell fordi sett/reps/vekt passer dårlig i utholdenhets-skjemaet.
- `beregnet_belastning` rulles opp til `load_metrics` så hybrid ses samlet.

### daily_metrics
`athlete_id, dato (PK sammen med athlete_id), sovn_timer, sovn_score,
hrv_ms, hvilepuls, body_battery, vekt_kg, kilde, opprettet`

### load_metrics  *(beregnes, hentes ikke)*
`athlete_id, dato (PK m/ athlete_id), daglig_load, ctl, atl, tsb, kilde='calc'`
- CTL = 42-dagers eksponentielt snitt av daglig load (fitness).
- ATL = 7-dagers eksponentielt snitt (fatigue).
- TSB = CTL − ATL (form/formtopp).
- Daglig load = sum av `tss/trimp` (activities) + `beregnet_belastning`
  (strength_sessions) for dagen.

### feedback
`id, athlete_id, dato, opplevd_anstrengelse (1-10), energi (1-5),
sovnkvalitet (1-5), humor (1-5), notat, opprettet`
- Driver adaptiv coaching. Kort 10-sekunders daglig logg i UI.

### plans / plan_items
`plans: id, athlete_id, navn, sesong_mal, periode_start, periode_slutt`
`plan_items: id, plan_id, dato, sport, type (rolig|intervall|langtur|styrke|hvile),
mal (jsonb: pace/HR/watt/distanse/varighet), beskrivelse, status
(planlagt|gjennomført|hoppet_over), garmin_planned_workout_id (nullable)`
- `garmin_planned_workout_id` settes når økten er pushet til klokka.
- Justerbar pr sesong/måned/uke/dag → planen redigeres på item-nivå.

### insights
`id, athlete_id, nivå ('uke'|'måned'|'år'), periode_start, periode_slutt,
sammendrag (text), funn (jsonb), modell, generert (utc)`
- Cache slik at vi ikke kaller AI på nytt for samme periode.

### sync_state
`kilde, datatype, sist_cursor, sist_synket (utc)`
- Lar innhenting starte der forrige kjøring slapp.

## Bevisste designvalg (flagget)
1. **Styrke i egen tabell, ikke i `activities`.** Felles belastning rulles opp
   til `load_metrics` for samlet hybrid-bilde.
2. **`load_metrics` beregnes lokalt.** CTL/ATL/TSB finnes ikke i API-ene — det
   er hele poenget med egen DB.
3. **`rådata jsonb` på activities.** Beholder kildefelt vi ikke modellerer ennå,
   så vi slipper re-henting når modellen utvides.
4. **Idempotens via UNIQUE(source, source_id).** Cron kan kjøre trygt om igjen.

## Avhengigheter mot CLAUDE.md-regler
- `docs/naming-conventions.md` i mål-repoet er obligatorisk lesning før
  tabeller/kolonner låses. Navnene over er forslag, ikke fasit.
