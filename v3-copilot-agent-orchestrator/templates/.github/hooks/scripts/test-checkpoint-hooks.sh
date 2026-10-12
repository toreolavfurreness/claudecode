#!/usr/bin/env bash
# {{PROJECT_NAME}} — regresjonsharness for precompact-checkpoint.sh.
# Kjører hooken mot en midlertidig LOOP_PROJECT_DIR med Copilot preCompact-payloads
# (sessionId, trigger, …). Skriver "ALLE OK" og "AVVIK: 0" når alt er grønt.
#   bash .github/hooks/scripts/test-checkpoint-hooks.sh
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
PC="$HERE/precompact-checkpoint.sh"
command -v jq >/dev/null 2>&1 || { echo "jq mangler — harnessen trenger jq"; exit 1; }

T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
export LOOP_PROJECT_DIR="$T"
D="$T/tasks/.loop-state"; mkdir -p "$D"
SID="abcdef12-3456-7890-abcd-ef1234567890"
CP="$D/checkpoint-$SID.md"
FAIL=0
ok()  { echo "OK    $1"; }
bad() { echo "AVVIK $1"; FAIL=$((FAIL+1)); }
check() { if [ "$2" = "1" ]; then ok "$1"; else bad "$1"; fi; }
pc() { # $1 = payload; stdout fra hooken
  printf '%s' "$1" | sh "$PC"
}
payload() { # $1 = sessionId, $2 = trigger, $3 = ekstra felt (valgfritt, med ledende komma)
  printf '{"sessionId":"%s","timestamp":1760000000000,"cwd":"%s","transcriptPath":"/tmp/t.jsonl","trigger":"%s","customInstructions":""%s}' "$1" "$T" "$2" "${3:-}"
}

write_cp() {  # $1 = epoch
  printf '# Checkpoint %s\nSkrevet: 2026-10-01T10:00:00Z epoch=%s\nAktiv todo: 42\nNeste handling: "kjør §5b" \\ tab:\there æøå\n' "$SID" "$1" > "$CP"
}
lastlog() { tail -1 "$D/precompact.log" 2>/dev/null; }
nlog() { if [ -f "$D/precompact.log" ]; then wc -l < "$D/precompact.log" | tr -d ' '; else echo 0; fi; }

# --- preCompact ---
write_cp "$(date -u +%s)"
out="$(pc "$(payload "$SID" auto)")"
check "P1 stdout alltid tom" "$([ -z "$out" ] && echo 1)"
check "P1 fersk → FERSK i loggen" "$(lastlog | grep -q "FERSK trigger=auto session=$SID" && echo 1)"
check "P1 statuslinje lagt til i sjekkpunktet" "$(tail -1 "$CP" | grep -q '^<!-- PreCompact .* status=FERSK -->$' && echo 1)"

write_cp "$(( $(date -u +%s) - 3600 ))"
pc "$(payload "$SID" auto)" >/dev/null
check "P2 time gammel → FORELDET" "$(lastlog | grep -q 'FORELDET' && echo 1)"

printf '1\n2\n3\n4\n5\nSkrevet: x epoch=%s\n' "$(date -u +%s)" > "$CP"
pc "$(payload "$SID" auto)" >/dev/null
check "P3 Skrevet: under linje 5 → UKJENT" "$(lastlog | grep -q 'UKJENT' && echo 1)"

n="$(nlog)"
out="$(pc "$(payload "$SID" auto ',"agentId":"x"')")"
check "P4 agentId satt (defensivt) → ingen loggrad, tom stdout" "$([ "$(nlog)" = "$n" ] && [ -z "$out" ] && echo 1)"

n="$(nlog)"
out="$(pc "$(payload "$SID" manual)")"
check "P5 trigger=manual → ingen loggrad, tom stdout" "$([ "$(nlog)" = "$n" ] && [ -z "$out" ] && echo 1)"

printf 'hemmelig\n' > "$D/checkpoint-abcdefgh ijk.md"   # fila finnes — bare id-valideringen stopper den
n="$(nlog)"
out="$(pc "$(payload "abcdefgh ijk" auto)")"
check "P6 sessionId med ulovlige tegn → ingen loggrad, tom stdout" "$([ "$(nlog)" = "$n" ] && [ -z "$out" ] && echo 1)"

n="$(nlog)"
out="$(pc "$(payload "zzzzzzzz-missing" auto)")"
check "P7 ingen sjekkpunkt-fil → ingen loggrad, tom stdout" "$([ "$(nlog)" = "$n" ] && [ -z "$out" ] && echo 1)"

n="$(nlog)"
out="$(pc '{"session_id":"'"$SID"'","trigger":"auto"}')"
check "P8 snake_case session_id (feil payloadform) → ingen loggrad" "$([ "$(nlog)" = "$n" ] && [ -z "$out" ] && echo 1)"

n="$(nlog)"
out="$(pc 'ikke-json{{{')"; rc=$?
check "P9 ugyldig JSON → ingen loggrad, tom stdout, exit 0" "$([ "$(nlog)" = "$n" ] && [ -z "$out" ] && [ "$rc" = 0 ] && echo 1)"

# --- jq mangler ---
# PATH med bare verktøyene hooken trenger utenom jq (/bin kan være en lenke til /usr/bin, som har jq).
NOJQ="$T/nojq-bin"; mkdir -p "$NOJQ"
for b in sh mkdir date printf cat sed head git; do
  p="$(command -v "$b" 2>/dev/null)" && [ -n "$p" ] && [ "${p#/}" != "$p" ] && ln -s "$p" "$NOJQ/$b"
done
out="$(printf '%s' "$(payload "$SID" auto)" | PATH="$NOJQ" "$NOJQ/sh" "$PC")"
check "J1 jq mangler → ingen output, én loggrad" "$([ -z "$out" ] && lastlog | grep -q 'jq: command not found' && echo 1)"

echo "AVVIK: $FAIL"
[ "$FAIL" -eq 0 ] && echo "ALLE OK" || { echo "$FAIL AVVIK"; exit 1; }
