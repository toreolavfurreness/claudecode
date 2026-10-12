<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# Koordinator-runbook — hvorfor (begrunnelser og målinger flyttet ut av kjernen og stegfilene)

→ Regler: `coordinator-runbook.md` (kjerne) og `steps/`; denne fila er kun begrunnelser og målinger.

## Bevis-regel (global, jf. `report-schema.md`)

→ Regel: «Konkret grense, som er etterprøvbar»

**Målt håndhevelse.** Regelen over har eksistert hele tiden og er likevel brutt: median
dispatch-promptlengde gikk fra 1 676 tegn (uke 28) til 3 294 (uke 37), og over 72 dispatcher i uke
36–37 ga korteste tredjedel 54k subagent-tokens mot lengste tredjedels 176k — 3,2×.

## 0. Synk


## 0c. Sjekkpunkt ved komprimering

→ Regel: «les sjekkpunktfila før hvert steg»

**Hvorfor lesingen er en regel og ikke en hook.** Ingen hook-hendelse kan legge tekst inn i
konteksten etter en komprimering (`preCompact` er bare et varsel, og `sessionStart` fyrer ikke for
en komprimering). Et sjekkpunkt som bare leses «når noe virker rart», leses ikke når det trengs mest:
etter en komprimering ser sammendraget komplett ut. Å lese fila før hvert steg koster noen hundre
linjer og gjør komprimeringen ufarlig uansett når den skjer.


## 0b. Rydd en worker-worktree (gjenbrukbar prosedyre)

→ Regel: «Worktree per dispatch»

**Hvorfor koordinatoren lager treet.** En `task`-subagent deler filsystem og arbeidskatalog med
den som dispatcher den. Uten et eget tre ville to workers — eller en worker og koordinatoren —
skrevet i samme sjekkout, og feil-cwd-klassen (planfil skrevet til hovedsjekkuten) ville vært
normaltilstanden, ikke en bug. Treet lages derfor av ett skript, ett sted, før hver dispatch, og
stien gis i prompten. Det gjør bevis-sjekken skarpere enn et mønster: `evidence.toplevel` skal være
lik en sti koordinatoren kjenner på forhånd.

**Hvorfor snapshotet tas før bootstrap-kallet.** Vakt 5 skal bevise at treet ble laget for nettopp
denne dispatchen. Et snapshot tatt etter bootstrap ville inneholde treet og avvist det som
`preexisting`.

**Hvorfor én sti per dispatch-forsøk, men samme tre for fix-rundene.** En forkastet worker
(canary-/bevis-mismatch) kan ha etterlatt halvskrevne filer; et nytt forsøk i samme tre ville arvet
dem og gjort bevisene tvetydige. Fix-rundene er motsatt: treet bærer PR-branchen, er rent etter
push, og en fersk worker der bygger på nøyaktig det som ble reviewet.

**Hvorfor read-only-sjekken etter dispatch.** Hook-inndataene for et verktøykall sier ikke hvilken
subagent som kaller, så en hook kan ikke skille en reviewer fra en implementer. Vernet er derfor to
ledd: read-only-rollene har ikke `edit` i verktøylista (håndhevet av plattformen), og
`scripts/readonly-check.sh` måler etterpå at treet er rent og at HEAD står der koordinatoren satte
den. Skriving via shell fanges dermed ved kilden — i treet — og ikke av en vakt som må gjette
avsenderen. Et brudd er nivå A fordi en reviewer som skrev, har gjennomgått noe annet enn det som
skal merges.


## 1. Kø-utvelgelse (med ekte deps-gating)

**Hvorfor releasen styrer utvalget:** uten et mål plukker loopen øverste todo i hele køen, og en
release blir det som tilfeldigvis var ferdig da noen kjørte prod-releasen. Et filter
på release-scope for hånd («filtrer på release-scope først, sorter på `order` innenfor
scopet») glipper når det blir glemt. Nå gjør skriptet det.

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

→ Regel: «Sende en worker tilbake» (kjernen) og «Fix-mode-dispatch-mal»

**Hvorfor fersk dispatch som standard.** En worker som har levert sluttrapporten, er avsluttet; det
finnes ingen sesjon å sende en melding til. `write_agent` når bare en worker som fortsatt kjører i
bakgrunnen. Intensjonen bak reglene om å ikke vekke en død worker og om at en lås ikke er et
liveness-signal, er derfor: (1) en worker regnes som død i det rapporten er levert, (2) et
tre som er ryddet eller navngitt i en navngitt sweep, er dødt og gjenbrukes aldri, (3) en worker som
kan leve (B-sporet i §5c/§5d), får aldri treet sitt navngitt. Den ferske workeren får det den gamle
hadde i kontekst gjennom prompten: samme WORKTREE, en peker til forrige rapport og funnene — som
pekere, ikke sitater, av samme grunn som Bevis-regelens måling over.

