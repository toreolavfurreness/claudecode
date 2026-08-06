<!--
  Statisk mal — kopieres til prosjektets tasks/bugs/inbox/README.md av
  setup-scriptet, med token-verdier fra loop.config.yaml substituert.
-->
# Bug-innboks

Slipp én fil per bug her: `bug-<slug>.md`. Én fil = null merge-konflikt (samme prinsipp som
én-fil-per-todo). Koordinatoren triagerer innboksen inn i `tasks/bugs.md` (eller forfremmer til
en todo) og sletter fila. **Rør aldri `tasks/bugs.md` manuelt** — den er koordinator-eid.

Format per fil:

```markdown
---
reporter: <navn>
date: <YYYY-MM-DD>
priority: høy | middels | lav
---
Hva skjer, hvordan reprodusere, hvilken side/flyt.
```

Haster det? Opprett en todo direkte i stedet (`tasks/todos/todo-NN-fix-<slug>.md`,
`priority: prioritert`).
