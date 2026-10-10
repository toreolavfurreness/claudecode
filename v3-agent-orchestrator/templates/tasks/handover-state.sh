#!/usr/bin/env bash
# målt tilstand for /handover. Skriver markdown på stdout; vurderer ingenting.
# Bruk: bash tasks/handover-state.sh --since <YYYY-MM-DDTHH:MM> [--base <branch>]
# Exit 1 hvis en måling feilet (seksjonen viser da «FEIL: …») — en tom seksjon er «(ingen)», aldri blank.
set -u
SINCE="" BASE="{{BASE_BRANCH}}"
while [ $# -gt 0 ]; do
  case "$1" in
    --since) SINCE="$2"; shift 2 ;;
    --base)  BASE="$2"; shift 2 ;;
    *) echo "ukjent argument: $1" >&2; exit 2 ;;
  esac
done
[ -n "$SINCE" ] || { echo "mangler --since <YYYY-MM-DDTHH:MM>" >&2; exit 2; }
# --since er lokal tid; GitHub-søket tolker en dato uten sone som UTC. Legg på lokal offset (+02:00).
TZ_OFF=$(date +%z | sed -E 's/([+-][0-9]{2})([0-9]{2})/\1:\2/')
RC=0
fail() { echo "FEIL: $1"; RC=1; }
or_none() { local out; out=$(cat); [ -n "$out" ] && echo "$out" || echo "(ingen)"; }

git fetch -q origin 2>/dev/null || fail "git fetch origin"
MAIN=$(git worktree list --porcelain | sed -n '1s/^worktree //p')

echo "### origin/$BASE"
git log -1 --format='`%h` %s (%ci)' "origin/$BASE" 2>/dev/null || fail "origin/$BASE finnes ikke"

echo; echo "### Hovedsjekkout ($MAIN)"
if head=$(git -C "$MAIN" rev-parse --short HEAD 2>/dev/null); then
  behind=$(git -C "$MAIN" rev-list --count "HEAD..origin/$BASE")
  echo "- HEAD \`$head\` på \`$(git -C "$MAIN" branch --show-current)\`, $behind commits bak origin/$BASE"
  git -C "$MAIN" status --porcelain | sed 's/^/- skitten: /' | or_none
else fail "kan ikke lese $MAIN"; fi

echo; echo "### node_modules (hovedsjekkout)"
[ -f "$MAIN/node_modules/.package-lock.json" ] && echo "installert" || echo "MANGLER — kjør npm ci (pausepunkt i /run-loop-preflight)"

echo; echo "### Worktrees"
git worktree list | tail -n +2 | sed 's/^/- /' | or_none

echo; echo "### Claims"
for f in "$MAIN"/tasks/todos/todo-*.md; do
  st=$(sed -n 's/^status: *//p' "$f" | head -1); cb=$(sed -n 's/^claimed_by: *//p' "$f" | head -1 | tr -d "\"'")
  { [ "$st" = in_progress ] || { [ -n "$cb" ] && [ "$cb" != null ]; }; } && echo "- $(basename "$f") (status=$st, claimed_by=$cb)"
done | or_none

echo; echo "### Release"
if [ -f "$MAIN/tasks/release.py" ]; then
  (cd "$MAIN" && python3 tasks/release.py status 2>&1) || fail "release.py status"
else echo "(ingen release.py)"; fi

echo; echo "### Åpne PR-er mot $BASE"
# Fang ut-data først: `gh … | or_none` ville gitt «(ingen)» også når gh feiler.
if out=$(gh pr list --base "$BASE" --state open --json number,title -q '.[] | "- #\(.number) \(.title)"' 2>&1); then
  echo "$out" | or_none; else fail "gh pr list (open): $out"; fi

echo; echo "### Merget mot $BASE siden $SINCE"
if out=$(gh pr list --base "$BASE" --state merged --search "merged:>=${SINCE}${TZ_OFF}" --limit 100 \
    --json number,title -q '.[] | "- #\(.number) \(.title)"' 2>&1); then
  echo "$out" | or_none; else fail "gh pr list (merged): $out"; fi

echo; echo "### Decision-log siden $SINCE"
LOG="$MAIN/docs/superpowers/loop/decision-log.md"
git show "origin/$BASE:docs/superpowers/loop/decision-log.md" 2>/dev/null \
  | awk -v s="${SINCE/T/ }" '/^### [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}/ { if (substr($0,5,16) >= s) print "- " substr($0,5) }' \
  | or_none
[ -f "$LOG" ] || echo "(merk: $LOG finnes ikke i hovedsjekkouten)"

echo; echo "### Forrige overlevering"
# Sist LAGT TIL, ikke alfabetisk siste («formiddag» < «morgen»).
git log "origin/$BASE" --diff-filter=A --format= --name-only -- 'docs/superpowers/loop/handover-*' | head -1 | or_none

exit $RC
