#!/usr/bin/env bash
# Regresjonstest for guard-fix-round-model.sh (generert av /setup). Kjøres: bash .claude/hooks/test-guard-fix-round-model.sh
H="$(dirname "$0")/guard-fix-round-model.sh"; fail=0
t() { # forventet-exit  json  beskrivelse
  echo "$2" | bash "$H" 2>/dev/null; got=$?
  [ "$got" = "$1" ] && echo "OK   $3" || { echo "AVVIK $3 (fikk $got, ventet $1)"; fail=1; }
}
I='"subagent_type":"{{PROJECT_NAME}}-implementer"'
t 2 "{\"tool_input\":{$I,\"prompt\":\"Implementer TODO 4\"}}" "vanlig implementering uten model blokkeres"
t 0 "{\"tool_input\":{$I,\"model\":\"{{IMPLEMENTER_MODEL_ALIAS}}\",\"prompt\":\"Implementer TODO 4\"}}" "implementer-modellen slipper"
t 0 "{\"tool_input\":{$I,\"model\":\"{{DEEP_MODEL_ALIAS}}\",\"prompt\":\"Implementer TODO 4\"}}" "dyp modell slipper alltid"
t 2 "{\"tool_input\":{$I,\"model\":\"{{BELOW_IMPLEMENTER_ALIAS}}\",\"prompt\":\"Implementer TODO 4\"}}" "modell under implementer-klassen blokkeres"
t 0 "{\"tool_input\":{$I,\"model\":\"{{IMPLEMENTER_MODEL_ALIAS}}\",\"prompt\":\"FIX-MODE — fix-runde 2\"}}" "fix-runde 2 med implementer-modellen slipper"
t 2 "{\"tool_input\":{$I,\"prompt\":\"FIX-MODE — fix-runde 3\"}}" "fix-runde 3 uten model blokkeres"
t 0 "{\"tool_input\":{$I,\"model\":\"{{DEEP_MODEL_ALIAS}}\",\"prompt\":\"FIX-MODE — Fix-runde 3\"}}" "fix-runde 3 med dyp modell slipper"
t {{FIXR3_IMPL_EXPECT}} "{\"tool_input\":{$I,\"model\":\"{{IMPLEMENTER_MODEL_ALIAS}}\",\"prompt\":\"FIX-MODE — fix-runde 12\"}}" "fix-runde 12 med implementer-modellen (blokkeres når den er grunnere enn dyp)"
t 0 '{"tool_input":{"subagent_type":"{{PROJECT_NAME}}-code-reviewer","prompt":"fix-runde 5"}}' "annen agenttype slipper"
t 0 '{"tool_input":{"subagent_type":"{{PROJECT_NAME}}-planner","prompt":"Planlegg TODO 9"}}' "planner uten model slipper"
[ $fail = 0 ] && echo "ALLE OK" || { echo "FEIL"; exit 1; }
