#!/usr/bin/env bash
# {{PROJECT_NAME}} — bootstrap-worktree.sh
#
# Gjør en fersk agent-worktree kjørbar:
#   1. Synker avhengigheter mot lockfile med worktree_bootstrap.install_cmd
#      (idempotent; kjøres kun når install_marker mangler eller er eldre enn lockfila).
#   2. Kopierer et definert MINIMALT sett env-nøkler fra hovedsjekkuten inn i denne
#      worktreen (nøkkel-for-nøkkel, aldri hele filer, aldri nøkler med et forbudt prefiks).
#
# Skriver ALDRI nøkkelverdier til stdout — kun nøkkelnavn og status.
#
# Alle verdier kommer fra worktree_bootstrap i loop.config.yaml, substituert av /setup.
# Mangler seksjonen, er både installasjon og env-kopi tomme — skriptet er da en trygg no-op.
#
# Bakgrunn (kildeprosjektet): avhengighets- og env-friksjon i agent-worktrees ble
# re-diagnostisert runde etter runde før oppskriften ble en lesson. Dette skriptet gjør
# lessonen kjørbar.

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
