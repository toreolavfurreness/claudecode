#!/usr/bin/env bash
# Regresjonstest for guard-fix-round-model.sh (generert av /setup). Kjøres: bash .github/hooks/scripts/test-guard-fix-round-model.sh
# Forventet utfall: 2 = blokkert (exit 0 + permissionDecision "deny" på stdout), 0 = slipper
# (exit 0 + tom stdout). Alt annet er AVVIK. Payloadene er Copilot preToolUse-form:
# {"toolName":"task","toolArgs":<JSON-streng eller objekt med agent_type/model/prompt>}.
H="$(dirname "$0")/guard-fix-round-model.sh"; fail=0; n=0
t() { # forventet(0|2)  toolArgs-objekt-json  beskrivelse
  local p o rc got
  n=$((n + 1))
  # Annenhver rad sender toolArgs som JSON-streng, resten som objekt — begge former skal virke.
  if [ $((n % 2)) = 1 ]; then
    p=$(/usr/bin/jq -cn --argjson a "$2" '{toolName: "task", toolArgs: ($a | tojson), sessionId: "s-test-0001", cwd: "/tmp"}')
  else
    p=$(/usr/bin/jq -cn --argjson a "$2" '{toolName: "task", toolArgs: $a, sessionId: "s-test-0001", cwd: "/tmp"}')
  fi
  o=$(printf '%s' "$p" | bash "$H" 2>/dev/null); rc=$?
  if [ "$rc" != 0 ]; then got="exit$rc"
  elif [ -z "$o" ]; then got=0
  elif printf '%s' "$o" | /usr/bin/jq -e '.permissionDecision == "deny"' >/dev/null 2>&1; then got=2
  else got="stdout?"; fi
  [ "$got" = "$1" ] && echo "OK   $3" || { echo "AVVIK $3 (fikk $got, ventet $1)"; fail=1; }
}
raw() { # forventet(0|2)  hel-payload  beskrivelse (for payloads utenfor task-formen)
  local o rc got
  o=$(printf '%s' "$2" | bash "$H" 2>/dev/null); rc=$?
  if [ "$rc" != 0 ]; then got="exit$rc"; elif [ -z "$o" ]; then got=0
  elif printf '%s' "$o" | /usr/bin/jq -e '.permissionDecision == "deny"' >/dev/null 2>&1; then got=2
  else got="stdout?"; fi
  [ "$got" = "$1" ] && echo "OK   $3" || { echo "AVVIK $3 (fikk $got, ventet $1)"; fail=1; }
}
I='"agent_type":"{{PROJECT_NAME}}-implementer"'
t 2 "{$I,\"prompt\":\"Implementer TODO 4\"}" "vanlig implementering uten model blokkeres"
t 0 "{$I,\"model\":\"{{IMPLEMENTER_MODEL_ALIAS}}\",\"prompt\":\"Implementer TODO 4\"}" "implementer-modellen slipper"
t 0 "{$I,\"model\":\"{{DEEP_MODEL_ALIAS}}\",\"prompt\":\"Implementer TODO 4\"}" "dyp modell slipper alltid"
t 2 "{$I,\"model\":\"{{BELOW_IMPLEMENTER_ALIAS}}\",\"prompt\":\"Implementer TODO 4\"}" "modell under implementer-klassen blokkeres"
t 0 "{$I,\"model\":\"{{IMPLEMENTER_MODEL_ALIAS}}\",\"prompt\":\"FIX-MODE — fix-runde 2\"}" "fix-runde 2 med implementer-modellen slipper"
t 2 "{$I,\"prompt\":\"FIX-MODE — fix-runde 3\"}" "fix-runde 3 uten model blokkeres"
t 0 "{$I,\"model\":\"{{DEEP_MODEL_ALIAS}}\",\"prompt\":\"FIX-MODE — Fix-runde 3\"}" "fix-runde 3 med dyp modell slipper"
t {{FIXR3_IMPL_EXPECT}} "{$I,\"model\":\"{{IMPLEMENTER_MODEL_ALIAS}}\",\"prompt\":\"FIX-MODE — fix-runde 12\"}" "fix-runde 12 med implementer-modellen (blokkeres når den er grunnere enn dyp)"
t 0 '{"agent_type":"{{PROJECT_NAME}}-code-reviewer","prompt":"fix-runde 5"}' "annen agenttype slipper"
t 0 '{"agent_type":"{{PROJECT_NAME}}-planner","prompt":"Planlegg TODO 9"}' "planner uten model slipper"
raw 0 '{"toolName":"bash","toolArgs":{"agent_type":"{{PROJECT_NAME}}-implementer","command":"ls"}}' "annet verktøy enn task slipper"
raw 2 '{"toolName":"task","toolArgs":"{\"agent_type\":\"{{PROJECT_NAME}}-implementer\",\"mode\":\"background\",\"prompt\":\"x\"}"}' "task i bakgrunnsmodus uten model blokkeres"
[ $fail = 0 ] && echo "ALLE OK" || { echo "FEIL"; exit 1; }
