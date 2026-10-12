#!/usr/bin/env bash
# Finnes det en nyere versjon av kitet enn den som ligger i dette repoet?
#
#   bash scripts/check-kit-upgrade.sh [REF]     (REF i kit-repoet, standard main)
#
# Leser kit-repo, kit-path og kit-commit fra org/KIT-VERSION, henter historikken til kit-path fra
# kit-repoet (uten filinnhold) og lister commits som endrer kitet etter kit-commit.
#   exit 0 = oppdatert, 1 = ny versjon finnes (commitene på stdout), 2 = kan ikke måles.
set -uo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" || exit 2
REF="${1:-main}"
F=org/KIT-VERSION
[ -f "$F" ] || { echo "IKKE MÅLT: $F mangler"; exit 2; }
val() { sed -n "s/^$1:[[:space:]]*//p" "$F" | head -1; }
REPO="$(val kit-repo)"; KPATH="$(val kit-path)"; CUR="$(val kit-commit)"
[ -n "$REPO" ] && [ -n "$KPATH" ] || { echo "IKKE MÅLT: kit-repo eller kit-path mangler i $F"; exit 2; }
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
git clone -q --filter=blob:none --no-checkout --branch "$REF" "$REPO" "$TMP/kit" 2>"$TMP/err" \
  || { echo "IKKE MÅLT: kunne ikke hente $REPO ($REF): $(tail -1 "$TMP/err")"; exit 2; }
LATEST="$(git -C "$TMP/kit" log -1 --format=%H -- "$KPATH/")"
[ -n "$LATEST" ] || { echo "IKKE MÅLT: fant ingen commits for $KPATH/ i $REPO"; exit 2; }
if git -C "$TMP/kit" cat-file -e "$CUR^{commit}" 2>/dev/null; then
  NEWER="$(git -C "$TMP/kit" log --format='  %h %ad %s' --date=short "$CUR..origin/$REF" -- "$KPATH/")"
  if [ -z "$NEWER" ]; then
    echo "OPPDATERT: ingen endringer i $KPATH/ etter ${CUR:0:7}."
    exit 0
  fi
  echo "NY VERSJON: kitet i $REPO har endringer etter ${CUR:0:7} (siste: ${LATEST:0:7})."
  echo
  printf '%s\n' "$NEWER"
else
  echo "NY VERSJON: kit-commit «$CUR» er ukjent i $REPO — kan ikke se hva som er tatt inn (siste: ${LATEST:0:7})."
  echo
  git -C "$TMP/kit" log -10 --format='  %h %ad %s' --date=short -- "$KPATH/"
fi
echo
echo "Oppgrader med: bash scripts/upgrade-kit.sh $REF"
exit 1
