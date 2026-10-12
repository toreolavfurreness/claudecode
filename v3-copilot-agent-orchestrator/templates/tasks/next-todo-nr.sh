#!/usr/bin/env bash
# Neste ledige todo-nummer for /todo-new. Skriver nummeret på stdout, kildene på stderr.
# Bruk: bash tasks/next-todo-nr.sh [--base <branch>]
# Nummeret er global nøkkel på tvers av tasks/todos/, tasks/todo_archive.md OG åpne PR-er
# (tasks/todos/README.md, kantbærende felt pkt. 4). Leser origin/<base>, ikke arbeidskopien,
# så en utdatert lokal checkout gir ikke et brukt nummer. Exit 1 hvis en kilde ikke kan leses.
set -u
BASE="{{BASE_BRANCH}}"
while [ $# -gt 0 ]; do
  case "$1" in
    --base) BASE="$2"; shift 2 ;;
    *) echo "ukjent argument: $1" >&2; exit 2 ;;
  esac
done
GH="${GH:-gh}"  # overstyres i tasks/test-next-todo-nr.sh
max_of() { grep -oE '^[0-9]+' | sort -n | tail -1; }

git fetch -q origin "$BASE" 2>/dev/null || { echo "FEIL: git fetch origin $BASE" >&2; exit 1; }
REF="origin/$BASE"

todos=$(git grep -h '^nr:' "$REF" -- 'tasks/todos/todo-*.md' 2>/dev/null | sed 's/^nr: *//' | tr -d "\"'" | max_of)
archive=$(git show "$REF:tasks/todo_archive.md" 2>/dev/null | sed -n 's/^## TODO \([0-9][0-9A-Za-z]*\).*/\1/p' | max_of)
[ -n "$todos" ] || { echo "FEIL: fant ingen nr: i tasks/todos/ på $REF" >&2; exit 1; }
[ -n "$archive" ] || { echo "FEIL: fant ingen «## TODO N» i tasks/todo_archive.md på $REF" >&2; exit 1; }

# Åpne PR-er: todo-filer de legger til, og «TODO N» i tittelen. Feil i gh er FEIL; null treff er lov.
if ! prs=$("$GH" pr list --state open --limit 200 --json title,files \
  --jq '.[] | (.title, (.files[].path))' 2>/dev/null); then
  echo "FEIL: gh pr list (åpne PR-er kan holde et nummer)" >&2; exit 1
fi
pr=$(printf '%s\n' "$prs" | grep -oE 'tasks/todos/todo-[0-9]+|TODO [0-9]+' | grep -oE '[0-9]+$' | max_of)

echo "tasks/todos: ${todos} · arkiv: ${archive} · åpne PR-er: ${pr:-(ingen)}" >&2
printf '%s\n' "$todos" "$archive" "${pr:-0}" | sort -n | tail -1 | awk '{print $1 + 1}'
