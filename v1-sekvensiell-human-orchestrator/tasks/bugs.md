<!-- Bugs nummereres sekvensielt. Flytt til tasks/bugs_archive.md når lukket. Slett aldri. -->

# <PROSJEKTNAVN> — Bugs

> Aktive bugs vises her. Lukkede bugs flyttes til `bugs_archive.md` (opprettes ved første lukking).

## Format

```md
### BUG-NNN — [kort tittel]

- **Beskrivelse:** Hva som er galt
- **Kilde:** code-review | manuell-test | bruker | claude-code
- **Fil:** filnavn og linje
- **Alvorlighet:** kritisk | høy | lav
- **Status:** åpen | under arbeid | lukket
- **Oppdaget:** YYYY-MM-DD
- **Løst:** YYYY-MM-DD eller —
- **Rotårsak:** fylles inn når løst
- **Ref:** Relevant TODO-nummer hvis det jobbes med fix
```

**Alvorlighet:**
- Score ≥ 90, eller sikkerhet/datatap → **kritisk**
- Score 80–89, eller funksjonell feil → **høy**
- Score < 80 som likevel registreres → **lav**

---

## Åpne bugs

*(Tom ved start. Legg til første bug under denne linjen.)*
