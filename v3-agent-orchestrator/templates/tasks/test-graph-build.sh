#!/usr/bin/env bash
# Sjekk for `tasks/graph-build.py --check-todo`, `--lint` og doc-nodene (`graph-query.py --docs`). Kjør fra repo-roten: bash tasks/test-graph-build.sh
set -u
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
ok=0; total=0

# todo <navn> <ekstra frontmatter-linjer> <brødtekst>
todo() { printf -- '---\nnr: "9"\n%s---\n\n%s\n' "$2" "$3" > "$T/$1.md"; }
# check <navn> <ventet exit> <ventet tekst i stderr, tom = stille> <fil> [fil …]
check() {
  local name=$1 want=$2 text=$3 err rc; shift 3
  err=$(python3 tasks/graph-build.py --check-todo "$@" 2>&1 >/dev/null); rc=$?
  total=$((total + 1))
  if [ "$rc" = "$want" ] && { if [ -n "$text" ]; then printf '%s' "$err" | grep -qF -- "$text"; else [ -z "$err" ]; fi; }; then
    echo "ok   $name"; ok=$((ok + 1))
  else
    echo "RØD  $name: exit $rc (ventet $want), stderr «${err}»"
  fi
}

FIL='Endrer `tasks/graph-build.py`.'
todo c1 '' "$FIL"
todo c2 $'files: []\n' "$FIL"
todo c3 $'files:\n  - tasks/graph-build.py\n' "$FIL"
todo c4 '' 'Lukker BUG-001.'
todo c5 $'bugs: ["BUG-001"]\n' 'Lukker BUG-001.'
todo c6 '' 'Ingen omtale.'
todo c7 $'pr: ["1"]\n' 'Ingen omtale.'

check "C1 fil navngitt, files mangler" 1 "files mangler" "$T/c1.md"
check "C2 files: [] er lovlig svar" 0 "" "$T/c2.md"
check "C3 files: i blokkform" 0 "" "$T/c3.md"
check "C4 bug navngitt, bugs mangler" 1 "bugs mangler" "$T/c4.md"
check "C5 bugs: satt" 0 "" "$T/c5.md"
check "C6 ingen omtale, ingen felt" 0 "" "$T/c6.md"
check "C7 pr er strøket" 1 "strøket" "$T/c7.md"
check "C8 to filer, én rød" 1 "c1.md: files mangler" "$T/c6.md" "$T/c1.md"
# C8, andre halvdel: stderr navngir bare den røde fila.
total=$((total + 1))
if python3 tasks/graph-build.py --check-todo "$T/c6.md" "$T/c1.md" 2>&1 >/dev/null | grep -qF 'c6.md'; then
  echo "RØD  C8 den grønne fila er navngitt i stderr"
else
  echo "ok   C8 bare den røde fila er navngitt"; ok=$((ok + 1))
fi

# --lint. Hver fixture er et eget git-repo; skriptet kalles med absolutt sti derfra.
S=$PWD/tasks/graph-build.py
# ft <filnavn uten .md> <nr> <deps-innhold> <status>
ft() { printf -- '---\nnr: "%s"\ndeps: [%s]\ntags: [forslag]\nstatus: %s\n---\n' "$2" "$3" "$4" > "$R/tasks/todos/$1.md"; }
g() { git -C "$R" -c user.name=t -c user.email=t@example.invalid -c commit.gpgsign=false "$@"; }
# ci <dato>: commit alt, datert kl. 12:00
ci() { g add -A && GIT_AUTHOR_DATE="$1T12:00:00" GIT_COMMITTER_DATE="$1T12:00:00" g commit -qm x; }

R=$T/l1; mkdir -p "$R/tasks/todos" "$R/tasks/followups"; git init -q "$R"
ft todo-1-a 1 '"2", "99"' deferred
ft todo-4-x 4 '' deferred
ft todo-5-e 5 '' open
printf '## TODO 3 — x\n' > "$R/tasks/todo_archive.md"
printf 'Gjelder TODO 1.\n' > "$R/tasks/followups/a.md"
printf 'Gjelder TODO 3.\n' > "$R/tasks/followups/b.md"
printf 'Ingen eier.\n' > "$R/tasks/followups/c.md"
ci 2020-01-01
g mv tasks/todos/todo-4-x.md tasks/todos/todo-4-d.md; ci 2020-02-01
ft todo-2-b 2 '"3"' deferred; ci "$(date +%F)"
out=$(cd "$R" && python3 "$S" --lint); rc=$?
total=$((total + 1))
if [ "$rc" = 0 ] && [ "$(printf '%s\n' "$out" | head -1)" = 'hygiene=cf_orphans:2,deps_dangling:1,forslag_stale:2' ] \
  && printf '%s\n' "$out" | grep -qxF 'forslag_stale tasks/todos/todo-1-a.md 2020-01-01' \
  && printf '%s\n' "$out" | grep -qxF 'forslag_stale tasks/todos/todo-4-d.md 2020-02-01' \
  && printf '%s\n' "$out" | grep -qxF 'deps_dangling todo:1 -> todo:99' \
  && ! printf '%s\n' "$out" | grep -qE '^forslag_stale .*todo-(2-b|5-e)\.md|^cf_orphan '; then
  echo "ok   L1 --lint teller klassene"; ok=$((ok + 1))
