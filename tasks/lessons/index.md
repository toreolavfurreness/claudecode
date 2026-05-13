# Lessons — indeks

Les denne filen ved sesjonstart. Last deretter KUN filene som er relevante
for oppgaven du skal jobbe med — ikke alle på én gang.

## Navigering

Les sammendraget for hver fil nedenfor. Åpne de som matcher oppgaven.
Følg `→ se også`-lenker videre kun hvis de berører oppgaven direkte.
Usikker? Les `general.md` alltid, resten etter skjønn.

## Sider

**`general.md`** — Fallgruver som ikke passer et spesifikt tema.
→ Les alltid ved usikkerhet om hva som er relevant.

**`auth.md`** — Innlogging, session-håndtering, tokens, RLS-policies,
permissions, middleware.
→ se også: [[database]] hvis oppgaven berører RLS eller row-level data

**`database.md`** — Migrasjoner, skjemaendringer, constraints, foreign keys,
seeding, Supabase-spesifikke fallgruver.
→ se også: [[auth]] hvis oppgaven berører permissions eller RLS

**`api.md`** — Endepunkter, feilhåndtering, statuskoder, retries, webhooks,
integrasjoner mot eksterne tjenester.
→ se også: [[testing]] for API-testemønstre

**`ui.md`** — Komponenter, skjemaer, state-håndtering, navigation,
lokalisering, stil og designsystem.
→ se også: [[api]] hvis komponenten henter data

**`testing.md`** — Testmønstre, assertions, mocking, CI-oppsett,
hva som gjør en test meningsfull vs. tom.
→ se også: domenefilen for området som testes

**`git-workflow.md`** — Branch-håndtering, merge-konflikter, PR-prosess,
commit-rekkefølge, rebase vs. merge.

## Lint — periodisk vedlikehold

Kjør lint når lessons-wikien føles utdatert, eller ca. én gang per måned.
Gå gjennom alle tema-filer og sjekk:
- **Motsetninger:** to entries som sier det motsatte — behold den nyeste, slett den gamle
- **Foreldede entries:** løsningen er byttet ut siden entry ble skrevet — marker eller slett
- **Orphans:** entries som refererer til kode, mønstre eller avhengigheter som ikke lenger finnes
- **Feil fil:** entry ligger i `api.md` men handler egentlig om auth — flytt den

Oppdater sammendragene i denne filen hvis innholdet i tema-filene har endret seg vesentlig.

---

## Hvilke filer å lese — etter oppgavetype

| Oppgave | Les |
|---------|-----|
| Database-migrasjon eller skjemaendring | `database.md` + `auth.md` hvis RLS berøres |
| Auth-flyt eller permissions | `auth.md` + `database.md` |
| Nytt API-endepunkt eller integrasjon | `api.md` + `testing.md` |
| UI-komponent eller skjema | `ui.md` + `api.md` hvis datahenting |
| Bugfix (ukjent årsak) | `general.md` + nærmeste domenefil |
| Refaktorering eller opprydding | `general.md` + relevant domenefil |
| Git-problem eller PR | `git-workflow.md` |
