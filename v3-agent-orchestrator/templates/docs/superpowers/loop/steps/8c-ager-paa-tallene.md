<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# 8c. Agér på tallene (ved §6c-helsesjekk — begge triggere — kun koordinator)

→ Kjerne: `coordinator-runbook.md` § 8c · Begrunnelser: `runbook-hvorfor.md` § 8c

Kjøres rett etter §8b, ved begge §6c-triggere, og **kun ved grønn helsesjekk** (rød helsesjekk
er et pausepunkt — da kjøres verken §8b eller §8c).

### Steg 1 — mål, to kilder

```bash
python3 tasks/lesson-classes.py --days 7      # feilklasser i lessons
python3 tasks/measure-cost.py "$(date -v-30d +%F)" --trend   # 30-dagersvindu: kostnad, review-runder, Gate F, $/dag
```

Transkriptene slettes etter `cleanupPeriodDays` (standard 30 dager), så 30-dagersvinduet er
også taket for hva som kan måles uten å heve den innstillingen.

`--trend` skriver de samme fire dommene som Trend-seksjonen i måle-artifactet, fra samme
datauttrekk og samme terskelfunksjon — så en graf som viser oppgang og en §8c-kjøring som sier
«uendret» kan ikke sprike. Den avslutter med **exit 1** hvis minst én måling har gått feil vei.

Alle fire målingene er «lavere er bedre», og dommen er snittet av de siste N mot de N før
(N ≤ 5, minst 3 på hver side). Under 3+3 punkter skriver den «for få til en retning» i stedet for
en pil — en retning utledet av to punkter er støy, og en pil ville påstått noe dataene ikke bærer.

Vinduet er 7 døgn fordi det er langt nok til at en klasse rekker å gjenta seg, og kort nok til
at en klasse vi allerede har gatet faller ut av det igjen. Scriptet klassifiserer hver lesson i
ÉN primærklasse (tittel + `**Problem:**`-linja; ikke `**Løsning:**`/`**Unngå:**`, som nesten
alltid nevner et verktøy uten at DET er feilklassen) og rangerer klassene etter volum.

### Steg 2 — les handlingslinja

Hver kilde skriver enten en «ingen handling»-linje eller en `§8c-HANDLING`-linje:

- `Alle forekommende klasser har en mekanisk gate. Ingen §8c-handling.` og `Ingen måling går feil
  vei.` → ferdig. Ingen rad, ingen commit. Dette er det normale utfallet, og steget koster da under
  ett sekund.
- `§8c-HANDLING: «<klasse>» (N lessons) er den høyest rangerte klassen uten mekanisk gate.` →
  gå til steg 3.
- `§8c-HANDLING (måletall): «<måling>» <endring>` → gå til steg 3.

Fyrer begge, håndteres begge — de er to ulike spørsmål («hvilken feil gjentar vi?» og «hvilket
tall går feil vei?»), ikke to varsler om det samme. Taket på én klasse per kjøring gjelder
lesson-siden; måletall-siden har sjelden mer enn én måling i rødt om gangen, og har den det, ta
den største.

**Terskelen er gate-dekning, ikke et råtall.** Første versjon av scriptet brukte «≥ 3 forekomster
på ≤ 7 dager ⇒ plikt», og fikk 6 av 6 klasser over terskel på første kjøring. En teller som alltid
utløser er nøyaktig like verdiløs som en vakt som aldri blir rød — samme feilklasse som steget
finnes for å bekjempe. Kriteriet er derfor: *klassen forekommer OG ingen mekanisk gate dekker den
ennå*, og **maks én klasse håndteres per §8c-kjøring** (kostnadsgrep: én handling per helsesjekk,
ikke en liste).

### Steg 3 — handle. Nøyaktig ett av tre utfall, alle logget

Utfallet er nivå B (bestem selv, logg, mennesket kan vetoe). Rad i `decision-log.md`, format som
presedensen `### 2026-09-17 03:10 — §6c/e2e [B]: …`:

```
### <dato> <tid> — §8c [B]: <klasse> — <gate innført | todo NN | ikke gatebar: grunn>
```

