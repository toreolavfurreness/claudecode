#!/usr/bin/env bash
# PreToolUse-hook (Bash): stopper `$NAVN:<bokstav>` uten klammer. For prosjekter der agentens skall er zsh.
#
# Registrering i .claude/settings.json, under PreToolUse med matcher "Bash":
#   { "type": "command", "command": "\"$CLAUDE_PROJECT_DIR/.claude/hooks/guard-zsh-modifier.sh\"" }
#
# zsh leser `:t`, `:h`, `:r`, `:s` osv. etter et variabelnavn som modifikator, også i dobbeltsitat,
# så `git show $B:tasks/x` gir feil sti uten feilmelding. Alle bokstaver blokkeres, ikke bare dagens modifikatorer: `${NAVN}:` er riktig i alle skall.
# ponytail: skanner hele kommandostrengen, så enkeltsitert tekst og heredocs treffes også.
# Slik tekst skrives med Write/Edit. En sitat-parser hvis den kostnaden blir for høy.
# Feiler åpent: ugyldig JSON på stdin gir exit 0. Blokkert = exit 2.
set -euo pipefail
CMD=$(/usr/bin/jq -r '.tool_input.command // ""') || exit 0
HIT=$(printf '%s\n' "$CMD" | grep -oE '\$[A-Za-z_][A-Za-z0-9_]*:[A-Za-z]' | head -1 || true)
[ -n "$HIT" ] || exit 0
NAME=${HIT#\$}
NAME=${NAME%:*}
echo "Bash-kall blokkert — \`$HIT\` leses av zsh som en modifikator på variabelen. Skriv \`\${$NAME}:\` med klammer. Er teksten bokstavelig (commit-melding, PR-tekst, heredoc), skriv den med Write/Edit og bruk -F/--body-file. GraphQL-variabler skrives med mellomrom etter kolon." >&2
exit 2
