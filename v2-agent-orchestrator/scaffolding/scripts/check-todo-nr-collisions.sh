#!/bin/sh
# SCAFFOLDING — maskinell gate mot todo-nr-kollisjoner mellom parallelle
# koordinatorer. Kopier til prosjektets scripts/ og kall den fra CI (se
# scaffolding/github-workflows/ci.yml, jobben `todo-nr-guard`).
# POSIX sh, macOS/BSD-trygt. Ingen GNU-only-flagg (aldri `sed s///i`, aldri `grep -P`)
# — kasus-folding gjøres med `tr`, ekstraksjon med `grep -oE`/`grep -ioE` (begge
# støttet av BSD grep på macOS).
#
# Kilder (KANONISKE — aldri en aggregert indeksfil, jf. tasks/todos/README.md):
#   - tasks/todos/todo-*.md   frontmatter `nr:` + `status:` (README.md er IKKE
#     inkludert — globbet er `todo-*.md`, ikke `*.md`)
#   - tasks/todo_archive.md   `## TODO-N` / `## todo-N`-overskrifter (blandet kasus)
#
# Tre-sett-modell:
#   LIVE    = nr fra aktive filer med status == open
#   RETIRED = nr fra aktive filer med status == done  ∪  arkiv-overskrifter
#   PARKED  = nr fra aktive filer med status ∈ {split, deferred}
#
# Blokkerende (exit 1):
#   (1) Intern duplikat   — samme nr i ≥2 distinkte AKTIVE filer, UANSETT status
#   (2) Gjenbruk          — LIVE ∩ RETIRED (et open-nr som alt er pensjonert)
# Ikke-blokkerende (exit 0, WARN til stderr):
#   (3) Premature-archive — PARKED ∩ arkiv (§6.3-kontraktbrudd — arkivert før
#       `status` ble satt til `done`). Synliggjøres, gater ALDRI en urelatert PR.
#
# Kollisjonsenheten er HELE (case-foldede) `nr`-strengen, ALDRI bare-nummeret —
# suffiks-par (`238`/`238B`) er distinkte strenger og flagges derfor aldri.
#
# Modus:
#   sh scripts/check-todo-nr-collisions.sh          kjør kollisjonssjekken
#   sh scripts/check-todo-nr-collisions.sh --next    skriv neste ledige nr til stdout
#
# Exit: 0 = ingen blokkerende kollisjon (WARN kan likevel være skrevet til stderr)
#       1 = ≥1 blokkerende kollisjon (stdout lister hvert kolliderende nr + kildene)
#       2 = intern feil (tasks/todos ikke funnet relativt til nåværende katalog)
#
# Kjøres fra repo-roten (slik CI-jobben og koordinatorens §6-pre-merge-kjøring gjør
# det) — bevisst IKKE selv-lokaliserende via `git`, slik at den kan kjøres mot et
# rent `tasks/`-fixture-tre uten å måtte være et ekte git-repo.

set -u

mode="${1:-check}"

todos_dir="tasks/todos"
archive_path="tasks/todo_archive.md"

if [ ! -d "$todos_dir" ]; then
  printf 'FEIL: fant ikke %s relativt til %s — kjør scriptet fra repo-roten.\n' \
    "$todos_dir" "$(pwd)" >&2
  exit 2
fi

tmp_dir=$(mktemp -d) || exit 2
trap 'rm -rf "$tmp_dir"' EXIT

# --- Les aktive filer: nr<TAB>klasse<TAB>path --------------------------------
active_file="$tmp_dir/active.tsv"
: > "$active_file"

for f in "$todos_dir"/todo-*.md; do
  [ -e "$f" ] || continue

  nr_raw=$(awk '/^---[[:space:]]*$/{c++; next} c==1 && /^nr:/{print; exit}' "$f")
  status_raw=$(awk '/^---[[:space:]]*$/{c++; next} c==1 && /^status:/{print; exit}' "$f")

  nr=$(printf '%s' "$nr_raw" \
    | sed -e 's/^nr:[[:space:]]*//' -e "s/[\"']//g" -e 's/[[:space:]]*$//' \
    | tr '[:lower:]' '[:upper:]')
  status=$(printf '%s' "$status_raw" \
    | sed -e 's/^status:[[:space:]]*//' -e 's/[[:space:]]*#.*$//' -e 's/[[:space:]]*$//')

  if [ -z "$nr" ] || [ -z "$status" ]; then
    printf 'ADVARSEL: mangler nr/status i %s — hoppet over.\n' "$f" >&2
    continue
  fi

  case "$status" in
    open) class=OPEN ;;
    done) class=DONE ;;
    split|deferred) class=PARKED ;;
    *) class=OTHER ;;
  esac

  printf '%s\t%s\t%s\n' "$nr" "$class" "$f" >> "$active_file"
done

