#!/usr/bin/env bash
# {{PROJECT_NAME}} — PostToolUse hook: kjører typesjekk etter redigering av
# kildefiler med en av filendelsene i hooks.typecheck_on_edit_extensions.
#
# Fanger typefeil med en gang i stedet for først i CI/bygget.
#
# Atferd: ikke-blokkerende. Typefeil rapporteres tilbake til Claude som kontekst
# (exit 2 → stderr vises). Hele prosjektet typesjekkes — ikke bare fila — fordi
# en typesjekker med prosjekt-config sjelden kan sjekke enkeltfiler isolert.

set -uo pipefail

INPUT=$(cat)
TOOL=$(echo "$INPUT" | /usr/bin/jq -r '.tool_name // ""')
FILE=$(echo "$INPUT" | /usr/bin/jq -r '.tool_input.file_path // ""')
CWD=$(echo "$INPUT" | /usr/bin/jq -r '.cwd // ""')

# Gate først: kjør kun for fil-redigerende verktøy på de konfigurerte filendelsene.
case "$TOOL" in
  Edit|Write|MultiEdit|NotebookEdit) ;;
  *) exit 0 ;;
esac
case "$FILE" in
  {{TYPECHECK_ON_EDIT_CASE}}) ;;
  *) exit 0 ;;
esac

# Rot-resolusjon: utled fra DEN REDIGERTE FILENS sti, så sjekken kjører i worktreen som EIER
# fila (ikke koordinatorens/hovedsjekkutens worktree).
PROJECT_DIR=""
if [ -n "$FILE" ]; then
  PROJECT_DIR=$(git -C "$(dirname "$FILE")" rev-parse --show-toplevel 2>/dev/null || true)
fi
# Fallback når fil-sti mangler / ikke lar seg resolve.
if [ -z "${PROJECT_DIR:-}" ]; then
  PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${CWD:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || echo ".")}}"
fi

cd "$PROJECT_DIR" || exit 0

# Avhengigheter ikke klare i DENNE worktreen → forståelig melding, ikke kryptisk modul-feil.
DEPS_MARKER="{{BOOTSTRAP_INSTALL_MARKER}}"
if [ -n "$DEPS_MARKER" ] && [ ! -e "$DEPS_MARKER" ]; then
  echo "{{PROJECT_NAME}} typecheck-hook: $DEPS_MARKER mangler i $PROJECT_DIR — type-sjekk hoppet over (IKKE en type-feil)." >&2
  echo "Kjør .claude/scripts/bootstrap-worktree.sh for worktreen." >&2
  exit 0
fi

TYPE_CMD=$(cat <<'CMD'
{{CMD_TYPE_CHECK}}
CMD
)

OUT=$(bash -c "$TYPE_CMD" 2>&1) || {
  echo "{{PROJECT_NAME}}: typesjekk fant feil etter endring i $FILE:" >&2
  echo "" >&2
  echo "$OUT" | head -40 >&2
  exit 2
}

exit 0
