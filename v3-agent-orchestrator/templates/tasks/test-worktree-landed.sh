#!/usr/bin/env bash
# Harness for tasks/worktree-landed.sh — fjorten konstruerte tilfeller (§ 7 V1) og et
# mutasjonskrok-punkt (§ 8 M1-M4, M9, M10). Se tasks/plans/todo-380-loopen-rydder-aldri-worktrees.md.
#
# Hver case bygger sitt EGET, disjunkte git-repo under mktemp -d — ingen delt tilstand mellom
# casene, og ALDRI mot dette prosjektets egne worktrees. C10a/b/c/d (env-delmengde, 380-
# oppfølging) bruker et EKTE `git worktree add` inne i sitt eget scratch-repo (i motsetning til
# C1-C9, som simulerer «treet» med en ren branch-bytte i samme katalog) — dette er nødvendig for
# at klassifikatorens `--git-common-dir`-basert `main_root`-oppslag faktisk skal peke på en
# ANNEN katalog enn selve treet, slik det gjør i en ekte agent-worktree.
#
# Bruk: tasks/test-worktree-landed.sh [--classifier <sti-til-worktree-landed.sh>] [--mutant M1|M2P|M3P|M4|M9|M10]
#
# --mutant appliserer én av § 8-mutasjonene (M1, M2', M3', M4, M9, M10) på en TEMP-kopi av
# klassifikatoren (originalen røres aldri) og kjører alle casene mot kopien. Skriptet bekrefter
# at mutasjonen faktisk endret filen (diff ikke-tom) FØR kjøringen telles — se lesson
# 2026-09-21 "verifiser at mutasjonen TRAFF".
#
# Utskrift: "CASE=<id> forventet=<0|1> faktisk=<n>" per case, "CASES_KJØRT=14" til slutt.
# Exit 0 kun hvis alle fjorten matcher forventet verdi. "HARNESS-FEIL:<...>" betyr at OPPSETTET
# feilet — det er IKKE et rødt case-resultat og teller ikke som bevis i noen retning.
set -uo pipefail

REPO_ROOT=$(git rev-parse --show-toplevel) || { echo "HARNESS-FEIL:oppsett:repo-root"; exit 2; }
CLASSIFIER="$REPO_ROOT/tasks/worktree-landed.sh"
MUTANT=""

while [ $# -gt 0 ]; do
  case "$1" in
    --classifier)
      CLASSIFIER="$2"
      shift 2
      ;;
    --mutant)
      MUTANT="$2"
      shift 2
      ;;
    *)
      echo "HARNESS-FEIL:oppsett:ukjent-flagg:$1"
      exit 2
      ;;
  esac
done

if [ ! -x "$CLASSIFIER" ]; then
  echo "HARNESS-FEIL:oppsett:klassifikator-ikke-kjorbar:$CLASSIFIER"
  exit 2
fi

MUT_WORKROOT=$(mktemp -d) || { echo "HARNESS-FEIL:oppsett:mktemp-mutant"; exit 2; }
trap 'rm -rf "$MUT_WORKROOT"' EXIT

