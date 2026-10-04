<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# 6c. Helsesjekk + release-rådgiver (betinget, kun koordinator)

→ Kjerne: `coordinator-runbook.md` § 6c · Begrunnelser: `runbook-hvorfor.md` § 6c

**Koordinatoren** kjører `/loop-health-check` (`.claude/commands/loop-health-check.md`) når én av
to deterministiske triggere slår inn. Workers dispatches aldri til denne oppgaven — single-writer-
kontrakten gjelder.

### Triggerlogikk

**Trigger 1 — Kø tom / grooming (§7):** Kjør §6c FØR grooming-forslag, slik at mennesket får
en samlet statusrapport samtidig. Helseraden som skrives nullstiller merge-telleren (Trigger 2).

**Trigger 2 — Hver N-te merge (N={{HEALTH_CHECK_INTERVAL}}):** Kjør kadens-gaten etter
hver merged-rad (§6 steg 5) og før neste dispatch:

```bash
python3 tasks/loop-cadence.py
```

Den teller `outcome=merged` etter den *nyeste* `outcome=health`-raden, sortert på tidsstempel
(run-loggen står ikke alltid i tidsrekkefølge, så «siste health-rad i fila» kan være en eldre rad).
Exit 1 (`FORFALT`) → kjør §6c nå, før neste dispatch. Ikke en huskeregel: målt i opphavsprosjektet
kom helsesjekkene etter 44, 13, 11, 9 og 7 merger med intervall 5. Helseraden som §6c skriver blir den nye
nullstillings-markøren. Ingen health-rad ennå → tell fra toppen av fila.

**Begge triggere skriver en health-rad** → telleren nullstilles alltid uansett hvilken som fyrer.

**Persistering:** health-raden appendes til `docs/superpowers/loop/run-log.md` (ingen dedup-guard
her, se «Re-kjørbarhet»-noten under §6 steg 6 for hvorfor det ikke trengs), deretter kjøres
**Delt-state-git-halen** (§6, steg 6 — samme blokk, `$MSG="chore(loop): helsesjekk — health-rad"`).
`loop-health-check.md` Del C appender kun raden selv — commit/push skjer via denne halen; ingen
edit i `loop-health-check.md` er nødvendig.

### Release-fremdrift

Med en aktiv release tar helsesjekken med utdataene fra `python3 tasks/release.py status` i
rapporten (Del B). ADVARSEL-linjene (manglende prod-release-todo, tom `done_when`, utsatte todoer
i scope, todoer inn etter cut-off) meldes til mennesket. De stopper ikke loopen. `FEIL` (exit 2)
er en rød helsesjekk.

### Etter §6c

- Grønn helsesjekk → kjør §8b (drain retro-logg), deretter §8c (agér på tallene — uten denne
  forover-pekeren lærer en koordinator som leser ovenfra og ned aldri at steget finnes),
  fortsett så normalt (til grooming eller neste todo).
- Rød helsesjekk (regresjon eller infra-feil) → ⚠️ PAUSEPUNKT: eskalér til mennesket med detaljer,
  sett `pause_event=helsesjekk-rød` i health-raden, release evt. aktiv claim og stopp loopen.
  §8b og §8c kjøres IKKE.

**TODO 246 — Del D:** `/loop-health-check` kjører i tillegg Del D (regelmotor-selvtest,
regel-paritet, monoton decision-log, nivå-B-oppsummering + avstemming mot run-loggen, treffsikkerhet per type (D5)) som en del av
DENNE helsesjekken, FØR «Etter §6c» over evalueres — se `loop-health-check.md` Del D. Rødt i Del D
er samme klasse som Del A/A6: rød helsesjekk, §8b kjøres IKKE.
