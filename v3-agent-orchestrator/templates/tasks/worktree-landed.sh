#!/usr/bin/env bash
# Innholdsbasert "er dette landet i {{BASE_BRANCH}}?"-klassifikator for én agent-worktree.
# Se tasks/plans/todo-380-loopen-rydder-aldri-worktrees.md § 4a for design og § 9 for
# hvilket spørsmål hver vakt IKKE kan svare på.
#
# Bruk:  tasks/worktree-landed.sh <wt_path> [--ref origin/{{BASE_BRANCH}}] [--ignored-only]
#
# --ignored-only (fix-runde 1, R2): kjør KUN steg 0 (ignorerte filer utenfor allowlisten)
# og returner umiddelbart — brukes av worktree-sweep.sh sin «raske vei» (HEAD på remote +
# rent tre), som ellers aldri kalte klassifikatoren og dermed aldri så ignorerte filer som
# .env.local/*.log utenfor allowlisten før treet ble fjernet.
#
# Exit 0     = LANDED  (stdout: valgfrie "LANDED-MOVED:<sti>"-linjer, deretter "LANDED:<grunn>")
# Exit 1     = KEEP    (stdout: nøyaktig "KEEP:<grunn>")
# Exit >= 2  = intern feil (stdout: "KEEP:internal-feil:<detalj>")
#
# Kontrakt for kallstedet (worktree-sweep.sh): rc != 0 => BEHOLD. Ingen oppregning av koder
# utover dette skillet — kallstedet skal ALDRI grene på det eksakte tallet.
#
# Denne fila skal ALDRI omdirigere stderr til null-enheten (se dispatch-regelen i planen): det
# mønsteret har historisk gjort en kommandofeil om til et stille "ingen treff".
set -uo pipefail

wt="${1:-}"
ref="origin/{{BASE_BRANCH}}"
ignored_only=0
if [ -n "$wt" ]; then shift; fi
while [ $# -gt 0 ]; do
  case "$1" in
    --ref)
      # fix-runde 1, MINDRE: uten denne sjekken konsumerer `shift 2` med bare ÉN
      # gjenværende arg ingenting (bash feiler stille, $1 forblir «--ref») — evig løkke.
      if [ $# -lt 2 ]; then
        echo "KEEP:internal-feil:--ref-uten-verdi"
        exit 2
      fi
      ref="$2"
      shift 2
      ;;
    --ignored-only)
      ignored_only=1
      shift
      ;;
    *)
      echo "KEEP:internal-feil:ukjent-flagg:$1"
      exit 2
      ;;
  esac
done

if [ -z "$wt" ] || [ ! -d "$wt" ]; then
  echo "KEEP:internal-feil:mangler-wt-path"
  exit 2
fi

EMPTY_BLOB="e69de29bb2d1d6434b8b29ae775ad8c2e48c5391"
TMP=$(mktemp -d) || exit 2
trap 'rm -rf "$TMP"' EXIT

err() {
  echo "KEEP:internal-feil:$1"
  exit 2
}

keep() {
  echo "KEEP:$1"
  exit 1
}

# env_wt_is_safe_subset: en .env.local/.env.test i treet er TRYGG hvis HVER IKKE-TOM linje
# i den finnes ORDRETT som en HEL linje i hovedsjekkutens tilsvarende fil. Dette tillater at
# bootstrap-worktree.sh sin bevisste allowlist-filtrering (færre nøkler, ingen kommentarer/
# blanke linjer — se bootstrap-worktree.sh:127-130) gir et trygt tre selv om filen ikke
# lenger er byte-identisk med `cmp -s` (fix-runde: 380-oppfølging — cmp -s krevde full
# byte-likhet og holdt bootstrap-genererte trær evig KEEP).
#
# Kommentarlinjer (`#`-prefiks) hoppes IKKE over (kode-review r1, punkt 1) — bootstrap-
# worktree.sh skriver ALDRI kommentarer inn i treets kopi, så en `#`-linje i treet er lagt
# til ETTERPÅ (av noen/noe annet enn bootstrap) og er per definisjon unikt innhold, ikke en
# ufarlig rest av kildefilen. En kommentarlinje matches derfor som en HEL linje, akkurat som
# alle andre linjer — kun TOMME linjer ("") hoppes over.
#
# Skriver ALDRI ut en verdi — verken her eller i noe kall-sted som bruker denne
# funksjonen, og stderr fra selve grep-kallet omdirigeres ALDRI til null-enheten (kode-review
# r1, punkt 2 — se dispatch-regelen øverst i fila): stderr fra en `-F`-fast-streng-søk viser
# uansett bare filnavnet grep ble kalt med, aldri verdien den lette etter. En grep-feil
# (rc >= 2, f.eks. ikke-lesbar fil) telles som IKKE trygg, akkurat som et manglende
# linjetreff (rc 1) — begge gir KEEP, ALDRI LANDED.
env_wt_is_safe_subset() {
  main_file="$1"
  wt_file="$2"
  [ -r "$main_file" ] || return 1
  [ -r "$wt_file" ] || return 1
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      "") continue ;;
    esac
    if ! grep -qxF -- "$line" "$main_file"; then
      return 1
    fi
  done < "$wt_file"
  return 0
}

