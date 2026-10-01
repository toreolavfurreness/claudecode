#!/bin/sh
# {{PROJECT_NAME}} — SessionStart-hook (matcher "compact"), generert av /setup når
# hooks.compaction_checkpoint er på.
#
# Legger koordinatorens egen sjekkpunkt-fil, tasks/.loop-state/checkpoint-<session_id>.md, inn i
# konteksten rett etter en komprimering. Hvordan fila skrives: docs/superpowers/loop/steps/0c-sjekkpunkt.md.
#
# Filtrene kjøres i denne rekkefølgen:
#   1. jq mangler → én linje i precompact.log, exit 0. Uten loggraden degraderer hooken uten spor.
#   2. agent_id er satt → exit 0. En subagent skal ikke få koordinatorens sjekkpunkt.
#   3. session_id må matche ^[A-Za-z0-9_-]{8,64}$, ellers exit 0. Stien under bygges av inndata.
#   4. Ingen sjekkpunkt-fil → exit 0 uten output.
#
# Maks 400 linjer injiseres. JSON-en bygges med `jq -R -s` fra rå tekst. printf-interpolasjon av
# innholdet inn i en JSON-streng knekker på ekte innhold (anførselstegn, tab, kontrolltegn).

DIR="$CLAUDE_PROJECT_DIR/tasks/.loop-state"
LOG="$DIR/precompact.log"

if ! command -v jq >/dev/null 2>&1; then
  mkdir -p "$DIR"
  printf '%s %s jq: command not found\n' "sessionstart-checkpoint.sh" "$(date -u +%FT%TZ)" >> "$LOG"
  exit 0
fi

input="$(cat)"

agent_id="$(printf '%s' "$input" | jq -r '.agent_id // empty')"
[ -n "$agent_id" ] && exit 0

sid="$(printf '%s' "$input" | jq -r '.session_id // empty')"
len=${#sid}
if [ "$len" -lt 8 ] || [ "$len" -gt 64 ]; then
  exit 0
fi
case "$sid" in
  *[!A-Za-z0-9_-]*) exit 0 ;;
esac

f="$DIR/checkpoint-$sid.md"
[ -f "$f" ] || exit 0

ctx="$(printf 'KOORDINATOR-CHECKPOINT GJENOPPRETTET (%s)\n' "$sid"
       head -n 400 "$f"
       if [ "$(wc -l < "$f")" -gt 400 ]; then
         printf '[AVKORTET etter 400 linjer — les %s]\n' "$f"
       fi)"
printf '%s' "$ctx" | jq -R -s '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:.}}'
