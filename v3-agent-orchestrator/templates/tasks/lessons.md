# Lessons — indeks

Scope-katalog over Codes wiki-baserte langtidsminne. Per-lesson-detaljer ligger i
`tasks/lessons/<tema>.md`-filene — denne indeksen er kun en veiviser for å velge hvilke tema-filer
som skal leses. Regelverket står i `docs/loop-rules.md` § «Lessons learned — wiki-struktur».

**Slik bruker sesjonene den:**

- `/start` leser kun denne indeksen
- `/todo-plan`, `/todo-plan-review`, `/todo-execute` leser indeksen + 1–3 relevante tema-filer per
  todo (aldri alle)
- `/todo-done` appender ny lesson til riktig tema-fil; oppdaterer lesson-count her kun hvis
  tema-filen har vokst med ≥ 5 lessons siden forrige count

**Kategoriserings-prinsipp:** Lessons kategoriseres etter _temaet de blir reaktivert mot_ i
fremtidige todos, ikke etter hvilken todo de oppstod i.

---

## Tema-filer

<!-- Grupper gjerne etter område (Backend / Frontend / Testing / Prosess) etter hvert som filene
     fylles. Hold «(N lessons)» omtrentlig — se telleregelen over. Marker periode-splittede filer
     med **current** / periode-arkiv. -->

{{LESSONS_INDEX_ENTRIES}}
- `tasks/lessons/open-followups.md` — carry-forwards som krever oppfølging

---

## Slik finner du eksisterende lessons

- **Tittel-liste på tvers av tema-filer:** `grep -rE "^## " tasks/lessons/`
- **Innholdssøk etter nøkkelord:** `grep -ri "<keyword>" tasks/lessons/`
- **Tittel + dato per fil:** `grep -nE "^## 20" tasks/lessons/<tema>.md`

## Cross-cutting lessons

Hvis en lesson berører flere temaer, legges den som full blokk i én primær tema-fil og som peker
under `## Se også`-seksjonen i sekundære tema-filer (format: `- **<kort claim>** — relevant for
<kort kontekst> (se [primær-tema.md](primær-tema.md))`). Søk derfor alltid både i tittel-listen og
i `## Se også`-seksjonene når du leter etter relevante presedenser.