landed_moved_file="$TMP/landed-moved.list"
: > "$landed_moved_file"

# ---------------------------------------------------------------------------
# Steg 0 — ignorerte filer. `status --porcelain` ser dem ALDRI, men
# `git worktree remove --force` sletter dem uansett. Regenererbare kataloger/
# filer er trygge; alt annet (unntatt .env.local/.env.test, som er trygge når hver
# ikke-blank/ikke-kommentar-linje er en delmengde av hovedsjekkutens kopi — se
# env_wt_is_safe_subset() under) tvinger KEEP av hele treet.
# ---------------------------------------------------------------------------
if ! git -C "$wt" ls-files --others --ignored --exclude-standard --directory > "$TMP/ignored.txt"; then
  err "ls-files-ignored"
fi

allow_pattern='(^|/)(node_modules|test-results|playwright-report|\.expo|dist|__pycache__)(/|$)|(^|/)supabase/\.temp(/|$)|(^|/)deno\.lock$|^tasks/graph\.json$'

if ! common_git_dir=$(git -C "$wt" rev-parse --path-format=absolute --git-common-dir); then
  err "git-common-dir"
fi
main_root="${common_git_dir%/.git}"

while IFS= read -r ig; do
  [ -z "$ig" ] && continue
  if printf '%s\n' "$ig" | grep -Eq "$allow_pattern"; then
    continue
  fi
  base_ig="${ig%/}"
  if [ "$base_ig" = ".env.local" ] || [ "$base_ig" = ".env.test" ]; then
    if [ -f "$main_root/$base_ig" ] && env_wt_is_safe_subset "$main_root/$base_ig" "$wt/$base_ig"; then
      continue
    fi
    keep "ignorert-env-avviker:$base_ig"
  fi
  keep "ignorert-utenfor-allowlist:$ig"
done < "$TMP/ignored.txt"

# ---------------------------------------------------------------------------
# Steg 0b (fix-runde 1, MINDRE) — skip-worktree/assume-unchanged. `git status
# --porcelain` ser ALDRI en fil med et av disse flaggene satt, selv om innholdet
# avviker fra det som er committet — samme blindsone-klasse som steg 0 lukker for
# ignorerte filer. `git ls-files -v` tagger slike linjer med en LITEN bokstav
# (assume-unchanged) eller stor `S` (skip-worktree); alt annet er `H`/`M`/`R`/`C`/
# `K`/`?` (store bokstaver) og er allerede dekket av vanlig status-basert sjekk.
# ---------------------------------------------------------------------------
if ! git -C "$wt" ls-files -v > "$TMP/ls-files-v.txt"; then
  err "ls-files-v"
fi
if grep -Eq '^[a-zS] ' "$TMP/ls-files-v.txt"; then
  flagged=$(grep -E '^[a-zS] ' "$TMP/ls-files-v.txt" | head -1)
  keep "skip-worktree-eller-assume-unchanged:$flagged"
fi

if [ "$ignored_only" -eq 1 ]; then
  echo "LANDED:ignored-only-ok"
  exit 0
fi

# ---------------------------------------------------------------------------
# Kandidatliste — (1) uncommittet tilstand, (2) committet men ikke nådd ref.
# rc != 0 på noen av disse er en INTERN feil, ikke "ingen kandidater".
# ---------------------------------------------------------------------------
if ! mb=$(git -C "$wt" merge-base "$ref" HEAD); then
  err "merge-base"
fi

if ! git -C "$wt" status --porcelain -uall -z --no-renames > "$TMP/status.z"; then
  err "status"
fi
if ! git -C "$wt" diff --name-status -z --no-renames "$mb" HEAD > "$TMP/diff.z"; then
  err "diff"
fi

tr '\0' '\n' < "$TMP/status.z" | sed '/^$/d' > "$TMP/status.lines"
tr '\0' '\n' < "$TMP/diff.z" | sed '/^$/d' > "$TMP/diff.flat"
awk 'NR % 2 == 1 { st = $0; next } { print st "\t" $0 }' "$TMP/diff.flat" > "$TMP/diff.pairs"

