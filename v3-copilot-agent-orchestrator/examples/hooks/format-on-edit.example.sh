#!/usr/bin/env bash
# postToolUse-hook: formaterer den ene redigerte fila med repoets egen, pinnede Prettier.
#
# Registrering: kopier til .github/hooks/scripts/format-on-edit.sh og legg den i prosjektets EGEN
# hook-fil i .github/hooks/ (f.eks. .github/hooks/project.json) — ikke i loop-guards.json, som
# /setup eier og overskriver:
#   { "version": 1, "hooks": { "postToolUse": [
#       { "type": "command", "bash": "bash .github/hooks/scripts/format-on-edit.sh", "cwd": ".", "timeoutSec": 10 } ] } }
# Copilot-hooks har ingen matcher: skriptet filtrerer selv på fil-redigerende verktøy
# (edit, create, apply_patch, str_replace_editor) og leser filstien fra toolArgs
# (.path // .file_path // .filePath; toolArgs kan være JSON-streng eller objekt).
#
# Atferd: blokkerer aldri (alltid exit 0). Prettier avgjør selv hva som dekkes (--ignore-unknown,
# .prettierignore, .gitignore), så dekningen er lik `prettier --check .`. Filer utenfor dette repoet
# (annen git-common-dir) røres ikke. Ble fila endret, får agenten beskjed via additionalContext og må
# lese fila på nytt før neste redigering.
#
# Kjører en typesjekk-hook på samme hendelse, går de parallelt: linjenumre i en tsc-melding kan da
# vise til enten den uformaterte eller den formaterte fila. Prettier kan også endre INNHOLD i markdown
# (f.eks. `_*` i et kodespenn tolket som emfase), derfor ber meldingen for .md-filer om en diff-sjekk.

set -uo pipefail
INPUT=$(cat)
TOOL=$(printf '%s' "$INPUT" | /usr/bin/jq -r '.toolName // ""' 2>/dev/null) || exit 0
case "$TOOL" in edit|create|apply_patch|str_replace_editor) ;; *) exit 0 ;; esac
FILE=$(printf '%s' "$INPUT" | /usr/bin/jq -r '.toolArgs | if type=="string" then (fromjson? // {}) else (. // {}) end | .path // .file_path // .filePath // ""' 2>/dev/null) || exit 0
CWD=$(printf '%s' "$INPUT" | /usr/bin/jq -r '.cwd // ""' 2>/dev/null) || CWD=""
case "$FILE" in ""|/*) ;; *) [ -n "$CWD" ] && FILE="$CWD/$FILE" ;; esac
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
/usr/bin/jq -cn --arg f "$FILE" '{additionalContext:("format-on-edit: Prettier reformaterte " + $f + ". Les fila på nytt før neste redigering." + (if ($f | endswith(".md")) then " Prettier kan endre innhold i markdown: se over diffen for fila." else "" end))}'
exit 0
