# Faseplan

> TODO for når prosjektet settes opp i **eget repo**. Ikke noe av dette
> implementeres i `claudecode`-repoet. `[ ]` = ikke startet.

## Fase 0 — Oppsett av eget repo
- [ ] Opprett GitHub-repo for TindraFit
- [ ] Kopier denne mappa inn som `docs/` / planunderlag
- [ ] Skriv `CLAUDE.md`, `docs/naming-conventions.md`, `tasks/todo.md`
- [ ] Opprett Supabase-prosjekt + Vercel-prosjekt, koble til repo
- [ ] Legg tokens (Strava, Chirona, Claude API) som secrets

## Fase 1 — Fundament
- [ ] Supabase-skjema fra `datamodell.md` (migrasjon)
- [ ] Row Level Security pr `athlete_id`
- [ ] Next.js-skall på Vercel, Supabase Auth, PWA-manifest
- [ ] Ett dag/uke-view som leser ekte rader

## Fase 2 — Innhenting
- [ ] Cron: hent activities (Strava + Garmin), idempotent på source_id
- [ ] Cron: hent daily_metrics (søvn/HRV/hvilepuls/vekt)
- [ ] Engangs backfill (Garmin i 3-mnd-bolker, Strava paginert)
- [ ] `sync_state` for inkrementell henting

## Fase 3 — Analyse
- [ ] Beregn TRIMP/TSS pr økt ved innhenting
- [ ] Beregn daglig load + CTL/ATL/TSB → `load_metrics`
- [ ] Bygg år/måned/uke/dag-visning: kort + trendgrafer
- [ ] Varselgrenser (HRV-fall, lav TSB, monotoni)

## Fase 4 — Assistent (innsikt, nivå A)
- [ ] `insights`-tabell + cache
- [ ] System-prompt med treningsprinsipper
- [ ] Cron søndag kveld: generer ukesoppsummering via Claude API
- [ ] Vis oppsummering i dashbordet

## Fase 5 — Loop og adaptiv plan (senere)
- [ ] Daglig feedback-logg i UI
- [ ] `plans`/`plan_items`, planlagt vs gjennomført
- [ ] Push av planlagte økter til Garmin via Chirona
- [ ] Plan-justering pr sesong/måned/uke/dag basert på data + feedback
- [ ] Vurder assistent-nivå B (rådgiver) / C (chat)

## Suksesskriterier
- Dashbordet viser ferske, korrekte tall på alle fire nivåer uten manuell henting.
- Form-kurven (CTL/ATL/TSB) stemmer med kjente referanseverktøy.
- Ukesoppsummeringen begrunner «bra/dårlig» i faktiske tall.
- Fungerer like godt på mobil som laptop.
