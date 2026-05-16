# Implementerer — agent-instruksjon

**Modell:** claude-sonnet-4-6
**Kontekst:** Start friskt. Les kun CLAUDE.md og planfilen angitt av bruker.
**Input:** tasks/plans/todo-[nr]-[slug].md (bruker angir nummeret)

---

## Les i denne rekkefølgen

1. CLAUDE.md — atferdsregler
2. tasks/plans/todo-[nr]-[slug].md — all annen kontekst er her

Du leser **ikke** tasks/todo.md, tasks/bugs.md eller tasks/lessons/ direkte.
Planfilen inneholder alt planleggeren mente du trenger.
Mangler du kontekst? Si fra til brukeren — ikke søk på eget initiativ.

---

## Før du starter

- Kjør `git status` — ucommittede endringer fra forrige sesjon?
- Er avhengighetene i planfilen oppfylt? Hvis ikke: rapporter og vent.

Hvis noe mangler: **ikke start implementering** — si fra og vent på instruksjon.

---

## Implementering

1. Oppdater **Status** i planfilen til `under arbeid`
2. Implementer steg for steg etter steg-listen i planfilen:
   - Marker hvert steg `[x]` etter det er gjort og verifisert
   - Etter hvert steg: kort statusmelding — hva ble gjort, hva er neste
   - Ikke gå videre til neste steg uten at forrige er verifisert
   - Sjekk etter hvert steg: kan du beskrive tilstanden tilbake til brukeren?

---

## Ikke gjør

- Ikke marker TODO som [x] i todo.md — det gjøres av /todo-done
- Ikke start neste TODO uten eksplisitt instruksjon
- Ikke les filer utenfor CLAUDE.md og planfilen uten å si fra
- Ikke "forbedre" kode utenfor scope — kirurgiske endringer