if [ -n "$MUTANT" ]; then
  MUT_COPY="$MUT_WORKROOT/mutant-$MUTANT.sh"
  cp "$CLASSIFIER" "$MUT_COPY" || { echo "HARNESS-FEIL:oppsett:mutant-kopi"; exit 2; }
  case "$MUTANT" in
    M1)
      # Fjern innholdssøket (basenavn + blob) — en sti som ikke finnes i ref blir alltid KEEP.
      # Retning: falsk-KEEP. Rammer C4_omdoept_fil (forventet 0, skal bli 1). Tom-blobb-sjekken
      # (flyttet FØRST i fix-runde 1, R3) ligger FØR markøren under og påvirkes ikke.
      awk '
        $0 == "  # (a) basenavn-treff, deretter (b) blob-treff. Begge er LANDED-MOVED (fix-runde 1," {
          print "  keep \"sti-mangler:$p\""
          skip = 1
          next
        }
        skip && $0 == "  keep \"ingen-treff:$p\"" { skip = 0; next }
        skip { next }
        { print }
      ' "$CLASSIFIER" > "$MUT_COPY"
      ;;
    M2P)
      # Fjern tom-blobb-unntaket — datatap-retning. Rammer C7_tom_fil OG C7b (fix-runde 1,
      # R3: samme sjekk beskytter nå begge siden den flyttet FØR basenavn-fallbacken) —
      # begge forventet 1, skal bli 0.
      awk '
        $0 == "  if [ \"$blobsha\" = \"$EMPTY_BLOB\" ]; then" { skip = 1; next }
        skip && $0 == "  fi" { skip = 0; next }
        skip { next }
        { print }
      ' "$CLASSIFIER" > "$MUT_COPY"
      ;;
    M3P)
      # Fjern "sti finnes og avviker => endelig KEEP" — datatap-retning (tillater fallback).
      # Rammer C8_kit_speil (forventet 1, skal bli 0).
      awk '
        $0 == "    keep \"sti-finnes-avviker:$p\"" { next }
        { print }
      ' "$CLASSIFIER" > "$MUT_COPY"
      ;;
    M4)
      # Bytt innholdstesten på steg 1 med en ren ancestry-sjekk — falsk-KEEP-retning.
      # Rammer C2_squash_merget (forventet 0, skal bli 1).
      awk '
        $0 == "    if git -C \"$wt\" show \"$ref:$p\" | cmp -s - \"$wt/$p\"; then" {
          print "    if git -C \"$wt\" merge-base --is-ancestor HEAD \"$ref\"; then"
          next
        }
        { print }
      ' "$CLASSIFIER" > "$MUT_COPY"
      ;;
    M9)
      # Nøytraliser env_wt_is_safe_subset() til "alltid trygg", uansett innhold — datatap-
      # retning (380-oppfølging). Rammer C10b og C10c (begge forventet 1, skal bli 0).
      awk '
        $0 == "env_wt_is_safe_subset() {" {
          print
          print "  return 0 # MUTANT M9: alltid trygg, uansett innhold"
          skip = 1
          next
        }
        skip && $0 == "}" { skip = 0; print; next }
        skip { next }
        { print }
      ' "$CLASSIFIER" > "$MUT_COPY"
      ;;
    M10)
      # Gjeninnfør kommentar-unntaket i env-delmengde-sjekken (kode-review r1, punkt 1) —
      # datatap-retning. Rammer C10d (forventet 1, skal bli 0), øvrige upåvirket.
      awk '
        $0 == "      \"\") continue ;;" {
          print "      \"\"|\\#*) continue ;; # MUTANT M10: kommentar-unntak gjeninnfort"
          next
        }
        { print }
      ' "$CLASSIFIER" > "$MUT_COPY"
      ;;
    "")
      : ;;
    *)
      echo "HARNESS-FEIL:oppsett:ukjent-mutant:$MUTANT"
      exit 2
      ;;
  esac
  if [ -n "$MUTANT" ]; then
    chmod +x "$MUT_COPY"
    if diff -q "$CLASSIFIER" "$MUT_COPY" > /dev/null; then
      echo "HARNESS-FEIL:mutant-traff-ikke:$MUTANT"
      exit 2
    fi
    echo "--- mutant $MUTANT diff (bekrefter treff) ---"
    diff -u "$CLASSIFIER" "$MUT_COPY" || true
    echo "--- slutt diff ---"
    CLASSIFIER="$MUT_COPY"
  fi
fi

WORKROOT_RAW=$(mktemp -d) || { echo "HARNESS-FEIL:oppsett:mktemp"; exit 2; }
trap 'rm -rf "$WORKROOT_RAW" "$MUT_WORKROOT"' EXIT
# Fysisk sti, ikke literal /tmp/... — macOS /tmp er en symlink (lesson 2026-07-12).
WORKROOT=$(cd "$WORKROOT_RAW" && pwd -P)

git_ok() {
  d="$1"; shift
  if ! git -C "$d" "$@" > /dev/null; then
    return 1
  fi
}

