#!/usr/bin/env bash
# Drift-vakt: har v3-agent-orchestrator/ endret seg siden v3-copilot-agent-orchestrator/ sist ble synket?
#
#   bash .github/kit-port/check-drift.sh [REF]     (REF = commit å sammenligne mot, standard HEAD)
#
# Leser `synket-mot: <sha>` fra v3-copilot-agent-orchestrator/KIT-SYNC og lister filene under
# v3-agent-orchestrator/ som er endret mellom den commiten og REF.
#   exit 0 = i synk
#   exit 1 = drift (fillista og commitene står på stdout)
#   exit 2 = kan ikke måles (KIT-SYNC mangler, ugyldig sha, eller historikken er for grunn)
# Krever full historikk (actions/checkout med fetch-depth: 0).
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "IKKE MÅLT: ikke et git-repo"; exit 2; }
cd "$ROOT" || exit 2
REF="${1:-HEAD}"
SRC="v3-agent-orchestrator"
SYNC_FILE="v3-copilot-agent-orchestrator/KIT-SYNC"

[ -f "$SYNC_FILE" ] || { echo "IKKE MÅLT: $SYNC_FILE mangler"; exit 2; }
SHA="$(sed -n 's/^synket-mot:[[:space:]]*\([0-9a-f]\{7,40\}\)[[:space:]]*$/\1/p' "$SYNC_FILE" | head -1)"
[ -n "$SHA" ] || { echo "IKKE MÅLT: fant ingen gyldig 'synket-mot: <sha>' i $SYNC_FILE"; exit 2; }
git cat-file -e "$SHA^{commit}" 2>/dev/null || {
  echo "IKKE MÅLT: commit $SHA finnes ikke lokalt (grunn klone? bruk fetch-depth: 0)"; exit 2; }
git merge-base --is-ancestor "$SHA" "$REF" 2>/dev/null || {
  echo "IKKE MÅLT: $SHA er ikke en forfar av $REF"; exit 2; }

FILES="$(git diff --name-only "$SHA" "$REF" -- "$SRC/")"
if [ -z "$FILES" ]; then
  echo "I SYNK: $SRC/ er uendret siden $(git rev-parse --short "$SHA")."
  exit 0
fi

N="$(printf '%s\n' "$FILES" | grep -c .)"
echo "DRIFT: $N fil(er) i $SRC/ er endret siden Copilot-kitet sist ble synket ($(git rev-parse --short "$SHA"))."
echo
echo "Commits:"
git log --format='  %h %ad %s' --date=short "$SHA..$REF" -- "$SRC/"
echo
echo "Filer:"
printf '%s\n' "$FILES" | sed 's/^/  /'
echo
echo "Port endringene etter .github/kit-port/PORT-RULES.md og oppdater synket-mot i $SYNC_FILE."
exit 1
