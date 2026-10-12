#!/usr/bin/env bash
# {{PROJECT_NAME}} — readonly-check.sh: beviser at en read-only-rolle (reviewer, code-reviewer,
# scout, tech-review-agenter) ikke har endret sin worktree.
#
# Bruk:  bash scripts/readonly-check.sh <WORKTREE> <base-sha>
#   <WORKTREE>  worktreen rollen fikk i prompten (WORKTREE: <sti>), laget av
#               scripts/bootstrap-worktree.sh <todo-nr> <rolle>
#   <base-sha>  HEAD i worktreen FØR dispatch (koordinatoren noterer `git -C <WORKTREE> rev-parse HEAD`)
#
# Kjøres av koordinatoren etter HVER read-only-dispatch. To lag håndhever read-only:
#   1. agentfila har ikke `edit` i `tools` (Copilot håndhever verktøylisten), og
#   2. dette skriptet: et `execute`-verktøy kan fortsatt skrive via shell, så tilstanden måles.
# preToolUse-payloaden har ingen agent-identitet, så en hook kan ikke skille en read-only-rolle
# fra koordinatoren — derfor en måling etterpå i stedet for en vakt underveis.
#
# Brudd når:
#   - `git status --porcelain --untracked-files=all` ikke er tom (endrede, stagede, slettede eller
#     nye filer — ignorerte filer, f.eks. avhengigheter og env-kopien fra bootstrap, teller ikke), eller
#   - HEAD har flyttet seg fra <base-sha> (commit, reset, checkout av en annen branch).
#
# Exit 0 = READONLY OK. Exit 1 = READONLY BRUDD → rapporten forkastes, nivå A.
# Exit 2 = bruksfeil / kan ikke måle (behandles som brudd: en måling som ikke lar seg gjøre,
# beviser ingenting).
set -uo pipefail

usage() { echo "Bruk: bash scripts/readonly-check.sh <WORKTREE> <base-sha>" >&2; exit 2; }
[ $# -eq 2 ] || usage
WT="$1"; BASE="$2"
[ -n "$WT" ] && [ -n "$BASE" ] || usage

if [ ! -d "$WT" ]; then
  echo "READONLY KAN IKKE MÅLES: $WT finnes ikke"; exit 2
fi
if ! top=$(git -C "$WT" rev-parse --show-toplevel 2>&1); then
  echo "READONLY KAN IKKE MÅLES: $WT er ikke et git-tre ($top)"; exit 2
fi
wt_phys=$(cd "$WT" && pwd -P)
top_phys=$(cd "$top" && pwd -P)
if [ "$wt_phys" != "$top_phys" ]; then
  echo "READONLY KAN IKKE MÅLES: $WT er ikke roten i worktreen (toplevel er $top_phys)"; exit 2
fi
if ! base_sha=$(git -C "$WT" rev-parse --verify --quiet "${BASE}^{commit}"); then
  echo "READONLY KAN IKKE MÅLES: base-sha $BASE finnes ikke i $WT"; exit 2
fi
if ! head_sha=$(git -C "$WT" rev-parse --verify HEAD 2>&1); then
  echo "READONLY KAN IKKE MÅLES: HEAD i $WT kan ikke leses ($head_sha)"; exit 2
fi
if ! dirty=$(git -C "$WT" status --porcelain --untracked-files=all 2>&1); then
  echo "READONLY KAN IKKE MÅLES: git status feilet i $WT ($dirty)"; exit 2
fi

brudd=0
if [ "$head_sha" != "$base_sha" ]; then
  echo "READONLY BRUDD: HEAD har flyttet seg i $WT ($base_sha -> $head_sha)"
  brudd=1
fi
if [ -n "$dirty" ]; then
  echo "READONLY BRUDD: worktreen $WT er ikke ren:"
  printf '%s\n' "$dirty" | head -50 | sed 's/^/  /'
  brudd=1
fi
if [ "$brudd" -ne 0 ]; then
  echo "→ forkast rapporten fra read-only-rollen (nivå A)."
  exit 1
fi
echo "READONLY OK: $WT ren, HEAD = $head_sha"
exit 0
