#!/usr/bin/env bash
# scaffolding/scripts/setup.sh — render scaffolding files fra loop.config.yaml.
#
# VIKTIG FORSKJELL fra kildens /setup (se docs/PORTING-DECISIONS.md §3-4): dette
# skriptet kompilerer KUN scaffolding (githooks, CI-workflow, tasks/-READMEs) —
# ikke rolle- eller kommando-templates. De leses av koordinatoren direkte ved
# hvert dispatch og trenger ingen kompileringssteg eller restart. Dette skriptet
# kjøres derfor typisk ÉN gang per prosjekt (og på nytt kun hvis
# branch-navn/verifiseringskommandoer endres).
#
# Bruk (fra prosjektets rot, med copilot-agent-orchestrator/ og en utfylt
# loop.config.yaml til stede):
#   bash copilot-agent-orchestrator/scaffolding/scripts/setup.sh
#
# Prinsipper (samme disiplin som kildens /setup):
#   1. Deterministisk substitusjon — ingen verdier skrives inn med skjønn.
#   2. Valideringsgate: stopper hardt hvis en påkrevd nøkkel mangler, eller hvis
#      et {{TOKEN}} står igjen usubstituert i en generert fil.
#   3. Idempotent for de fleste filer (overskriver rent). SEED_ONLY-filer
#      (docs/run-log.md) seedes kun når de mangler — overskrives ALDRI, for å
#      ikke nullstille koordinatorens akkumulerte telemetri.
#   4. Kilde vs. generert adskilt: templates/scaffolding-filene i
#      copilot-agent-orchestrator/ er kilden; dette skriptet skriver til
#      prosjektets faktiske stier (.githooks/, .github/workflows/, scripts/,
#      tasks/, docs/).

set -euo pipefail

kit_dir="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
project_root="$(pwd)"
config_file="${1:-$project_root/loop.config.yaml}"

if [ ! -f "$config_file" ]; then
  echo "FEIL: fant ikke $config_file — kopier loop.config.example.yaml, fyll den ut, og kjør på nytt." >&2
  exit 1
fi

# --- Enkel YAML-lesing (flate og én-nivå-nøstede skalarer) -------------------
# Ikke en generell YAML-parser — dekker kun nøkkelformen i loop.config.example.yaml.
yaml_get() {
  # yaml_get <key>            -> topnivå-skalar
  # yaml_get <parent.key>     -> ett nivå nøstet skalar (2-space indent)
  key="$1"
  case "$key" in
    *.*)
      parent="${key%%.*}"
      child="${key#*.}"
      awk -v parent="$parent" -v child="$child" '
        $0 ~ "^"parent":" { in_block=1; next }
        in_block && /^[^ ]/ { in_block=0 }
        in_block && $0 ~ "^  "child":" {
          sub("^  "child":[ \t]*", "");
          sub(/[ \t]+#.*$/, "");
          gsub(/^"|"$/, "");
          print; exit
        }
      ' "$config_file"
      ;;
    *)
      awk -v k="$key" '
        $0 ~ "^"k":" {
          sub("^"k":[ \t]*", "");
          sub(/[ \t]+#.*$/, "");
          gsub(/^"|"$/, "");
          print; exit
        }
      ' "$config_file"
      ;;
  esac
}

require() {
  val="$(yaml_get "$1")"
  if [ -z "$val" ]; then
    echo "FEIL: påkrevd nøkkel «$1» mangler eller er tom i $config_file." >&2
    exit 1
  fi
  printf '%s' "$val"
}

PROJECT_NAME="$(require project_name)"
GITHUB_REPO="$(require github_repo)"
BASE_BRANCH="$(require branch_strategy.base_branch)"
RELEASE_BRANCH="$(require branch_strategy.release_branch)"
PROD_BRANCH="$(require branch_strategy.prod_branch)"
DEV_ENV_ID="$(require environments.dev_id)"
PROD_ENV_ID="$(require environments.prod_id)"
CMD_TEST="$(yaml_get verification_commands.test)"
CMD_TYPE_CHECK="$(yaml_get verification_commands.type_check_script)"
CMD_LINT="$(yaml_get verification_commands.lint)"
RELEASE_COMMAND="$(yaml_get release.command)"

echo "Config lest: project_name=$PROJECT_NAME base_branch=$BASE_BRANCH prod_branch=$PROD_BRANCH"

