# Datamodell

Postgres (Supabase). Tabellnavn i flertall, snake_case. Alle tider i UTC,
visning lokaliseres i frontend.

## Oversikt
> **Primærkilde: Garmin/Chirona.** Strava er valgfri berikelse (se `datakilder.md`).
> **Utholdenhet og styrke holdes adskilt** — ingen felles lastenhet.

```
athletes            – profil, soner, FTP, maxHR (sjelden endring)
activities          – én rad per utholdenhetsøkt (primær: Garmin/Chirona)
strength_sessions   – styrkeøkter (primær: Garmin/Hevy via Chirona)
daily_metrics       – én rad per dag: søvn, HRV, hvilepuls, vekt (readiness-lag)
endurance_load      – én rad per dag: TRIMP-basert CTL / ATL / TSB (beregnes)
strength_load       – én rad per dag/uke: tonnasje-trend (beregnes, SEPARAT)
feedback            – subjektiv daglig logg (del av readiness-laget)
plans / plan_items  – treningsplan, justerbar pr nivå, kan synces til Garmin
insights            – cache av assistentens AI-oppsummeringer
sync_state          – sist synkede cursor/tid per kilde (idempotent innhenting)
```

**Tre lag, bevisst adskilt:**
1. **Utholdenhets-last** (`endurance_load`) — kardiovaskulær, TRIMP → CTL/ATL/TSB.
2. **Styrke-last** (`strength_load`) — mekanisk, tonnasje. Egen trend, IKKE summert.
3. **Readiness** (`daily_metrics` + `feedback`) — modalitets-uavhengig «på tvers»-
   måler (HRV, hvilepuls, søvn, følelse). Dette er den ærlige tverrsnitt-lasten.

## Tabeller (skisse)

### athletes
`id, navn, kjønn, fødselsdato, vekt_kg, max_hr, hvilepuls_baseline,
ftp_watt, hr_soner (jsonb), pace_soner (jsonb), maleenhet, opprettet`

### activities
`id, athlete_id, source ('garmin'|'strava'), source_id, sport,
start_tid (utc), start_tid_lokal, varighet_s, distanse_m, hoydemeter_m,
snitt_hr, max_hr, snitt_watt, normalized_power, snitt_kadens, kalorier,
relative_effort, trimp, tss, polyline (nullable), rådata (jsonb), opprettet`
- **UNIQUE (source, source_id)** → idempotent innhenting.
- `trimp`/`tss` beregnes ved innhenting fra HR/watt + soner.

### strength_sessions
`id, athlete_id, source, source_id, start_tid, varighet_s, øvelser (jsonb:
[{navn, sett:[{reps, vekt_kg}]}]), totalvolum_kg, opprettet`
- Egen tabell fordi sett/reps/vekt passer dårlig i utholdenhets-skjemaet.
- `totalvolum_kg` (sett×reps×vekt) fylles når Hevy via Chirona er koblet på;
  til da kun `varighet_s` + antall. **Rulles opp til `strength_load`, IKKE til
  utholdenhets-lasten** — ulike stimuli, ingen felles enhet.

### daily_metrics
`athlete_id, dato (PK sammen med athlete_id), sovn_timer, sovn_score,
hrv_ms, hvilepuls, body_battery, vekt_kg, kilde, opprettet`

### endurance_load  *(beregnes, hentes ikke)*
`athlete_id, dato (PK m/ athlete_id), daglig_trimp, ctl, atl, tsb, kilde='calc'`
- `daglig_trimp` = sum av `trimp` (activities) for dagen. **Kun utholdenhet.**
- CTL = 42-dagers eksponentielt snitt (fitness).
- ATL = 7-dagers eksponentielt snitt (fatigue).
- TSB = CTL − ATL (form/formtopp).

### strength_load  *(beregnes, SEPARAT fra utholdenhet)*
`athlete_id, periode (dato el. uke), tonnasje_kg, antall_okter, akutt, kronisk`
- Egen, enkel akkumulert-trend for mekanisk last.
- Bevisst IKKE slått sammen med `endurance_load` — det ville midle to
  uforenlige stimuli (jf. `beslutninger.md` #1–2).

### readiness  *(avledet av daily_metrics + feedback)*
- Ikke nødvendigvis egen tabell; kan beregnes on-the-fly eller caches.
- Modalitets-uavhengig «på tvers»-signal: HRV-trend, hvilepuls, søvn, følelse.
- Dette er måten vi sier noe om total belastning UTEN felles lastenhet.

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
1. **Utholdenhet og styrke er adskilt hele veien.** To stimuli (kardiovaskulær
   vs mekanisk) → to lastserier, ingen felles enhet. Forening skjer kun på
   readiness-laget (HRV/søvn/puls/følelse).
2. **`endurance_load`/`strength_load` beregnes lokalt.** CTL/ATL/TSB finnes ikke
   i API-ene — det er hele poenget med egen DB.
3. **Garmin/Chirona er primærkilde**, Strava valgfri berikelse. `source`-feltet
   tillater begge, men Garmin er default sannhet.
4. **`rådata jsonb` på activities.** Beholder kildefelt vi ikke modellerer ennå,
   så vi slipper re-henting når modellen utvides.
5. **Idempotens via UNIQUE(source, source_id).** Cron kan kjøre trygt om igjen.

## Avhengigheter mot CLAUDE.md-regler
- `docs/naming-conventions.md` i mål-repoet er obligatorisk lesning før
  tabeller/kolonner låses. Navnene over er forslag, ikke fasit.
