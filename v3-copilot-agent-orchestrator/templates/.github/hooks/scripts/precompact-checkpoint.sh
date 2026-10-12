#!/bin/sh
# {{PROJECT_NAME}} — preCompact-hook, generert av /setup når hooks.compaction_checkpoint er på.
#
# Logger om koordinatorens sjekkpunkt var ferskt da auto-komprimeringen startet. Håndhever aldri:
# alltid exit 0, og ALDRI noe på stdout. preCompact er bare et varsel (kan ikke påvirke
# komprimeringen); tom stdout holder det slik uansett hvordan harnessen tolker utdata.
#
# Copilot-payload: sessionId, timestamp, cwd, transcriptPath, trigger (manual|auto),
# customInstructions. Copilot-hooks har ingen matcher, så filtrene ligger her, i denne rekkefølgen:
# jq → agentId/agent_id (defensivt: preCompact-payloaden har ingen agent-identitet i dag, men en
# payload som HAR det, er en subagent og skal ikke røre koordinatorens sjekkpunkt) → trigger == auto
# → sessionId (8–64 tegn, [A-Za-z0-9_-]) → sjekkpunktfila finnes.
#
# Gjenopplesing etter komprimering er IKKE en hook: koordinatorens runbook (steg 0c) sier at
# sjekkpunktfila leses før hvert steg og når tilstanden ikke huskes.
#
# Ferskhet leses fra sjekkpunktets egen `Skrevet: <ISO> epoch=<sekunder>`-linje blant de fem første
# linjene, ikke fra mtime (en checkout eller reset fornyer mtime uten å endre innholdet). En
# `Skrevet:`-linje lenger ned teller som UKJENT, aldri FERSK.

LOOP_PROJECT_DIR="${LOOP_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
DIR="$LOOP_PROJECT_DIR/tasks/.loop-state"
LOG="$DIR/precompact.log"

if ! command -v jq >/dev/null 2>&1; then
  mkdir -p "$DIR"
  printf '%s %s jq: command not found\n' "precompact-checkpoint.sh" "$(date -u +%FT%TZ)" >> "$LOG"
  exit 0
fi

input="$(cat)"

agent_id="$(printf '%s' "$input" | jq -r '.agentId // .agent_id // empty' 2>/dev/null)"
[ -n "$agent_id" ] && exit 0

trigger="$(printf '%s' "$input" | jq -r '.trigger // empty' 2>/dev/null)"
[ "$trigger" = "auto" ] || exit 0

sid="$(printf '%s' "$input" | jq -r '.sessionId // empty' 2>/dev/null)"
len=${#sid}
if [ "$len" -lt 8 ] || [ "$len" -gt 64 ]; then
  exit 0
fi
case "$sid" in
  *[!A-Za-z0-9_-]*) exit 0 ;;
esac

f="$DIR/checkpoint-$sid.md"
[ -f "$f" ] || exit 0

epoch="$(sed -n '1,5s/^Skrevet:.*epoch=\([0-9]\{1,\}\).*/\1/p' "$f" | head -1)"
now="$(date -u +%s)"
if [ -z "$epoch" ]; then
  status="UKJENT"
else
  age=$(( now - epoch ))
  # ponytail: fast grense på 30 min; gjør den til en config-nøkkel hvis stegene dine varer lenger.
  if [ "$age" -le 1800 ]; then status="FERSK"; else status="FORELDET"; fi
fi

printf '<!-- PreCompact %s trigger=%s status=%s -->\n' "$(date -u +%FT%TZ)" "$trigger" "$status" >> "$f"
printf '%s %s %s trigger=%s session=%s\n' "precompact-checkpoint.sh" "$(date -u +%FT%TZ)" "$status" "$trigger" "$sid" >> "$LOG"
exit 0