seed_common() {
  d="$1"
  mkdir -p "$d" || return 1
  git_ok "$d" init -q -b {{BASE_BRANCH}} || return 1
  git -C "$d" config user.email "test@example.com" || return 1
  git -C "$d" config user.name "Test Harness" || return 1
  mkdir -p "$d/tasks/plans/archive" "$d/lib" "$d/v3-agent-orchestrator/templates/tasks" || return 1
  printf 'seed\n' > "$d/README.md"
  printf '' > "$d/.gitkeep-empty"
  printf 'value=42\n' > "$d/config.txt"
  printf 'will be moved\n' > "$d/mv-source.md"
  printf 'original graph builder v1\n' > "$d/tasks/graph-build.py"
  printf 'kit template mirrored body\n' > "$d/v3-agent-orchestrator/templates/tasks/graph-build.py"
  printf '*.secret\n' > "$d/.gitignore"
  git_ok "$d" add -A || return 1
  git_ok "$d" commit -q -m "seed" || return 1
  git_ok "$d" branch agent-work {{BASE_BRANCH}} || return 1
  git_ok "$d" checkout -q agent-work || return 1
}

# --- Case-byggere -------------------------------------------------------------

build_C1_untracked_identisk() {
  d="$1"
  seed_common "$d" || return 1
  git_ok "$d" checkout -q {{BASE_BRANCH}} || return 1
  printf 'hello\n' > "$d/notes.md"
  git_ok "$d" add notes.md || return 1
  git_ok "$d" commit -q -m "{{BASE_BRANCH}}: notes.md landet" || return 1
  git_ok "$d" checkout -q agent-work || return 1
  printf 'hello\n' > "$d/notes.md"
}

build_C2_squash_merget() {
  d="$1"
  seed_common "$d" || return 1
  git_ok "$d" checkout -q {{BASE_BRANCH}} || return 1
  printf 'squash content\n' > "$d/feature.md"
  git_ok "$d" add feature.md || return 1
  git_ok "$d" commit -q -m "{{BASE_BRANCH}}: feature.md squash-merget (fremmed commit)" || return 1
  git_ok "$d" checkout -q agent-work || return 1
  printf 'squash content\n' > "$d/feature.md"
  git_ok "$d" add feature.md || return 1
  git_ok "$d" commit -q -m "agent-work: samme innhold, egen commit" || return 1
}

build_C3_plan_flyttet_til_arkiv() {
  d="$1"
  seed_common "$d" || return 1
  git_ok "$d" checkout -q {{BASE_BRANCH}} || return 1
  printf 'plan content\n' > "$d/tasks/plans/archive/todo-99-old.md"
  git_ok "$d" add tasks/plans/archive/todo-99-old.md || return 1
  git_ok "$d" commit -q -m "{{BASE_BRANCH}}: plan arkivert" || return 1
  git_ok "$d" checkout -q agent-work || return 1
  # git prunet den nå-tomme tasks/plans/-katalogen ved forrige checkout (den fantes kun pga.
  # arkiv-fila som ikke er en del av agent-work) — gjenskap den før filskrivingen.
  mkdir -p "$d/tasks/plans" || return 1
  printf 'plan content\n' > "$d/tasks/plans/todo-99-old.md"
}

build_C4_omdoept_fil() {
  d="$1"
  seed_common "$d" || return 1
  git_ok "$d" checkout -q {{BASE_BRANCH}} || return 1
  printf 'shopping content\n' > "$d/lib/shoppingName.ts"
  git_ok "$d" add lib/shoppingName.ts || return 1
  git_ok "$d" commit -q -m "{{BASE_BRANCH}}: shoppingItems.ts omdoept til shoppingName.ts" || return 1
  git_ok "$d" checkout -q agent-work || return 1
  mkdir -p "$d/lib" || return 1
  printf 'shopping content\n' > "$d/lib/shoppingItems.ts"
}

build_C5_ekte_staged_arbeid() {
  d="$1"
  seed_common "$d" || return 1
  # mv-source.md finnes identisk i begge grener fra seed-committen. En staged `git mv` av en
  # ulandet fil (r2 VIKTIG-1) — med --no-renames skal dette IKKE unnslippe som en R-post.
  git_ok "$d" mv mv-source.md mv-target.md || return 1
}

build_C6_en_byte_forskjell() {
  d="$1"
  seed_common "$d" || return 1
  printf 'value=43\n' > "$d/config.txt"
}

build_C7_tom_fil() {
  d="$1"
  seed_common "$d" || return 1
  # .gitkeep-empty er allerede en tom fil i {{BASE_BRANCH}} (tom-blobben finnes altså i ref-treet).
  # new-empty-file.txt er en NY, tom, usporet fil på en sti som IKKE finnes i {{BASE_BRANCH}}.
  : > "$d/new-empty-file.txt"
}

