#!/usr/bin/env bash
# {{PROJECT_NAME}} — PreToolUse-hook (Agent), generert av /setup: en implementer-dispatch MÅ bære
# eksplisitt `model` i Agent-kallet. Charterets `model:`-frontmatter leses ved sesjonsstart, så en
# sesjon som startet før en modellendring kjører den gamle modellen i stillhet — målt i
# opphavsprosjektet: implementeren kjørte en rimeligere modell fra et utdatert sesjons-snapshot i en hel
# release. Fix-runde 1–2: `models.implementer`-klassen eller dypere ({{IMPLEMENTER_DISPATCH_ALLOWED}}).
# Fix-runde 3+: prosjektets dype modell eller dypere ({{DEEP_DISPATCH_ALLOWED}}) — runbook §5b
# «Modell-eskalering fra fix-runde 3». Exit 2 = blokkert. Trenger /usr/bin/jq (fail-open uten).
set -euo pipefail
[ -x /usr/bin/jq ] || exit 0
INPUT=$(cat)
TYPE=$(printf '%s' "$INPUT" | /usr/bin/jq -r '.tool_input.subagent_type // ""')
[ "$TYPE" = "{{PROJECT_NAME}}-implementer" ] || exit 0
MODEL=$(printf '%s' "$INPUT" | /usr/bin/jq -r '.tool_input.model // ""')
PROMPT=$(printf '%s' "$INPUT" | /usr/bin/jq -r '.tool_input.prompt // ""')
if printf '%s' "$PROMPT" | grep -qiE 'fix-runde ([3-9]|[1-9][0-9])'; then
  case "$MODEL" in {{DEEP_DISPATCH_ALLOWED}}) exit 0 ;; esac
  echo "{{PROJECT_NAME}}: fix-runde 3+ blokkert — legg til model: \"{{DEEP_MODEL_ALIAS}}\" i Agent-kallet (runbook §5b, Modell-eskalering fra fix-runde 3)." >&2
  exit 2
fi
case "$MODEL" in {{IMPLEMENTER_DISPATCH_ALLOWED}}) exit 0 ;; esac
echo "{{PROJECT_NAME}}: implementer-dispatch blokkert — legg til model: \"{{IMPLEMENTER_MODEL_ALIAS}}\" i Agent-kallet. Frontmatter alene holder ikke: et utdatert sesjons-snapshot kan kjøre en annen modell." >&2
exit 2
