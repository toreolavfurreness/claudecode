#!/usr/bin/env bash
# EKSEMPEL — miljø-ref-vakt for Supabase (PreToolUse på `mcp__.*[Ss]upabase.*|Bash`).
# Ikke en fast del av kit-et: den er Supabase-spesifikk. Slik tar du den i bruk:
#   1. Kopier til .claude/hooks/guard-supabase-ref.sh og sett DEV_REF/PROD_REF under til
#      environments.dev_id / prod_id fra loop.config.yaml. chmod +x.
#   2. Legg til i .claude/settings.json under hooks.PreToolUse:
#        {"matcher": "mcp__.*[Ss]upabase.*|Bash",
#         "hooks": [{"type": "command", "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/guard-supabase-ref.sh\""}]}
#   /setup rører ikke denne oppføringen (den merger kun sine egne hook-kommandoer).
# <prosjekt> — PreToolUse hook: blokkerer Supabase-kall mot feil project-ref.
#
# Bakgrunn: Den vanligste dokumenterte feilkilden i prosjektet er forveksling
# av dev-/prod-ref, og at den globale FIFA Match Night-CLAUDE.md har lekket inn
# en fremmed ref to ganger. Denne hooken er
# en allowlist-vakt: enhver Supabase-ref som dukker opp i et MCP- eller CLI-kall
# må være <prosjekt>s dev- eller prod-ref — alt annet blokkeres.
#
# Dekker:
#   1. MCP Supabase-verktøy        → felt project_id i tool_input
#   2. supabase CLI                → --project-ref XXX / -p XXX / --project-ref=XXX
#   3. Vilkårlig <ref>.supabase.co → URL i kommando eller MCP-arg
#
# Logg: tasks/hook-blocks.log (ikke versjonert)

set -euo pipefail

# ── Tillatte refs ─────────────────────────────────────────────────────────────
DEV_REF="<DEV_ENV_ID>"
PROD_REF="<PROD_ENV_ID>"

INPUT=$(cat)
TOOL=$(echo "$INPUT" | /usr/bin/jq -r '.tool_name // ""')
CWD=$(echo "$INPUT" | /usr/bin/jq -r '.cwd // ""')

# ── Loggstiutledning (speiler guard-main-merge.sh) ────────────────────────────
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${CWD:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || echo "/tmp")}}"
LOG="$PROJECT_DIR/tasks/hook-blocks.log"

block() {
  local ref="$1"
  local where="$2"
  local ts
  ts=$(date '+%Y-%m-%dT%H:%M:%S')
  mkdir -p "$(dirname "$LOG")" 2>/dev/null || true
  echo "$ts | BLOKKERT | $TOOL | fremmed Supabase-ref '$ref' ($where)" >> "$LOG" 2>/dev/null || true
  echo "<prosjekt>: Supabase-kall blokkert av sikkerhets-hook." >&2
  echo "" >&2
  echo "Fant ref '$ref' ($where) som IKKE er <prosjekt>s dev eller prod." >&2
  echo "" >&2
  echo "Tillatte refs:" >&2
  echo "  dev  = $DEV_REF" >&2
  echo "  prod = $PROD_REF" >&2
  echo "" >&2
  echo "Sannsynlig årsak: feil miljø, eller en fremmed ref (f.eks. FIFA" >&2
  echo "Match Night) lekket inn fra global ~/CLAUDE.md. Bekreft miljø før" >&2
  echo "du fortsetter — prod kun ved planlagte releaser." >&2
  exit 2
}

# Sjekk én kandidat-ref mot allowlist. Ignorerer tom streng.
check_ref() {
  local ref="$1"
  local where="$2"
  [ -z "$ref" ] && return 0
  if [ "$ref" != "$DEV_REF" ] && [ "$ref" != "$PROD_REF" ]; then
    block "$ref" "$where"
  fi
}

# ── 1. MCP Supabase-verktøy: project_id-felt ──────────────────────────────────
# Gjelder kun verktøy med "Supabase" i navnet for å unngå falske treff.
if echo "$TOOL" | grep -qi "supabase"; then
  PROJECT_ID=$(echo "$INPUT" | /usr/bin/jq -r '.tool_input.project_id // .tool_input.projectId // .tool_input.ref // ""')
  check_ref "$PROJECT_ID" "MCP project_id"
fi

# ── 2 + 3. Tekstskanning av hele tool_input ───────────────────────────────────
# Dekker CLI-flagg og .supabase.co-URLer uansett hvilket felt de ligger i.
RAW=$(echo "$INPUT" | /usr/bin/jq -r '.tool_input | tostring')

# 2. supabase CLI: --project-ref XXX | --project-ref=XXX | -p XXX
while IFS= read -r ref; do
  check_ref "$ref" "--project-ref"
done < <(echo "$RAW" | grep -oE '(--project-ref[ =]|[-]p )[a-z]{20}' | grep -oE '[a-z]{20}$' || true)

# 3. <ref>.supabase.co
while IFS= read -r ref; do
  check_ref "$ref" "supabase.co URL"
done < <(echo "$RAW" | grep -oE '[a-z]{20}\.supabase\.co' | grep -oE '^[a-z]{20}' || true)

# ── Alt annet: tillat ─────────────────────────────────────────────────────────
exit 0
