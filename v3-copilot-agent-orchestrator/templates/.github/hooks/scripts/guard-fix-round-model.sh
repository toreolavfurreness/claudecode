#!/usr/bin/env bash
# {{PROJECT_NAME}} — preToolUse-hook (task), generert av /setup: en implementer-dispatch MÅ bære
# eksplisitt `model` i task-kallet. Agentfilas `model:`-frontmatter leses ved sesjonsstart, så en
# sesjon som startet før en modellendring kjører den gamle modellen i stillhet.
# Fix-runde 1–2: en modell fra `models.implementer` eller en dyp modell ({{IMPLEMENTER_DISPATCH_ALLOWED}}).
# Fix-runde 3+: en dyp modell ({{DEEP_DISPATCH_ALLOWED}}) — runbook §5b
# «Modell-eskalering fra fix-runde 3».
#
# Copilot-hooks har ingen matcher: hooken filtrerer selv på toolName == "task" og leser
# agent_type/model/prompt fra toolArgs (JSON-streng eller objekt). Blokkering =
# {"permissionDecision":"deny",…} på stdout og exit 0; lar svaret seg ikke skrive, exit 2
# (fail-closed). Trenger /usr/bin/jq (fail-open uten).
set -euo pipefail
[ -x /usr/bin/jq ] || exit 0
INPUT=$(cat)
TOOL=$(printf '%s' "$INPUT" | /usr/bin/jq -r '.toolName // ""')
[ "$TOOL" = "task" ] || exit 0
ARGS=$(printf '%s' "$INPUT" | /usr/bin/jq -c '.toolArgs | if type=="string" then (fromjson? // {}) else (. // {}) end')
TYPE=$(printf '%s' "$ARGS" | /usr/bin/jq -r '.agent_type // ""')
[ "$TYPE" = "{{PROJECT_NAME}}-implementer" ] || exit 0
MODEL=$(printf '%s' "$ARGS" | /usr/bin/jq -r '.model // ""')
PROMPT=$(printf '%s' "$ARGS" | /usr/bin/jq -r '.prompt // ""')

deny() {
  printf '%s\n' "$1" >&2
  printf '%s' "$1" | /usr/bin/jq -Rsc '{permissionDecision: "deny", permissionDecisionReason: .}' || exit 2
  exit 0
}

if printf '%s' "$PROMPT" | grep -qiE 'fix-runde ([3-9]|[1-9][0-9])'; then
  case "$MODEL" in {{DEEP_DISPATCH_ALLOWED}}) exit 0 ;; esac
  deny "{{PROJECT_NAME}}: fix-runde 3+ blokkert — legg til model: \"{{DEEP_MODEL_ALIAS}}\" i task-kallet (runbook §5b, Modell-eskalering fra fix-runde 3)."
fi
case "$MODEL" in {{IMPLEMENTER_DISPATCH_ALLOWED}}) exit 0 ;; esac
deny "{{PROJECT_NAME}}: implementer-dispatch blokkert — legg til model: \"{{IMPLEMENTER_MODEL_ALIAS}}\" i task-kallet. Frontmatter alene holder ikke: et utdatert sesjons-snapshot kan kjøre en annen modell."
