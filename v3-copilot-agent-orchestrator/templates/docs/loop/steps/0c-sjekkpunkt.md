<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# 0c. Sjekkpunkt ved komprimering

→ Kjerne: `coordinator-runbook.md` § 0c

Denne fila finnes bare når `hooks.compaction_checkpoint` er på. Den gjelder koordinatoren, ikke
workerne.

**Hvorfor:** en auto-komprimering erstatter samtalen med et sammendrag, og sammendraget mister
detaljer: ordrette review-funn, hvilke PR-er som faktisk er merget, beslutninger tatt i økta. Du kan
ikke forutsi eller utsette en auto-komprimering. Gjør derfor ethvert øyeblikk trygt å bli komprimert på, og
fortsett gjennom den. Kontekstpress er ikke i seg selv en grunn til å overlevere: skriv sjekkpunktet
og fortsett.

## Fila

`tasks/.loop-state/checkpoint-<session_id>.md`. Mappa er gitignored, og fila committes aldri.

`<session_id>` er verdien av `$COPILOT_SESSION_ID` i shell. Er variabelen tom, bruk navnet på den
nyeste katalogen i `${COPILOT_HOME:-$HOME/.copilot}/session-state/`
(`ls -t "${COPILOT_HOME:-$HOME/.copilot}/session-state" | head -1`). UVERIFISERT: at sesjons-ID-en
er tilgjengelig på en av disse måtene i alle Copilot-flater. Finner du ingen, bruk
`manual-<epoch>` fra `date -u +%s`: prosedyren virker da like godt, men `preCompact`-hooken finner
ikke fila og logger ingen ferskhet. Den samme ID-en kommer som `sessionId` i hook-inndataene, og
hooken finner fila på den. Har du mistet ID-en etter en komprimering, er den nyeste fila
(`ls -t tasks/.loop-state/checkpoint-*.md | head -1`) din, med mindre flere koordinator-sesjoner
deler sjekkouten; overskriftslinja bærer ID-en.

## Skriv

**Første handling i sesjonen, før § 0-synken:** skriv stubben.
```bash
mkdir -p tasks/.loop-state
SID="${COPILOT_SESSION_ID:-<session_id fra regelen over>}"
printf '# Checkpoint %s\nSkrevet: %s epoch=%s\nAktiv todo: ingen ennå\nNeste handling: kjør /run-loop § 0\n' \
  "$SID" "$(date -u +%FT%TZ)" "$(date -u +%s)" \
  > "tasks/.loop-state/checkpoint-$SID.md"
```

**Ved hver steg-overgang:** skriv fila på nytt.
- **Header:** `Skrevet: <ISO> epoch=<sek>`, `Aktiv todo:` og `Neste handling:` blant de fem første
  linjene, med nøkkelordet i kolonne 1. En liste-kule foran (`- Skrevet:`) gjør ferskheten `UKJENT`
  for alltid. Alltid en fersk `Skrevet:`-linje.
- **Innhold utover headeren, kun dette:**
  - Hva du har claimet, og hva som faktisk er merget (PR-nr og SHA).
  - Review-funn som ennå ikke er foldet inn, ordrett og ikke oppsummert.
  - Eierbeslutninger fra økta som ikke står på disk noe annet sted.
- **Ikke gjenta** det som allerede er kanonisk på disk (todo-frontmatter, run-log, planfiler).
  Duplisert state som kan divergere er verre enn ingen.
- Hold fila kort (under ~400 linjer): du leser den før hvert steg.

## Les

Ingen hook legger sjekkpunktet tilbake i konteksten etter en komprimering. Lesingen er derfor din
egen, og regelen er mekanisk — ikke «når du merker at noe mangler»:

```bash
cat tasks/.loop-state/checkpoint-<session_id>.md
```

- **Før hvert steg** (samme øyeblikk som du leser stegfilen, jf. kjernen).
- **Når du gjenopptar** en sesjon.
- **Når du er usikker på tilstanden** — typisk når konteksten starter med et sammendrag der du
  ventet ordrette funn, PR-numre eller beslutninger.

Er sjekkpunktet og sammendraget uenige, **gjelder sjekkpunktet**. Du skrev det selv;
sammendraget er tapsbeheftet.

## Hookene

- `precompact-checkpoint.sh` (`preCompact`, `trigger=auto`) logger
  `FERSK`/`FORELDET`/`UKJENT` til `tasks/.loop-state/precompact.log` og legger en statuslinje nederst
  i sjekkpunktet. Den blokkerer aldri og skriver aldri til stdout: `preCompact` er kun et varsel og
  kan ikke påvirke komprimeringen. Hooken kan mangle (`.github/hooks/loop-guards.json` følger ikke
  alltid med til en annen maskin) eller degradere (uten `jq` skriver den bare én loggrad); lesingen
  over avhenger ikke av den.
- Harness: `bash .github/hooks/scripts/test-checkpoint-hooks.sh`.

## Før du slår på i et nytt prosjekt: mål

Mekanismen er målt på en eldre runtime. Mål den på din runtime før du stoler
på den:
1. Slå på `hooks.compaction_checkpoint`, kjør `/setup` og start en fersk sesjon.
2. Kjør loopen til en auto-komprimering skjer.
3. Sjekk at `tasks/.loop-state/precompact.log` har en linje med `trigger=auto` og riktig `session=`.
4. Sjekk at statuslinja (`<!-- PreCompact … -->`) står nederst i sjekkpunktfila, og at du leste
   fila før neste steg etter komprimeringen.

Feiler punkt 3, virker prosedyren fortsatt: lesingen er en regel, ikke en hook. Bare
ferskhetsloggen mangler.

<!-- ponytail: sjekkpunktet er lokalt og committes aldri. Kjører koordinatoren på flere maskiner
     (sky-containere), må fila committes og pushes ved todo-overgang — legg det til da. -->
