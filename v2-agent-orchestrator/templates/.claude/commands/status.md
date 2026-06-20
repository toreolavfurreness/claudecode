<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->
Les CLAUDE.md og tasks/bugs.md.

Kjør git-orientering:
  git branch --show-current && git log --oneline -5 && git status

**Todo-oversikt:**
Glob over `tasks/todos/todo-*.md`, les frontmatter-feltene `nr`, `status`, `order`, `title`, `tags` fra hver fil.
Sorter på `order`. Presenter en kompakt liste gruppert på status:
- `in_progress` / `reviewed` — øverst
- `open` — deretter
- `deferred` / `split` — til slutt (ikke list ut individuelt, bare tell)

Gi meg en kort oversikt over:
1. Nåværende branch og eventuelle ucommittede endringer
2. Todos med status `in_progress` eller `reviewed` (navns og nr — disse er neste)
3. Antall `open` todos totalt
4. Åpne bugs i bugs.md
5. Om tasks/sessions/ inneholder en dump for nåværende branch — kommenter kort hvis den virker utdatert

Ikke lag en plan, ikke endre noe, og ikke begynn å kode.
