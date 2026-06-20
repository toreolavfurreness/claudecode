# Treningsassistent

## Ambisjonsnivåer
| Nivå | Hva | Kostnad/kompleksitet |
|------|-----|----------------------|
| **A) Innsikt** ← V1 | Ukentlig auto-oppsummering: hva var bra/dårlig | Lav |
| B) Rådgiver | A + konkrete forslag til neste ukes økter | Middels |
| C) Samtale-coach | Chat: «bør jeg ta langtur i morgen?» ut fra ferske data | Høy |

**Besluttet for V1: nivå A.** B og C bygges oppå når data flyter og modellen
er validert.

## Hva nivå A krever
1. **Claude API-nøkkel** (miljøvariabel, aldri i kode).
2. **Aggregert kontekst** til modellen: ukens activities, load_metrics
   (CTL/ATL/TSB), daily_metrics (søvn/HRV) og feedback — som kompakt JSON.
3. **System-prompt med treningsprinsipper** (progresjon, restitusjon,
   polarisert trening, varselgrenser). Uten dette gir modellen generiske råd.
4. **`insights`-tabell** som cache → vi kaller ikke AI på nytt for samme uke.
5. **Cron-trigger** søndag kveld som genererer og lagrer oppsummeringen.

## Hva nivå B/C krever i tillegg
- **Verktøy-lag (tool use)** så modellen kan slå opp egne data on-demand
  (hent uke X, hent søvn siste 14 dager) i stedet for å få alt forhåndspakket.
- **Skriving til `plan_items`** + valgfri **push til Garmin** via Chirona
  `push-planned-workout` (pace i min/km, HR i % av maxHR, intervaller som
  `repeat` med nøstede steg). Dette lukker loopen: råd → økt på klokka.
- For chat (C): samtalehistorikk + ferske data ved hvert svar.

## Designprinsipp
Assistenten skal **begrunne** råd i brukerens faktiske tall («HRV ned 12% og
TSB på -25 → legg inn en ekstra restdag»), ikke gi generiske fraser. Subjektiv
feedback vektes sammen med data.

## Personvern
Helsedata sendes til ekstern modell ved oppsummering. Gjør dette eksplisitt for
brukeren, send kun nødvendig aggregat (ikke rå GPS), og la det kunne skrus av.
