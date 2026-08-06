#!/bin/sh
# SCAFFOLDING — pre-merge todo-nr-kollisjonsgate mot MERGE-RESULTATET.
# Kopier til prosjektets scripts/ sammen med check-todo-nr-collisions.sh; kalles
# fra koordinator-runbookens §6.4 (gate b), som SISTE handling før `gh pr merge`.
#
# HVORFOR denne finnes: scripts/check-todo-nr-collisions.sh (uten --next) ser kun
# arbeidstreet ELLER en gitt ref — aldri hva de to blir SAMMEN. `--next` regner mot
# arbeidstree ∪ integrasjons-tippen, men to PR-er som velger nr FØR noen av dem har
# merget ser fortsatt ikke hverandre. Denne wrapperen bygger merge-TREET av
# `<base>` og `<branch>` (uten å faktisk merge noe), materialiserer `tasks/`-treet
# derfra i en midlertidig katalog, og kjører den eksisterende, rene checkeren mot
# DET treet. Det fanger PR-ens innkommende nr mot en fersk base — noe ingen av de to
# andre gatene strukturelt kan se.
#
# Krymper — LUKKER IKKE — TOCTOU-vinduet: gaten leser `<base>` på kjøretidspunktet,
# så vinduet er nå «fra gaten kjørte» i stedet for «fra branchen ble skåret». Ekte
# lukking krever branch-protection «require branches up to date» — kostnaden er
# full CI-runde per parallell merge i et repo med bevisst mange parallelle
# koordinatorer (se §6.4/§6g i coordinator-runbook.md for avveiningen). Kjør denne
# SOM SISTE handling før `gh pr merge` — ingen steg imellom; endres `<base>` i
# mellomtiden, kjør på nytt.
#
# Gate (a)-forholdet: `check-todo-nr-collisions.sh` i arbeidstreet (kjørt av
# runbookens §6.4-punkt a) dekker koordinatorens EGNE ucommitterte §6.3/§6b/§7-
# endringer på base-branchen — noe DENNE gaten (b) aldri ser, fordi merge-tree kun
# leser committede refs. De to er et TILLEGG til hverandre, ikke et alternativ:
# exit 2 fra (b) stopper uansett hva (a) sa.
#
# POSIX sh, macOS/BSD-trygt. Ingen GNU-only-flagg. Samme shell-kontrakt som
# check-todo-nr-collisions.sh.
#
# Modus:
#   sh scripts/check-todo-nr-premerge.sh <branch> [--base <ref>] [--no-fetch]
#
# <branch>  PR-branchens navn eller ref. Løses via origin/<branch> FØRST når fetch
#           lyktes (fersk er da mer pålitelig enn en ev. lokal ref med samme navn);
#           rått navn FØRST når --no-fetch eller fetch feilet (da vet vi ikke om
#           origin/<branch> i det hele tatt finnes/er fersk lokalt).
# --base    default ${TODO_NR_REF:-origin/dev} — samme env-navn som checkeren.
#           Juster defaulten til prosjektets faktiske base-branch, eller sett
#           TODO_NR_REF/--base ved kall. Krever en verdi; `--base` uten
#           påfølgende argument er en FEIL (exit 2).
# --no-fetch  hopp over `git fetch` (kun for tester/fixtures uten remote).
#
# MERK: materialiseringen bruker `git archive`, som respekterer export-ignore i .gitattributes.
# Har repoet en export-ignore som treffer tasks/, ser gaten FÆRRE filer enn merge-resultatet og
# kan feile ÅPENT. Hold tasks/ utenfor export-ignore.
#
# Exit-kontrakt (se også runbokens §6.4):
#   0  ingen kollisjon i merge-RESULTATET. ⚠️ Står det en WARN om fetch-svikt på
#      stderr («git fetch origin … feilet» lenger ned i scriptet), er basen
#      muligens foreldet — 0 er DA IKKE grønt. Les WARN-linja før du stoler på
#      exit-koden; dette er den dokumenterte kombinasjonen, ikke en uspesifisert
#      grense.
#   1  BLOKKERENDE kollisjon → ikke merge; se stdout for nr + kilder
#   2  intern feil (ukjent ref / git for gammel VED OPPSTART / uventet
#      `merge-tree`-exit — typisk ubeslektede historier (ingen felles merge-base)
#      eller et utilgjengelig objekt, IKKE en for gammel git siden versjonen alt er
#      verifisert på det tidspunktet / tasks/ mangler i treet) → ⚠️ STOPP, les
#      ALDRI som grønt
#   3  merge-konflikt (ikke en nr-kollisjon i seg selv) → §6.4-pausen gjelder,
#      sjekken ble ikke kjørt. UNNTAK (§6.4/renummererings-oppskriften): en
#      konfliktsti under tasks/todos/ MED SAMME nr+slug på begge sider ER en
#      nr-kollisjon (add/add på identisk sti, ulikt innhold); identisk innhold på
#      begge sider merges derimot rent og gir exit 0, ikke exit 3.
#
# ⚠️ set -u ALENE — ALDRI set -e: med set -e ville `git merge-tree`s rc 1
# (konflikt, en FORVENTET gren, ikke en scriptfeil) avbrutt wrapperen midt i og gitt
# feil exit-kode. rc fanges eksplisitt med `$?` rett etter hvert git/tar-kall.