if ! git -C "$wt" ls-tree -r --name-only "$ref" > "$TMP/ref-files.txt"; then
  err "ls-tree-names"
fi
if ! git -C "$wt" ls-tree -r "$ref" > "$TMP/ref-tree-raw.txt"; then
  err "ls-tree-raw"
fi
awk '$2 == "blob" { print $3 }' "$TMP/ref-tree-raw.txt" | sort -u > "$TMP/ref-blobs.txt"

# check_path: avgjør ÉN kandidatsti. Kaller keep() (exit 1) direkte hvis den ikke er landet.
# Faller bare gjennom (returnerer) når kandidaten ER landet.
check_path() {
  p="$1"

  # Rule 3 — alltid KEEP: symlink, katalog/submodul, ikke-regulær fil.
  if [ -L "$wt/$p" ]; then keep "symlink:$p"; fi
  if [ -d "$wt/$p" ]; then keep "katalog-eller-submodul:$p"; fi
  if [ ! -e "$wt/$p" ]; then keep "fil-mangler-uventet:$p"; fi
  if [ ! -f "$wt/$p" ]; then keep "ikke-regulaer-fil:$p"; fi

  # Steg 1 — samme sti i ref. Avvik er ENDELIG KEEP — ingen fallback (lukker kit-speil, C8).
  # stderr fra et forventet "finnes ikke"-oppslag går til en per-kall tempfil, ALDRI til
  # null-enheten (se dispatch-regelen øverst i fila); rc er allerede det eneste vi leser.
  if git -C "$wt" cat-file -e "$ref:$p" 2>"$TMP/cat-file-e.err"; then
    if git -C "$wt" show "$ref:$p" | cmp -s - "$wt/$p"; then
      return 0
    fi
    keep "sti-finnes-avviker:$p"
  fi

  # Steg 2 — stien finnes ikke i ref. Tom-blobb-unntaket sjekkes FØRST og gjelder
  # BEGGE fallbackene under (fix-runde 1, R3/C7b) — ellers kan en tom usporet fil
  # «lånes» LANDED via en tilfeldig tom fil et annet sted i {{BASE_BRANCH}} (cmp av to tomme
  # filer er alltid identisk, uavhengig av om innholdet faktisk har noe med
  # hverandre å gjøre, f.eks. to urelaterte `.gitkeep`-filer).
  if ! blobsha=$(git -C "$wt" hash-object --no-filters "$wt/$p"); then
    keep "hash-object-feilet:$p"
  fi
  if [ "$blobsha" = "$EMPTY_BLOB" ]; then
    keep "tom-fil-ukjent-sti:$p"
  fi

  # (a) basenavn-treff, deretter (b) blob-treff. Begge er LANDED-MOVED (fix-runde 1,
  # R4) — filen ligger ikke på sin opprinnelige sti, så sweepen må redde den til
  # RESCUE_DIR før fjerning uansett HVILKEN av de to fallbackene som traff.
  base=$(basename "$p")
  found_basename=0
  while IFS= read -r cand; do
    [ -z "$cand" ] && continue
    if [ "$(basename "$cand")" = "$base" ]; then
      if git -C "$wt" show "$ref:$cand" | cmp -s - "$wt/$p"; then
        found_basename=1
        break
      fi
    fi
  done < "$TMP/ref-files.txt"
  if [ "$found_basename" -eq 1 ]; then
    echo "$p" >> "$landed_moved_file"
    return 0
  fi

  if grep -qx "$blobsha" "$TMP/ref-blobs.txt"; then
    echo "$p" >> "$landed_moved_file"
    return 0
  fi

  keep "ingen-treff:$p"
}

# Fra status --porcelain: D/R/C/U er alltid KEEP uten videre vurdering.
while IFS= read -r line; do
  [ -z "$line" ] && continue
  code="${line:0:2}"
  path="${line:3}"
  case "$code" in
    *D*|*R*|*C*|*U*)
      keep "status-$code:$path"
      ;;
    *)
      check_path "$path"
      ;;
  esac
done < "$TMP/status.lines"

# Fra diff mellom merge-base og HEAD: samme regel.
while IFS=$'\t' read -r st path; do
  [ -z "${path:-}" ] && continue
  case "$st" in
    D|R*|C*|U|T)
      keep "diffstatus-$st:$path"
      ;;
    *)
      check_path "$path"
      ;;
  esac
done < "$TMP/diff.pairs"

while IFS= read -r moved; do
  [ -z "$moved" ] && continue
  echo "LANDED-MOVED:$moved"
done < "$landed_moved_file"
echo "LANDED:ok"
exit 0
