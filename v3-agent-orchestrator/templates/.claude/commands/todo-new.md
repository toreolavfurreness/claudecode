---
description: 'Opprett én ny todo-fil: søk etter duplikat, neste ledige nr, frontmatter etter skjemaet, docs/-branch + PR.'
---

# /todo-new — opprett en todo

Bruk når eieren ber om en ny todo, eller når et funn må leve videre som egen jobb. Kommandoen
oppretter én fil i `tasks/todos/` og en PR. Den planlegger ikke, claimer ikke og endrer ingen
andre todoer. Skjemaet er `tasks/todos/README.md`; les det hvis et felt er uklart.

Argument: en kort beskrivelse av saken (kan være tomt — spør da eieren hva todoen gjelder).

## 1. Trengs en ny todo?

Søk før du skriver. Køen vokser raskere enn den tømmes, og en duplikat-todo koster en hel
plan-runde senere.

```bash
git fetch -q origin dev
git grep -n -i '<2–3 nøkkelord>' origin/{{BASE_BRANCH}} -- tasks/todos/ tasks/todo_archive.md tasks/bugs.md
```

- **Finnes en åpen todo som dekker saken:** legg til observasjonen i den (brødtekst eller
  `observed:`), ikke lag en ny. Stopp her og si hvilken.
- **Er saken arkivert som ferdig, men tilbake:** ny todo, og pek på den gamle i brødteksten.
- **Er det et funn som ikke blokkerer noe:** foreslå PR-tekst eller en lesson i stedet, og spør
  eieren. Opprett bare hvis eieren vil ha todoen.
- **Er det en bug brukeren ser:** den hører i `tasks/bugs/inbox/`, ikke her.

## 2. Nummer og slug

```bash
bash tasks/next-todo-nr.sh
```

Skriptet leser `tasks/todos/`, `tasks/todo_archive.md` og åpne PR-er på `origin/{{BASE_BRANCH}}`, og gir
neste ledige nummer. Exit 1 betyr at en kilde ikke kunne leses — ikke gjett et nummer, si fra.
Gjenbruk aldri et arkivert nummer, og fyll ikke hull.

Slug: kebab-case, kort, beskriver saken (norsk tillatt, se `docs/naming-conventions.md`). Samme
slug brukes senere i planfila og branchen.

## 3. Fila

`tasks/todos/todo-<nr>-<slug>.md` (filnavnet med små bokstaver, `nr:` slik eieren skriver det):

```markdown
---
nr: "<nr>"
slug: <slug>
title: "<Område>: <hva som er galt eller skal lages, i én setning>"
status: open
order: <se under>
priority: normal
tags: [<domene-tag>]
deps: []
claimed_by: null
plan: null
---

**Kilde:** <hvor saken kommer fra: eier, PR, bug, review-funn — med dato>

**Problem:** <hva som er galt eller mangler, og hvem det rammer>

**Løsning:** <retning hvis den er kjent; ellers «Avklares i planen»>

**Ferdig når:**
- <målbar påstand som en reviewer kan sjekke>
```

Regler for feltene:

- **`order`:** se naboene. Uten release: `nr × 10`. I en release: like etter todoene den hører sammen
  med i samme release (`grep -h '^order:' tasks/todos/*.md` for nabo-verdiene). Ukesmålet
  overstyrer uansett `order`.
- **`priority`:** `normal` med mindre eieren sier noe annet.
- **`tags`:** gjenbruk eksisterende tags (`git grep -h '^tags:' origin/{{BASE_BRANCH}} -- tasks/todos/ | sort | uniq -c`).
  `[forslag]` + `status: deferred` er for u-triagerte grooming-forslag, ikke for eierens bestillinger.
- **`deps`:** bare ekte blokkere, som nr-strenger (`["443"]`).
- **`release` / `epic` / `release_blocker`:** bare når eieren legger todoen i en release.
  Sjekk at releasen finnes (`ls tasks/releases/`). Kommer todoen inn i en aktiv release, skriv i
  brødteksten hvilken `done_when`-linje den blokkerer, ellers sett ikke `release_blocker`.
- **`effort`:** valgfri. Skriv bare et anslag hvis du har lest koden; det er en påstand, ikke en måling.
- **`files` / `lessons`:** fyll når de er kjent (inline-liste, doble anførselstegn).
- **Brødtekst:** på norsk, konkret. «Ferdig når» må kunne sjekkes uten å spørre deg.

## 4. Branch og PR

```bash
git worktree add <scratchpad>/wt-todo-<nr> -b docs/todo-<nr>-<slug> origin/{{BASE_BRANCH}}
# skriv fila der
npx prettier --check tasks/todos/todo-<nr>-<slug>.md
git add tasks/todos/todo-<nr>-<slug>.md
git commit -m "docs(todo): TODO <nr> — <kort tittel>"
git push -u origin docs/todo-<nr>-<slug>
gh pr create --base {{BASE_BRANCH}} --title "docs(todo): TODO <nr> — <kort tittel>" --body "<Kilde + Problem i to linjer>"
```

Flere todoer fra samme sak kan gå i samme PR. Kjør `bash tasks/next-todo-nr.sh` på nytt før
hver ny fil — skriptet ser ikke filer som bare ligger lokalt, så øk nummeret selv for nummer to.

Avslutt med PR-lenken, nummeret og én linje om hvor i køen todoen havnet. **Merge bare når eieren sier det.**
