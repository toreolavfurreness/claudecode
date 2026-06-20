# Dashboard — visninger, kort og grafer

Fire nivåer, samme komponenter, ulik tidsoppløsning: **år / måned / uke / dag**.
Mobil-først, men utnytter bredde på laptop. PWA for app-følelse uten app-store.

## Nøkkeltall-kort (gjenbrukes pr nivå)
- Treningsbelastning (sum TSS/TRIMP) for perioden + endring vs forrige
- Distanse og høydemeter (utholdenhet)
- Totalvolum kg / antall styrkeøkter (styrke)
- Snittpuls + hvilepuls-trend
- Søvnsnitt + HRV-status
- **Form (TSB)** — bygger du form eller graver du deg ned?
- Antall økter / aktive dager / restdager

## Grafer
### Kortsiktig (uke/dag)
- Daglig belastning siste 7/28 dager (stolper)
- Sonefordeling (er for mye trening i «gråsonen»?)
- Søvn + HRV mot belastning — tidlig varsel om overtrening

### Langsiktig (måned/år)
- **CTL / ATL / TSB-kurven** (fitness/fatigue/form) — den klassiske
  treningsbelastningskurven over tid
- Ukentlig/månedlig volum og distanse (trend)
- Hvilepuls + vekt over tid
- Personlige rekorder / beste innsatser

## Per nivå — hva er i fokus
| Nivå | Fokus |
|------|-------|
| **Dag** | Dagens økt(er), søvn/HRV i natt, dagens planlagte økt, rask feedback-logg |
| **Uke** | Belastning vs plan, sonefordeling, balanse utholdenhet/styrke, restdager |
| **Måned** | Volumtrend, form-utvikling, måloppnåelse, bra/dårlig-oppsummering |
| **År** | Sesongbuer, totaler, langsiktig form, milepæler/PR-er |

## Auto-oppdatering
- Data ferskes via cron (se `arkitektur.md`); UI viser «sist oppdatert»-tid.
- Optimistisk: hent ved sidelast + revalidering, evt. webhook fra Strava senere.

## Andre ting verdt å bygge inn
- **Subjektiv følelse synlig sammen med data** — gjør «bra/dårlig» ærlig.
- **Varsler/flagg:** brå fall i HRV, TSB for lav (overbelastning), monotoni
  (for lik trening for lenge).
- **Utstyrsslitasje** (sko/sykkel-km fra Strava gear) — enkel, nyttig.
- **Mål mot faktisk:** planlagt vs gjennomført pr uke.