| Utfall | Når | Hva du gjør |
|---|---|---|
| **a) Innfør gaten nå** | Regelen er mekanisk uttrykkbar og koster < ~30 linjer | Legg regelen **der klassen faktisk kan observeres**: `tasks/vblock-lint.py` for mønstre som står i en planfil, ellers en hook i `.claude/hooks/`, et eget script under `tasks/`, eller et CI-steg. Linteren leser kun planfiler, så en klasse som ikke er et planfil-mønster (f.eks. branch-alder) er fortsatt gatebar — bare ikke der. Legg nye linter-regler inn som SOFT først (se nivå-noten der). Oppdater `GATES`-tabellen i `tasks/lesson-classes.py` slik at verdien **peker på stedet gaten faktisk kjører**, og **motprøv begge veier**: regelen MÅ være rød på et navngitt, datert historisk eksempel fra klassen og ren på den fiksede formen. Uten motprøven har du lagt til en vakt av samme klasse du prøvde å gate — og fordi en ikke-tom `GATES`-verdi filtrerer klassen ut av `ungated`, slår du den da permanent av for §8c. En gate som ikke er koblet inn noe sted kan aldri bli rød: da er raden «regelsett skrevet, ikke koblet inn», ikke «gate innført», og `GATES` skal stå tom. |
| **b) Fremm til todo** | Gaten er reell, men for stor for en helsesjekk | Todo-utkast (`status: deferred`, `tags: [forslag]`), og `ref=TODO NN` i decision-log-raden. Teller mot §8bs utestående-tak på 3. |
| **c) Ikke gatebar** | Klassen krever skjønn en maskin ikke har | Skriv grunnen i raden, og sett klassens `GATES`-verdi i `tasks/lesson-classes.py` til `'ikke gatebar: <grunn>'` — ellers foreslår scriptet den samme klassen ved hver eneste helsesjekk. |

**For en måletall-handling** er de samme tre utfallene: (a) innfør tiltaket nå, (b) fremm til todo,
(c) forklart avvik — men (c) krever her en ÅRSAK, ikke bare «ikke gatebar». En kostnadsøkning som
skyldes at loopen kjørte flere timer den dagen er en forklaring; «tallet svinger» er ikke. Skriv
årsaken i raden, så neste §8c kan se om den fortsatt holder.

**«Ingenting skjedde» er ikke et lovlig utfall.** Er handlingslinja der, skal én av de tre radene
skrives. Det er hele poenget med steget.

### Steg 4 — mål effekten av forrige §8c-handling

Før du forlater steget: finn forrige `§8c [B]`-rad i `decision-log.md` og sjekk om klassen den
handlet på faktisk har falt. To kilder, begge mekaniske:

```bash
# Hvor ofte gaten faktisk fyrer. `log_run()` skriver nøkkelen `hard` (ikke `level`) —
# verifisert mot en ekte loggrad 2026-09-17. Feiler kommandoen med «No such file»,
# har linteren aldri kjørt med `--log`, og svaret er «ukjent», ikke «null».
# Tallet teller HARD-FUNN, ikke bekreftede defekter — en falsk positiv teller likt.
# Les det sammen med `rules`-feltet i samme loggrad og med klassens fall i
# `lesson-classes.py`, aldri alene.
python3 -c 'import json; print(sum(json.loads(l)["hard"] for l in open("tasks/metrics/vblock-lint-log.jsonl")))'
python3 tasks/lesson-classes.py --days 7 --json | python3 -c \
  'import json,sys; d=json.load(sys.stdin); print({k: len(v) for k, v in d["classes"].items()})'
```

Falt klassen ikke etter to helsesjekker, var gaten feil gate — noter det i den nye raden og
vurder utfall (b) eller (c) i stedet. En gate som er innført og aldri fyrer er ikke et bevis på
at klassen er borte; den er like ofte et bevis på at gaten ikke kan se klassen.

**Persistering:** endringer i `tasks/`, `docs/superpowers/loop/` og decision-log-raden committes
via **Delt-state-git-halen** (§6, steg 6) med `$MSG="chore(loop): §8c — <klasse>"`. Ved Trigger 1
fanges de av §7s hale (samme mønster som §8b); ved Trigger 2 MÅ §8c kjøre halen selv — ellers
treffer neste todo §0s «Working tree ikke ren → stopp».
