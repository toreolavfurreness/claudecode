<!--
  GENERERT av /setup fra loop.config.yaml — IKKE rediger her.
  Endre loop.config.yaml og kjør /setup på nytt.
-->
# tasks/todos/ — Én fil per todo

Hver aktiv todo har én fil: `todo-NN-slug.md` (f.eks. `todo-66-todos-one-file-per-todo.md`).

Ferdige todos flyttes ikke hit — de arkiveres i `tasks/todo_archive.md` (append-only).

---

## Frontmatter-skjema

```yaml
---
nr: "66"                          # STRING — stabil nøkkel; håndterer 6, 6A, 6C3a
slug: todos-one-file-per-todo     # kebab-case, norsk tillatt (tracking-unntak)
title: "Refaktor: todo.md → én fil per todo"
status: open                      # se Status-enum nedenfor
order: 660                        # kuratert rekkefølge (nr × 10, sub: 6A=61, 6C3a=631)
priority: normal                  # normal | prioritert
tags: []                          # [domene-tag] | []
deps: []                          # ["18","60"] — nr-strenger til avhengige todos
claimed_by: null                  # branch/worktree som jobber med den (ADVISORY i MVP)
plan: null                        # tasks/plans/todo-NN-slug.md (settes når planned/reviewed)
---
```

### Status-enum

| Verdi | Betyr |
|---|---|
| `open` | Klar for planlegging — tilsvarer `[ ] Gjennomført` uten plan |
| `reviewed` | Plan skrevet og godkjent, klar for `/todo-execute` |
| `in_progress` | `/todo-execute` er startet |
| `done` | Ferdig — flyttes til `tasks/todo_archive.md` |
| `deferred` | Utsatt til videre — tilsvarer `[~]`. `deferred` + `tags: [forslag]` = u-triagert grooming-forslag (se `docs/orchestration-loop.md`) |
| `split` | Overordnet container splittet i sub-todos |

### Tagging

- `[domene-tag]` — valgfri tag som grupperer todos rundt et avgrenset domene/delsystem
  (erstatt med prosjektets egne domene-tags). Todos uten tag = generelle app-features.
- `[forslag]` — u-triagert grooming-forslag (universell; brukes av grooming-flyten).

### Regler

- **`nr` er alltid string** — håndterer sammensatte IDer som `6A`, `6C3a`.
- **`order`** bevarer kuratert rekkefølge: heltall. Regel: enkle tall `nr × 10` (todo-8 → 80, todo-66 → 660). 6-serien: `6 + alfabetisk posisjon` (A=1…H=8) → 61–68 (6A=61, 6H=68). Siffer-sub: `6C3 = 63` (ingen videre multiplikasjon).
- **`deps`-gating:** `/todo-execute` verifiserer at alle `deps`-todos har `status: done` FØR start.
- **`claimed_by`** er advisory i MVP — TOCTOU-race er mulig. Atomisk lås hører til loopen (egen spec).
- **ALDRI** committ en aggregert indeksfil som aggregerer status fra alle todos — det gjenskaper konflikt-fellen. Status leses on-demand via glob + frontmatter.
- **Slug-konsistens:** bruk samme slug i `todos/todo-NN-slug.md`, `plans/todo-NN-slug.md` og branches.

---

## Opplisting (glob + frontmatter)

```bash
# Vis alle aktive todos sortert på order (zsh-kompatibel):
for f in tasks/todos/todo-*.md; do
  nr=$(grep '^nr:' "$f" | sed 's/nr: *"\(.*\)"/\1/')
  st=$(grep '^status:' "$f" | awk '{print $2}')
  title=$(grep '^title:' "$f" | sed 's/title: *"\(.*\)"/\1/')
  order=$(grep '^order:' "$f" | awk '{print $2}')
  echo "$order|$nr|$st|$title"
done | sort -t'|' -k1,1n | awk -F'|' '{printf "TODO %-6s %-12s %s\n", $2, $3, $4}'
```

Ikke bruk variabelnavnet `status` i shell-løkker — det er read-only i zsh. Bruk `st`.

## Deps-gating

```bash
# Sjekk at alle deps for en todo er done (zsh-kompatibel):
# deps_array er et space-separert liste av nr-strenger, f.eks. "6D 6F"
# OBS: nr-strenger i deps er uppercase (6D, 6F), men filnavn er lowercase (todo-6d-...).
# Bruk `tr '[:upper:]' '[:lower:]'` — IKKE `${dep,,}` (bash-only, virker ikke i zsh).
for dep in $deps_array; do
  dep_lower=$(echo "$dep" | tr '[:upper:]' '[:lower:]')
  f=$(ls tasks/todos/todo-${dep_lower}-*.md 2>/dev/null | head -1)
  if [ -n "$f" ]; then
    s=$(grep '^status:' "$f" | awk '{print $2}')
    if [ "$s" != "done" ]; then
      echo "BLOKKERT: dep $dep har status $s"
    fi
  fi
  # Fil ikke funnet = todo er done og arkivert (done-todos slettes fra tasks/todos/)
done
```

**Regel:** Fil ikke funnet ⟹ antatt done (arkivert). Done todos slettes fra `tasks/todos/` av `/todo-done`.

Commands (`/start`, `/status`, `/todo-execute`, `/todo-done`) bruker glob + frontmatter-lesing.
Se CLAUDE.md for kanonisk dokumentasjon av kommando-protokollen.
