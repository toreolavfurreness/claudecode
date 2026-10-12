#!/usr/bin/env bash
# {{PROJECT_NAME}} — bootstrap-worktree.sh
#
# To moduser:
#
#   bash scripts/bootstrap-worktree.sh <todo-nr> <rolle>
#     Lag-modus (koordinatoren, FØR dispatch). Lager `.loop-worktrees/<rolle>-<todo-nr>` under
#     hovedsjekkuten på en egen branch `loop/<rolle>-<todo-nr>` fra `origin/{{BASE_BRANCH}}`
#     (gjenbruker worktreen hvis den allerede finnes — f.eks. en fersk fix-dispatch for samme
#     rolle), kjører bootstrap-modus inni den, og skriver worktree-stien (fysisk, absolutt) som
#     ENESTE linje på stdout, så `WT=$(bash scripts/bootstrap-worktree.sh 42 implementer)` virker.
#     All logg går til stderr. Stien sendes til workeren i prompten som `WORKTREE: <sti>`.
#     <todo-nr> er et todo-nummer eller en annen id som matcher ^[a-z0-9-]+$ (f.eks. `health`
#     for helsesjekken); <rolle> matcher også ^[a-z0-9-]+$ (planner, reviewer, implementer,
#     code-reviewer, et tech-review-agentnavn …).
#
#   bash scripts/bootstrap-worktree.sh
#     Bootstrap-modus (uten argumenter, idempotent) i GJELDENDE worktree — kjøres fra worktree-
#     roten av workeren selv (Steg 0) og av skills som trenger avhengigheter:
#       1. Synker avhengigheter mot lockfile med worktree_bootstrap.install_cmd
#          (idempotent; kjøres kun når install_marker mangler eller er eldre enn lockfila).
#       2. Kopierer et definert MINIMALT sett env-nøkler fra hovedsjekkuten inn i denne
#          worktreen (nøkkel-for-nøkkel, aldri hele filer, aldri nøkler med et forbudt prefiks).
#     Logger til stdout som før.
#
# Skriver ALDRI nøkkelverdier — kun nøkkelnavn og status.
#
# Alle verdier kommer fra worktree_bootstrap i loop.config.yaml, substituert av /setup.
# Mangler seksjonen, er både installasjon og env-kopi tomme — bootstrap-modus er da en trygg no-op.
#
# Bakgrunn: avhengighets- og env-friksjon i agent-worktrees ble
# re-diagnostisert runde etter runde før oppskriften ble en lesson. Dette skriptet gjør
# lessonen kjørbar. Copilot-subagenter deler filsystem og arbeidskatalog med koordinatoren, så
# isolasjonen er en worktree koordinatoren lager før dispatch — ikke noe harnessen gjør.

set -euo pipefail

# Restriktiv default-permisjon for alt dette skriptet skriver (env-filer inneholder
# hemmeligheter). Fjerner vinduet mellom `printf > "$DST"` og en etterfølgende `chmod 600`
# der fila ellers ville vært verden-lesbar.
umask 077

INSTALL_CMD=$(cat <<'CMD'
{{BOOTSTRAP_INSTALL_CMD}}
CMD
)
LOCKFILE="{{BOOTSTRAP_LOCKFILE}}"
INSTALL_MARKER="{{BOOTSTRAP_INSTALL_MARKER}}"
ENV_FILES=({{BOOTSTRAP_ENV_FILES}})
# Kun disse nøklene kopieres, uansett hvilke andre nøkler kildefilene måtte inneholde.
ALLOWED_KEYS=(
{{BOOTSTRAP_ENV_ALLOWED_KEYS}}
)
# Forsvar i dybden: en worktree-fil som likevel inneholder en nøkkel som matcher denne
# regexen, slettes. Tom = ingen denylist.
DENY_RE="{{BOOTSTRAP_ENV_DENY_REGEX}}"

# --- 0. Lag-modus: <todo-nr> <rolle> ----------------------------------------

BASE_BRANCH="{{BASE_BRANCH}}"
SELF_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/$(basename "${BASH_SOURCE[0]}")"

