<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->

# 6b. Drain bug-innboks (hver syklus, kun koordinator)

→ Kjerne: `coordinator-runbook.md` § 6b · Begrunnelser: `runbook-hvorfor.md` § 6b

Sjekk `tasks/bugs/inbox/` for nye `bug-*.md` (mennesker slipper dem her — én fil per bug, ingen konflikt). For hver:
- **Reell, ikke-planlagt bug** → legg en oppføring i `tasks/bugs.md` (format: se eksisterende).
- **Bug som bør fikses nå** → forfremm til en ny todo (`tasks/todos/todo-NN-fix-<slug>.md`, sett `priority` etter innboks-filens vurdering).
  Med en aktiv release får den nye todoen **ikke** `release:`, med ett unntak: blokkerer buggen en
  `done_when`-linje, sett `release: "<aktiv>"`, `release_blocker: true` og navngi linja i
  brødteksten (scope-vakten, `tasks/releases/README.md`).
- **Ugyldig/duplikat** → noter og forkast.
**Årsakspåstander: MÅLT eller HYPOTESE.** Hver oppføring (i `bugs.md` eller en fix-todo) som sier
noe om årsak eller atferd, bærer enten en **MÅLT**-kilde (hva som ble kjørt, og hva som ble sett) eller
ordet **HYPOTESE**. En videreformidlet feilmelding er ikke en måling: en testrunners feiltekst er som
regel en gjetning om årsak. Målt: en bug skrevet ut fra en smoke-feilmelding
sendte feilsøkingen feil vei i over en time.
Slett den drainede innboks-fila etterpå. Dette er koordinatorens skriving (single-writer) — mennesker rører aldri `bugs.md` selv.
