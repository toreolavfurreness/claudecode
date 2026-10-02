---
description: "Koordinator: overlevering til neste sesjon — målt tilstand, faste artefakter republisert, overleveringsfil + PR, startprompt."
---

# /handover — overlevering mellom koordinator-sesjoner

Bruk når koordinator-sesjonen skal avsluttes eller byttes (kontekst full, eieren ber om ny sesjon, «gi meg en
handover-prompt»). For manuell jobbing på én todo: bruk `/endsession`.

Formålet er at neste sesjon starter uten at eieren må huske noe for den. Alt som kan måles, måles av skript;
du skriver bare det som krever vurdering. Endre ingen claims eller todo-status her.

## 1. Tilstand

Finn sesjonsstart: tidspunktet i forrige overleverings filnavn/innhold, eller det eieren oppgir. Lokal tid.

```bash
bash tasks/handover-state.sh --since <YYYY-MM-DDTHH:MM> --base {{BASE_BRANCH}}
```

Exit 1 betyr at en måling feilet (`FEIL:`-linje). Ta linja med i overleveringen og si fra — ikke skriv rundt den.

## 2. Faste artefakter

Les `docs/superpowers/loop/artifacts.md`. For hver rad: kjør generatoren fra et tre på `origin/{{BASE_BRANCH}}` (ucommittede filer i
samme tre kommer med på siden — greit hvis de skal med i PR-en i steg 4), kjør vakt-kommandoen,
og publiser med `url` (les først hvis sesjonen ikke har lest eller publisert siden). Noter versjonsnummeret fra
publiseringen. En feilet publisering skrives i overleveringen.

## 3. Overleveringsfila

`docs/superpowers/loop/handover-<YYYY-MM-DD>-<HHMM>.md` (lokal tid; unikt og sorterbart). Første linje etter
tittelen: «Erstatter `<forrige fil fra skriptet>`. Les denne først.» Seksjonene, i denne rekkefølgen:

1. **Tilstand** — skriptets utdata, uredigert. Legg til loopens tilstand (kjører / stoppet etter eierens ordre).
2. **Endringer i sesjonen** — én linje per merget PR: hva og *hvorfor*. Hvorfor-et har du fra sesjonen; mangler det,
   hent det fra PR-teksten (`gh pr view <nr> --json body`). Ikke gjett.
3. **Eiervedtak** — fra decision-log-linjene i skriptet, med det neste sesjon må vite.
4. **Følg med** — tidsfestede ting neste sesjon må sjekke (cron-kjøringer, ventende bygg, PR-er som venter på eier).
5. **Fallgruver fra sesjonen** — det som kostet tid og kan skje igjen, fra din egen kontekst. Husker du ingen: «(ingen)».
6. **Faste artefakter** — hver rad fra `artifacts.md` med URL og versjonen du nettopp publiserte.

Tomme seksjoner skrives som «(ingen)», ikke utelates — da ser neste sesjon at du sjekket.

## 4. Branch og PR

Branch `docs/handover-<dato>-<tid>` fra `origin/{{BASE_BRANCH}}`, commit overleveringsfila og `tasks/queue-status.md` hvis
`git status` viser den endret (generatoren i steg 2 skriver den), PR mot `{{BASE_BRANCH}}`. **Merge bare når eieren sier det.**

## 5. Startprompt

Skriv ut i en `text`-blokk, klar til å limes inn:

```text
Du er KOORDINATOR for <prosjekt>-loopen. Les docs/superpowers/loop/<overleveringsfil> på origin/{{BASE_BRANCH}} først.
<Loop-tilstand: «Loopen er stoppet etter eierens ordre. Ikke kjør /run-loop og ikke claim todoer før eieren sier det.» eller «Fortsett med /run-loop.»>
Ta over de faste artefaktene (docs/superpowers/loop/artifacts.md). Kjør Artifact action:"read" på hver URL først. Republiser alltid med url, aldri som ny side:
- <navn>: <url> (v<N>)
...
Første oppgaver:
1. <fra «Følg med»>
...
```

Avslutt med lenken til PR-en og et spørsmål om merge.
