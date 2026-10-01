<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# Koordinator-runbook — hvorfor (begrunnelser og målinger flyttet ut av kjernen og stegfilene)

→ Regler: `coordinator-runbook.md` (kjerne) og `steps/`; denne fila er kun begrunnelser og målinger (TODO 408).

## Bevis-regel (global, jf. `report-schema.md`)

→ Regel: «Konkret grense, som er etterprøvbar»

**Målt håndhevelse (2026-09-10).** Regelen over har eksistert hele tiden og er likevel brutt: median
dispatch-promptlengde gikk fra 1 676 tegn (uke 28) til 3 294 (uke 37), og over 72 dispatcher i uke
36–37 ga korteste tredjedel 54k subagent-tokens mot lengste tredjedels 176k — 3,2×.

## 0. Synk


## 0b. Rydd en worker-worktree (gjenbrukbar prosedyre)


## 1. Kø-utvelgelse (med ekte deps-gating)

**Hvorfor releasen styrer utvalget:** uten et mål plukker loopen øverste todo i hele køen, og en
release blir det som tilfeldigvis var ferdig da noen kjørte prod-releasen. Opphavsprosjektet
filtrerte på release-scope for hånd («filtrer på release-scope først, sorter på `order` innenfor
scopet»), og glippene kom når filteret ble glemt. Nå gjør skriptet det.

**Hvorfor stopp og ikke grooming når scopet er tomt:** et tomt scope betyr at releasen er ferdig
eller at noe mangler i den. Begge deler er menneskets beslutning. Å hente arbeid utenfor scope ville
skjult at målet er nådd.

**Hvorfor exit 2 på en ukjent `release:`-verdi:** `release: 1.4` i stedet for `1.4.0` ville tatt
todoen stille ut av scope, og releasen ville meldt `MÅL NÅDD` uten den.


## 2. Claim + pre-løs lessons-tema


## 2b. Fast-path (hopp §3/§4 → rett til §5)


## 3. Dispatch planner


## 4. Dispatch reviewer + gate


## 5. Dispatch implementer


## 5b. Uavhengig kode-review

→ Regel: «F3a: **gulvet** — antall»

**Overskrifts-formen (rettet 2026-09-10).** Regexen matchet opprinnelig KUN fet form (`**V1**`,
`| **V1**`) og var blind for `### V1 — …`, som er en helt ordinær markdown-form. TODO 236s plan
bruker den formen: F3a ga **0** for 13 reelle kriterier, og runbookens egen tolkning av 0 er
`vblock=legacy` — «skrevet før formatkravet, gulvet ikke bindende». Gate F ville altså slått av sitt
eget gulv i stille, på en plan skrevet samme dag. Alternasjonen over dekker begge former, og
`sed`-en normaliserer til bar V-ID så `sort -u` ikke teller `### V4` og `**V4**` som to. **Målt
bakoverkompatibel:** TODO 296 `26 → 26`, TODO 289 `7 → 7`, TODO 267 `17 → 17`, TODO 236 `0 → 13`.
Dette er samme defektklasse som `tasks/todos/todo-281-gate-f-teller-literaler-ikke-klasser.md`
beskriver: en detektor som leter etter én skrivemåte i stedet for én klasse.


## 5c. Pipelining (plan neste todo mens denne implementeres)


## 5d. Parallelle implementere (fil-disjunkt-gate — TODO 233)


## 6. Skriv delt state (seriell, re-kjørbar) + merge (kun koordinator)


## 6b. Drain bug-innboks (hver syklus, kun koordinator)


## 6c. Helsesjekk + release-rådgiver (betinget, kun koordinator)


## 6d. Worktree-sweep (hver syklus, kun koordinator)

→ Regel: «**Sweepen er ikke en svakere §0b»

**Hvorfor denne finnes ved siden av §0b.** §0b er en per-runde sikkerhetsgate med seks vakter, og
den feiler med rette LUKKET: ved enhver advarsel er utfallet «INGEN rydding». Konsekvensen er at
hver agent som dør, avbrytes, eller etterlater en foreldreløs lås, legger igjen et tre som INGEN
senere plukker opp. Det er ikke en defekt i §0b — det er et manglende oppsamlingssteg bak den.
Målt 2026-09-09: 30 trær, 4,1 GB, det eldste flere uker gammelt, og disken gikk full som følge.
Målt igjen 2026-09-21 (TODO 380): sweepen hadde ALDRI kjørt (`grep -c wtsweep run-log.md` = 0) —
72 trær, 19,4 GB, og `--dry-run` viste at den ville slettet treet som bar HEAD-branchen til en
åpen PR.


## 7. Grooming-modus (kø tom)


## 8. Mini-retro (kø-tom/stopp)


## 8b. Drain retro-logg (ved §6c-helsesjekk — begge triggere — kun koordinator)


## 8c. Agér på tallene (ved §6c-helsesjekk — begge triggere — kun koordinator)

→ Regel: «Kjøres rett etter §8b, ved begge §6c-triggere»

**Hvorfor dette steget finnes.** Vi måler mye — `measure-cost.py`, `run-log.md`,
`decision-log.md`, `retro-triage.md`, lessons-filene — og fram til 2026-09-17 var det ingen
prosedyre som PLIKTET noen å gjøre noe med det som ble målt. Resultatet var målbart: 29 av 33
BLOKKERENDE review-funn den uka tilhørte én og samme feilklasse — «en vakt som ikke kan bli rød
av riktig grunn» — og hver enkelt ble funnet på nytt, av en fersk reviewer, til full pris.
Mønsteret lå i tallene fra dag to. Eieren måtte peke på det. Det er den feilen dette steget
lukker: *tall og statistikk er ikke verdt noe om ingen agerer på dem.*


## Pausepunkter (nivå A — spør + eskalér; nivå B — bestem selv, logg, mennesket kan vetoe, TODO 246)

