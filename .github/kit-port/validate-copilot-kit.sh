#!/usr/bin/env bash
# Validerer v3-copilot-agent-orchestrator/ slik README «Selvtest» beskriver, pluss ordvakta:
#   1. Ordvakt: ingen «claude/anthropic/opus/sonnet/haiku/superpowers» i mappa (unntatt kit-repoets URL).
#   2. /setup med uendret eksempel-config SKAL stoppe på modellplassholderne.
#   3. /setup med plassholderne byttet SKAL gå grønt, uten gjenværende tokens og med gyldig
#      YAML-frontmatter og gyldig loop-guards.json, og en ny kjøring SKAL være idempotent.
#   4. Alle harnesser og selvtester på det installerte kitet SKAL være grønne.
#   5. Org-modus: /setup krever org-standarden, setter den inn øverst i AGENTS.md og registrerer
#      compliance-hooken; compliance-check.py --self-test SKAL være grønn.
#
#   bash .github/kit-port/validate-copilot-kit.sh
# Krever git, python3 + pyyaml og jq. Exit 0 = alt grønt, ellers 1.
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel)"
KIT="$ROOT/v3-copilot-agent-orchestrator"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
FAIL=0
ok()   { echo "OK    $*"; }
bad()  { echo "FEIL  $*"; FAIL=1; }

# 1. Ordvakt -----------------------------------------------------------------------------------
HITS="$(grep -rnI -i -E 'claude|anthropic|\bopus\b|sonnet|haiku|superpowers' "$KIT" \
        | grep -v 'github\.com/toreolavfurreness/claudecode' || true)"
if [ -z "$HITS" ]; then ok "ordvakt: ingen forbudte ord"; else bad "ordvakt:"; printf '%s\n' "$HITS" | sed 's/^/      /'; fi

# Felles oppsett av et testprosjekt --------------------------------------------------------------
new_project() {  # $1 = katalog
  mkdir -p "$1" && cd "$1" || exit 1
  git init -q -b dev && git -c user.name=ci -c user.email=ci@ci commit -q --allow-empty -m init
  cp -R "$KIT" . && cp v3-copilot-agent-orchestrator/loop.config.example.yaml v3-copilot-agent-orchestrator/loop.config.yaml
  awk '/^python3 - <<.PY.$/{f=1;next} /^PY$/{f=0} f' v3-copilot-agent-orchestrator/setup.md > "$WORK/setup-body.py"
}

# 2. Plassholdere stopper /setup -----------------------------------------------------------------
new_project "$WORK/placeholder"
if python3 "$WORK/setup-body.py" >"$WORK/p.out" 2>&1; then
  bad "/setup gikk grønt med plassholdere i models:"
elif grep -q 'plassholdere' "$WORK/p.out"; then ok "/setup stopper på modellplassholderne"
else bad "/setup feilet av en annen grunn enn plassholderne:"; sed 's/^/      /' "$WORK/p.out" | tail -5; fi

# 3. Installasjon -------------------------------------------------------------------------------
new_project "$WORK/kitcheck"
sed -i.bak 's/<DYP_MODELL>/deep-model-a/g; s/<KODE_MODELL>/code-model-b/g; s/<BILLIG_MODELL>/cheap-model-c/g' \
  v3-copilot-agent-orchestrator/loop.config.yaml
for a in security-reviewer rls-auditor; do
  mkdir -p .github/agents
  cp "v3-copilot-agent-orchestrator/examples/tech-review-agents/$a.example.md" ".github/agents/$a.agent.md"
done
if python3 "$WORK/setup-body.py" >"$WORK/s.out" 2>&1 && grep -q 'Ingen gjenværende tokens' "$WORK/s.out"; then
  ok "/setup: exit 0, ingen gjenværende tokens"
else bad "/setup feilet:"; tail -15 "$WORK/s.out" | sed 's/^/      /'; fi

python3 - <<'PY' && ok "frontmatter og loop-guards.json er gyldige" || bad "ugyldig frontmatter eller loop-guards.json"
import glob, json, sys, yaml
bad = []
for f in glob.glob('.github/agents/*.agent.md') + glob.glob('.github/skills/*/SKILL.md'):
    t = open(f, encoding='utf-8').read()
    try:
        assert t.startswith('---\n'); yaml.safe_load(t.split('---\n')[1])
    except Exception as e:
        bad.append(f'{f}: {e}')
try:
    json.load(open('.github/hooks/loop-guards.json'))
except Exception as e:
    bad.append(f'loop-guards.json: {e}')
