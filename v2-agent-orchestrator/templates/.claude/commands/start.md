<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->
Les følgende filer i denne rekkefølgen:
1. CLAUDE.md
2. tasks/lessons.md (indeks — peker til detaljfiler under tasks/lessons/)
3. tasks/bugs.md
4. `tasks/todos/README.md` — forstå frontmatter-skjema og status-enum

Kjør git-orientering:
  git branch --show-current && git log --oneline -5 && git status

Sjekk session dump:
- Finn branch-navnet fra git-orienteringen
- Sjekk om tasks/sessions/todo-<nr>-<slug>.md eksisterer for denne branchen
- Hvis ja: les den og inkluder innholdet i statusoppdateringen
- Hvis nei: ingen tidligere session dump funnet — fortsett normalt

Hvis du er på {{PROD_BRANCH}}: opprett en passende feature-branch før du fortsetter.
Navngi branchen etter konvensjonen i docs/naming-conventions.md (prefix: feat/, fix/, docs/, chore/).

Hvis du finner ucommittede endringer fra tidligere sesjon: rapporter dette.

**Finn neste todo:**
Glob over `tasks/todos/todo-*.md` og les frontmatter-feltene `nr`, `status`, `order`, `title`, `deps`, `tags` fra hver fil.
Sorter på `order` (numerisk). Finn første todo med `status: open` eller `status: reviewed`.

**Deps-sjekk:**
For den kandidat-todoen: les `deps`-feltet. For hver dep-nr: prøv å finn `tasks/todos/todo-{dep}-*.md`.
- Fil ikke funnet → dep er done og arkivert (done-todos slettes fra tasks/todos/) → OK
- Fil funnet med `status: done` → OK
- Fil funnet med annen status → blokkert; hopp til neste kandidat i order-rekkefølgen og gjenta

**Gi meg en kort statusoppdatering med:**
- Nåværende branch og git-status
- Session dump hvis funnet — særlig "Ikke glem" og "Hvor vi er"
- Eventuelle funn fra avbrutt sesjon
- Neste todo (nr, tittel, status) + evt. blokkerte todos (deps ikke done)

Vent på bekreftelse før du begynner å kode.
