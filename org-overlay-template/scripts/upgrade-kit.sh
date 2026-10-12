#!/usr/bin/env bash
# Erstatter kit-mappa med en ny versjon fra kit-repoet og oppdaterer org/KIT-VERSION.
#
#   bash scripts/upgrade-kit.sh [REF]          (REF i kit-repoet, standard main)
#
# Kit-mappa skal aldri redigeres i dette repoet; derfor kan den byttes ut i sin helhet.
# Det eneste som bevares, er prosjektets loop.config.yaml inne i kit-mappa.
# Kjør på en egen branch, kjør /setup etterpå, og la endringen gå gjennom en vanlig PR.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
REF="${1:-main}"
F=org/KIT-VERSION
val() { sed -n "s/^$1:[[:space:]]*//p" "$F" | head -1; }
REPO="$(val kit-repo)"; KPATH="$(val kit-path)"
[ -n "$(git status --porcelain -- "$KPATH" ":!$KPATH/loop.config.yaml" "$F")" ] && { echo "FEIL: $KPATH/ (utenom loop.config.yaml) eller $F har ucommittede endringer"; exit 1; }
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
git clone -q --depth 1 --branch "$REF" "$REPO" "$TMP/kit"
NEW="$(git -C "$TMP/kit" log -1 --format=%H)"
[ -d "$TMP/kit/$KPATH" ] || { echo "FEIL: $KPATH/ finnes ikke i $REPO ($REF)"; exit 1; }
CFG="$KPATH/loop.config.yaml"
[ -f "$CFG" ] && cp "$CFG" "$TMP/loop.config.yaml"
rm -rf "$KPATH" && cp -R "$TMP/kit/$KPATH" "$KPATH"
[ -f "$TMP/loop.config.yaml" ] && cp "$TMP/loop.config.yaml" "$CFG"
sed -i.bak "s/^kit-commit:.*/kit-commit: $NEW/" "$F" && rm -f "$F.bak"
echo "Kitet er oppdatert til ${NEW:0:7}."
echo "Neste: sammenlign $KPATH/loop.config.example.yaml med $CFG (nye nøkler?), kjør"
echo "bash scripts/apply-org-config.sh, kjør /setup i en ny Copilot-sesjon, og lag en PR."
