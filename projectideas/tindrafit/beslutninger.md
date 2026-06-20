# Beslutninger (avklart)

Disse erstatter de åpne spørsmålene i `apne-sporsmal.md`. Avklart 2026-06-20.

| # | Tema | Beslutning |
|---|------|-----------|
| 0 | **Primærkilde** | **Garmin/Chirona** er primærkilde for ALL treningsdata (og restitusjon). Garmin er kilden (Strava er speilet), og restitusjonsdata (HRV/søvn/puls) finnes kun her. **Strava = fullverdig fallback**, ikke bare berikelse: brukes (a) når Garmin/Chirona-data mangler, og (b) for evt. fremtidige brukere som kun har Strava (ingen Chirona). Krever at kildene abstraheres bak et felles provider-grensesnitt. |
| 1 | **Belastning — SEPARERT** | Utholdenhet og styrke holdes **adskilt** (ulike stimuli: kardiovaskulær vs mekanisk). **Ingen felles lastenhet.** Utholdenhet → TRIMP → egen CTL/ATL/TSB. Styrke → tonnasje/sett×RPE → egen trend. TSS i tillegg for sykkel med watt. |
| 2 | **På tvers uten felles enhet** | Belastning «på tvers» uttrykkes via det **modalitets-uavhengige restitusjonslaget** (HRV, hvilepuls, søvn, subjektiv følelse) + beskrivende balanse/volum (tid, antall økter, monotoni). IKKE via et sammenslått lasttall. |
| 3 | **Styrkebelastning** | Tonnasje (sett×reps×vekt) når **Hevy via Chirona** er koblet på. Inntil da: kun antall økter + varighet (IKKE HR-TRIMP — puls måler ikke mekanisk last). |
| 4 | **Dobbelttelling** | Match på `start_tid` + varighet. Garmin/Chirona er sannhet; Strava kun supplement der det fyller hull. |
| 5 | **Historikk-dybde** | Backfill alt tilgjengelig. Garmin/Chirona i 3-mnd-bolker. |
| 6 | **Sesongmål** | **Generell form** — balansert base-bygging uten konkurransedato. Fokus på jevn progresjon + restitusjon, ikke formtopping. |
| 7 | **Frontend-graf** | **Recharts**. |
| 8 | **Personvern** | Kun aggregat (ikke rå GPS) sendes til Claude API. Kan skrus av. |
| 9 | **Assistent-modell** | Nyeste passende Claude-modell, ukentlig budsjett-tak. Settes ved Fase 4. |
| 10 | **Cron-plattform** | **Vercel Cron**. |
| 11 | **Flerbruker** | Kun eier i V1, men **RLS på `athlete_id`** fra start. |

## MÅ verifiseres tidlig i byggesesjonen
Avgjør om Strava i det hele tatt trengs som supplement:
1. Eksponerer Chirona **detaljerte HR-tidsserier (streams)** per økt? (Trengs til
   stream-vektet TRIMP + sonefordeling-graf.)
2. Eksponerer Chirona **maxHR + hvilepuls / HR-soner**? (Trengs til TRIMP.)
3. Eksponerer Chirona Garmins egne **Training Load / Readiness / VO2max**?
   (Kan brukes som referanse mot vår egen TRIMP.)

Hvis 1 eller 2 mangler → hent akkurat det fra Strava som berikelse.

## Arkitektur-konsekvens: provider-grensesnitt
Siden Strava skal kunne stå alene (fallback / Strava-only-bruker), bygg
innhentingen bak ett felles grensesnitt (f.eks. `TrainingDataProvider` med
`getActivities`, `getDailyMetrics`, `getZones`, `pushWorkout`). Garmin/Chirona
og Strava er to implementasjoner. Resten av appen kjenner ikke kilden.
- Readiness-data (HRV/søvn) finnes kun hos Garmin/Chirona → en Strava-only-bruker
  får utholdenhet + form-kurve, men ikke readiness-laget. Degrader pent.

## Konsekvenser for datamodellen
- `athletes` MÅ ha `max_hr` og `hvilepuls_baseline` — TRIMP avhenger av dem.
- **`load_metrics` splittes**: utholdenhets-last (CTL/ATL/TSB fra TRIMP) er én
  ting; styrke-last er en separat serie. Ikke summer dem.
- **Readiness** blir et eget, modalitets-uavhengig lag fra `daily_metrics` +
  `feedback` — dette er «på tvers»-måleren.
- `strength_sessions.beregnet_belastning` = tonnasje når Hevy er på, ellers null.

## Datakilder å planlegge for
- **Garmin via Chirona** — primær: aktiviteter, søvn, HRV, hvilepuls, body data,
  styrke, push av planlagte økter.
- **Hevy via Chirona** — ekte styrkevolum (sett/reps/vekt) når koblet på.
- **Strava** — valgfri berikelse (streams/soner) ved behov.
