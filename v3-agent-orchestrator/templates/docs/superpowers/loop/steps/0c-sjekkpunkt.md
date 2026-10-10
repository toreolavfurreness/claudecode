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
ikke trigge eller utsette komprimeringen. Gjør derfor ethvert øyeblikk trygt å bli komprimert på, og
fortsett gjennom den. Kontekstpress er ikke i seg selv en grunn til å overlevere: skriv sjekkpunktet
og fortsett.

## Fila

`tasks/.loop-state/checkpoint-<session_id>.md`. Mappa er gitignored, og fila committes aldri.

`<session_id>` er verdien av `$CLAUDE_CODE_SESSION_ID` i Bash. Er variabelen tom, bruk UUID-en i
scratchpad-stien din (`…/<session_id>/scratchpad`). Den samme ID-en kommer som `session_id` i
hook-inndataene, og hooken finner fila på den.

## Skriv

**Første handling i sesjonen, før § 0-synken:** skriv stubben.
```bash
mkdir -p tasks/.loop-state
printf '# Checkpoint %s\nSkrevet: %s epoch=%s\nAktiv todo: ingen ennå\nNeste handling: kjør /run-loop § 0\n' \
  "$CLAUDE_CODE_SESSION_ID" "$(date -u +%FT%TZ)" "$(date -u +%s)" \
  > "tasks/.loop-state/checkpoint-$CLAUDE_CODE_SESSION_ID.md"
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
- Hooken injiserer maks 400 linjer. Hold fila kort.

## Les

Etter en komprimering skal konteksten ha en blokk som starter med
`KOORDINATOR-CHECKPOINT GJENOPPRETTET`. Ser du den ikke, les fila selv. Hooken kan mangle
(`.claude/settings.json` følger ikke alltid med til en annen maskin) eller degradere (uten `jq`
skriver den bare én loggrad).

Er sjekkpunktet og sammendraget uenige, **gjelder sjekkpunktet**. Du skrev det selv;
sammendraget er tapsbeheftet.

## Hookene

- `sessionstart-checkpoint.sh` (SessionStart, matcher `compact`) injiserer fila etter komprimeringen.
- `precompact-checkpoint.sh` (PreCompact, matcher `auto`) logger `FERSK`/`FORELDET`/`UKJENT` til
  `tasks/.loop-state/precompact.log` og legger en statuslinje nederst i sjekkpunktet. Den blokkerer
  aldri og skriver aldri til stdout: ikke-tom PreCompact-stdout erstatter oppsummeringsprompten uten
  varsel.
- Harness: `bash .claude/hooks/test-checkpoint-hooks.sh`.

## Før du slår på i et nytt prosjekt: mål

Mekanismen er målt på en eldre runtime. Mål den på din runtime før du stoler
på den:
1. Slå på `hooks.compaction_checkpoint`, kjør `/setup` og start en fersk sesjon.
2. Kjør loopen til en auto-komprimering skjer.
3. Sjekk at `tasks/.loop-state/precompact.log` har en linje med `trigger=auto`.
4. Sjekk at `KOORDINATOR-CHECKPOINT GJENOPPRETTET`-blokken står i konteksten etter komprimeringen.

Feiler punkt 4, virker prosedyren fortsatt manuelt: les fila selv etter hver komprimering.

<!-- ponytail: sjekkpunktet er lokalt og committes aldri. Kjører koordinatoren på flere maskiner
     (sky-containere), må fila committes og pushes ved todo-overgang — legg det til da. -->
