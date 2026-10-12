#!/usr/bin/env bash
# {{PROJECT_NAME}} — postToolUse-hook: kjører typesjekk etter redigering av
# kildefiler med en av filendelsene i hooks.typecheck_on_edit_extensions.
#
# Fanger typefeil med en gang i stedet for først i CI/bygget.
#
# Atferd: ikke-blokkerende, alltid exit 0. Typefeil rapporteres tilbake til agenten som
# kontekst: {"additionalContext":"…"} på stdout. Hele prosjektet typesjekkes — ikke bare fila —
# fordi en typesjekker med prosjekt-config sjelden kan sjekke enkeltfiler isolert.
#
# Copilot-hooks har ingen matcher: hooken filtrerer selv på fil-redigerende verktøy
# (edit, create, apply_patch, str_replace_editor) og leser filstien fra toolArgs
# (.path // .file_path // .filePath; for apply_patch fra patch-teksten). toolArgs kan være
# JSON-streng eller objekt. UVERIFISERT: VS Code-agenten kan bruke andre verktøynavn
# (create_file, replace_string_in_file, insert_edit_into_file, multi_replace_string_in_file) —
# de er tatt med her; et ukjent navn gir bare at sjekken hoppes over.

set -uo pipefail

[ -x /usr/bin/jq ] || exit 0
INPUT=$(cat)
TOOL=$(printf '%s' "$INPUT" | /usr/bin/jq -r '.toolName // ""' 2>/dev/null) || exit 0
ARGS=$(printf '%s' "$INPUT" | /usr/bin/jq -c '.toolArgs | if type=="string" then (fromjson? // {}) else (. // {}) end' 2>/dev/null) || exit 0
CWD=$(printf '%s' "$INPUT" | /usr/bin/jq -r '.cwd // ""' 2>/dev/null) || CWD=""

# Gate først: kjør kun for fil-redigerende verktøy på de konfigurerte filendelsene.
case "$TOOL" in
  edit|create|apply_patch|str_replace_editor|create_file|replace_string_in_file|insert_edit_into_file|multi_replace_string_in_file) ;;
  *) exit 0 ;;
esac
FILE=$(printf '%s' "$ARGS" | /usr/bin/jq -r '.path // .file_path // .filePath // ""')
if [ -z "$FILE" ]; then
  # apply_patch: første «*** Add/Update File: <sti>»-linje i patch-teksten.
  FILE=$(printf '%s' "$ARGS" | /usr/bin/jq -r '.input // .patch // ""' \
    | sed -n 's/^\*\*\* \(Add\|Update\) File: *//p' | head -1)
fi
# Relativ sti tolkes fra payloadens cwd.
case "$FILE" in
  ""|/*) ;;
  *) [ -n "$CWD" ] && FILE="$CWD/$FILE" ;;
esac
case "$FILE" in
  {{TYPECHECK_ON_EDIT_CASE}}) ;;
  *) exit 0 ;;
esac

say() { # say <tekst> — additionalContext på stdout, så exit 0
  printf '%s' "$1" | /usr/bin/jq -Rsc '{additionalContext: .}' 2>/dev/null || true
  exit 0
}

# Rot-resolusjon: utled fra DEN REDIGERTE FILENS sti, så sjekken kjører i worktreen som EIER
# fila (ikke koordinatorens/hovedsjekkutens worktree).
PROJECT_DIR=""
if [ -n "$FILE" ]; then
  PROJECT_DIR=$(git -C "$(dirname "$FILE")" rev-parse --show-toplevel 2>/dev/null || true)
fi
# Fallback når fil-sti mangler / ikke lar seg resolve.
if [ -z "${PROJECT_DIR:-}" ]; then
  PROJECT_DIR="${LOOP_PROJECT_DIR:-${CWD:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || echo ".")}}"
fi

cd "$PROJECT_DIR" || exit 0

# Avhengigheter ikke klare i DENNE worktreen → forståelig melding, ikke kryptisk modul-feil.
DEPS_MARKER="{{BOOTSTRAP_INSTALL_MARKER}}"
if [ -n "$DEPS_MARKER" ] && [ ! -e "$DEPS_MARKER" ]; then
  say "{{PROJECT_NAME}} typecheck-hook: $DEPS_MARKER mangler i $PROJECT_DIR — type-sjekk hoppet over (IKKE en type-feil).
Kjør scripts/bootstrap-worktree.sh i worktreen."
fi

TYPE_CMD=$(cat <<'CMD'
{{CMD_TYPE_CHECK}}
CMD
)

OUT=$(bash -c "$TYPE_CMD" 2>&1 </dev/null) || say "{{PROJECT_NAME}}: typesjekk fant feil etter endring i $FILE:

$(printf '%s\n' "$OUT" | head -40)"

exit 0
