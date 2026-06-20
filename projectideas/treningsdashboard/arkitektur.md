# Arkitektur

## Lag
| Lag | Valg | Rolle |
|-----|------|-------|
| Datakilder | Strava MCP + Garmin via Chirona | Aktiviteter, HR, søvn, HRV, vekt |
| Lagring | Supabase (Postgres) | Rådata + beregnede aggregater |
| Innhenting | Vercel Cron (evt. Supabase scheduled functions) | Friske data på rutine |
| Beregning | Edge/serverless jobb | TRIMP/TSS + CTL/ATL/TSB |
| Frontend | Next.js på Vercel, PWA | Responsivt mobil + laptop |
| Auth | Supabase Auth | Én bruker nå, ryddig for flere |
| Assistent | Claude API (`claude-opus-4-8` / passende modell) | Ukentlig innsikt |

## Dataflyt
```
Strava / Garmin(Chirona)
        │  (cron: henter rådata, idempotent på source_id)
        ▼
   activities / strength_sessions / daily_metrics   (Supabase)
        │  (beregningsjobb)
        ▼
   load_metrics (CTL/ATL/TSB)
        │
        ▼
   Next.js dashboard  ──reads──▶  kort + grafer (år/måned/uke/dag)
        │
        ▼
   Claude API  ──▶  insights (ukentlig oppsummering)
        │
        ▼
   plan_items  ──push──▶  Garmin-klokke (valgfritt, senere fase)
```

## Innhentingsrutiner (cron)
| Jobb | Frekvens | Gjør |
|------|----------|------|
| Aktiviteter | hver natt + hver time på treningsdager | hent nye økter (Strava + Garmin) |
| Daily metrics | hver morgen | søvn/HRV/hvilepuls/vekt fra Garmin |
| Beregning | etter hver innhenting | oppdater load_metrics |
| Ukesoppsummering | søndag kveld | regenerer form-kurve + AI-innsikt |
| Backfill | engangs ved oppstart | Garmin i 3-mnd-bolker, Strava paginert |

## Sikkerhet
- API-nøkler/tokens kun i miljøvariabler (Vercel/Supabase secrets), aldri i kode.
- Row Level Security i Supabase fra start (athlete_id-scoping).
- Aldri commit direkte til `main` i mål-repoet — branch + PR.

## Hosting / miljøer
- `main` → produksjon (Vercel). Forhåndsvisning pr PR.
- Ett Supabase-prosjekt for V1; vurder eget for dev hvis migrasjoner blir hyppige.

## Hvorfor egen DB i stedet for live-kall
- API-ene har rate limits og grunn historikk.
- Form-kurven (CTL/ATL/TSB) og hybrid-belastning må beregnes over tid.
- Dashbordet skal være raskt → leser fra egen DB, ikke fra tredjeparts-API.