build_C7b_tom_fil_kjent_basenavn() {
  d="$1"
  seed_common "$d" || return 1
  # {{BASE_BRANCH}} har en TOM, sporet fil `.gitkeep` på én sti. agent-work har en TOM, usporet fil med
  # SAMME basenavn på en ANNEN sti. cmp av to tomme filer er alltid "identisk" uansett om
  # innholdet faktisk har noe med hverandre å gjøre (fix-runde 1, R3/C7b) — uten at
  # tom-blobb-unntaket gjelder FØR basenavn-fallbacken, ville dette blitt LANDED via 2a.
  git_ok "$d" checkout -q {{BASE_BRANCH}} || return 1
  mkdir -p "$d/some/dir" || return 1
  : > "$d/some/dir/.gitkeep"
  git_ok "$d" add some/dir/.gitkeep || return 1
  git_ok "$d" commit -q -m "{{BASE_BRANCH}}: tom .gitkeep for å holde katalogen i git" || return 1
  git_ok "$d" checkout -q agent-work || return 1
  mkdir -p "$d/other/place" || return 1
  : > "$d/other/place/.gitkeep"
}

build_C8_kit_speil() {
  d="$1"
  seed_common "$d" || return 1
  # tasks/graph-build.py redigeres til å bli BYTE-IDENTISK med template-kopien — men
  # tasks/graph-build.py finnes SELV i {{BASE_BRANCH}}, med det opprinnelige (ikke-speilede) innholdet.
  printf 'kit template mirrored body\n' > "$d/tasks/graph-build.py"
}

build_C9_ignorert_utenfor_allowlist() {
  d="$1"
  seed_common "$d" || return 1
  printf 'leaked token\n' > "$d/private-notes.secret"
}

# --- C10a/b/c (380-oppfølging: env-delmengde) -----------------------------------
# Bruker EKTE `git worktree add` (se toppkommentaren) — "$d" er hovedsjekkuten ({{BASE_BRANCH}}-
# branch, ALDRI committert .env.local — akkurat som i et ekte repo), "$d/wt" er den
# lenkede worktreen (agent-work-branch) klassifikatoren faktisk kjøres mot.

seed_env_worktree() {
  d="$1"
  mkdir -p "$d" || return 1
  git_ok "$d" init -q -b {{BASE_BRANCH}} || return 1
  git -C "$d" config user.email "test@example.com" || return 1
  git -C "$d" config user.name "Test Harness" || return 1
  printf 'seed\n' > "$d/README.md"
  printf '.env.local\n.env.test\n' > "$d/.gitignore"
  git_ok "$d" add -A || return 1
  git_ok "$d" commit -q -m "seed" || return 1
  git_ok "$d" branch agent-work {{BASE_BRANCH}} || return 1
  # Hovedsjekkutens EGEN, gitignorerte .env.local — aldri committet, akkurat som i et
  # ekte repo. Inneholder en kommentarlinje og en blank linje, slik den ekte feilen
  # (koordinatorens funn) faktisk gjorde.
  printf '# kommentar\n\nEXPO_PUBLIC_SUPABASE_URL=https://example.supabase.co\nEXPO_PUBLIC_SUPABASE_ANON_KEY=anonkey123\nTEST_USER_EMAIL=test@example.com\n' > "$d/.env.local"
  git_ok "$d" worktree add -q "$d/wt" agent-work || return 1
}

build_C10a_env_delmengde_trygg() {
  d="$1"
  seed_env_worktree "$d" || return 1
  # Treets .env.local: bootstrap-worktree.sh sin allowlist-filtrerte delmengde — færre
  # nøkler, ingen kommentar/blank linje. Skal være TRYGT (forventet 0).
  printf 'EXPO_PUBLIC_SUPABASE_URL=https://example.supabase.co\nEXPO_PUBLIC_SUPABASE_ANON_KEY=anonkey123\n' > "$d/wt/.env.local"
}