for b in bad: print('      ' + b)
sys.exit(1 if bad else 0)
PY

git add -A >/dev/null && git -c user.name=ci -c user.email=ci@ci commit -qm kit
python3 "$WORK/setup-body.py" >/dev/null 2>&1
if [ -z "$(git status --porcelain)" ]; then ok "/setup er idempotent"; else bad "/setup endret filer ved ny kjøring:"; git status --porcelain | sed 's/^/      /'; fi

# 4. Harnesser og selvtester --------------------------------------------------------------------
run() {
  local out rc; out="$("$@" 2>&1)"; rc=$?
  if [ $rc -eq 0 ]; then ok "$*"; else bad "$* (exit $rc)"; printf '%s\n' "$out" | tail -8 | sed 's/^/      /'; fi
}
run bash .github/hooks/scripts/test-guard-main-merge.sh
run bash .github/hooks/scripts/test-guard-fix-round-model.sh
run bash scripts/test-readonly-check.sh
run bash tasks/test-gate-f.sh
run bash tasks/test-worktree-sweep.sh
run bash tasks/test-worktree-landed.sh
run bash tasks/test-next-todo-nr.sh
for t in ci-gate vblock-lint loop-cadence release decision-level lesson-path retro-numbers \
         review-fan-in-verify parallel-disjoint queue-status; do
  run python3 "tasks/$t.py" --self-test
done
run python3 tasks/measure-cost.py --brake-self-test
run python3 tasks/measure-cost.py --calibrate-self-test
run python3 scripts/kit-release-check.py --self-test
[ -f .github/hooks/scripts/test-checkpoint-hooks.sh ] && run bash .github/hooks/scripts/test-checkpoint-hooks.sh

# 5. Org-modus (compliance.enabled: true) ------------------------------------------------------
new_project "$WORK/orgmode"
sed -i.bak 's/<DYP_MODELL>/deep-model-a/g; s/<KODE_MODELL>/code-model-b/g; s/<BILLIG_MODELL>/cheap-model-c/g; s/^  enabled: false$/  enabled: true/' \
  v3-copilot-agent-orchestrator/loop.config.yaml
if python3 "$WORK/setup-body.py" >"$WORK/o1.out" 2>&1; then bad "org-modus: /setup gikk grønt uten org-fil"
elif grep -q 'org_instructions' "$WORK/o1.out"; then ok "org-modus: /setup stopper når org-standarden mangler"
else bad "org-modus: uventet feil uten org-fil:"; tail -5 "$WORK/o1.out" | sed 's/^/      /'; fi
mkdir -p docs/org && printf '# Org-standard\n\nAgenten skal aldri skrive ut hemmeligheter.\n' > docs/org/AGENTS.org.md
if python3 "$WORK/setup-body.py" >"$WORK/o2.out" 2>&1 && grep -q 'Ingen gjenværende tokens' "$WORK/o2.out"; then
  ok "org-modus: /setup exit 0, ingen gjenværende tokens"
else bad "org-modus: /setup feilet:"; tail -15 "$WORK/o2.out" | sed 's/^/      /'; fi
if head -1 AGENTS.md | grep -q 'ORG-STANDARD START' && grep -q 'aldri skrive ut hemmeligheter' AGENTS.md; then
  ok "org-modus: org-standarden står øverst i AGENTS.md"
else bad "org-modus: org-standarden mangler øverst i AGENTS.md"; fi
if python3 -c "import json,sys; d=json.load(open('.github/hooks/loop-guards.json')); sys.exit(0 if any('compliance-check.py hook' in h['bash'] for h in d['hooks'].get('preToolUse', [])) else 1)"; then
  ok "org-modus: compliance-hooken er registrert"
else bad "org-modus: compliance-hooken mangler i loop-guards.json"; fi
for f in docs/loop/compliance.md tasks/compliance-check.py; do
  [ -f "$f" ] && ! grep -q '{{' "$f" && ok "org-modus: $f generert" || bad "org-modus: $f mangler eller har tokens"
done
run python3 tasks/compliance-check.py --self-test
git add -A >/dev/null && git -c user.name=ci -c user.email=ci@ci commit -qm org
python3 "$WORK/setup-body.py" >/dev/null 2>&1
if [ -z "$(git status --porcelain)" ]; then ok "org-modus: /setup er idempotent"; else bad "org-modus: /setup endret filer ved ny kjøring"; fi

echo
if [ $FAIL -eq 0 ]; then echo "GRØNN: Copilot-kitet er installerbart og alle kontroller består."; exit 0; fi
echo "RØD: se FEIL-linjene over."; exit 1
