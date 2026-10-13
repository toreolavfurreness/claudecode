#!/usr/bin/env bash
# Regresjonstest for guard-zsh-modifier.sh.
# Kjøres: bash .claude/hooks/test-guard-zsh-modifier.sh [sti til hook]
H="${1:-$(dirname "$0")/guard-zsh-modifier.sh}"; fail=0
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
p() { jq -n --arg c "$1" '{tool_input:{command:$c}}'; }
chk() { [ "$1" = "$2" ] && echo "OK   $3" || { echo "AVVIK $3 (fikk $1, ventet $2)"; fail=1; }; }
t() { p "$2" | bash "$H" 2>/dev/null; chk $? "$1" "$3"; } # forventet-exit  kommando  navn
C22='git show origin/$B:tasks/plans/x.md'
t 2 'git show $SHA:supabase/migrations/x.sql' "uten klammer 06"
t 2 'git show $H:supabase/functions/x/index.ts' "uten klammer 11"
t 2 'git show "$B:tasks/metrics/effort-experiment.md"' "uten klammer 20"
t 2 "$C22" "uten klammer 22"
t 2 $'echo a\ngit show $B:tasks/x' "treff på linje 2"
t 2 'gh api graphql -f query='\''query($owner:String!){viewer{login}}'\' "graphql uten mellomrom, kjent kostnad"
t 0 'git show "${SHA}:supabase/migrations/x.sql"' "med klammer 06"
t 0 'git show "${H}:supabase/functions/x/index.ts"' "med klammer 11"
t 0 'git show "${B}:tasks/metrics/effort-experiment.md"' "med klammer 20"
t 0 'git show "origin/${B}:tasks/plans/x.md"' "med klammer 22"
t 0 'gh api graphql -f query='\''query($owner: String!){viewer{login}}'\' "graphql med mellomrom"
t 0 'export PATH=$HOME/bin:$PATH' "kolon foran dollar"
t 0 'docker run -v $PWD:/app x' "kolon foran skråstrek"
t 0 'curl http://$HOST:8080/' "kolon foran siffer"
t 0 'echo $(git rev-parse HEAD):tasks' "kommandosubstitusjon"
echo '{}' | bash "$H" 2>/dev/null; chk $? 0 "tom kommando"
echo 'ikke json' | bash "$H" 2>/dev/null; chk $? 0 "ugyldig JSON feiler åpent"
p "$C22" | bash "$H" 2>&1 >/dev/null | grep -qF '${B}:'; chk $? 0 "melding foreslår klammer"
# Registrering: kjør kommandoen slik den står i settings.json. Tom streng skal ikke kjøres som en no-op.
REG=$(jq -r '.hooks.PreToolUse[] | select(.matcher=="Bash") | .hooks[].command | select(contains("guard-zsh-modifier.sh"))' "$ROOT/.claude/settings.json" | head -1)
if [ -n "$REG" ]; then
  p "$C22" | CLAUDE_PROJECT_DIR="$ROOT" sh -c "$REG" 2>/dev/null; chk $? 2 "registrert i settings.json"
else
  echo "AVVIK registrert i settings.json (ingen kommando med guard-zsh-modifier.sh i Bash-blokken)"; fail=1
fi
[ $fail = 0 ] && echo "ALLE OK" || { echo "FEIL"; exit 1; }