build_C10b_env_verdi_endret() {
  d="$1"
  seed_env_worktree "$d" || return 1
  # Samme nøkkel som hovedfila, men ANNEN verdi — linjen finnes ikke ordrett i
  # hovedfila. Skal IKKE være trygt (forventet 1).
  printf 'EXPO_PUBLIC_SUPABASE_URL=https://example.supabase.co\nEXPO_PUBLIC_SUPABASE_ANON_KEY=et-annet-nokkelinnhold\n' > "$d/wt/.env.local"
}

build_C10c_env_ekstra_nokkel() {
  d="$1"
  seed_env_worktree "$d" || return 1
  # En nøkkel hovedfila ikke har i det hele tatt. Skal IKKE være trygt (forventet 1).
  printf 'EXPO_PUBLIC_SUPABASE_URL=https://example.supabase.co\nTEST_USER2_EMAIL=other@example.com\n' > "$d/wt/.env.local"
}

build_C10d_env_kommentar_avviker() {
  d="$1"
  seed_env_worktree "$d" || return 1
  # Kommentarlinje i treet som ikke finnes ordrett i hovedfila (kode-review r1, punkt 1 —
  # målt av revieweren: hovedfila A=1/B=2, treet A=1 + en kommentarlinje unik for treet, ga
  # tidligere LANDED:ok fordi kommentarer ble hoppet over). Skal IKKE være trygt (forventet 1)
  # — kun tomme linjer hoppes over, kommentarer matches som alle andre linjer.
  printf 'EXPO_PUBLIC_SUPABASE_URL=https://example.supabase.co\n#EXPO_PUBLIC_SUPABASE_ANON_KEY=PROD-UNIK-VERDI-kun-her\n' > "$d/wt/.env.local"
}

# --- Runner --------------------------------------------------------------------

all_ok=1
run_count=0

run_case() {
  id="$1"; expected="$2"; subdir="${3:-}"; must_contain="${4:-}"
  d="$WORKROOT/$id"
  rm -rf "$d"
  if ! "build_$id" "$d"; then
    echo "HARNESS-FEIL:oppsett-feilet:$id"
    all_ok=0
    run_count=$((run_count + 1))
    return
  fi
  target="$d"
  [ -n "$subdir" ] && target="$d/$subdir"
  out=$(bash "$CLASSIFIER" "$target" --ref {{BASE_BRANCH}})
  rc=$?
  printf '%s\n' "$out" | sed "s/^/[$id] /"
  echo "CASE=$id forventet=$expected faktisk=$rc"
  if [ "$rc" != "$expected" ]; then
    all_ok=0
  fi
  # kode-review r1, punkt 3 (MINDRE): for env-casene er en riktig rc IKKE nok bevis — en
  # klassifikator som ga rc=1 av en HELT ANNEN grunn (f.eks. status-D) ville også bestått.
  # Kreves derfor eksplisitt at utdata bærer den NAVNGITTE grunnen. Teller IKKE som en egen
  # case i run_count/CASES_KJØRT — det er et tilleggskrav på SAMME case.
  if [ -n "$must_contain" ]; then
    if printf '%s\n' "$out" | grep -qF -- "$must_contain"; then
      echo "CASE=$id-grunn forventet=1 faktisk=1"
    else
      echo "CASE=$id-grunn forventet=1 faktisk=0"
      all_ok=0
    fi
  fi
  run_count=$((run_count + 1))
}

run_case C1_untracked_identisk 0
run_case C2_squash_merget 0
run_case C3_plan_flyttet_til_arkiv 0
run_case C4_omdoept_fil 0
run_case C5_ekte_staged_arbeid 1
run_case C6_en_byte_forskjell 1
run_case C7_tom_fil 1
run_case C7b_tom_fil_kjent_basenavn 1
run_case C8_kit_speil 1
run_case C9_ignorert_utenfor_allowlist 1
run_case C10a_env_delmengde_trygg 0 wt
run_case C10b_env_verdi_endret 1 wt "KEEP:ignorert-env-avviker:.env.local"
run_case C10c_env_ekstra_nokkel 1 wt "KEEP:ignorert-env-avviker:.env.local"
run_case C10d_env_kommentar_avviker 1 wt "KEEP:ignorert-env-avviker:.env.local"

echo "CASES_KJØRT=$run_count"

if [ "$all_ok" -eq 1 ] && [ "$run_count" -eq 14 ]; then
  exit 0
fi
exit 1
