#!/usr/bin/env bash
# {{PROJECT_NAME}} — PreToolUse hook: blokkerer utilsiktede {{PROD_BRANCH}}-merges og {{PROD_BRANCH}}-pushes.
# Krever eksplisitt manuell kjøring i terminal for å overstyre.
#
# Dekker:
#   1. git push mot {{PROD_BRANCH}} (origin {{PROD_BRANCH}}, HEAD:{{PROD_BRANCH}}, :{{PROD_BRANCH}}, -u origin {{PROD_BRANCH}})
#   2. gh pr create uten --base (defaulter til {{PROD_BRANCH}}) eller med --base {{PROD_BRANCH}}
#   3. gh pr merge <pr> eller REST-merge (gh api --method PUT/-X PUT .../pulls/<pr>/merge,
#      alle flaggformer inkl. --method=PUT, -XPUT og siterte verdier) der PR-ens base er
#      {{PROD_BRANCH}} (oppslag med timeout 5s)
#
# Logg: tasks/hook-blocks.log (ikke versjonert)

set -euo pipefail

INPUT=$(cat)
CMD=$(echo "$INPUT" | /usr/bin/jq -r '.tool_input.command // ""')
CWD=$(echo "$INPUT" | /usr/bin/jq -r '.cwd // ""')

# Bruk kun første linje for pattern-matching — heredoc-innhold i commit-meldinger
# kan inneholde cmd-lignende strenger som ellers ville gi falske treff.
FIRST="${CMD%%$'\n'*}"

# ── Loggstiutledning ──────────────────────────────────────────────────────────
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${CWD:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null || echo "/tmp")}}"
LOG="$PROJECT_DIR/tasks/hook-blocks.log"

block() {
  local reason="$1"
  local ts
  ts=$(date '+%Y-%m-%dT%H:%M:%S')
  mkdir -p "$(dirname "$LOG")" 2>/dev/null || true
  echo "$ts | BLOKKERT | $CMD | $reason" >> "$LOG" 2>/dev/null || true
  echo "{{PROJECT_NAME}}: {{PROD_BRANCH}}-merge blokkert av sikkerhets-hook." >&2
  echo "" >&2
  echo "Årsak: $reason" >&2
  echo "" >&2
  echo "For å kjøre med vilje — kopier og kjør dette i terminal:" >&2
  echo "" >&2
  echo "  $CMD" >&2
  exit 2
}

# ── 1. git push mot {{PROD_BRANCH}} ──────────────────────────────────────────────────────
if echo "$FIRST" | grep -qE '^git\s+push\b'; then
  # Treff: origin {{PROD_BRANCH}}, -u origin {{PROD_BRANCH}}, HEAD:{{PROD_BRANCH}}, :{{PROD_BRANCH}}, refs/heads/{{PROD_BRANCH}}
  if echo "$FIRST" | grep -qE '\borigin\s+{{PROD_BRANCH}}\b|-u\s+origin\s+{{PROD_BRANCH}}\b|HEAD:{{PROD_BRANCH}}\b|:{{PROD_BRANCH}}\b|refs/heads/{{PROD_BRANCH}}\b'; then
    block "git push direkte til {{PROD_BRANCH}}"
  fi
fi

# ── 2. gh pr create ───────────────────────────────────────────────────────────
if echo "$FIRST" | grep -qE '^gh\s+pr\s+create\b'; then
  if echo "$FIRST" | grep -qE '\-\-base\s+{{PROD_BRANCH}}\b'; then
    block "gh pr create med --base {{PROD_BRANCH}}"
  fi
  if ! echo "$FIRST" | grep -qE '\-\-base\b'; then
    block "gh pr create uten --base (defaulter til {{PROD_BRANCH}})"
  fi
fi

# ── 3. gh pr merge — sjekk PR-ens base via API ────────────────────────────────
if echo "$FIRST" | grep -qE '^gh\s+pr\s+merge\b'; then
  PR_ARG=$(echo "$FIRST" | awk '{for(i=1;i<=NF;i++) if($i=="merge") {print $(i+1); exit}}' | grep -oE '^[0-9]+$' || true)
  if [ -n "$PR_ARG" ]; then
    BASE=$(perl -e 'alarm 5; exec @ARGV' gh pr view "$PR_ARG" --json baseRefName -q .baseRefName 2>/dev/null || echo "")
    if [ "$BASE" = "{{PROD_BRANCH}}" ]; then
      block "gh pr merge av PR #$PR_ARG — base er {{PROD_BRANCH}}"
    elif [ -z "$BASE" ]; then
      # Kan ikke resolve (offline/timeout/ikke-eksisterende PR) → fail-safe: blokker
      block "gh pr merge av PR #$PR_ARG — kunne ikke bekrefte base (fail-safe)"
    fi
  else
    block "gh pr merge uten PR-argument (fail-safe)"
  fi
fi

# ── 3b. gh api --method PUT .../pulls/<pr>/merge — REST-merge ───
# Deteksjon = konjunksjon av tre ledd (alle på $FIRST):
#   (1) kommando: gh api
#   (2) metode = PUT, alle gyldige flaggformer, siterte og usiterte
#   (3) sti er et merge-endepunkt (bevisst romslig, ingen trailing-anker — se T13)
# Bracket-uttrykket i (2) MÅ inneholde både ' og " — bygges i en double-quoted
# variabel (ikke et single-quoted grep-literal) fordi kilden ellers ikke er
# kjørbar bash (single-quoted streng kan ikke inneholde en literal ').
RX_PUT_METHOD="(^|[[:space:]])(--method|-X)[[:space:]]*=?[[:space:]]*['\"]?[Pp][Uu][Tt](['\"]|[[:space:]]|\$)"
if echo "$FIRST" | grep -qE '^gh[[:space:]]+api\b' \
  && echo "$FIRST" | grep -qE "$RX_PUT_METHOD" \
  && echo "$FIRST" | grep -qE '/pulls/[^[:space:]]*merge'; then
  PR_ARG=$(printf '%s' "$FIRST" | grep -oE '/pulls/[0-9]+/merge' | head -1 | grep -oE '[0-9]+' || true)
  if [ -n "$PR_ARG" ]; then
    BASE=$(perl -e 'alarm 5; exec @ARGV' gh pr view "$PR_ARG" --json baseRefName -q .baseRefName 2>/dev/null || echo "")
    if [ "$BASE" = "{{PROD_BRANCH}}" ]; then
      block "gh api REST-merge av PR #$PR_ARG — base er {{PROD_BRANCH}}"
    elif [ -z "$BASE" ]; then
      # Kan ikke resolve (offline/timeout/ikke-eksisterende PR) → fail-safe: blokker
      block "gh api REST-merge av PR #$PR_ARG — kunne ikke bekrefte base (fail-safe)"
    fi
  else
    block "gh api REST-merge uten uttrekkbart PR-nummer (fail-safe)"
  fi
fi

# ── Alle andre kommandoer: tillat ─────────────────────────────────────────────
exit 0
