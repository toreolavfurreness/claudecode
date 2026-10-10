---
description: 'Skriv én lesson-fil: duplikatsøk, riktig kunnskapsbase, filnavn fra skript, format og tagger, docs/-PR.'
---

# /lesson-new — skriv en lesson

Bruk når en lesson skal skrives utenfor `/todo-done`: eieren retter deg, en antakelse viste seg
feil, en fallgruve kostet tid, eller en bug ble fikset på en ikke-åpenbar måte. I loopen skriver
`/todo-done` lessons selv. Workers (planner, implementer, reviewere) kjører aldri denne — de
melder lessons i rapporten, og koordinatoren skriver.

Skrive-protokollen er `tasks/lessons.md`, formatet er `CLAUDE.md` § «Lessons learned». Denne
kommandoen følger dem; ved konflikt gjelder de.

Argument: hva som skjedde, kort (tomt: spør eieren).

## 1. Hører det hjemme i lessons?

Splitt først setningen i atomiske påstander. Så, per påstand (detaljer i `CLAUDE.md` § «Tre kunnskapsbaser»):

- **Samarbeidspreferanse** («eieren vil ha …») → `MEMORY.md`, ikke lessons. Stopp.
- **Statistikk om egen atferd** (signalord «de siste N rundene», «gir oftest», «pleier å») → agent-minne. Stopp.
- **Sann påstand om kodebasen, plattformen eller verktøyet** → lessons. Fortsett.
- **Uavgjort** → lessons.

## 2. Finnes den allerede?

```bash
grep -rli '<nøkkelord 1>' tasks/lessons/ | xargs grep -li '<nøkkelord 2>'
grep -m1 '^# ' tasks/lessons/<tema>/*.md | grep -i '<nøkkelord>'
```

Les treffene. Dekker en lesson samme mønster: **utvid den** (nytt avsnitt i Løsning/Unngå, kilden
inn i `kilder`) i stedet for å lage en ny. Er to eksisterende filer samme lesson, slå dem sammen og
slett den ene.

## 3. Tema og filnavn

Temaet er mappen (`ls tasks/lessons/`). Velg det som eier mekanismen; relevans for andre tema går i
`tags`, ikke i en peker.

```bash
python3 tasks/lesson-path.py <tema> "<tittel>"
```

Skriptet gir stien med en fast slug-algoritme og legger til `-2` ved kollisjon.
Exit 2 betyr ukjent tema: velg et som finnes, eller bruk `--new-tema` når et nytt tema faktisk trengs.

## 4. Fila

```md
---
tags: [<emne-tag>, <evt. annet tema>]
scope: project
kilder: [TODO-NN, BUG-NNN]
---

# <Kort tittel — mekanismen, ikke symptomet>

**Problem:** Hva som gikk galt eller var uventet
**Årsak:** Rotårsaken (utelates når problemet er selvforklarende)
**Løsning:** Hva som faktisk fungerte
**Unngå:** Konkret regel som kan følges neste gang
```

- **`tags`:** minst én emne-tag, aldri mappens eget navn. Gjenbruk: `python3 tasks/lesson-path.py --tags [<tema>]`.
- **`kilder`:** `TODO-NN` / `BUG-NNN`; tom liste er lov.
- **Unngå** er det viktigste feltet: en handling, ikke en refleksjon. «Vær forsiktig med X» er ikke
  en regel; «kjør Y før Z» er.
- Er regelen generell nok til å gjelde hver sesjon: foreslå den også for `CLAUDE.md`, men endre ikke
  `CLAUDE.md` uten at eieren sier ja.

## 5. Branch og PR

```bash
git worktree add <scratchpad>/wt-lesson -b docs/lesson-<slug> origin/{{BASE_BRANCH}}
# skriv fila der
npx prettier --check <fil>
git add <fil> && git commit -m "docs(lessons): <tittel>"
git push -u origin docs/lesson-<slug>
gh pr create --base {{BASE_BRANCH}} --title "docs(lessons): <tittel>" --body "<Problem + Unngå i to linjer>"
```

Flere lessons fra samme sesjon går i samme PR. Avslutt med PR-lenken og stien.
**Merge bare når eieren sier det.**