else
  echo "RØD  L1 --lint teller klassene: exit $rc, utdata «${out}»"
fi

R=$T/l2; mkdir -p "$R/tasks/todos"; git init -q "$R"
ft todo-1-a 1 '' deferred
out=$(cd "$R" && python3 "$S" --lint); rc=$?
total=$((total + 1))
if [ "$rc" = 0 ] && printf '%s\n' "$out" | head -1 | grep -q 'forslag_stale:n/a$'; then
  echo "ok   L2 --lint uten git-historikk gir n/a"; ok=$((ok + 1))
else
  echo "RØD  L2 --lint uten git-historikk gir n/a: exit $rc, utdata «${out}»"
fi

# doc:-noder. D-radene går mot et fixture-repo, P1 mot det ekte repoet.
R=$T/d; mkdir -p "$R/lib" "$R/tasks" "$R/docs/superpowers"; git init -q "$R"
: > "$R/lib/x.ts"; : > "$R/tasks/todo_archive.md"
printf '## S\nTODO 7\n' > "$R/docs/superpowers/s.md"
printf '%s\n' 'Ingress om `lib/x.ts`.' '## A' 'Se `lib/x.ts`.' '### B' 'TODO 12' '```' '## Fake' 'TODO 99' '```' '### C' 'Bare tekst.' > "$R/docs/a.md"
g add -A
(cd "$R" && python3 "$S") > "$T/d.json" 2>/dev/null
python3 "$S" > "$T/p.json" 2>/dev/null
# py <navn> <graf> <python-uttrykk over E (kanter) og N (noder)>
py() {
  total=$((total + 1))
  if python3 -c 'import json, sys
g = json.load(open(sys.argv[1])); E = [(e["source"], e["type"], e["target"]) for e in g["edges"]]; N = g["nodes"]
sys.exit(0 if eval(sys.argv[2]) else 1)' "$2" "$3" 2>/dev/null; then
    echo "ok   $1"; ok=$((ok + 1))
  else
    echo "RØD  $1"
  fi
}
py "D1 seksjon med sti gir documents-kant" "$T/d.json" '("doc:docs/a.md#A", "documents", "file:lib/x.ts") in E'
py "D2 seksjon uten sti gir ingen documents-kant" "$T/d.json" 'E and not [e for e in E if e[0] == "doc:docs/a.md#B" and e[1] == "documents"]'
py "D3 overskrift i kodegjerde er ikke en node" "$T/d.json" 'E and "doc:docs/a.md#Fake" not in N["doc"]'
py "D4 docs/superpowers leses ikke" "$T/d.json" 'E and not [e for e in E if e[0].startswith("doc:docs/superpowers/")]'
py "D5 TODO-referanse gir mentions-kant" "$T/d.json" '("doc:docs/a.md#B", "mentions", "todo:12") in E'
py "D6 ingressen gir ingen kant" "$T/d.json" 'len([e for e in E if e[1:] == ("documents", "file:lib/x.ts")]) == 1'
out=$(cd "$R" && python3 "${S%build.py}query.py" --docs lib/x.ts ukjent.ts 2>/dev/null); rc=$?
total=$((total + 1))
if [ "$rc" = 0 ] && [ "$out" = 'docs/a.md#A' ]; then
  echo "ok   D7 --docs skriver seksjonen, ukjent fil er ikke en feil"; ok=$((ok + 1))
else
  echo "RØD  D7 --docs: exit $rc, utdata «${out}»"
fi
py "P1 hver documents-kant står i kildefila" "$T/p.json" '(lambda D: D and all(t[5:].rsplit("/", 1)[-1] in open(s[4:].split("#", 1)[0], encoding="utf-8").read() for s, _, t in D))([e for e in E if e[1] == "documents"])'

echo "test-graph-build: $ok/$total OK"
# Gulvet: 11 uten doc-noder (C1–C8 med to halvdeler, L1, L2) + 8 nye (D1–D7, P1).
[ "$ok" = "$total" ] && [ "$total" -ge $((11 + 8)) ]
