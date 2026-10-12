#!/usr/bin/env bash
# Validerer v3-copilot-agent-orchestrator/ slik README «Selvtest» beskriver, pluss ordvakta:
#   1. Ordvakt: ingen «claude/anthropic/opus/sonnet/haiku/superpowers» i mappa (unntatt kit-repoets URL).
#   2. /setup med uendret eksempel-config SKAL stoppe på modellplassholderne.
#   3. /setup med plassholderne byttet SKAL gå grønt, uten gjenværende tokens og med gyldig
#      YAML-frontmatter og gyldig loop-guards.json, og en ny kjøring SKAL være idempotent.
#   4. Alle harnesser og selvtester på det installerte kitet SKAL være grønne.
#   6. Org-laget (org-overlay-template/): skriptene er gyldige, apply-org-config.sh og /setup virker.
#   5. Styring: /setup krever instruksfila når den er satt, setter den inn øverst i AGENTS.md og
#      registrerer governance-hooken; governance-check.py --self-test SKAL være grønn.
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

# 5. Styring (governance.enabled: true) ------------------------------------------------------
new_project "$WORK/governance"
sed -i.bak 's/<DYP_MODELL>/deep-model-a/g; s/<KODE_MODELL>/code-model-b/g; s/<BILLIG_MODELL>/cheap-model-c/g; s/^  enabled: false$/  enabled: true/; s|^  # instructions_file: |  instructions_file: |; s|^  # approved_mcp_servers: |  approved_mcp_servers: |' \
  v3-copilot-agent-orchestrator/loop.config.yaml
if python3 "$WORK/setup-body.py" >"$WORK/g1.out" 2>&1; then bad "styring: /setup gikk grønt uten instruksfil"
elif grep -q 'instructions_file' "$WORK/g1.out"; then ok "styring: /setup stopper når instruksfila mangler"
else bad "styring: uventet feil uten instruksfil:"; tail -5 "$WORK/g1.out" | sed 's/^/      /'; fi
mkdir -p docs/standards && printf '# Standard\n\nAgenten skal aldri skrive ut hemmeligheter.\n' > docs/standards/AGENTS.standard.md
if python3 "$WORK/setup-body.py" >"$WORK/g2.out" 2>&1 && grep -q 'Ingen gjenværende tokens' "$WORK/g2.out"; then
  ok "styring: /setup exit 0, ingen gjenværende tokens"
else bad "styring: /setup feilet:"; tail -15 "$WORK/g2.out" | sed 's/^/      /'; fi
if head -1 AGENTS.md | grep -q 'INSTRUKSFIL START' && grep -q 'aldri skrive ut hemmeligheter' AGENTS.md; then
  ok "styring: instruksfila står øverst i AGENTS.md"
else bad "styring: instruksfila mangler øverst i AGENTS.md"; fi
if python3 -c "import json,sys; d=json.load(open('.github/hooks/loop-guards.json')); sys.exit(0 if any('governance-check.py hook' in h['bash'] for h in d['hooks'].get('preToolUse', [])) else 1)"; then
  ok "styring: governance-hooken er registrert"
else bad "styring: governance-hooken mangler i loop-guards.json"; fi
for f in docs/loop/governance.md tasks/governance-check.py; do
  [ -f "$f" ] && ! grep -q '{{' "$f" && ok "styring: $f generert" || bad "styring: $f mangler eller har tokens"
done
grep -q 'godkjenning av plan' docs/loop/steps/4-dispatch-reviewer.md && ok "styring: plangodkjenning i §4" || bad "styring: plangodkjenning mangler i §4"
run python3 tasks/governance-check.py --self-test
git add -A >/dev/null && git -c user.name=ci -c user.email=ci@ci commit -qm gov
python3 "$WORK/setup-body.py" >/dev/null 2>&1
if [ -z "$(git status --porcelain)" ]; then ok "styring: /setup er idempotent"; else bad "styring: /setup endret filer ved ny kjøring"; fi

# 6. Org-laget (org-overlay-template/) oppå kitet -----------------------------------------------
OVL="$ROOT/org-overlay-template"
if [ -d "$OVL" ]; then
  new_project "$WORK/overlay"
  cp -R "$OVL/." .
  sed -i.bak 's/<DYP_MODELL>/deep-model-a/g; s/<KODE_MODELL>/code-model-b/g; s/<BILLIG_MODELL>/cheap-model-c/g' \
    v3-copilot-agent-orchestrator/loop.config.yaml
  for f in scripts/upgrade-kit.sh scripts/check-kit-upgrade.sh scripts/apply-org-config.sh; do run bash -n "$f"; done
  if bash scripts/apply-org-config.sh >/dev/null && bash scripts/apply-org-config.sh >/dev/null \
     && [ "$(grep -c '^governance:' v3-copilot-agent-orchestrator/loop.config.yaml)" = 1 ]; then
    ok "org-lag: apply-org-config.sh setter governance-blokken (idempotent)"
  else bad "org-lag: apply-org-config.sh feilet"; fi
  if python3 "$WORK/setup-body.py" >"$WORK/ov.out" 2>&1 && grep -q 'Ingen gjenværende tokens' "$WORK/ov.out" \
     && head -1 AGENTS.md | grep -q 'INSTRUKSFIL START'; then
    ok "org-lag: /setup med org-config gir org-standarden øverst i AGENTS.md"
  else bad "org-lag: /setup med org-config feilet:"; tail -10 "$WORK/ov.out" | sed 's/^/      /'; fi
fi

echo
if [ $FAIL -eq 0 ]; then echo "GRØNN: Copilot-kitet er installerbart og alle kontroller består."; exit 0; fi
echo "RØD: se FEIL-linjene over."; exit 1
