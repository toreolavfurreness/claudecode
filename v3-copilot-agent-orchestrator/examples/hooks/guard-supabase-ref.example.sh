#!/usr/bin/env bash
# EKSEMPEL — miljø-ref-vakt for Supabase (preToolUse på MCP-verktøy fra en Supabase-server og bash).
# Ikke en fast del av kit-et: den er Supabase-spesifikk. Slik tar du den i bruk:
#   1. Kopier til .github/hooks/scripts/guard-supabase-ref.sh og sett DEV_REF/PROD_REF under til
#      environments.dev_id / prod_id fra loop.config.yaml. chmod +x.
#   2. Legg den i prosjektets EGEN hook-fil i .github/hooks/ (f.eks. .github/hooks/project.json) —
#      ikke i loop-guards.json, som /setup eier og overskriver:
#        { "version": 1, "hooks": { "preToolUse": [
#            { "type": "command", "bash": "bash .github/hooks/scripts/guard-supabase-ref.sh", "cwd": ".", "timeoutSec": 30 } ] } }
#   Copilot-hooks har ingen matcher: skriptet filtrerer selv. MCP-verktøy heter `<server>/<verktøy>`
#   (f.eks. `supabase/execute_sql`); terminalverktøyet heter `bash`.
# <prosjekt> — preToolUse-hook: blokkerer Supabase-kall mot feil project-ref.
#
# Bakgrunn: Den vanligste dokumenterte feilkilden i prosjektet er forveksling
# av dev-/prod-ref, og at globale brukerinstruksjoner fra FIFA Match Night har lekket inn
# en fremmed ref to ganger. Denne hooken er
# en allowlist-vakt: enhver Supabase-ref som dukker opp i et MCP- eller CLI-kall
# må være <prosjekt>s dev- eller prod-ref — alt annet blokkeres.
#
# Dekker:
#   1. MCP Supabase-verktøy        → felt project_id i toolArgs
#   2. supabase CLI                → --project-ref XXX / -p XXX / --project-ref=XXX
#   3. Vilkårlig <ref>.supabase.co → URL i kommando eller MCP-arg
#
# Blokkering: {"permissionDecision":"deny","permissionDecisionReason":"…"} på stdout og exit 0
# (exit 2 hvis svaret ikke lar seg skrive — fail-closed).
#
# Logg: tasks/hook-blocks.log (ikke versjonert)

set -euo pipefail

# ── Tillatte refs ─────────────────────────────────────────────────────────────
DEV_REF="<DEV_ENV_ID>"
PROD_REF="<PROD_ENV_ID>"

INPUT=$(cat)
TOOL=$(echo "$INPUT" | /usr/bin/jq -r '.toolName // ""')
# Bare Supabase-MCP-verktøy og terminalen vaktes (tidligere matcherens jobb) — ellers ville en
# filredigering som nevner en .supabase.co-URL blitt blokkert.
case "$TOOL" in bash|run_in_terminal|*[Ss]upabase*) ;; *) exit 0 ;; esac
ARGS=$(echo "$INPUT" | /usr/bin/jq -c '.toolArgs | if type=="string" then (fromjson? // {}) else (. // {}) end')
CWD=$(echo "$INPUT" | /usr/bin/jq -r '.cwd // ""')

# ── Loggstiutledning (speiler guard-main-merge.sh) ────────────────────────────
PROJECT_DIR="${LOOP_PROJECT_DIR:-${CWD:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || echo "/tmp")}}"
LOG="$PROJECT_DIR/tasks/hook-blocks.log"

block() {
  local ref="$1"
  local where="$2"
  local ts
  ts=$(date '+%Y-%m-%dT%H:%M:%S')
  mkdir -p "$(dirname "$LOG")" 2>/dev/null || true
  echo "$ts | BLOKKERT | $TOOL | fremmed Supabase-ref '$ref' ($where)" >> "$LOG" 2>/dev/null || true
  local msg="<prosjekt>: Supabase-kall blokkert av sikkerhets-hook.

Fant ref '$ref' ($where) som IKKE er <prosjekt>s dev eller prod.

Tillatte refs:
  dev  = $DEV_REF
  prod = $PROD_REF

Sannsynlig årsak: feil miljø, eller en fremmed ref (f.eks. FIFA
Match Night) lekket inn fra globale brukerinstruksjoner. Bekreft miljø før
du fortsetter — prod kun ved planlagte releaser."
  printf '%s\n' "$msg" >&2
  printf '%s' "$msg" | /usr/bin/jq -Rsc '{permissionDecision: "deny", permissionDecisionReason: .}' || exit 2
  exit 0
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
  PROJECT_ID=$(echo "$ARGS" | /usr/bin/jq -r '.project_id // .projectId // .ref // ""')
  check_ref "$PROJECT_ID" "MCP project_id"
fi

# ── 2 + 3. Tekstskanning av hele toolArgs ─────────────────────────────────────
# Dekker CLI-flagg og .supabase.co-URLer uansett hvilket felt de ligger i.
RAW=$(echo "$ARGS" | /usr/bin/jq -r 'tostring')

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