substitute() {
  # substitute <src> <dest>
  src="$1"; dest="$2"
  mkdir -p "$(dirname "$dest")"
  sed \
    -e "s|{{PROJECT_NAME}}|$PROJECT_NAME|g" \
    -e "s|{{GITHUB_REPO}}|$GITHUB_REPO|g" \
    -e "s|{{BASE_BRANCH}}|$BASE_BRANCH|g" \
    -e "s|{{RELEASE_BRANCH}}|$RELEASE_BRANCH|g" \
    -e "s|{{PROD_BRANCH}}|$PROD_BRANCH|g" \
    -e "s|{{DEV_ENV_ID}}|$DEV_ENV_ID|g" \
    -e "s|{{PROD_ENV_ID}}|$PROD_ENV_ID|g" \
    -e "s|{{CMD_TEST}}|$CMD_TEST|g" \
    -e "s|{{CMD_TYPE_CHECK}}|$CMD_TYPE_CHECK|g" \
    -e "s|{{CMD_LINT}}|$CMD_LINT|g" \
    -e "s|{{RELEASE_COMMAND}}|$RELEASE_COMMAND|g" \
    "$src" > "$dest"

  if grep -qE '\{\{[A-Z_]+\}\}' "$dest"; then
    echo "FEIL: $dest har gjenværende usubstituerte tokens:" >&2
    grep -oE '\{\{[A-Z_]+\}\}' "$dest" | sort -u >&2
    exit 1
  fi
}

# --- Githooks -----------------------------------------------------------------
substitute "$kit_dir/scaffolding/githooks/pre-commit" "$project_root/.githooks/pre-commit"
substitute "$kit_dir/scaffolding/githooks/pre-push"   "$project_root/.githooks/pre-push"
chmod +x "$project_root/.githooks/pre-commit" "$project_root/.githooks/pre-push"
# base_branch="dev" / protected_branch="main" i hookene er PLACEHOLDER-verdier
# (ikke {{TOKEN}}-er) — de rettes her, én gang, idempotent:
sed -i.bak "s|^base_branch=\"dev\"|base_branch=\"$BASE_BRANCH\"|" "$project_root/.githooks/pre-commit" && rm -f "$project_root/.githooks/pre-commit.bak"
sed -i.bak "s|^protected_branch=\"main\"|protected_branch=\"$PROD_BRANCH\"|" "$project_root/.githooks/pre-push" && rm -f "$project_root/.githooks/pre-push.bak"

echo "Githooks skrevet. Aktiver med: git config core.hooksPath .githooks"

# --- CI-workflow ----------------------------------------------------------------
substitute "$kit_dir/scaffolding/github-workflows/ci.yml" "$project_root/.github/workflows/ci.yml"

# --- Todo-nr-kollisjonsskript (kopieres rått, ingen tokens i kjørbar logikk selv) --
mkdir -p "$project_root/scripts"
substitute "$kit_dir/scaffolding/scripts/check-todo-nr-collisions.sh" "$project_root/scripts/check-todo-nr-collisions.sh"
substitute "$kit_dir/scaffolding/scripts/check-todo-nr-premerge.sh" "$project_root/scripts/check-todo-nr-premerge.sh"
chmod +x "$project_root/scripts/check-todo-nr-collisions.sh" "$project_root/scripts/check-todo-nr-premerge.sh"

# --- tasks/-READMEs ---------------------------------------------------------------
substitute "$kit_dir/templates/tasks/todos/README.md" "$project_root/tasks/todos/README.md"
substitute "$kit_dir/templates/tasks/bugs/inbox/README.md" "$project_root/tasks/bugs/inbox/README.md"

# --- Seed-only: docs/run-log.md (aldri overskriv en eksisterende) ----------------
run_log="$project_root/docs/run-log.md"
if [ -f "$run_log" ]; then
  echo "docs/run-log.md finnes allerede — hoppet over (seed-only, ikke overskrevet)."
else
  substitute "$kit_dir/docs/run-log.md" "$run_log"
  echo "docs/run-log.md seedet."
fi

# --- tasks/todo_archive.md (seed tom hvis den ikke finnes) ------------------------
archive="$project_root/tasks/todo_archive.md"
if [ ! -f "$archive" ]; then
  mkdir -p "$(dirname "$archive")"
  printf '# Todo-arkiv\n\n<!-- Koordinatoren appender hit. Ikke rediger eksisterende oppføringer. -->\n' > "$archive"
  echo "tasks/todo_archive.md seedet (tom)."
fi

echo ""
echo "Ferdig. Neste steg:"
echo "  1. git config core.hooksPath .githooks"
echo "  2. Kopier eventuelle tech-review-agenter fra copilot-agent-orchestrator/examples/ inn i"
echo "     templates/roles/ (eller prosjektets egen agent-konvensjon) og registrer dem i"
echo "     loop.config.yaml under tech_review_agents (tom liste er gyldig)."
echo "  3. Commit de genererte filene (.githooks/, .github/workflows/ci.yml, scripts/, tasks/, docs/run-log.md)."
echo "  4. Les copilot-agent-orchestrator/docs/orchestration-loop.md og start koordinator-sesjonen."