# --- Les arkiv-overskrifter, case-foldet, prefiks stripped -------------------
archive_file="$tmp_dir/archive.txt"
if [ -f "$archive_path" ]; then
  grep -ioE '^##[[:space:]]*todo-[0-9]+[a-z]*' "$archive_path" \
    | tr '[:lower:]' '[:upper:]' \
    | sed -e 's/^##[[:space:]]*TODO-//' \
    > "$archive_file"
else
  : > "$archive_file"
fi

# --- Bygg settene -------------------------------------------------------------
open_file="$tmp_dir/open.txt"
awk -F'\t' '$2=="OPEN"{print $1}' "$active_file" | sort -u > "$open_file"

done_file="$tmp_dir/done.txt"
awk -F'\t' '$2=="DONE"{print $1}' "$active_file" | sort -u > "$done_file"

parked_file="$tmp_dir/parked.txt"
awk -F'\t' '$2=="PARKED"{print $1}' "$active_file" | sort -u > "$parked_file"

retired_file="$tmp_dir/retired.txt"
cat "$done_file" "$archive_file" | sort -u > "$retired_file"

# --- --next-modus: max(numerisk del av OPEN ∪ RETIRED ∪ PARKED) + 1 ----------
if [ "$mode" = "--next" ]; then
  all_nrs_file="$tmp_dir/all_nrs.txt"
  cat "$open_file" "$retired_file" "$parked_file" | sort -u > "$all_nrs_file"

  max=0
  while IFS= read -r nr; do
    [ -z "$nr" ] && continue
    num=$(printf '%s' "$nr" | grep -oE '^[0-9]+' || true)
    [ -z "$num" ] && continue
    # Strip ledende nuller POSIX-rent (ikke bash-ismen 10#) så $(( )) ikke tolker oktal
    num=$(printf '%s' "$num" | sed 's/^0*//')
    num=${num:-0}
    num=$((num))
    if [ "$num" -gt "$max" ]; then
      max=$num
    fi
  done < "$all_nrs_file"

  echo $((max + 1))
  exit 0
fi

# --- (1) Intern duplikat: samme nr i ≥2 distinkte aktive filer, uansett status
dup_nrs_file="$tmp_dir/dup_nrs.txt"
cut -f1 "$active_file" | sort | uniq -d > "$dup_nrs_file"

# --- (2) Gjenbruk: LIVE (OPEN) ∩ RETIRED (DONE ∪ arkiv) -----------------------
reuse_file="$tmp_dir/reuse.txt"
: > "$reuse_file"
if [ -s "$open_file" ] && [ -s "$retired_file" ]; then
  grep -Fxf "$retired_file" "$open_file" > "$reuse_file" 2>/dev/null || true
fi

# --- (3) Premature-archive: PARKED ∩ arkiv (kun arkiv-siden, ikke DONE) -------
premature_file="$tmp_dir/premature.txt"
: > "$premature_file"
if [ -s "$parked_file" ] && [ -s "$archive_file" ]; then
  grep -Fxf "$archive_file" "$parked_file" > "$premature_file" 2>/dev/null || true
fi

exit_code=0

if [ -s "$dup_nrs_file" ]; then
  exit_code=1
  echo "BLOKKERENDE: intern duplikat — samme nr i flere aktive filer:"
  while IFS= read -r nr; do
    [ -z "$nr" ] && continue
    echo "  nr=$nr:"
    awk -F'\t' -v n="$nr" '$1==n{print "    - "$3" (status="$2")"}' "$active_file"
  done < "$dup_nrs_file"
fi

if [ -s "$reuse_file" ]; then
  exit_code=1
  echo "BLOKKERENDE: gjenbruk av pensjonert nr — et open-nr matcher RETIRED:"
  while IFS= read -r nr; do
    [ -z "$nr" ] && continue
    echo "  nr=$nr:"
    awk -F'\t' -v n="$nr" '$1==n && $2=="OPEN"{print "    - LIVE (status=open): "$3}' "$active_file"
    if grep -Fxq "$nr" "$done_file" 2>/dev/null; then
      awk -F'\t' -v n="$nr" '$1==n && $2=="DONE"{print "    - RETIRED (status=done): "$3}' "$active_file"
    fi
    if grep -Fxq "$nr" "$archive_file" 2>/dev/null; then
      echo "    - RETIRED (arkiv): $archive_path"
    fi
  done < "$reuse_file"
fi

if [ -s "$premature_file" ]; then
  echo "WARN: premature-archive (§6.3-kontraktbrudd) — PARKED-nr har allerede en arkiv-gravstein, gater IKKE:" >&2
  while IFS= read -r nr; do
    [ -z "$nr" ] && continue
    awk -F'\t' -v n="$nr" '$1==n && $2=="PARKED"{print "  WARN: nr="n" fil="$3" status="$2}' "$active_file" >&2
  done < "$premature_file"
fi

exit "$exit_code"
