#!/usr/bin/env bash
# {{PROJECT_NAME}} — regresjonsharness for sessionstart-checkpoint.sh og precompact-checkpoint.sh.
# Kjører begge hookene mot en midlertidig CLAUDE_PROJECT_DIR. Skriver "ALLE OK" når alt er grønt.
#   bash .claude/hooks/test-checkpoint-hooks.sh
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
SS="$HERE/sessionstart-checkpoint.sh"
PC="$HERE/precompact-checkpoint.sh"
command -v jq >/dev/null 2>&1 || { echo "jq mangler — harnessen trenger jq"; exit 1; }

T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
export CLAUDE_PROJECT_DIR="$T"
D="$T/tasks/.loop-state"; mkdir -p "$D"
SID="abcdef12-3456-7890-abcd-ef1234567890"
CP="$D/checkpoint-$SID.md"
FAIL=0
ok()  { echo "OK    $1"; }
bad() { echo "AVVIK $1"; FAIL=$((FAIL+1)); }
check() { if [ "$2" = "1" ]; then ok "$1"; else bad "$1"; fi; }

write_cp() {  # $1 = epoch
  printf '# Checkpoint %s\nSkrevet: 2026-10-01T10:00:00Z epoch=%s\nAktiv todo: 42\nNeste handling: "kjør §5b" \\ tab:\there æøå\n' "$SID" "$1" > "$CP"
}

# --- SessionStart ---
write_cp "$(date -u +%s)"
out="$(printf '{"session_id":"%s","agent_id":"x"}' "$SID" | sh "$SS")"
check "S1 agent_id satt → ingen output" "$([ -z "$out" ] && echo 1)"

printf 'hemmelig\n' > "$D/checkpoint-abcdefgh ijk.md"   # fila finnes — bare id-valideringen stopper den
out="$(printf '{"session_id":"abcdefgh ijk"}' | sh "$SS")"
check "S2 session_id med ulovlige tegn → ingen output" "$([ -z "$out" ] && echo 1)"

out="$(printf '{"session_id":"zzzzzzzz-missing"}' | sh "$SS")"
check "S3 ingen sjekkpunkt-fil → ingen output" "$([ -z "$out" ] && echo 1)"

out="$(printf '{"session_id":"%s"}' "$SID" | sh "$SS")"
ctx="$(printf '%s' "$out" | jq -r '.hookSpecificOutput.additionalContext' 2>/dev/null)"
ev="$(printf '%s' "$out" | jq -r '.hookSpecificOutput.hookEventName' 2>/dev/null)"
check "S4 gyldig JSON med hookEventName SessionStart" "$([ "$ev" = "SessionStart" ] && echo 1)"
check "S4 markørlinje først" "$(printf '%s' "$ctx" | head -1 | grep -q "^KOORDINATOR-CHECKPOINT GJENOPPRETTET ($SID)" && echo 1)"
check "S4 innhold ordrett (anførselstegn, backslash, tab, æøå)" "$([ "$(printf '%s' "$ctx" | tail -n +2)" = "$(cat "$CP")" ] && echo 1)"

seq 1 450 > "$CP"
out="$(printf '{"session_id":"%s"}' "$SID" | sh "$SS")"
ctx="$(printf '%s' "$out" | jq -r '.hookSpecificOutput.additionalContext')"
check "S5 >400 linjer → avkortet med henvisning" "$(printf '%s' "$ctx" | grep -q '^\[AVKORTET etter 400 linjer' && ! printf '%s' "$ctx" | grep -qx 401 && echo 1)"

# --- PreCompact ---
lastlog() { tail -1 "$D/precompact.log" 2>/dev/null; }
write_cp "$(date -u +%s)"
out="$(printf '{"session_id":"%s","trigger":"auto"}' "$SID" | sh "$PC")"
check "P1 stdout alltid tom" "$([ -z "$out" ] && echo 1)"
check "P1 fersk → FERSK i loggen" "$(lastlog | grep -q "FERSK trigger=auto session=$SID" && echo 1)"
check "P1 statuslinje lagt til i sjekkpunktet" "$(tail -1 "$CP" | grep -q '^<!-- PreCompact .* status=FERSK -->$' && echo 1)"

write_cp "$(( $(date -u +%s) - 3600 ))"
printf '{"session_id":"%s","trigger":"auto"}' "$SID" | sh "$PC" >/dev/null
check "P2 time gammel → FORELDET" "$(lastlog | grep -q 'FORELDET' && echo 1)"

printf '1\n2\n3\n4\n5\nSkrevet: x epoch=%s\n' "$(date -u +%s)" > "$CP"
printf '{"session_id":"%s","trigger":"auto"}' "$SID" | sh "$PC" >/dev/null
check "P3 Skrevet: under linje 5 → UKJENT" "$(lastlog | grep -q 'UKJENT' && echo 1)"

n="$(wc -l < "$D/precompact.log")"
printf '{"session_id":"%s","agent_id":"x"}' "$SID" | sh "$PC" >/dev/null
check "P4 agent_id satt → ingen loggrad" "$([ "$(wc -l < "$D/precompact.log")" = "$n" ] && echo 1)"

# --- jq mangler ---
out="$(printf '{"session_id":"%s"}' "$SID" | PATH=/bin /bin/sh "$SS")"
check "J1 jq mangler → ingen output, én loggrad" "$([ -z "$out" ] && lastlog | grep -q 'jq: command not found' && echo 1)"

[ "$FAIL" -eq 0 ] && echo "ALLE OK" || { echo "$FAIL AVVIK"; exit 1; }
