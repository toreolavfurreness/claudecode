# Lessons — katalog

Codes langtidsminne: én fil per lesson under `tasks/lessons/<tema>/`. Filsystemet er indeksen —
ingenting her telles eller genereres, så ingenting her kan bli utdatert. Temaene er mappene:
`ls tasks/lessons/`. Filformatet står i `docs/loop-rules.md` § «Lessons learned — én fil per lesson».

## Tema

<!-- Fyll inn scope per tema: hvilke fremtidige todos lessons i mappa reaktiveres mot. Et nytt tema
     er bare en ny mappe — legg det til her med én linje. -->

{{LESSONS_INDEX_ENTRIES}}

Oppfølgingskøen (carry-forwards) er ikke lessons. Den ligger i `tasks/followups/`, én fil per
oppfølging, og en fil slettes når oppfølgingen er lukket.

## Lese-protokoll

1. Velg 1–3 tema for todoen, eller bruk dem koordinatoren oppga.
2. List titlene: `grep -m1 '^# ' tasks/lessons/<tema>/*.md`. For et stort tema, filtrer først:
   `grep -m1 '^# ' tasks/lessons/<tema>/*.md | grep -i '<nøkkelord>'`.
3. På tvers av tema: `grep -rli '<nøkkelord>' tasks/lessons/`. Tagger:
   `grep -rlE '^tags: \[(.*, )?<tag>(,|\])' tasks/lessons/`.
4. Les de 3–5 relevante filene i sin helhet — aldri en hel tema-mappe.

## Skrive-protokoll

Kommandoen `/lesson-new` følger stegene under; `python3 tasks/lesson-path.py <tema> "<tittel>"` gir filnavnet.

1. Velg tema-mappe. Passer ingen, lag en ny med kebab-case-navn.
2. Skriv `tasks/lessons/<tema>/<YYYY-MM-DD>-<slug>.md` i formatet fra `docs/loop-rules.md`. Slug:
   tittelen med små bokstaver, æ→ae, ø→oe, å→aa, alt annet enn a–z og 0–9 → `-`, maks 60 tegn.
   Finnes navnet, legg til `-2`.
3. Ingen indeks, ingen telling, ingen Se også-peker. Relevans for andre tema går i `tags`.
4. Dekker en eksisterende lesson samme mønster: utvid den og legg kilden til i `kilder`. Slår du
   sammen to filer, slett den ene.
5. `tags` har minst én emne-tag og aldri mappens eget navn. Relevans for et annet tema er tema-navnet
   som tag. Gjenbruk eksisterende tagger:
   `grep -h '^tags:' tasks/lessons/*/*.md | sed 's/^tags: \[//; s/\]$//' | tr ',' '\n' | tr -d ' ' | grep . | sort | uniq -c | sort -rn`.
