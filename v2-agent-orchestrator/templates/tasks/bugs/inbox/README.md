<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->
# Bug-innboks

Slipp én fil per bug her: `bug-<slug>.md`. Én fil = null merge-konflikt (samme prinsipp som én-fil-per-todo). Koordinatoren triagerer innboksen inn i `tasks/bugs.md` (eller forfremmer til en todo) og sletter fila. **Rør aldri `tasks/bugs.md` manuelt** — den er koordinator-eid.

Format per fil:

```markdown
---
reporter: <navn>
date: <YYYY-MM-DD>
priority: høy | middels | lav
---
Hva skjer, hvordan reprodusere, hvilken side/flyt.
```

Haster det? Opprett en todo direkte i stedet (`tasks/todos/todo-NN-fix-<slug>.md`, `priority: prioritert`).
