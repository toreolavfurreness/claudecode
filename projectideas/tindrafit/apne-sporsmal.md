# Åpne spørsmål / beslutninger som gjenstår

> **Alle ti er nå avklart — se `beslutninger.md`.** Denne fila beholdes som
> historikk over hva som ble vurdert.

Avklares før eller tidlig i oppsett av eget repo.

1. **Belastningsmetrikk:** TSS (krever FTP/power, best på sykkel) vs TRIMP
   (HR-basert, fungerer på alt). Forslag: **TRIMP som felles base**, TSS i
   tillegg der watt finnes. Bekreft.
2. **Styrkebelastning:** hvordan kvantifisere styrke inn i felles load?
   (totalvolum kg, sett × RPE, fast estimat per økt). Trenger en enkel modell.
3. **Dobbelttelling:** bekreft at samme økt ikke kommer inn fra både Strava og
   Garmin — match på start_tid + varighet, eller velg kilde pr sport.
4. **Historikk-dybde:** hvor langt tilbake skal backfill gå? (Garmin-historikk
   varierer per provider.)
5. **Sesongmål:** hvilke konkrete mål skal planen styres mot? (løp/ritt/dato)
   Påvirker plan-strukturen.
6. **Tech-valg frontend:** grafbibliotek (Recharts / visx / annet), UI-kit.
7. **Personvern:** bekreft at helsedata kan sendes til Claude API for
   oppsummering, og hva som skal kunne skrus av.
8. **Modellvalg for assistent:** hvilken Claude-modell + budsjett pr uke.
9. **Cron-plattform:** Vercel Cron vs Supabase scheduled functions — hvem eier
   innhentingen.
10. **Flerbruker:** kun deg i overskuelig framtid, eller skal det åpnes for
    flere (påvirker auth/RLS-ambisjon)?