→ Regel: «F3a: **gulvet** — antall»

**Overskrifts-formen.** Regexen matchet opprinnelig KUN fet form (`**V1**`,
`| **V1**`) og var blind for `### V1 — …`, som er en helt ordinær markdown-form. For en plan
med den formen ga F3a **0** for 13 reelle kriterier, og runbookens egen tolkning av 0 er
`vblock=legacy` — «skrevet før formatkravet, gulvet ikke bindende». Gate F ville altså slått av sitt
eget gulv i stille, på en plan skrevet samme dag. Alternasjonen over dekker begge former, og
`sed`-en normaliserer til bar V-ID så `sort -u` ikke teller `### V4` og `**V4**` som to. **Målt
bakoverkompatibel** mot planer i fet form (uendret antall). Defektklassen: en detektor som leter etter én skrivemåte i stedet for én klasse.


## 5c. Pipelining (plan neste todo mens denne implementeres)

→ Regel: «Mekanikk: parvis dispatch i bakgrunnen, med en par-barriere»

**Hvorfor barrieren beholdes selv om bakgrunnsmodus tillater mer.** Med `mode: "background"` kunne
A sin §5b starte i det implementer(A) leverer. Snapshot-parene, pre-par-2-halen og §0b-kallene er
likevel skrevet for et par som er ferdig samtidig: par 2s snapshot skal inneholde BEGGE par 1-trærne,
og B sin plan skal være pushet før reviewer(B) får sitt tre. Å slippe barrieren ville krevd en ny
runde med disse invariantene; latensen for A er prisen, og den er kjent og akseptert.


## 5d. Parallelle implementere (fil-disjunkt-gate)


## 6. Skriv delt state (seriell, re-kjørbar) + merge (kun koordinator)


## 6b. Drain bug-innboks (hver syklus, kun koordinator)


## 6c. Helsesjekk + release-rådgiver (betinget, kun koordinator)


## 6d. Worktree-sweep (hver syklus, kun koordinator)

→ Regel: «**Sweepen er ikke en svakere §0b»

**Hvorfor denne finnes ved siden av §0b.** §0b er en per-runde sikkerhetsgate med seks vakter, og
den feiler med rette LUKKET: ved enhver advarsel er utfallet «INGEN rydding». Konsekvensen er at
hver agent som dør, avbrytes, eller etterlater en foreldreløs lås, legger igjen et tre som INGEN
senere plukker opp. Det er ikke en defekt i §0b — det er et manglende oppsamlingssteg bak den.
Målt: 30 trær, 4,1 GB, det eldste flere uker gammelt, og disken gikk full som følge.
Målt: sweepen hadde ALDRI kjørt (`grep -c wtsweep run-log.md` = 0) —
72 trær, 19,4 GB, og `--dry-run` viste at den ville slettet treet som bar HEAD-branchen til en
åpen PR.


## 7. Grooming-modus (kø tom)


## 8. Mini-retro (kø-tom/stopp)


## 8b. Drain retro-logg (ved §6c-helsesjekk — begge triggere — kun koordinator)


## 8c. Agér på tallene (ved §6c-helsesjekk — begge triggere — kun koordinator)

→ Regel: «Kjøres rett etter §8b, ved begge §6c-triggere»

**Hvorfor dette steget finnes.** Vi måler mye — `measure-cost.py`, `run-log.md`,
`decision-log.md`, `retro-triage.md`, lessons-filene — og uten dette steget finnes ingen
prosedyre som PLIKTER noen å gjøre noe med det som blir målt. Resultatet er at de fleste
BLOKKERENDE review-funn kan tilhøre én og samme feilklasse — «en vakt som ikke kan bli rød
av riktig grunn» — og hver enkelt ble funnet på nytt, av en fersk reviewer, til full pris.
Mønsteret lå i tallene fra dag to. Eieren måtte peke på det. Det er den feilen dette steget
lukker: *tall og statistikk er ikke verdt noe om ingen agerer på dem.*


## Pausepunkter (nivå A — spør + eskalér; nivå B — bestem selv, logg, mennesket kan vetoe)