set -u

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
check_script="$script_dir/check-todo-nr-collisions.sh"

branch=""
base=""
do_fetch=1

while [ $# -gt 0 ]; do
  case "$1" in
    --base)
      if [ $# -lt 2 ]; then
        printf 'FEIL: «--base» krever en verdi.\n' >&2
        exit 2
      fi
      base="$2"
      shift 2
      ;;
    --no-fetch)
      do_fetch=0
      shift
      ;;
    -*)
      printf 'FEIL: ukjent flagg «%s».\n' "$1" >&2
      exit 2
      ;;
    *)
      if [ -z "$branch" ]; then
        branch="$1"
      else
        printf 'FEIL: uventet ekstra argument «%s».\n' "$1" >&2
        exit 2
      fi
      shift
      ;;
  esac
done

if [ -z "$branch" ]; then
  printf 'Bruk: sh %s <branch> [--base <ref>] [--no-fetch]\n' "$0" >&2
  exit 2
fi

base=${base:-${TODO_NR_REF:-origin/dev}}

if [ ! -f "$check_script" ]; then
  printf 'FEIL: fant ikke %s.\n' "$check_script" >&2
  exit 2
fi

# --- Git-versjon: merge-tree --write-tree krever git >= 2.38 -----------------
git_version=$(git version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -n1)
if [ -z "$git_version" ]; then
  printf 'FEIL: fant ikke git.\n' >&2
  exit 2
fi
git_major=$(printf '%s' "$git_version" | cut -d. -f1)
git_minor=$(printf '%s' "$git_version" | cut -d. -f2)
if [ "$git_major" -lt 2 ] || { [ "$git_major" -eq 2 ] && [ "$git_minor" -lt 38 ]; }; then
  printf 'FEIL: krever git >= 2.38 (fant %s).\n' "$git_version" >&2
  exit 2
fi

# --- Ref-oppslag: rekkefølgen avhenger av om fetch lyktes --------------------
# fetch_ok=1 → origin/<arg> FØRST (fersk er mer pålitelig enn en ev. samnavnet
# lokal ref som fetch ikke rørte). fetch_ok=0 (--no-fetch ELLER fetch feilet) →
# rå <arg> FØRST — vi vet da ikke om origin/<arg> i det hele tatt finnes eller er
# fersk.
fetch_ok=0
resolve_ref() {
  arg="$1"
  if [ "$fetch_ok" -eq 1 ]; then
    if git rev-parse --verify "origin/${arg}^{commit}" >/dev/null 2>&1; then
      printf 'origin/%s' "$arg"
      return 0
    fi
    if git rev-parse --verify "${arg}^{commit}" >/dev/null 2>&1; then
      printf '%s' "$arg"
      return 0
    fi
    return 1
  fi
  if git rev-parse --verify "${arg}^{commit}" >/dev/null 2>&1; then
    printf '%s' "$arg"
    return 0
  fi
  if git rev-parse --verify "origin/${arg}^{commit}" >/dev/null 2>&1; then
    printf 'origin/%s' "$arg"
    return 0
  fi
  return 1
}

