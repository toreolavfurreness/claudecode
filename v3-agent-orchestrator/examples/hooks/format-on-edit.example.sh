#!/usr/bin/env bash
# PostToolUse-hook: formaterer den ene redigerte fila med repoets egen, pinnede Prettier.
#
# Registrering i .claude/settings.json, under PostToolUse med matcher "Edit|Write|MultiEdit":
#   { "type": "command", "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/format-on-edit.sh\"", "timeout": 10 }
#
# Atferd: blokkerer aldri (alltid exit 0). Prettier avgjør selv hva som dekkes (--ignore-unknown,
# .prettierignore, .gitignore), så dekningen er lik `prettier --check .`. Filer utenfor dette repoet
# (annen git-common-dir) røres ikke. Ble fila endret, får agenten beskjed via additionalContext og må
# lese fila på nytt før neste Edit.
#
# Kjører en typesjekk-hook under samme matcher, går de parallelt: linjenumre i en tsc-melding kan da
# vise til enten den uformaterte eller den formaterte fila. Prettier kan også endre INNHOLD i markdown
# (f.eks. `_*` i et kodespenn tolket som emfase), derfor ber meldingen for .md-filer om en diff-sjekk.

set -uo pipefail
FILE=$(/usr/bin/jq -r '.tool_input.file_path // ""' 2>/dev/null) || exit 0
[ -f "$FILE" ] || exit 0
ROOT=$(git -C "$(dirname "$FILE")" rev-parse --show-toplevel 2>/dev/null) || exit 0
OWN=$(git -C "$(dirname "$0")" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)
THEIRS=$(git -C "$ROOT" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)
[ -n "$OWN" ] && [ "$OWN" = "$THEIRS" ] || exit 0
P="$ROOT/node_modules/.bin/prettier"
[ -x "$P" ] || exit 0
cd "$ROOT" || exit 0
BEFORE=$(cksum <"$FILE")
"$P" --write --ignore-unknown --log-level silent "$FILE" >/dev/null 2>&1 || exit 0
[ "$BEFORE" = "$(cksum <"$FILE")" ] && exit 0
/usr/bin/jq -cn --arg f "$FILE" '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:("format-on-edit: Prettier reformaterte " + $f + ". Les fila på nytt (Read) før neste Edit." + (if ($f | endswith(".md")) then " Prettier kan endre innhold i markdown: se over diffen for fila." else "" end))}}'
exit 0
