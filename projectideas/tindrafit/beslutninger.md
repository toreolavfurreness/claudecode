# Beslutninger (avklart)

Disse erstatter de åpne spørsmålene i `apne-sporsmal.md`. Avklart 2026-06-20.

| # | Tema | Beslutning |
|---|------|-----------|
| 1 | **Belastningsmetrikk** | **TRIMP** som felles base for CTL/ATL/TSB (puls finnes på tvers av alle sporter). **TSS** legges på toppen kun for sykkeløkter med watt. Krever maxHR + hvilepuls. |
| 2 | **Styrkebelastning** | Foreløpig: estimer fra varighet + HR (TRIMP), siden bare økt-tid logges på klokka. **Plan: koble Hevy via Chirona** → oppgrader til ekte totalvolum (sett×reps×vekt) i `strength_sessions`. Ren påbygging. |
| 3 | **Dobbelttelling** | Match på `start_tid` + varighet. Sannhet pr sport: **Strava** for utholdenhet, **Garmin/Hevy** for styrke. |
| 4 | **Historikk-dybde** | Backfill alt tilgjengelig. Garmin i 3-mnd-bolker, Strava paginert. |
| 5 | **Sesongmål** | **Generell form** — balansert base-bygging uten konkurransedato. Plan fokuserer på jevn progresjon + restitusjon, ikke formtopping. |
| 6 | **Frontend-graf** | **Recharts** (godt nok for trendgrafer). |
| 7 | **Personvern** | Kun aggregat (ikke rå GPS) sendes til Claude API. Funksjonen kan skrus av. |
| 8 | **Assistent-modell** | Nyeste passende Claude-modell, med ukentlig budsjett-tak. Endelig modell/tak settes ved Fase 4. |
| 9 | **Cron-plattform** | **Vercel Cron** (appen bor uansett på Vercel). |
| 10 | **Flerbruker** | Kun eier i V1, men **RLS på `athlete_id`** fra start. |

## Konsekvenser for datamodellen
- `athletes` MÅ ha `max_hr` og `hvilepuls_baseline` — TRIMP avhenger av dem.
- `activities.trimp` er primær load-kilde; `activities.tss` fylles kun for watt-økter.
- `strength_sessions`: `beregnet_belastning` = TRIMP-estimat nå, byttes til
  volum-basert når Hevy er koblet på.

## Ny datakilde å planlegge for: Hevy
- Tilgang vurderes via **Chirona** (samme MCP-lag som Garmin).
- Gir sett/reps/vekt → ekte styrkevolum.
- Til da er styrke en grov TRIMP-basert estimering.