# --- Fersk-het: default fetch, WARN + fortsett hvis den feiler ---------------
if [ "$do_fetch" -eq 1 ]; then
  base_bare=${base#origin/}
  branch_bare=${branch#origin/}
  if git fetch origin "$base_bare" "$branch_bare" >/dev/null 2>&1; then
    fetch_ok=1
  else
    printf 'WARN: «git fetch origin %s %s» feilet — fortsetter med lokale refs (kan være foreldet).\n' \
      "$base_bare" "$branch_bare" >&2
  fi
fi

branch_ref=$(resolve_ref "$branch") || {
  printf 'FEIL: fant ikke branch-ref «%s» (verken lokalt eller som origin/%s).\n' "$branch" "$branch" >&2
  exit 2
}
base_ref=$(resolve_ref "$base") || {
  printf 'FEIL: fant ikke base-ref «%s» (verken lokalt eller som origin/%s).\n' "$base" "$base" >&2
  exit 2
}

base_sha=$(git rev-parse "$base_ref" 2>/dev/null)
branch_sha=$(git rev-parse "$branch_ref" 2>/dev/null)

# --- Materialiser i mktemp FØR merge-tree, så konflikt-output kan lagres der -
tmp_dir=$(mktemp -d) || exit 2
trap 'rm -rf "$tmp_dir"' EXIT

# --- Merge-resultat: bygg treet uten å faktisk merge noe ---------------------
# `git merge-tree --write-tree` skriver ALT (tree-OID på rc=0; tree-OID +
# konflikt-detaljer på rc=1) til STDOUT, aldri stderr — fanges i en fil så vi kan
# lese tree-OID (linje 1) ved rc=0 og videresende hele konflikt-teksten til stderr
# ved rc=1, uten en pipe (se header — pipe ville svelget denne rc-en også).
mt_out="$tmp_dir/merge-tree.out"
git merge-tree --write-tree "$base_ref" "$branch_ref" >"$mt_out" 2>&1
mt_rc=$?

if [ "$mt_rc" -eq 1 ]; then
  printf 'MERGE-KONFLIKT mellom %s (%s) og %s (%s) — sjekken ble IKKE kjørt.\n' \
    "$base_ref" "$base_sha" "$branch_ref" "$branch_sha" >&2
  printf 'Se §6.4 i coordinator-runbook: konfliktstier under tasks/todos/ med SAMME nr+slug\n' >&2
  printf 'på begge sider ER en nr-kollisjon (identisk innhold merges rent og gir exit 0).\n' >&2
  cat "$mt_out" >&2
  exit 3
fi

if [ "$mt_rc" -gt 1 ]; then
  # git-versjonen er ALT verifisert >= 2.38 ovenfor — en uventet rc her er derfor
  # IKKE en for gammel git. Typisk ubeslektede historier (ingen felles merge-base)
  # eller et utilgjengelig objekt; se git-outputen under.
  printf 'FEIL: «git merge-tree --write-tree» ga uventet exit %s — typisk ubeslektede\n' "$mt_rc" >&2
  printf 'historier (ingen felles merge-base) eller et utilgjengelig objekt. Se git-outputen under.\n' >&2
  cat "$mt_out" >&2
  exit 2
fi

tree=$(head -n1 "$mt_out")
if [ -z "$tree" ]; then
  printf 'FEIL: «git merge-tree --write-tree» ga tomt tree-OID.\n' >&2
  exit 2
fi
if ! printf '%s\n' "$tree" | grep -Eq '^[0-9a-f]{40,64}$'; then
  printf 'FEIL: «git merge-tree --write-tree» sin førstelinje er ikke et gyldig tree-OID: «%s».\n' "$tree" >&2
  cat "$mt_out" >&2
  exit 2
fi

git archive -o "$tmp_dir/tasks.tar" "$tree" tasks
archive_rc=$?
if [ "$archive_rc" -ne 0 ]; then
  printf 'FEIL: «git archive» av tasks/ fra tre %s feilet (rc=%s) — tasks/ mangler i treet?\n' \
    "$tree" "$archive_rc" >&2
  exit 2
fi

tar -xf "$tmp_dir/tasks.tar" -C "$tmp_dir"
tar_rc=$?
if [ "$tar_rc" -ne 0 ]; then
  printf 'FEIL: utpakking av tasks.tar feilet (rc=%s).\n' "$tar_rc" >&2
  exit 2
fi

if [ ! -d "$tmp_dir/tasks/todos" ]; then
  printf 'FEIL: tasks/todos finnes ikke i merge-treet %s.\n' "$tree" >&2
  exit 2
fi

printf 'INFO: base=%s (%s) branch=%s (%s) tree=%s\n' \
  "$base_ref" "$base_sha" "$branch_ref" "$branch_sha" "$tree" >&2

(cd "$tmp_dir" && sh "$check_script")
exit $?
