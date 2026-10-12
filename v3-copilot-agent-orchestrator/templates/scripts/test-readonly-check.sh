#!/usr/bin/env bash
# {{PROJECT_NAME}} — regresjonstest for scripts/readonly-check.sh. Kjøres:
#   bash scripts/test-readonly-check.sh
# Bygger et engangsrepo med en worktree under .loop-worktrees/ og måler hvert tilfelle.
# Skriver «AVVIK: 0» når alt er grønt.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
RC_SCRIPT="$HERE/readonly-check.sh"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
FAIL=0
t() { # forventet-exit beskrivelse kommando...
  local want="$1" desc="$2"; shift 2
  "$@" >"$T/out" 2>&1; local got=$?
  if [ "$got" = "$want" ]; then echo "OK    $desc"; else echo "AVVIK $desc (fikk $got, ventet $want)"; sed 's/^/      /' "$T/out"; FAIL=$((FAIL+1)); fi
}
R="$T/repo"
git init -q "$R"
git -C "$R" config user.email t@example.com; git -C "$R" config user.name t
printf 'node_modules/\n.env.local\n.loop-worktrees/\n' > "$R/.gitignore"
echo a > "$R/a.txt"; git -C "$R" add -A; git -C "$R" commit -qm seed
git -C "$R" worktree add -q -b loop/reviewer-7 "$R/.loop-worktrees/reviewer-7" HEAD
W="$R/.loop-worktrees/reviewer-7"
B=$(git -C "$W" rev-parse HEAD)
chk() { bash "$RC_SCRIPT" "$@"; }

t 0 "R1 rent tre, HEAD uendret → OK" chk "$W" "$B"
mkdir -p "$W/node_modules"; echo x > "$W/node_modules/m.js"; echo K=1 > "$W/.env.local"
t 0 "R2 ignorerte filer (avhengigheter, env-kopi) → OK" chk "$W" "$B"
echo endret > "$W/a.txt"
t 1 "R3 endret sporet fil → BRUDD" chk "$W" "$B"
git -C "$W" checkout -q -- a.txt
echo ny > "$W/ny.txt"
t 1 "R4 ny usporet fil → BRUDD" chk "$W" "$B"
mkdir -p "$W/dypt/nede"; mv "$W/ny.txt" "$W/dypt/nede/ny.txt"
t 1 "R5 ny usporet fil i ny mappe → BRUDD" chk "$W" "$B"
rm -rf "$W/dypt"
git -C "$W" rm -q a.txt
t 1 "R6 staget sletting → BRUDD" chk "$W" "$B"
git -C "$W" reset -q --hard "$B"
echo c > "$W/c.txt"; git -C "$W" add c.txt; git -C "$W" commit -qm "rollen committet"
t 1 "R7 ny commit (rent tre, HEAD flyttet) → BRUDD" chk "$W" "$B"
git -C "$W" reset -q --hard "$B"
t 0 "R8 tilbake på base → OK" chk "$W" "$B"
t 2 "R9 mangler argument → bruksfeil" chk "$W"
t 2 "R10 worktree finnes ikke → kan ikke måles" chk "$T/finnes-ikke" "$B"
t 2 "R11 ukjent base-sha → kan ikke måles" chk "$W" 0123456789abcdef0123456789abcdef01234567
mkdir -p "$W/sub"; touch "$W/sub/.keep"
t 2 "R12 undermappe i stedet for worktree-roten → kan ikke måles" chk "$W/sub" "$B"
rm -rf "$W/sub"
mkdir -p "$T/ikke-git"
t 2 "R13 mappe utenfor git → kan ikke måles" chk "$T/ikke-git" "$B"
echo "AVVIK: $FAIL"
[ "$FAIL" -eq 0 ]