if [ $# -gt 0 ]; then
  if [ $# -ne 2 ]; then
    echo "Bruk: bash scripts/bootstrap-worktree.sh [<todo-nr> <rolle>]" >&2
    exit 2
  fi
  ID="$1"; ROLE="$2"
  for v in "$ID" "$ROLE"; do
    if ! printf '%s' "$v" | grep -Eq '^[a-z0-9-]+$' || [ "${v#-}" != "$v" ]; then
      echo "FEIL: ugyldig id/rolle '$v' (må matche ^[a-z0-9-]+$ og ikke starte med -)." >&2
      exit 2
    fi
  done
  if ! COMMON=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null); then
    echo "FEIL: ikke et git-repo (git rev-parse --git-common-dir feilet)." >&2
    exit 1
  fi
  MAIN=$(cd "$COMMON/.." && pwd -P)
  NAME="$ROLE-$ID"
  WT="$MAIN/.loop-worktrees/$NAME"
  BRANCH="loop/$NAME"

  if [ -e "$WT" ]; then
    # Gjenbruk kun en REGISTRERT worktree med egen rot — en løs mappe med samme navn er en feil.
    if ! git -C "$MAIN" worktree list --porcelain | grep -qxF "worktree $WT"; then
      echo "FEIL: $WT finnes, men er ikke en registrert worktree. Sjekk innholdet og fjern den manuelt før ny dispatch." >&2
      exit 1
    fi
    echo "worktree: gjenbruker $WT ($(git -C "$WT" rev-parse --abbrev-ref HEAD))" >&2
  else
    if ! git -C "$MAIN" fetch -q origin "$BASE_BRANCH" >&2; then
      echo "ADVARSEL: git fetch origin $BASE_BRANCH feilet — bruker eksisterende origin/$BASE_BRANCH." >&2
    fi
    if ! git -C "$MAIN" rev-parse --verify --quiet "origin/$BASE_BRANCH^{commit}" >/dev/null; then
      echo "FEIL: origin/$BASE_BRANCH finnes ikke — kan ikke lage $WT." >&2
      exit 1
    fi
    mkdir -p "$MAIN/.loop-worktrees"
    if git -C "$MAIN" rev-parse --verify --quiet "refs/heads/$BRANCH" >/dev/null; then
      # Branchen finnes fra en tidligere runde (worktreen er ryddet) — sjekk den ut igjen, ikke
      # nullstill den: den kan bære arbeid.
      git -C "$MAIN" worktree add -q "$WT" "$BRANCH" >&2 || { echo "FEIL: git worktree add $WT $BRANCH feilet." >&2; exit 1; }
    else
      git -C "$MAIN" worktree add -q -b "$BRANCH" "$WT" "origin/$BASE_BRANCH" >&2 \
        || { echo "FEIL: git worktree add -b $BRANCH $WT origin/$BASE_BRANCH feilet." >&2; exit 1; }
    fi
    echo "worktree: laget $WT på $BRANCH fra origin/$BASE_BRANCH" >&2
  fi
  WT=$(cd "$WT" && pwd -P)
  # Bootstrap-modus inni den nye worktreen; all utskrift til stderr så stdout bare er stien.
  if ! (cd "$WT" && bash "$SELF_SCRIPT") >&2; then
    echo "FEIL: bootstrap av $WT feilet (se over)." >&2
    exit 1
  fi
  printf '%s\n' "$WT"
  exit 0
fi

# --- 1. Root-finding -------------------------------------------------------

SELF_ROOT=$(git rev-parse --show-toplevel)

if ! git rev-parse --git-common-dir >/dev/null 2>&1; then
  echo "FEIL: ikke et git-repo (git rev-parse --git-common-dir feilet)." >&2
  exit 1
fi

# git-common-dir peker på hovedsjekkutens .git-mappe (delt mellom worktrees).
# `pwd -P` gir fysisk sti — konsistent med `git rev-parse --show-toplevel`, som også alltid
# returnerer fysisk sti (macOS: /tmp er symlink til /private/tmp — asserter aldri på
# ikke-oppløst sti).
MAIN_ROOT=$(cd "$(git rev-parse --git-common-dir)" && cd .. && pwd -P)

if [ ! -d "$MAIN_ROOT/.git" ]; then
  echo "FEIL: fant ikke $MAIN_ROOT/.git — MAIN_ROOT-oppløsning ga feil sti." >&2
  exit 1
fi

echo "Hovedsjekkut-rot: $MAIN_ROOT"
echo "Denne worktreens rot: $SELF_ROOT"

# --- 2. Avhengighets-synk (idempotent, lockfile-tro) -------------------------

cd "$SELF_ROOT"

if [ -z "$INSTALL_CMD" ]; then
  echo "avhengigheter: ingen install_cmd konfigurert — hopper over."
else
  NEEDS_INSTALL=0
  if [ -n "$INSTALL_MARKER" ] && [ ! -e "$INSTALL_MARKER" ]; then
    NEEDS_INSTALL=1
  elif [ -z "$INSTALL_MARKER" ]; then
    NEEDS_INSTALL=1
  elif [ -n "$LOCKFILE" ] && [ "$LOCKFILE" -nt "$INSTALL_MARKER" ]; then
    NEEDS_INSTALL=1
  fi

  if [ "$NEEDS_INSTALL" -eq 1 ]; then
    echo "avhengigheter: mangler eller foreldet — kjører: $INSTALL_CMD"
    if ! bash -c "$INSTALL_CMD"; then
      echo "" >&2
      echo "FEIL: '$INSTALL_CMD' feilet. Dette er typisk lockfile-drift (${LOCKFILE:-lockfila}" >&2
      echo "matcher ikke manifestet), IKKE en feil i dette skriptet." >&2
      echo "Diagnose: resynk lockfila i HOVEDSJEKKUTEN ($MAIN_ROOT), commit den, og prøv" >&2
      echo "deretter dette skriptet på nytt i worktreen." >&2
      exit 1
    fi
    echo "avhengigheter: installasjon fullført."
  else
    echo "avhengigheter: ajour (ingen installasjon nødvendig)."
  fi
fi

# --- 3. Env-kopi (default-deny allowlist) ----------------------------------

is_allowed_key() {
  local key="$1"
  local allowed
  for allowed in "${ALLOWED_KEYS[@]+"${ALLOWED_KEYS[@]}"}"; do
    if [ "$key" = "$allowed" ]; then
      return 0
    fi
  done
  return 1
}

if [ "${#ENV_FILES[@]}" -eq 0 ] || [ "${#ALLOWED_KEYS[@]}" -eq 0 ]; then
  echo "env: ingen env_files/env_allowed_keys konfigurert — hopper over env-kopi."
elif [ "$SELF_ROOT" = "$MAIN_ROOT" ]; then
  echo "Kjører fra hovedsjekkuten — hopper over env-kopi (hovedsjekkuten har allerede sine egne env-filer)."
else
  for envfile in "${ENV_FILES[@]}"; do
    SRC="$MAIN_ROOT/$envfile"
    DST="$SELF_ROOT/$envfile"

    if [ ! -f "$SRC" ]; then
      echo "$envfile: MANGLER i kilde ($SRC) — hopper over."
      for key in "${ALLOWED_KEYS[@]}"; do
        echo "  $envfile: $key — MANGLER i kilde"
      done
      continue
    fi

    OLD_DST_CONTENT=""
    [ -f "$DST" ] && OLD_DST_CONTENT=$(cat "$DST")

    # Bygg filtrert innhold: kun linjer der KEY (splittet på FØRSTE '=') er en eksakt
    # (ikke prefiks-) match i ALLOWED_KEYS. Blanke linjer og kommentarer hoppes over.
    FILTERED=""
    while IFS= read -r line || [ -n "$line" ]; do
      case "$line" in
        ""|\#*) continue ;;
      esac
      key="${line%%=*}"
      value="${line#*=}"
      if is_allowed_key "$key"; then
        FILTERED="${FILTERED}${key}=${value}"$'\n'
      fi
    done < "$SRC"

    # Skriv kun hvis innholdet avviker fra eksisterende worktree-fil (idempotent no-op på
    # kjøring #2).
    if [ "$OLD_DST_CONTENT" = "$(printf '%s' "$FILTERED")" ]; then
      WROTE=0
    else
      printf '%s' "$FILTERED" > "$DST"
      WROTE=1
    fi
    # chmod 600 ubetinget — håndhever permen idempotent selv om fila fantes med feil rettigheter.
    [ -f "$DST" ] && chmod 600 "$DST"

    # Positiv selv-verifisering: nøklene i den skrevne fila MÅ være en eksakt delmengde av
    # ALLOWED_KEYS (membership-sjekk, ikke bare denylist).
    while IFS= read -r written_key; do
      [ -z "$written_key" ] && continue
      if ! is_allowed_key "$written_key"; then
        echo "KRITISK: $DST inneholder nøkkelen '$written_key' som IKKE er i ALLOWED_KEYS." >&2
        rm -f "$DST"
        echo "Filen er slettet. Dette er en skript-bug — meld fra, ikke prøv på nytt uten fiks." >&2
        exit 1
      fi
    done < <(cut -d= -f1 "$DST" 2>/dev/null || true)

    # Per-nøkkel rapport (aldri verdier).
    for key in "${ALLOWED_KEYS[@]}"; do
      if ! grep -q "^${key}=" "$SRC"; then
        echo "  $envfile: $key — MANGLER i kilde"
      elif [ "$WROTE" -eq 1 ]; then
        echo "  $envfile: $key — kopiert"
      else
        echo "  $envfile: $key — allerede identisk"
      fi
    done
  done
fi

# --- 4. Denylist-assertion (defense-in-depth) ------------------------------

# Kjøres KUN når denne worktreen er forskjellig fra hovedsjekkuten. Uten denne guarden ville
# en kjøring FRA hovedsjekkuten grep-e dens EKTE env-filer (som legitimt kan inneholde
# forbudte nøkler), treffe, og SLETTE utviklerens ekte — gitignorerte, uopprettelige —
# hemmelighetsfil. Denylisten skal KUN validere worktree-SKREVNE filer.
if [ -n "$DENY_RE" ] && [ "$SELF_ROOT" != "$MAIN_ROOT" ]; then
  DENYLIST_HIT=0
  for envfile in "${ENV_FILES[@]+"${ENV_FILES[@]}"}"; do
    DST="$SELF_ROOT/$envfile"
    [ -f "$DST" ] || continue
    if grep -E "$DENY_RE" "$DST" >/dev/null 2>&1; then
      echo "KRITISK: $DST inneholder en forbudt nøkkel (matcher $DENY_RE)." >&2
      rm -f "$DST"
      echo "Filen er slettet. Dette er en allowlist-bug — meld fra, ikke prøv på nytt uten fiks." >&2
      DENYLIST_HIT=1
    fi
  done
  if [ "$DENYLIST_HIT" -eq 1 ]; then
    exit 1
  fi
fi

# --- 5. Sammendrag ----------------------------------------------------------

echo ""
echo "Bootstrap fullført."
[ -n "$DENY_RE" ] && echo "Bevisst utelatt fra env-kopien: alle nøkler som matcher $DENY_RE."
exit 0
