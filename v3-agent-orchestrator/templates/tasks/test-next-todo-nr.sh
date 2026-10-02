#!/usr/bin/env bash
# Sjekk for tasks/next-todo-nr.sh mot et engangs-repo med falsk gh. Kjør: bash tasks/test-next-todo-nr.sh
set -u
SCRIPT="$(cd "$(dirname "$0")" && pwd)/next-todo-nr.sh"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
fail=0
check() { if [ "$2" = "$3" ]; then echo "ok   $1"; else echo "RØD  $1: fikk «$2», ventet «$3»"; fail=1; fi; }

git init -q --bare "$T/origin.git"
git clone -q "$T/origin.git" "$T/w" 2>/dev/null
cd "$T/w" && git checkout -q -b dev
mkdir -p tasks/todos
printf -- '---\nnr: "12A"\n---\n' > tasks/todos/todo-12a-x.md
printf -- '---\nnr: "9"\n---\n' > tasks/todos/todo-9-y.md
printf '## TODO 40 — z (ferdig)\n## TODO 7B — w\n' > tasks/todo_archive.md
git add -A && git -c user.name=t -c user.email=t@t commit -qm init && git push -q origin dev

printf '#!/bin/sh\necho "fix: noe"\n' > "$T/gh-none"
printf '#!/bin/sh\necho "TODO 44 — tittel"\necho tasks/todos/todo-41-ny.md\n' > "$T/gh-pr"
printf '#!/bin/sh\nexit 1\n' > "$T/gh-fail"
chmod +x "$T"/gh-*

check "arkivet er høyest" "$(GH="$T/gh-none" bash "$SCRIPT" --base dev 2>/dev/null)" "41"
check "åpen PR holder et nummer" "$(GH="$T/gh-pr" bash "$SCRIPT" --base dev 2>/dev/null)" "45"
GH="$T/gh-fail" bash "$SCRIPT" --base dev >/dev/null 2>&1; check "gh-feil gir exit 1" "$?" "1"
: > tasks/todo_archive.md && git -c user.name=t -c user.email=t@t commit -qam tom && git push -q origin dev
GH="$T/gh-none" bash "$SCRIPT" --base dev >/dev/null 2>&1; check "tomt arkiv gir exit 1" "$?" "1"
exit $fail
