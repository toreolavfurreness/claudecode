#!/usr/bin/env bash
# {{PROJECT_NAME}} — sessionStart-hook: kjører en rask statisk kvalitetsstatus
# (typecheck + lint) ved sesjonsstart slik at agenten ser om koden er ren før
# arbeid starter.
#
# MYK feiling: hooken skal ALDRI blokkere sesjonsstart. Mangler avhengighetene
# (fersk container/worktree), rapporterer den det og avslutter 0. Statusen går til
# stdout som {"additionalContext":"…"} (Copilot legger den inn som kontekst). Mangler jq,
# skrives ingenting (myk) — en ikke-JSON-stdout kunne ellers blitt avvist av harnessen.
#
# Kjører for alle sessionStart-kilder (startup, resume, new); payloaden leses ikke.
#
# Kommandoene er verification_commands.type_check / .lint fra loop.config.yaml,
# substituert av /setup. En tom kommando hoppes over.

set -uo pipefail

# Payloaden (sessionId, source, …) trengs ikke, men stdin tømmes så harnessen ikke blokkerer.
cat >/dev/null 2>&1 || true

# Prosjektrot — bruk harness-variabel, fall tilbake til git-rot.
LOOP_PROJECT_DIR="${LOOP_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$LOOP_PROJECT_DIR" 2>/dev/null || exit 0

emit() { # emit <tekst> — én additionalContext-JSON på stdout, eller ingenting uten jq
  command -v jq >/dev/null 2>&1 || exit 0
  printf '%s' "$1" | jq -Rsc '{additionalContext: .}' 2>/dev/null || true
  exit 0
}

# worktree_bootstrap.install_marker — finnes den ikke, er avhengighetene ikke installert her.
DEPS_MARKER="{{BOOTSTRAP_INSTALL_MARKER}}"
if [ -n "$DEPS_MARKER" ] && [ ! -e "$DEPS_MARKER" ]; then
  emit "[session-start-lint] $DEPS_MARKER mangler — installer avhengigheter for lint/typecheck-status. Hopper over."
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

REPORT=""
add() { REPORT="${REPORT}$1"$'\n'; }

run() { # run <etikett> <kommando>
  [ -n "$2" ] || return 0
  local out rc
  out=$(bash -c "$2" 2>&1 </dev/null)
  rc=$?
  if [ "$rc" -eq 0 ]; then
    add "[session-start-lint] ✓ $1: rent"
  else
    add "[session-start-lint] ✗ $1: feil funnet (exit $rc)"
    add "$(printf '%s\n' "$out" | tail -10)"
  fi
}

add "[session-start-lint] Kjører typecheck + lint (myk status)…"
run typecheck "$TYPE_CMD"
run lint "$LINT_CMD"

# Alltid suksess — dette er en informativ status, ikke en gate.
emit "$REPORT"
