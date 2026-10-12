#!/usr/bin/env bash
# {{PROJECT_NAME}} — SessionStart-hook: kjører en rask statisk kvalitetsstatus
# (typecheck + lint) ved sesjonstart slik at Claude ser om koden er ren før
# arbeid starter.
#
# MYK feiling: hooken skal ALDRI blokkere sesjonsstart. Mangler avhengighetene
# (fersk container/worktree), rapporterer den det og avslutter 0. Output går til
# stdout (vises som kontekst til Claude).
#
# Kommandoene er verification_commands.type_check / .lint fra loop.config.yaml,
# substituert av /setup. En tom kommando hoppes over.

set -uo pipefail

# Prosjektrot — bruk harness-variabel, fall tilbake til git-rot.
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$PROJECT_DIR" 2>/dev/null || exit 0

# worktree_bootstrap.install_marker — finnes den ikke, er avhengighetene ikke installert her.
DEPS_MARKER="{{BOOTSTRAP_INSTALL_MARKER}}"
if [ -n "$DEPS_MARKER" ] && [ ! -e "$DEPS_MARKER" ]; then
  echo "[session-start-lint] $DEPS_MARKER mangler — installer avhengigheter for lint/typecheck-status. Hopper over."
  exit 0
fi

# Heredoc med sitert terminator: kommandoen tas ordrett, uansett anførselstegn i config-verdien.
TYPE_CMD=$(cat <<'CMD'
{{CMD_TYPE_CHECK}}
CMD
)
LINT_CMD=$(cat <<'CMD'
{{CMD_LINT}}
CMD
)

run() { # run <etikett> <kommando>
  [ -n "$2" ] || return 0
  local out rc
  out=$(bash -c "$2" 2>&1)
  rc=$?
  if [ "$rc" -eq 0 ]; then
    echo "[session-start-lint] ✓ $1: rent"
  else
    echo "[session-start-lint] ✗ $1: feil funnet (exit $rc)"
    echo "$out" | tail -10
  fi
}

echo "[session-start-lint] Kjører typecheck + lint (myk status)…"
run typecheck "$TYPE_CMD"
run lint "$LINT_CMD"

# Alltid suksess — dette er en informativ status, ikke en gate.
exit 0
