# Oppfølgingskø (carry-forwards)

Én fil per oppfølging: `tasks/followups/<YYYY-MM-DD>-<slug>.md` (eller `cf-<todo-nr>-<slug>.md` for
carry-forwards fra en merget todo). Koordinatoren er eneste skriver. Dette er ikke lessons: en fil
slettes når oppfølgingen er lukket, og et punkt som blir en konkret oppgave flyttes til en todo-fil.

Format:

```md
---
kilder: [TODO-<nr>]
---

# Kort tittel

- **Trigger:** hva som avdekket det
- **Åpent:** hva som står igjen
- **Plan:** hva som skal gjøres, og når
```

Finn oppfølginger for en todo eller fil: `grep -rl '<todo-nr eller filsti>' tasks/followups/`.
