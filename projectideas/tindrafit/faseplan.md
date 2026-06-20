# Faseplan

> TODO for når prosjektet settes opp i **eget repo**. Ikke noe av dette
> implementeres i `claudecode`-repoet. `[ ]` = ikke startet.

## Fase 0 — Oppsett av eget repo
- [ ] Opprett GitHub-repo for TindraFit
- [ ] Kopier denne mappa inn som `docs/` / planunderlag
- [ ] Skriv `CLAUDE.md`, `docs/naming-conventions.md`, `tasks/todo.md`
- [ ] Opprett Supabase-prosjekt + Vercel-prosjekt, koble til repo
- [ ] Legg tokens (Strava, Chirona, Claude API) som secrets

## Fase 0.5 — Datakvalitets-audit (FØR vi bygger beregninger)
> Terra normaliserer data. Vi må vite hva vi faktisk får før vi stoler på det.
- [ ] Les gjennom et representativt utvalg ekte økter via Chirona
      (ulike sporter: løp/sykkel/ski/styrke, både korte og lange).
- [ ] Sjekk for hver økt: finnes **HR-streams** (per-sekund) eller kun snitt-HR?
- [ ] Sjekk om **maxHR + hvilepuls / soner** er tilgjengelig.
- [ ] Sjekk **søvn/HRV/hvilepuls/body battery** — dekning, hull, enheter, tidsstempler.
- [ ] Sjekk om Garmins egne **Training Load / Readiness / VO2max** kommer gjennom.
- [ ] Verifiser tidssoner, varighet (elapsed vs moving), distanse-enheter.
- [ ] Se etter dubletter / manglende økter vs hva du vet du har gjort.
- [ ] **Skriv en kort kvalitetsrapport**: hva er pålitelig, hva har hull,
      hva må evt. hentes fra Strava som berikelse. Oppdater `datakilder.md`
      og `beslutninger.md` (verifiseringspunktene) ut fra funnene.
- [ ] Logg overraskelser i `tasks/lessons/` (data-kvalitet).

## Fase 1 — Fundament
- [ ] Supabase-skjema fra `datamodell.md` (migrasjon)
- [ ] Row Level Security pr `athlete_id`
- [ ] Next.js-skall på Vercel, Supabase Auth, PWA-manifest
- [ ] Ett dag/uke-view som leser ekte rader

## Fase 2 — Innhenting
- [ ] Cron: hent activities fra **Garmin/Chirona** (primær), idempotent på source_id
- [ ] Cron: hent daily_metrics (søvn/HRV/hvilepuls/vekt)
- [ ] Engangs backfill (Garmin/Chirona i 3-mnd-bolker)
- [ ] Ev. Strava-berikelse kun for det audit-en (Fase 0.5) viste mangler
- [ ] `sync_state` for inkrementell henting

## Fase 3 — Analyse
- [ ] Beregn TRIMP pr utholdenhetsøkt (TSS i tillegg for watt-sykkel)
- [ ] Beregn `endurance_load` (CTL/ATL/TSB) — kun utholdenhet
- [ ] Beregn `strength_load` (tonnasje/antall) — SEPARAT serie
- [ ] Beregn readiness-signal fra daily_metrics + feedback
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
